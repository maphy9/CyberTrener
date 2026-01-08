import cv2
import time

RELEVANT_LANDMARKS = [11, 12, 13, 14, 15, 16, 23, 24]

RELEVANT_CONNECTIONS = [
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (11, 23),
    (12, 24),
    (23, 24),
]

LEFT_ARM_LANDMARKS = [11, 13, 15]
RIGHT_ARM_LANDMARKS = [12, 14, 16]
TRUNK_LANDMARKS = [11, 12, 23, 24]

LEFT_ARM_CONNECTIONS = [(11, 13), (13, 15)]
RIGHT_ARM_CONNECTIONS = [(12, 14), (14, 16)]
TRUNK_CONNECTIONS = [(11, 12), (11, 23), (12, 24), (23, 24)]

NORMAL_COLOR = (245, 117, 66)
ERROR_COLOR = (0, 0, 255)


def draw_pose_with_errors(frame, results, error_states):
    if not results.pose_landmarks:
        return
    
    landmarks = results.pose_landmarks.landmark
    h, w, _ = frame.shape
    
    current_time = time.time()
    
    left_arm_error = error_states.get('left_arm', 0) > current_time
    right_arm_error = error_states.get('right_arm', 0) > current_time
    trunk_error = error_states.get('trunk', 0) > current_time
    
    for connection in RELEVANT_CONNECTIONS:
        start_idx, end_idx = connection
        start_landmark = landmarks[start_idx]
        end_landmark = landmarks[end_idx]
        
        if start_landmark.visibility > 0.5 and end_landmark.visibility > 0.5:
            start_point = (int(start_landmark.x * w), int(start_landmark.y * h))
            end_point = (int(end_landmark.x * w), int(end_landmark.y * h))
            
            color = NORMAL_COLOR
            if connection in LEFT_ARM_CONNECTIONS and left_arm_error:
                color = ERROR_COLOR
            elif connection in RIGHT_ARM_CONNECTIONS and right_arm_error:
                color = ERROR_COLOR
            elif connection in TRUNK_CONNECTIONS and trunk_error:
                color = ERROR_COLOR
            
            cv2.line(frame, start_point, end_point, color, 2)
    
    for idx in RELEVANT_LANDMARKS:
        landmark = landmarks[idx]
        if landmark.visibility > 0.5:
            cx, cy = int(landmark.x * w), int(landmark.y * h)
            
            color = NORMAL_COLOR
            if idx in LEFT_ARM_LANDMARKS and left_arm_error:
                color = ERROR_COLOR
            elif idx in RIGHT_ARM_LANDMARKS and right_arm_error:
                color = ERROR_COLOR
            elif idx in TRUNK_LANDMARKS and trunk_error:
                color = ERROR_COLOR
            
            cv2.circle(frame, (cx, cy), 3, color, -1)