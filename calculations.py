import numpy as np


def _safe_norm(v: np.ndarray, eps: float = 1e-8) -> float:
    n = float(np.linalg.norm(v))
    return n if n > eps else 0.0


def calculate_angle_2d(p1, p2, p3, eps: float = 1e-8):
    a = np.array(p1, dtype=np.float32)
    b = np.array(p2, dtype=np.float32)
    c = np.array(p3, dtype=np.float32)

    ba = a - b
    bc = c - b

    nba = _safe_norm(ba, eps)
    nbc = _safe_norm(bc, eps)
    if nba == 0.0 or nbc == 0.0:
        return None

    dot = float(np.dot(ba, bc))
    cross = float(ba[0] * bc[1] - ba[1] * bc[0])
    angle = float(np.degrees(np.arctan2(abs(cross), dot)))

    if not np.isfinite(angle):
        return None
    return angle


def calculate_angle(p1, p2, p3, eps: float = 1e-8):
    a = np.array(p1, dtype=np.float32)
    b = np.array(p2, dtype=np.float32)
    c = np.array(p3, dtype=np.float32)

    ba = a - b
    bc = c - b

    nba = _safe_norm(ba, eps)
    nbc = _safe_norm(bc, eps)
    if nba == 0.0 or nbc == 0.0:
        return None

    cross = np.cross(ba, bc)
    cross_mag = float(np.linalg.norm(cross))
    dot = float(np.dot(ba, bc))
    angle = float(np.degrees(np.arctan2(cross_mag, dot)))

    if not np.isfinite(angle):
        return None
    return angle


def calculate_vertical_angle(p1, p2, eps: float = 1e-8):
    a = np.array(p1, dtype=np.float32)
    b = np.array(p2, dtype=np.float32)

    direction = b - a
    nd = _safe_norm(direction, eps)
    if nd == 0.0:
        return None

    vertical = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    cosine_angle = float(np.dot(direction, vertical) / nd)  # |vertical| == 1
    cosine_angle = float(np.clip(cosine_angle, -1.0, 1.0))
    angle = float(np.degrees(np.arccos(cosine_angle)))

    if not np.isfinite(angle):
        return None
    return angle


def get_coords(landmarks, idx):
    lm = landmarks.landmark[idx]
    return (float(lm.x), float(lm.y), float(lm.z))


def get_coords_2d(landmarks, idx):
    lm = landmarks.landmark[idx]
    return (float(lm.x), float(lm.y))


def get_visibility(landmarks, idx, default: float = 0.0) -> float:
    lm = landmarks.landmark[idx]
    vis = getattr(lm, "visibility", None)
    try:
        return float(vis) if vis is not None else float(default)
    except Exception:
        return float(default)


def calculate_distance_2d(p1, p2):
    return float(np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2))


def calculate_front_angles(pose_landmarks):
    angles = {}

    right_shoulder = get_coords(pose_landmarks, 11)
    right_elbow = get_coords(pose_landmarks, 13)
    right_wrist = get_coords(pose_landmarks, 15)

    left_shoulder = get_coords(pose_landmarks, 12)
    left_elbow = get_coords(pose_landmarks, 14)
    left_wrist = get_coords(pose_landmarks, 16)

    angles["right_shoulder"] = calculate_vertical_angle(right_shoulder, right_elbow)
    angles["right_elbow"] = calculate_angle(right_shoulder, right_elbow, right_wrist)
    angles["left_shoulder"] = calculate_vertical_angle(left_shoulder, left_elbow)
    angles["left_elbow"] = calculate_angle(left_shoulder, left_elbow, left_wrist)

    return angles


def calculate_profile_angles(pose_landmarks, min_visibility: float = 0.35):
    angles = {}

    # LEFT arm landmarks
    l_sh, l_el, l_wr = 11, 13, 15
    # RIGHT arm landmarks
    r_sh, r_el, r_wr = 12, 14, 16

    def elbow_for(sh, el, wr):
        v = min(
            get_visibility(pose_landmarks, sh, 0.0),
            get_visibility(pose_landmarks, el, 0.0),
            get_visibility(pose_landmarks, wr, 0.0),
        )
        if v < float(min_visibility):
            return None
        shoulder = get_coords_2d(pose_landmarks, sh)
        elbow = get_coords_2d(pose_landmarks, el)
        wrist = get_coords_2d(pose_landmarks, wr)
        return calculate_angle_2d(shoulder, elbow, wrist)

    angles["left_elbow"] = elbow_for(l_sh, l_el, l_wr)
    angles["right_elbow"] = elbow_for(r_sh, r_el, r_wr)

    return angles


def smooth_angle(prev_angle, new_angle, alpha: float = 0.3):
    if new_angle is None:
        return prev_angle
    try:
        if not np.isfinite(float(new_angle)):
            return prev_angle
    except Exception:
        return prev_angle

    if prev_angle is None:
        return float(new_angle)
    try:
        if not np.isfinite(float(prev_angle)):
            return float(new_angle)
    except Exception:
        return float(new_angle)

    return float(alpha) * float(new_angle) + (1.0 - float(alpha)) * float(prev_angle)


def format_angle(angle):
    if angle is None:
        return "N/A"
    try:
        if not np.isfinite(float(angle)):
            return "N/A"
        return f"{float(angle):.1f}°"
    except Exception:
        return "N/A"
