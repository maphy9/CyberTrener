from core.calculations import (
    extract_pose_landmarks,
    get_landmark_confidence,
    check_landmarks_visible,
    calculate_angle,
    calculate_trunk_angle,
    AdaptiveSmoother,
    PhaseDetector
)
from core.constants import *
from exercises.overhead_press.constants import *

FRONT_REQUIRED_LANDMARKS = [
    POSE_RIGHT_SHOULDER, POSE_LEFT_SHOULDER,
    POSE_RIGHT_ELBOW, POSE_LEFT_ELBOW,
    POSE_RIGHT_WRIST, POSE_LEFT_WRIST,
    POSE_RIGHT_HIP, POSE_LEFT_HIP,
    POSE_NOSE
]

PROFILE_REQUIRED_LANDMARKS = [
    POSE_RIGHT_SHOULDER, POSE_LEFT_SHOULDER,
    POSE_RIGHT_ELBOW, POSE_RIGHT_WRIST,
    POSE_RIGHT_HIP, POSE_LEFT_HIP
]

_front_smoothers = {
    'right_angle': AdaptiveSmoother(base_smoothing=0.3, velocity_threshold=8.0),
    'left_angle': AdaptiveSmoother(base_smoothing=0.3, velocity_threshold=8.0),
    'right_wrist_y': AdaptiveSmoother(base_smoothing=0.3, velocity_threshold=0.05),
    'left_wrist_y': AdaptiveSmoother(base_smoothing=0.3, velocity_threshold=0.05),
}

_front_phase_detector = PhaseDetector(
    flex_threshold=FRONT_FLEX_THRESHOLD,
    extend_threshold=FRONT_EXTEND_THRESHOLD,
    hysteresis=15
)

_profile_smoothers = {
    'right_angle': AdaptiveSmoother(base_smoothing=0.3, velocity_threshold=8.0),
    'trunk_angle': AdaptiveSmoother(base_smoothing=0.4, velocity_threshold=3.0),
}

_profile_phase_detector = PhaseDetector(
    flex_threshold=PROFILE_FLEX_THRESHOLD,
    extend_threshold=PROFILE_EXTEND_THRESHOLD,
    hysteresis=15
)

_active_zone_state = {
    'in_active_zone': False,
    'entered_start_position': False,
    'frames_in_start_position': 0,
    'frames_in_active_zone': 0,
}


def reset_front_view_state():
    """Resetuje stan filtrów i strefy aktywnej (przód)."""
    global _active_zone_state
    for smoother in _front_smoothers.values():
        smoother.reset()
    _front_phase_detector.reset()
    _active_zone_state = {
        'in_active_zone': False,
        'entered_start_position': False,
        'frames_in_start_position': 0,
        'frames_in_active_zone': 0,
    }


def reset_profile_view_state():
    """Resetuje stan filtrów i detektora (profil)."""
    for smoother in _profile_smoothers.values():
        smoother.reset()
    _profile_phase_detector.reset()


def _check_in_active_zone(right_wrist_y, left_wrist_y, right_shoulder_y, left_shoulder_y, avg_angle, calibration=None):
    """Sprawdza wejście do aktywnej strefy ruchu."""
    global _active_zone_state
    
    avg_wrist_y = (right_wrist_y + left_wrist_y) / 2
    avg_shoulder_y = (right_shoulder_y + left_shoulder_y) / 2
    
    wrists_above_shoulders = avg_wrist_y < (avg_shoulder_y + SHOULDER_Y_OFFSET)
    
    in_start_position = wrists_above_shoulders and avg_angle < 120
    
    if wrists_above_shoulders:
        _active_zone_state['frames_in_active_zone'] += 1
        if _active_zone_state['frames_in_active_zone'] >= STABILITY_FRAMES:
            _active_zone_state['in_active_zone'] = True
    else:
        _active_zone_state['frames_in_active_zone'] = 0
        _active_zone_state['in_active_zone'] = False
    
    return _active_zone_state['in_active_zone'], in_start_position


def calculate_front_view(results, history, calibration=None):
    """Liczy metryki z widoku przodu dla OHP."""
    landmarks = extract_pose_landmarks(results)
    if not landmarks:
        return None
    
    basic_landmarks = [
        POSE_RIGHT_SHOULDER, POSE_LEFT_SHOULDER,
        POSE_RIGHT_ELBOW, POSE_LEFT_ELBOW,
        POSE_RIGHT_WRIST, POSE_LEFT_WRIST
    ]
    if not check_landmarks_visible(landmarks, basic_landmarks):
        return None
    
    prev = history[-1] if history else {}
    
    confidence = get_landmark_confidence(landmarks, basic_landmarks)
    
    right_shoulder = landmarks[POSE_RIGHT_SHOULDER]
    left_shoulder = landmarks[POSE_LEFT_SHOULDER]
    right_elbow = landmarks[POSE_RIGHT_ELBOW]
    left_elbow = landmarks[POSE_LEFT_ELBOW]
    right_wrist = landmarks[POSE_RIGHT_WRIST]
    left_wrist = landmarks[POSE_LEFT_WRIST]

    right_angle_raw = calculate_angle(right_shoulder, right_elbow, right_wrist)
    left_angle_raw = calculate_angle(left_shoulder, left_elbow, left_wrist)
    
    right_angle_smooth = _front_smoothers['right_angle'].update(right_angle_raw)
    left_angle_smooth = _front_smoothers['left_angle'].update(left_angle_raw)
    
    avg_angle = (right_angle_smooth + left_angle_smooth) / 2
    
    right_wrist_y_smooth = _front_smoothers['right_wrist_y'].update(right_wrist[1])
    left_wrist_y_smooth = _front_smoothers['left_wrist_y'].update(left_wrist[1])
    
    arm_sync_diff = abs(right_angle_smooth - left_angle_smooth)
    wrist_y_diff = abs(right_wrist_y_smooth - left_wrist_y_smooth)
    
    in_active_zone, in_start_position = _check_in_active_zone(
        right_wrist_y_smooth, left_wrist_y_smooth,
        right_shoulder[1], left_shoulder[1],
        avg_angle, calibration
    )
    
    phase = _front_phase_detector.update(avg_angle)
    
    reps = prev.get('reps', 0)
    rep_flag = prev.get('rep_flag', False)
    
    if in_active_zone:
        if phase == 'extended' and _front_phase_detector.is_stable(STABILITY_FRAMES):
            rep_flag = True
        elif phase == 'flexed' and rep_flag and _front_phase_detector.is_stable(STABILITY_FRAMES):
            reps += 1
            rep_flag = False
    else:
        rep_flag = False
    
    return {
        'right_angle': round(right_angle_smooth or 0, 1),
        'left_angle': round(left_angle_smooth or 0, 1),
        'avg_angle': round(avg_angle or 0, 1),
        'arm_sync_diff': round(arm_sync_diff or 0, 1),
        'wrist_y_diff': round(wrist_y_diff or 0, 3),
        'reps': reps,
        'phase': phase,
        'rep_flag': rep_flag,
        'right_velocity': _front_smoothers['right_angle'].get_velocity(),
        'left_velocity': _front_smoothers['left_angle'].get_velocity(),
        'confidence': round(confidence, 2),
        'in_active_zone': in_active_zone,
        'in_start_position': in_start_position,
        'right_wrist_y': round(right_wrist_y_smooth, 3),
        'left_wrist_y': round(left_wrist_y_smooth, 3),
        'right_shoulder_y': round(right_shoulder[1], 3),
        'left_shoulder_y': round(left_shoulder[1], 3),
    }


def calculate_profile_view(results, history, calibration=None):
    """Liczy metryki z widoku profilu dla OHP."""
    landmarks = extract_pose_landmarks(results)
    if not landmarks:
        return None
    
    if not check_landmarks_visible(landmarks, PROFILE_REQUIRED_LANDMARKS):
        return None
    
    prev = history[-1] if history else {}
    
    confidence = get_landmark_confidence(landmarks, PROFILE_REQUIRED_LANDMARKS)
        
    right_shoulder = landmarks[POSE_RIGHT_SHOULDER]
    left_shoulder = landmarks[POSE_LEFT_SHOULDER]
    right_elbow = landmarks[POSE_RIGHT_ELBOW]
    right_wrist = landmarks[POSE_RIGHT_WRIST]
    right_hip = landmarks[POSE_RIGHT_HIP]
    left_hip = landmarks[POSE_LEFT_HIP]
    
    right_angle_raw = calculate_angle(right_shoulder, right_elbow, right_wrist)
    right_angle_smooth = _profile_smoothers['right_angle'].update(right_angle_raw)
    
    shoulder_mid = ((right_shoulder[0] + left_shoulder[0]) / 2, 
                    (right_shoulder[1] + left_shoulder[1]) / 2)
    hip_mid = ((right_hip[0] + left_hip[0]) / 2,
               (right_hip[1] + left_hip[1]) / 2)
    
    trunk_angle_raw = calculate_trunk_angle(shoulder_mid, hip_mid)
    trunk_angle_smooth = _profile_smoothers['trunk_angle'].update(trunk_angle_raw)
    
    neutral_trunk = 180
    if calibration:
        neutral_trunk = calibration.neutral_trunk_angle
    trunk_deviation = abs(trunk_angle_smooth - neutral_trunk)
    
    elbow_forward_angle = calculate_angle(right_shoulder, right_elbow, right_hip)
    
    phase = _profile_phase_detector.update(right_angle_smooth)
    
    reps = prev.get('reps', 0)
    rep_flag = prev.get('rep_flag', False)
    
    wrist_above_shoulder = right_wrist[1] < (right_shoulder[1] + SHOULDER_Y_OFFSET)
    
    if wrist_above_shoulder:
        if REP_COUNT_AT_TOP:
            if phase == 'flexed' and _profile_phase_detector.is_stable(STABILITY_FRAMES):
                rep_flag = True
            elif phase == 'extended' and rep_flag and _profile_phase_detector.is_stable(STABILITY_FRAMES):
                reps += 1
                rep_flag = False
        else:
            if phase == 'extended' and _profile_phase_detector.is_stable(STABILITY_FRAMES):
                rep_flag = True
            elif phase == 'flexed' and rep_flag and _profile_phase_detector.is_stable(STABILITY_FRAMES):
                reps += 1
                rep_flag = False
    else:
        rep_flag = False
    
    return {
        'right_angle': round(right_angle_smooth or 0, 1),
        'reps': reps,
        'phase': phase,
        'trunk_angle': round(trunk_angle_smooth or 0, 1),
        'trunk_deviation': round(trunk_deviation, 1),
        'elbow_forward_angle': round(elbow_forward_angle or 0, 1),
        'rep_flag': rep_flag,
        'right_velocity': _profile_smoothers['right_angle'].get_velocity(),
        'trunk_velocity': _profile_smoothers['trunk_angle'].get_velocity(),
        'confidence': round(confidence, 2),
        'wrist_above_shoulder': wrist_above_shoulder,
    }