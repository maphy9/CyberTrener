from collections import deque
from calculations import *
from constants import *
import time


class BaseAnalyzer:
    def __init__(self, validation_fn, max_history=30):
        self.validation_fn = validation_fn
        self.max_history = max_history
        self.last_validation_error = None
    
    def validate(self, metrics):
        self.last_validation_error = self.validation_fn(metrics)
        return self.last_validation_error
    
    def get_validation_error(self):
        return self.last_validation_error


class FrontAnalyzer(BaseAnalyzer):
    def __init__(self, validation_fn, max_history=30):
        super().__init__(validation_fn, max_history)
        self.right_angle_history_timed = deque(maxlen=max_history)
        self.left_angle_history_timed = deque(maxlen=max_history)
        self.right_angle_smooth = None
        self.left_angle_smooth = None
        self.trunk_angle_smooth = None
        self.right_elbow_dist_smooth = None
        self.left_elbow_dist_smooth = None
        self.right_wrist_dist_smooth = None
        self.left_wrist_dist_smooth = None
        
        self.right_reps = 0
        self.left_reps = 0
        self.right_phase = 'unknown'
        self.left_phase = 'unknown'
        self.right_phase_count = 0
        self.left_phase_count = 0
        self.right_prev_phase = 'unknown'
        self.left_prev_phase = 'unknown'
        self.right_rep_flag = False
        self.left_rep_flag = False
        self.trunk_angle = 0
        self.last_time = time.time()
        
    def process_frame(self, results):
        landmarks = extract_pose_landmarks(results)
        if not landmarks:
            return
            
        current_time = time.time()
        self.last_time = current_time
            
        try:
            right_shoulder = landmarks[POSE_RIGHT_SHOULDER]
            left_shoulder = landmarks[POSE_LEFT_SHOULDER]
            right_elbow = landmarks[POSE_RIGHT_ELBOW]
            left_elbow = landmarks[POSE_LEFT_ELBOW]
            right_wrist = landmarks[POSE_RIGHT_WRIST]
            left_wrist = landmarks[POSE_LEFT_WRIST]
            right_hip = landmarks[POSE_RIGHT_HIP]
            left_hip = landmarks[POSE_LEFT_HIP]
        except KeyError:
            return
        
        right_angle_raw = calculate_angle(right_shoulder, right_elbow, right_wrist)
        left_angle_raw = calculate_angle(left_shoulder, left_elbow, left_wrist)
        
        self.right_angle_smooth = smooth_value(right_angle_raw, self.right_angle_smooth, FRONT_ANGLE_SMOOTHING)
        self.left_angle_smooth = smooth_value(left_angle_raw, self.left_angle_smooth, FRONT_ANGLE_SMOOTHING)
        
        self.right_angle_history_timed.append((current_time, self.right_angle_smooth))
        self.left_angle_history_timed.append((current_time, self.left_angle_smooth))
        
        right_dist_raw = calculate_elbow_to_torso_distance(right_elbow, right_shoulder, left_shoulder)
        left_dist_raw = calculate_elbow_to_torso_distance(left_elbow, right_shoulder, left_shoulder)
        
        self.right_elbow_dist_smooth = smooth_value(right_dist_raw, self.right_elbow_dist_smooth, FRONT_ELBOW_DIST_SMOOTHING)
        self.left_elbow_dist_smooth = smooth_value(left_dist_raw, self.left_elbow_dist_smooth, FRONT_ELBOW_DIST_SMOOTHING)
        
        right_wrist_dist_raw = calculate_wrist_to_shoulder_distance(right_wrist, right_shoulder)
        left_wrist_dist_raw = calculate_wrist_to_shoulder_distance(left_wrist, left_shoulder)
        
        self.right_wrist_dist_smooth = smooth_value(right_wrist_dist_raw, self.right_wrist_dist_smooth, FRONT_WRIST_DIST_SMOOTHING)
        self.left_wrist_dist_smooth = smooth_value(left_wrist_dist_raw, self.left_wrist_dist_smooth, FRONT_WRIST_DIST_SMOOTHING)
        
        right_phase_detected = detect_phase(
            self.right_angle_smooth,
            FRONT_FLEX_THRESHOLD,
            FRONT_EXTEND_THRESHOLD,
        )
        left_phase_detected = detect_phase(
            self.left_angle_smooth,
            FRONT_FLEX_THRESHOLD,
            FRONT_EXTEND_THRESHOLD,
        )
        
        if right_phase_detected == 'middle':
            self.right_phase = 'middle'
        elif right_phase_detected == self.right_prev_phase:
            self.right_phase_count += 1
            if self.right_phase_count >= PHASE_STABILITY_FRAMES:
                self.right_phase = right_phase_detected
        else:
            self.right_phase_count = 1
            self.right_prev_phase = right_phase_detected
        
        if left_phase_detected == 'middle':
            self.left_phase = 'middle'
        elif left_phase_detected == self.left_prev_phase:
            self.left_phase_count += 1
            if self.left_phase_count >= PHASE_STABILITY_FRAMES:
                self.left_phase = left_phase_detected
        else:
            self.left_phase_count = 1
            self.left_prev_phase = left_phase_detected
        
        if self.right_phase == 'flexed':
            self.right_rep_flag = True
        elif self.right_phase == 'extended' and self.right_rep_flag:
            self.right_reps += 1
            self.right_rep_flag = False
        
        if self.left_phase == 'flexed':
            self.left_rep_flag = True
        elif self.left_phase == 'extended' and self.left_rep_flag:
            self.left_reps += 1
            self.left_rep_flag = False
    
    def get_metrics(self):
        metrics = {
            'right_angle': round(self.right_angle_smooth or 0, 1),
            'left_angle': round(self.left_angle_smooth or 0, 1),
            'right_reps': self.right_reps,
            'left_reps': self.left_reps,
            'right_phase': self.right_phase,
            'left_phase': self.left_phase,
            'right_elbow_dist': round(self.right_elbow_dist_smooth or 0, 3),
            'left_elbow_dist': round(self.left_elbow_dist_smooth or 0, 3),
            'right_wrist_dist': round(self.right_wrist_dist_smooth or 0, 3),
            'left_wrist_dist': round(self.left_wrist_dist_smooth or 0, 3),
        }
        self.validate(metrics)
        return metrics


class ProfileAnalyzer(BaseAnalyzer):
    def __init__(self, validation_fn, max_history=30):
        super().__init__(validation_fn, max_history)
        self.right_angle_history_timed = deque(maxlen=max_history)
        self.right_angle_smooth = None
        self.trunk_angle_smooth = None
        self.right_wrist_dist_smooth = None
        
        self.right_reps = 0
        self.right_phase = 'unknown'
        self.right_phase_count = 0
        self.right_prev_phase = 'unknown'
        self.right_rep_flag = False
        self.trunk_angle = 0
        self.last_time = time.time()
        
    def process_frame(self, results):
        landmarks = extract_pose_landmarks(results)
        if not landmarks:
            return
            
        current_time = time.time()
        self.last_time = current_time
            
        try:
            right_shoulder = landmarks[POSE_RIGHT_SHOULDER]
            left_shoulder = landmarks[POSE_LEFT_SHOULDER]
            right_elbow = landmarks[POSE_RIGHT_ELBOW]
            right_wrist = landmarks[POSE_RIGHT_WRIST]
            right_hip = landmarks[POSE_RIGHT_HIP]
            left_hip = landmarks[POSE_LEFT_HIP]
        except KeyError:
            return
        
        right_angle_raw = calculate_angle(right_shoulder, right_elbow, right_wrist)
        self.right_angle_smooth = smooth_value(right_angle_raw, self.right_angle_smooth, PROFILE_ANGLE_SMOOTHING)
        self.right_angle_history_timed.append((current_time, self.right_angle_smooth))
        
        right_wrist_dist_raw = calculate_wrist_to_shoulder_distance(right_wrist, right_shoulder)
        self.right_wrist_dist_smooth = smooth_value(right_wrist_dist_raw, self.right_wrist_dist_smooth, PROFILE_WRIST_DIST_SMOOTHING)
        
        shoulder_mid = ((right_shoulder[0] + left_shoulder[0]) / 2, 
                        (right_shoulder[1] + left_shoulder[1]) / 2,
                        (right_shoulder[2] + left_shoulder[2]) / 2)
        hip_mid = ((right_hip[0] + left_hip[0]) / 2,
                   (right_hip[1] + left_hip[1]) / 2,
                   (right_hip[2] + left_hip[2]) / 2)
        
        trunk_angle_raw = calculate_trunk_angle(shoulder_mid, hip_mid)
        self.trunk_angle = smooth_value(trunk_angle_raw, self.trunk_angle, PROFILE_TRUNK_SMOOTHING)
        
        right_phase_detected = detect_phase(
            self.right_angle_smooth,
            PROFILE_FLEX_THRESHOLD,
            PROFILE_EXTEND_THRESHOLD,
        )
        
        if right_phase_detected == 'middle':
            self.right_phase = 'middle'
        elif right_phase_detected == self.right_prev_phase:
            self.right_phase_count += 1
            if self.right_phase_count >= PHASE_STABILITY_FRAMES:
                self.right_phase = right_phase_detected
        else:
            self.right_phase_count = 1
            self.right_prev_phase = right_phase_detected
        
        if self.right_phase == 'flexed':
            self.right_rep_flag = True
        elif self.right_phase == 'extended' and self.right_rep_flag:
            self.right_reps += 1
            self.right_rep_flag = False
    
    def get_metrics(self):
        metrics = {
            'right_angle': round(self.right_angle_smooth or 0, 1),
            'right_reps': self.right_reps,
            'right_phase': self.right_phase,
            'trunk_angle': round(self.trunk_angle or 0, 1),
            'right_wrist_dist': round(self.right_wrist_dist_smooth or 0, 3),
        }
        self.validate(metrics)
        return metrics