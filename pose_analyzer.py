from collections import deque
from calculations import (
    extract_pose_landmarks, calculate_angle, calculate_trunk_angle,
    calculate_elbow_to_torso_distance, smooth_value, detect_phase,
    assess_motion_control
)
from constants import *
import time


class FrontAnalyzer:
    def __init__(self, max_history=30):
        self.max_history = max_history
        self.right_angle_history_timed = deque(maxlen=max_history)
        self.left_angle_history_timed = deque(maxlen=max_history)
        self.right_angle_smooth = None
        self.left_angle_smooth = None
        self.trunk_angle_smooth = None
        self.right_elbow_dist_smooth = None
        self.left_elbow_dist_smooth = None
        
        self.right_reps = 0
        self.left_reps = 0
        self.right_phase = 'unknown'
        self.left_phase = 'unknown'
        self.right_rep_flag = False
        self.left_rep_flag = False
        self.trunk_angle = 0
        self.right_motion = {'max_vel': 0, 'avg_vel': 0, 'uncontrolled': 0}
        self.left_motion = {'max_vel': 0, 'avg_vel': 0, 'uncontrolled': 0}
        self.last_time = time.time()
        
    def process_frame(self, results):
        landmarks = extract_pose_landmarks(results)
        if not landmarks:
            return
            
        current_time = time.time()
        dt = current_time - self.last_time
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
        
        self.right_angle_smooth = smooth_value(right_angle_raw, self.right_angle_smooth, 0.25)
        self.left_angle_smooth = smooth_value(left_angle_raw, self.left_angle_smooth, 0.25)
        
        self.right_angle_history_timed.append((current_time, self.right_angle_smooth))
        self.left_angle_history_timed.append((current_time, self.left_angle_smooth))
        
        right_dist_raw = calculate_elbow_to_torso_distance(right_elbow, right_shoulder, left_shoulder)
        left_dist_raw = calculate_elbow_to_torso_distance(left_elbow, right_shoulder, left_shoulder)
        
        self.right_elbow_dist_smooth = smooth_value(right_dist_raw, self.right_elbow_dist_smooth, 0.25)
        self.left_elbow_dist_smooth = smooth_value(left_dist_raw, self.left_elbow_dist_smooth, 0.25)
        
        shoulder_mid = ((right_shoulder[0] + left_shoulder[0]) / 2, 
                        (right_shoulder[1] + left_shoulder[1]) / 2,
                        (right_shoulder[2] + left_shoulder[2]) / 2)
        hip_mid = ((right_hip[0] + left_hip[0]) / 2,
                   (right_hip[1] + left_hip[1]) / 2,
                   (right_hip[2] + left_hip[2]) / 2)
        
        trunk_angle_raw = calculate_trunk_angle(shoulder_mid, hip_mid)
        self.trunk_angle = smooth_value(trunk_angle_raw, self.trunk_angle, 0.25)
        
        self.right_phase = detect_phase(self.right_angle_smooth)
        self.left_phase = detect_phase(self.left_angle_smooth)
        
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
        
        if len(self.right_angle_history_timed) >= 3:
            self.right_motion = assess_motion_control(self.right_angle_history_timed)
        if len(self.left_angle_history_timed) >= 3:
            self.left_motion = assess_motion_control(self.left_angle_history_timed)
    
    def get_metrics(self):
        return {
            'right_angle': round(self.right_angle_smooth or 0, 1),
            'left_angle': round(self.left_angle_smooth or 0, 1),
            'right_reps': self.right_reps,
            'left_reps': self.left_reps,
            'right_phase': self.right_phase,
            'left_phase': self.left_phase,
            'trunk_angle': round(self.trunk_angle or 0, 1),
            'right_elbow_dist': round(self.right_elbow_dist_smooth or 0, 3),
            'left_elbow_dist': round(self.left_elbow_dist_smooth or 0, 3),
            'right_uncontrolled': self.right_motion.get('uncontrolled', 0),
            'left_uncontrolled': self.left_motion.get('uncontrolled', 0),
        }


class ProfileAnalyzer:
    def __init__(self, max_history=30):
        self.max_history = max_history
        self.right_angle_history_timed = deque(maxlen=max_history)
        self.right_angle_smooth = None
        self.trunk_angle_smooth = None
        self.right_elbow_dist_smooth = None
        
        self.right_reps = 0
        self.right_phase = 'unknown'
        self.right_rep_flag = False
        self.trunk_angle = 0
        self.right_motion = {'max_vel': 0, 'avg_vel': 0, 'uncontrolled': 0}
        self.last_time = time.time()
        
    def process_frame(self, results):
        landmarks = extract_pose_landmarks(results)
        if not landmarks:
            return
            
        current_time = time.time()
        dt = current_time - self.last_time
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
        self.right_angle_smooth = smooth_value(right_angle_raw, self.right_angle_smooth, 0.25)
        self.right_angle_history_timed.append((current_time, self.right_angle_smooth))
        
        right_dist_raw = calculate_elbow_to_torso_distance(right_elbow, right_shoulder, left_shoulder)
        self.right_elbow_dist_smooth = smooth_value(right_dist_raw, self.right_elbow_dist_smooth, 0.25)
        
        shoulder_mid = ((right_shoulder[0] + left_shoulder[0]) / 2, 
                        (right_shoulder[1] + left_shoulder[1]) / 2,
                        (right_shoulder[2] + left_shoulder[2]) / 2)
        hip_mid = ((right_hip[0] + left_hip[0]) / 2,
                   (right_hip[1] + left_hip[1]) / 2,
                   (right_hip[2] + left_hip[2]) / 2)
        
        trunk_angle_raw = calculate_trunk_angle(shoulder_mid, hip_mid)
        self.trunk_angle = smooth_value(trunk_angle_raw, self.trunk_angle, 0.25)
        
        self.right_phase = detect_phase(self.right_angle_smooth)
        
        if self.right_phase == 'flexed':
            self.right_rep_flag = True
        elif self.right_phase == 'extended' and self.right_rep_flag:
            self.right_reps += 1
            self.right_rep_flag = False
        
        if len(self.right_angle_history_timed) >= 3:
            self.right_motion = assess_motion_control(self.right_angle_history_timed)
    
    def get_metrics(self):
        return {
            'right_angle': round(self.right_angle_smooth or 0, 1),
            'right_reps': self.right_reps,
            'right_phase': self.right_phase,
            'trunk_angle': round(self.trunk_angle or 0, 1),
            'right_elbow_dist': round(self.right_elbow_dist_smooth or 0, 3),
            'right_uncontrolled': self.right_motion.get('uncontrolled', 0),
        }

