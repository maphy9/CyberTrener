from calculations import *
from constants import *


def calculate_front_bicep_curl(results, history):
    landmarks = extract_pose_landmarks(results)
    if not landmarks:
        return None
    
    prev = history[-1] if history else {}
    
    right_shoulder = landmarks[POSE_RIGHT_SHOULDER]
    left_shoulder = landmarks[POSE_LEFT_SHOULDER]
    right_elbow = landmarks[POSE_RIGHT_ELBOW]
    left_elbow = landmarks[POSE_LEFT_ELBOW]
    right_wrist = landmarks[POSE_RIGHT_WRIST]
    left_wrist = landmarks[POSE_LEFT_WRIST]

    right_angle_raw = calculate_angle(right_shoulder, right_elbow, right_wrist)
    left_angle_raw = calculate_angle(left_shoulder, left_elbow, left_wrist)
    
    right_angle_smooth = smooth_value(right_angle_raw, prev.get('right_angle_smooth'), FRONT_ANGLE_SMOOTHING)
    left_angle_smooth = smooth_value(left_angle_raw, prev.get('left_angle_smooth'), FRONT_ANGLE_SMOOTHING)
    
    right_verticality = calculate_arm_verticality(right_shoulder, right_elbow)
    left_verticality = calculate_arm_verticality(left_shoulder, left_elbow)
    
    right_dist_raw = calculate_elbow_to_torso_distance(right_elbow, right_shoulder, left_shoulder)
    left_dist_raw = calculate_elbow_to_torso_distance(left_elbow, right_shoulder, left_shoulder)
    
    right_elbow_dist_smooth = smooth_value(right_dist_raw, prev.get('right_elbow_dist_smooth'), FRONT_ELBOW_DIST_SMOOTHING)
    left_elbow_dist_smooth = smooth_value(left_dist_raw, prev.get('left_elbow_dist_smooth'), FRONT_ELBOW_DIST_SMOOTHING)
    
    right_wrist_dist_raw = calculate_wrist_to_shoulder_distance(right_wrist, right_shoulder)
    left_wrist_dist_raw = calculate_wrist_to_shoulder_distance(left_wrist, left_shoulder)
    
    right_wrist_dist_smooth = smooth_value(right_wrist_dist_raw, prev.get('right_wrist_dist_smooth'), FRONT_WRIST_DIST_SMOOTHING)
    left_wrist_dist_smooth = smooth_value(left_wrist_dist_raw, prev.get('left_wrist_dist_smooth'), FRONT_WRIST_DIST_SMOOTHING)
    
    right_phase_detected = detect_phase(right_angle_smooth, FRONT_FLEX_THRESHOLD, FRONT_EXTEND_THRESHOLD)
    left_phase_detected = detect_phase(left_angle_smooth, FRONT_FLEX_THRESHOLD, FRONT_EXTEND_THRESHOLD)
    
    right_phase = prev.get('right_phase', 'unknown')
    right_phase_count = prev.get('right_phase_count', 0)
    right_prev_phase = prev.get('right_prev_phase', 'unknown')
    
    if right_phase_detected == 'middle':
        right_phase = 'middle'
    elif right_phase_detected == right_prev_phase:
        right_phase_count += 1
        if right_phase_count >= PHASE_STABILITY_FRAMES:
            right_phase = right_phase_detected
    else:
        right_phase_count = 1
        right_prev_phase = right_phase_detected
    
    left_phase = prev.get('left_phase', 'unknown')
    left_phase_count = prev.get('left_phase_count', 0)
    left_prev_phase = prev.get('left_prev_phase', 'unknown')
    
    if left_phase_detected == 'middle':
        left_phase = 'middle'
    elif left_phase_detected == left_prev_phase:
        left_phase_count += 1
        if left_phase_count >= PHASE_STABILITY_FRAMES:
            left_phase = left_phase_detected
    else:
        left_phase_count = 1
        left_prev_phase = left_phase_detected
    
    right_reps = prev.get('right_reps', 0)
    right_rep_flag = prev.get('right_rep_flag', False)
    right_stance_valid = prev.get('right_stance_valid', True)
    
    if right_phase == 'extended' and not right_rep_flag:
        right_stance_valid = True
    
    if right_verticality > VERTICAL_STANCE_THRESHOLD:
        right_stance_valid = False
    
    if right_phase == 'flexed':
        right_rep_flag = True
    elif right_phase == 'extended' and right_rep_flag:
        right_reps += 1
        right_rep_flag = False
    
    left_reps = prev.get('left_reps', 0)
    left_rep_flag = prev.get('left_rep_flag', False)
    left_stance_valid = prev.get('left_stance_valid', True)
    
    if left_phase == 'extended' and not left_rep_flag:
        left_stance_valid = True
    
    if left_verticality > VERTICAL_STANCE_THRESHOLD:
        left_stance_valid = False
    
    if left_phase == 'flexed':
        left_rep_flag = True
    elif left_phase == 'extended' and left_rep_flag:
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
        'right_phase_count': right_phase_count,
        'left_phase_count': left_phase_count,
        'right_prev_phase': right_prev_phase,
        'left_prev_phase': left_prev_phase,
        'right_rep_flag': right_rep_flag,
        'left_rep_flag': left_rep_flag,
    }


def calculate_profile_bicep_curl(results, history):
    landmarks = extract_pose_landmarks(results)
    if not landmarks:
        return None
    
    prev = history[-1] if history else {}
        
    right_shoulder = landmarks[POSE_RIGHT_SHOULDER]
    left_shoulder = landmarks[POSE_LEFT_SHOULDER]
    right_elbow = landmarks[POSE_RIGHT_ELBOW]
    right_wrist = landmarks[POSE_RIGHT_WRIST]
    right_hip = landmarks[POSE_RIGHT_HIP]
    left_hip = landmarks[POSE_LEFT_HIP]
    
    right_angle_raw = calculate_angle(right_shoulder, right_elbow, right_wrist)
    right_angle_smooth = smooth_value(right_angle_raw, prev.get('right_angle_smooth'), PROFILE_ANGLE_SMOOTHING)
    
    right_wrist_dist_raw = calculate_wrist_to_shoulder_distance(right_wrist, right_shoulder)
    right_wrist_dist_smooth = smooth_value(right_wrist_dist_raw, prev.get('right_wrist_dist_smooth'), PROFILE_WRIST_DIST_SMOOTHING)
    
    shoulder_mid = ((right_shoulder[0] + left_shoulder[0]) / 2, 
                    (right_shoulder[1] + left_shoulder[1]) / 2)
    hip_mid = ((right_hip[0] + left_hip[0]) / 2,
               (right_hip[1] + left_hip[1]) / 2)
    
    trunk_angle_raw = calculate_trunk_angle(shoulder_mid, hip_mid)
    trunk_angle_smooth = smooth_value(trunk_angle_raw, prev.get('trunk_angle_smooth'), PROFILE_TRUNK_SMOOTHING)
    
    right_phase_detected = detect_phase(right_angle_smooth, PROFILE_FLEX_THRESHOLD, PROFILE_EXTEND_THRESHOLD)
    
    right_phase = prev.get('right_phase', 'unknown')
    right_phase_count = prev.get('right_phase_count', 0)
    right_prev_phase = prev.get('right_prev_phase', 'unknown')
    
    if right_phase_detected == 'middle':
        right_phase = 'middle'
    elif right_phase_detected == right_prev_phase:
        right_phase_count += 1
        if right_phase_count >= PHASE_STABILITY_FRAMES:
            right_phase = right_phase_detected
    else:
        right_phase_count = 1
        right_prev_phase = right_phase_detected
    
    right_reps = prev.get('right_reps', 0)
    right_rep_flag = prev.get('right_rep_flag', False)
    
    if right_phase == 'flexed':
        right_rep_flag = True
    elif right_phase == 'extended' and right_rep_flag:
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
        'right_phase_count': right_phase_count,
        'right_prev_phase': right_prev_phase,
        'right_rep_flag': right_rep_flag,
    }