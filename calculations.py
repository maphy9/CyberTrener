import math
import numpy as np


def extract_pose_landmarks(results):
    landmarks = {}
    try:
        landmark_list = results.pose_landmarks.landmark
    except Exception:
        return landmarks
    for i, lm in enumerate(landmark_list):
        landmarks[i] = (lm.x, lm.y, getattr(lm, 'visibility', 0))
    return landmarks


def calculate_angle(point_a, point_b, point_c):
    vector_ba = np.array([point_a[0] - point_b[0], point_a[1] - point_b[1]])
    vector_bc = np.array([point_c[0] - point_b[0], point_c[1] - point_b[1]])
    
    length_ba = np.linalg.norm(vector_ba)
    length_bc = np.linalg.norm(vector_bc)
    
    if length_ba == 0 or length_bc == 0:
        return 0
    
    cos_angle = np.clip(np.dot(vector_ba, vector_bc) / (length_ba * length_bc), -1, 1)
    return math.degrees(math.acos(cos_angle))


def calculate_trunk_angle(shoulder, hip):
    spine_vector = np.array([shoulder[0] - hip[0], shoulder[1] - hip[1]])
    vertical_axis = np.array([0, 1])
    
    spine_length = np.linalg.norm(spine_vector)
    if spine_length == 0:
        return 0
    
    cos_angle = np.clip(np.dot(spine_vector, vertical_axis) / spine_length, -1, 1)
    return abs(math.degrees(math.acos(cos_angle)))


def calculate_elbow_to_torso_distance(elbow, left_shoulder, right_shoulder):
    left_np = np.array([left_shoulder[0], left_shoulder[1]])
    right_np = np.array([right_shoulder[0], right_shoulder[1]])
    elbow_np = np.array([elbow[0], elbow[1]])
    
    shoulder_center = (left_np + right_np) / 2
    shoulder_width = np.linalg.norm(left_np - right_np)
    
    if shoulder_width == 0:
        shoulder_width = 1
    
    distance = np.linalg.norm(elbow_np - shoulder_center)
    return distance / shoulder_width


def calculate_wrist_to_shoulder_distance(wrist, shoulder):
    wrist_np = np.array([wrist[0], wrist[1]])
    shoulder_np = np.array([shoulder[0], shoulder[1]])
    return np.linalg.norm(wrist_np - shoulder_np)


def smooth_value(current_value, previous_value, smoothing_factor=0.25):
    if previous_value is None:
        return current_value
    return smoothing_factor * current_value + (1 - smoothing_factor) * previous_value


def detect_phase(angle, flex_threshold=80, extend_threshold=120):
    if angle <= flex_threshold:
        return 'flexed'
    elif angle >= extend_threshold:
        return 'extended'
    return 'middle'