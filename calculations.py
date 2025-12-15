import math
import numpy as np


def extract_pose_landmarks(results):
    landmarks = {}
    try:
        landmark_list = results.pose_landmarks.landmark
    except Exception:
        return landmarks
    for i, lm in enumerate(landmark_list):
        landmarks[i] = (lm.x, lm.y, lm.z, getattr(lm, 'visibility', 0))
    return landmarks


def landmark_to_pixel(landmark, frame_width, frame_height):
    x, y, z, visibility = landmark
    return (x * frame_width, y * frame_height, z, visibility)


def to_numpy(point):
    return np.array([point[0], point[1], point[2]], dtype=float)


def calculate_angle(point_a, point_b, point_c):
    vector_ba = np.array([point_a[0] - point_b[0], point_a[1] - point_b[1]], dtype=float)
    vector_bc = np.array([point_c[0] - point_b[0], point_c[1] - point_b[1]], dtype=float)
    length_ba = np.linalg.norm(vector_ba)
    length_bc = np.linalg.norm(vector_bc)
    if length_ba == 0 or length_bc == 0:
        return 0
    cos_angle = np.dot(vector_ba, vector_bc) / (length_ba * length_bc)
    cos_angle = max(-1, min(1, cos_angle))
    return math.degrees(math.acos(cos_angle))



def calculate_trunk_angle(shoulder, hip):
    shoulder = to_numpy(shoulder)
    hip = to_numpy(hip)
    spine_vector = np.array([shoulder[0] - hip[0], shoulder[1] - hip[1]], dtype=float)
    vertical_axis = np.array([0, 1])
    spine_length = np.linalg.norm(spine_vector)
    if spine_length == 0:
        return 0
    cos_angle = np.dot(spine_vector, vertical_axis) / spine_length
    cos_angle = max(-1, min(1, cos_angle))
    return abs(math.degrees(math.acos(cos_angle)))


def calculate_elbow_to_torso_distance(elbow, left_shoulder, right_shoulder):
    shoulder_center = ((to_numpy(left_shoulder) + to_numpy(right_shoulder)) / 2)
    shoulder_width = np.linalg.norm(to_numpy(left_shoulder) - to_numpy(right_shoulder))
    if shoulder_width == 0:
        shoulder_width = 1
    distance = np.linalg.norm(to_numpy(elbow) - shoulder_center)
    return distance / shoulder_width


def calculate_forearm_orientation(elbow, wrist):
    vector = to_numpy(wrist) - to_numpy(elbow)
    vx, vy = vector[0], vector[1]
    if vx == 0 and vy == 0:
        return 0
    angle = math.degrees(math.atan2(vx, vy))
    return angle


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