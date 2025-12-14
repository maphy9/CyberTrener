import numpy as np

def calculate_angle(p1, p2, p3):
    a = np.array(p1)
    b = np.array(p2)
    c = np.array(p3)
    
    ba = a - b
    bc = c - b
    
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.arccos(cosine_angle)
    
    return np.degrees(angle)

def calculate_vertical_angle(p1, p2):
    a = np.array(p1)
    b = np.array(p2)
    
    direction = b - a
    vertical = np.array([0, 1, 0])
    
    cosine_angle = np.dot(direction, vertical) / (np.linalg.norm(direction) * np.linalg.norm(vertical))
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.arccos(cosine_angle)
    
    return np.degrees(angle)

def get_coords(landmarks, idx):
    lm = landmarks.landmark[idx]
    return (lm.x, lm.y, lm.z)

def calculate_front_angles(pose_landmarks):
    angles = {}
    
    right_shoulder = get_coords(pose_landmarks, 11)
    right_elbow = get_coords(pose_landmarks, 13)
    right_wrist = get_coords(pose_landmarks, 15)
    
    left_shoulder = get_coords(pose_landmarks, 12)
    left_elbow = get_coords(pose_landmarks, 14)
    left_wrist = get_coords(pose_landmarks, 16)
    
    angles['right_shoulder'] = calculate_vertical_angle(right_shoulder, right_elbow)
    angles['right_elbow'] = calculate_angle(right_shoulder, right_elbow, right_wrist)
    angles['left_shoulder'] = calculate_vertical_angle(left_shoulder, left_elbow)
    angles['left_elbow'] = calculate_angle(left_shoulder, left_elbow, left_wrist)
    
    return angles

def calculate_profile_angles(pose_landmarks):
    angles = {}
    
    visible_shoulder = get_coords(pose_landmarks, 11)
    visible_elbow = get_coords(pose_landmarks, 13)
    visible_wrist = get_coords(pose_landmarks, 15)
    
    angles['elbow'] = calculate_angle(visible_shoulder, visible_elbow, visible_wrist)
    
    return angles

def smooth_angle(prev_angle, new_angle, alpha=0.3):
    return prev_angle is None and new_angle or alpha * new_angle + (1 - alpha) * prev_angle

def format_angle(angle):
    return angle is None and "N/A" or f"{angle:.1f}°"