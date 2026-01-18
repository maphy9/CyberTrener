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
    POSE_RIGHT_WRIST, POSE_LEFT_WRIST
]

PROFILE_REQUIRED_LANDMARKS = [
    POSE_RIGHT_SHOULDER, POSE_LEFT_SHOULDER,
    POSE_RIGHT_ELBOW, POSE_RIGHT_WRIST,
    POSE_RIGHT_HIP, POSE_LEFT_HIP
]

_front_smoothers = {
    'right_angle': AdaptiveSmoother(base_smoothing=0.3, velocity_threshold=8.0),
    'left_angle': AdaptiveSmoother(base_smoothing=0.3, velocity_threshold=8.0),
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


def reset_front_view_state():
    for smoother in _front_smoothers.values():
        smoother.reset()
    _front_phase_detector.reset()


def reset_profile_view_state():
    for smoother in _profile_smoothers.values():
        smoother.reset()
    _profile_phase_detector.reset()


def calculate_front_view(results, history):
    landmarks = extract_pose_landmarks(results)
    if not landmarks:
        return None
    
    if not check_landmarks_visible(landmarks, FRONT_REQUIRED_LANDMARKS):
        return None
    
    prev = history[-1] if history else {}
    
    confidence = get_landmark_confidence(landmarks, FRONT_REQUIRED_LANDMARKS)
    
    right_shoulder = landmarks[POSE_RIGHT_SHOULDER]
    left_shoulder = landmarks[POSE_LEFT_SHOULDER]
    right_elbow = landmarks[POSE_RIGHT_ELBOW]
    left_elbow = landmarks[POSE_LEFT_ELBOW]
    right_wrist = landmarks[POSE_RIGHT_WRIST]
    left_wrist = landmarks[POSE_LEFT_WRIST]

    # Calculate angles for both arms
    right_angle_raw = calculate_angle(right_shoulder, right_elbow, right_wrist)
    left_angle_raw = calculate_angle(left_shoulder, left_elbow, left_wrist)
    
    right_angle_smooth = _front_smoothers['right_angle'].update(right_angle_raw)
    left_angle_smooth = _front_smoothers['left_angle'].update(left_angle_raw)
    
    # Use average angle for synchronized movement
    avg_angle = (right_angle_smooth + left_angle_smooth) / 2
    
    # Calculate arm synchronization
    arm_sync_diff = abs(right_angle_smooth - left_angle_smooth)
    
    # Phase detection based on average angle
    phase = _front_phase_detector.update(avg_angle)
    
    # Rep counting
    reps = prev.get('reps', 0)
    rep_flag = prev.get('rep_flag', False)
    
    if phase == 'extended' and _front_phase_detector.is_stable(STABILITY_FRAMES):
        rep_flag = True
    elif phase == 'flexed' and rep_flag and _front_phase_detector.is_stable(STABILITY_FRAMES):
        reps += 1
        rep_flag = False
    
    return {
        'right_angle': round(right_angle_smooth or 0, 1),
        'left_angle': round(left_angle_smooth or 0, 1),
        'avg_angle': round(avg_angle or 0, 1),
        'arm_sync_diff': round(arm_sync_diff or 0, 1),
        'reps': reps,
        'phase': phase,
        'rep_flag': rep_flag,
        'right_velocity': _front_smoothers['right_angle'].get_velocity(),
        'left_velocity': _front_smoothers['left_angle'].get_velocity(),
        'confidence': round(confidence, 2),
    }


def calculate_profile_view(results, history):
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
    
    # Arm angle
    right_angle_raw = calculate_angle(right_shoulder, right_elbow, right_wrist)
    right_angle_smooth = _profile_smoothers['right_angle'].update(right_angle_raw)
    
    # Trunk angle (body posture)
    shoulder_mid = ((right_shoulder[0] + left_shoulder[0]) / 2, 
                    (right_shoulder[1] + left_shoulder[1]) / 2)
    hip_mid = ((right_hip[0] + left_hip[0]) / 2,
               (right_hip[1] + left_hip[1]) / 2)
    
    trunk_angle_raw = calculate_trunk_angle(shoulder_mid, hip_mid)
    trunk_angle_smooth = _profile_smoothers['trunk_angle'].update(trunk_angle_raw)
    
    # Elbow forward angle (shoulder-elbow-hip)
    elbow_forward_angle = calculate_angle(right_shoulder, right_elbow, right_hip)
    
    # Phase detection
    phase = _profile_phase_detector.update(right_angle_smooth)
    
    # Rep counting
    reps = prev.get('reps', 0)
    rep_flag = prev.get('rep_flag', False)
    
    if phase == 'extended' and _profile_phase_detector.is_stable(STABILITY_FRAMES):
        rep_flag = True
    elif phase == 'flexed' and rep_flag and _profile_phase_detector.is_stable(STABILITY_FRAMES):
        reps += 1
        rep_flag = False
    
    return {
        'right_angle': round(right_angle_smooth or 0, 1),
        'reps': reps,
        'phase': phase,
        'trunk_angle': round(trunk_angle_smooth or 0, 1),
        'elbow_forward_angle': round(elbow_forward_angle or 0, 1),
        'rep_flag': rep_flag,
        'right_velocity': _profile_smoothers['right_angle'].get_velocity(),
        'trunk_velocity': _profile_smoothers['trunk_angle'].get_velocity(),
        'confidence': round(confidence, 2),
    }