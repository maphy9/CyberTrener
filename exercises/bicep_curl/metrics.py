from core.calculations import (
    extract_pose_landmarks,
    get_landmark_confidence,
    check_landmarks_visible,
    calculate_angle,
    calculate_arm_verticality,
    calculate_elbow_to_torso_distance,
    calculate_wrist_to_shoulder_distance,
    calculate_trunk_angle,
    AdaptiveSmoother,
    PhaseDetector,
    detect_phase_with_hysteresis
)
from core.constants import *
from exercises.bicep_curl.constants import *


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
    'right_elbow_dist': AdaptiveSmoother(base_smoothing=0.4, velocity_threshold=0.05),
    'left_elbow_dist': AdaptiveSmoother(base_smoothing=0.4, velocity_threshold=0.05),
    'right_wrist_dist': AdaptiveSmoother(base_smoothing=0.35, velocity_threshold=0.03),
    'left_wrist_dist': AdaptiveSmoother(base_smoothing=0.35, velocity_threshold=0.03),
}

_front_phase_detectors = {
    'right': PhaseDetector(flex_threshold=FRONT_FLEX_THRESHOLD, extend_threshold=FRONT_EXTEND_THRESHOLD, hysteresis=10),
    'left': PhaseDetector(flex_threshold=FRONT_FLEX_THRESHOLD, extend_threshold=FRONT_EXTEND_THRESHOLD, hysteresis=10),
}

_profile_smoothers = {
    'right_angle': AdaptiveSmoother(base_smoothing=0.3, velocity_threshold=8.0),
    'trunk_angle': AdaptiveSmoother(base_smoothing=0.4, velocity_threshold=3.0),
    'right_wrist_dist': AdaptiveSmoother(base_smoothing=0.35, velocity_threshold=0.03),
}

_profile_phase_detector = PhaseDetector(
    flex_threshold=PROFILE_FLEX_THRESHOLD, 
    extend_threshold=PROFILE_EXTEND_THRESHOLD, 
    hysteresis=10
)


def reset_front_view_state():
    """Resetuje stan filtrów i detektorów (widok przód)."""
    for smoother in _front_smoothers.values():
        smoother.reset()
    for detector in _front_phase_detectors.values():
        detector.reset()


def reset_profile_view_state():
    """Resetuje stan filtrów i detektorów (widok profil)."""
    for smoother in _profile_smoothers.values():
        smoother.reset()
    _profile_phase_detector.reset()


def calculate_front_view(results, history):
    """Liczy metryki z widoku przodu dla uginania."""
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

    right_angle_raw = calculate_angle(right_shoulder, right_elbow, right_wrist)
    left_angle_raw = calculate_angle(left_shoulder, left_elbow, left_wrist)
    
    right_angle_smooth = _front_smoothers['right_angle'].update(right_angle_raw)
    left_angle_smooth = _front_smoothers['left_angle'].update(left_angle_raw)
    
    right_verticality = calculate_arm_verticality(right_shoulder, right_elbow)
    left_verticality = calculate_arm_verticality(left_shoulder, left_elbow)
    
    right_dist_raw = calculate_elbow_to_torso_distance(right_elbow, right_shoulder, left_shoulder)
    left_dist_raw = calculate_elbow_to_torso_distance(left_elbow, right_shoulder, left_shoulder)
    
    right_elbow_dist_smooth = _front_smoothers['right_elbow_dist'].update(right_dist_raw)
    left_elbow_dist_smooth = _front_smoothers['left_elbow_dist'].update(left_dist_raw)
    
    right_wrist_dist_raw = calculate_wrist_to_shoulder_distance(right_wrist, right_shoulder)
    left_wrist_dist_raw = calculate_wrist_to_shoulder_distance(left_wrist, left_shoulder)
    
    right_wrist_dist_smooth = _front_smoothers['right_wrist_dist'].update(right_wrist_dist_raw)
    left_wrist_dist_smooth = _front_smoothers['left_wrist_dist'].update(left_wrist_dist_raw)
    
    right_phase = _front_phase_detectors['right'].update(right_angle_smooth)
    left_phase = _front_phase_detectors['left'].update(left_angle_smooth)
    
    right_reps = prev.get('right_reps', 0)
    right_rep_flag = prev.get('right_rep_flag', False)
    right_stance_valid = prev.get('right_stance_valid', True)
    
    if right_phase == 'extended' and not right_rep_flag:
        right_stance_valid = True
    
    if right_verticality > VERTICAL_STANCE_THRESHOLD:
        right_stance_valid = False
    
    if right_phase == 'flexed' and _front_phase_detectors['right'].is_stable(3):
        right_rep_flag = True
    elif right_phase == 'extended' and right_rep_flag and _front_phase_detectors['right'].is_stable(3):
        right_reps += 1
        right_rep_flag = False
    
    left_reps = prev.get('left_reps', 0)
    left_rep_flag = prev.get('left_rep_flag', False)
    left_stance_valid = prev.get('left_stance_valid', True)
    
    if left_phase == 'extended' and not left_rep_flag:
        left_stance_valid = True
    
    if left_verticality > VERTICAL_STANCE_THRESHOLD:
        left_stance_valid = False
    
    if left_phase == 'flexed' and _front_phase_detectors['left'].is_stable(3):
        left_rep_flag = True
    elif left_phase == 'extended' and left_rep_flag and _front_phase_detectors['left'].is_stable(3):
        left_reps += 1
        left_rep_flag = False
    
    return {
        'right_angle': round(right_angle_smooth or 0, 1),
        'left_angle': round(left_angle_smooth or 0, 1),
        'right_reps': right_reps,
        'left_reps': left_reps,
        'right_phase': right_phase,
        'left_phase': left_phase,
        'right_elbow_dist': round(right_elbow_dist_smooth or 0, 3),
        'left_elbow_dist': round(left_elbow_dist_smooth or 0, 3),
        'right_wrist_dist': round(right_wrist_dist_smooth or 0, 3),
        'left_wrist_dist': round(left_wrist_dist_smooth or 0, 3),
        'right_verticality': round(right_verticality or 0, 1),
        'left_verticality': round(left_verticality or 0, 1),
        'right_stance_valid': right_stance_valid,
        'left_stance_valid': left_stance_valid,
        'right_angle_smooth': right_angle_smooth,
        'left_angle_smooth': left_angle_smooth,
        'right_elbow_dist_smooth': right_elbow_dist_smooth,
        'left_elbow_dist_smooth': left_elbow_dist_smooth,
        'right_wrist_dist_smooth': right_wrist_dist_smooth,
        'left_wrist_dist_smooth': left_wrist_dist_smooth,
        'right_rep_flag': right_rep_flag,
        'left_rep_flag': left_rep_flag,
        'right_velocity': _front_smoothers['right_angle'].get_velocity(),
        'left_velocity': _front_smoothers['left_angle'].get_velocity(),
        'confidence': round(confidence, 2),
    }


def calculate_profile_view(results, history):
    """Liczy metryki z widoku profilu dla uginania."""
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
    
    right_wrist_dist_raw = calculate_wrist_to_shoulder_distance(right_wrist, right_shoulder)
    right_wrist_dist_smooth = _profile_smoothers['right_wrist_dist'].update(right_wrist_dist_raw)
    
    shoulder_mid = ((right_shoulder[0] + left_shoulder[0]) / 2, 
                    (right_shoulder[1] + left_shoulder[1]) / 2)
    hip_mid = ((right_hip[0] + left_hip[0]) / 2,
               (right_hip[1] + left_hip[1]) / 2)
    
    trunk_angle_raw = calculate_trunk_angle(shoulder_mid, hip_mid)
    trunk_angle_smooth = _profile_smoothers['trunk_angle'].update(trunk_angle_raw)
    
    right_phase = _profile_phase_detector.update(right_angle_smooth)
    
    right_reps = prev.get('right_reps', 0)
    right_rep_flag = prev.get('right_rep_flag', False)
    
    if right_phase == 'flexed' and _profile_phase_detector.is_stable(3):
        right_rep_flag = True
    elif right_phase == 'extended' and right_rep_flag and _profile_phase_detector.is_stable(3):
        right_reps += 1
        right_rep_flag = False
    
    return {
        'right_angle': round(right_angle_smooth or 0, 1),
        'right_reps': right_reps,
        'right_phase': right_phase,
        'trunk_angle': round(trunk_angle_smooth or 0, 1),
        'right_wrist_dist': round(right_wrist_dist_smooth or 0, 3),
        'right_angle_smooth': right_angle_smooth,
        'trunk_angle_smooth': trunk_angle_smooth,
        'right_wrist_dist_smooth': right_wrist_dist_smooth,
        'right_rep_flag': right_rep_flag,
        'right_velocity': _profile_smoothers['right_angle'].get_velocity(),
        'trunk_velocity': _profile_smoothers['trunk_angle'].get_velocity(),
        'confidence': round(confidence, 2),
    }