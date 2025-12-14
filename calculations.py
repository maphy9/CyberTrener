import numpy as np


def _safe_norm(v: np.ndarray, eps: float = 1e-8) -> float:
    n = float(np.linalg.norm(v))
    return n if n > eps else 0.0


def calculate_angle(p1, p2, p3, eps: float = 1e-8):
    """Angle at p2 formed by p1-p2-p3 (3D), in degrees.

    Uses a numerically-stable formulation: atan2(|cross|, dot).
    Returns None if the geometry is degenerate.
    """
    a = np.array(p1, dtype=np.float32)
    b = np.array(p2, dtype=np.float32)
    c = np.array(p3, dtype=np.float32)

    ba = a - b
    bc = c - b

    nba = _safe_norm(ba, eps)
    nbc = _safe_norm(bc, eps)
    if nba == 0.0 or nbc == 0.0:
        return None

    # atan2(|ba x bc|, ba·bc)
    cross = np.cross(ba, bc)
    cross_mag = float(np.linalg.norm(cross))
    dot = float(np.dot(ba, bc))
    angle = float(np.degrees(np.arctan2(cross_mag, dot)))

    if not np.isfinite(angle):
        return None
    return angle


def calculate_angle_2d(p1, p2, p3, eps: float = 1e-8):
    """Angle at p2 formed by p1-p2-p3 in the image plane (2D), in degrees.

    For MediaPipe Pose this is often more stable than using z, because z is noisy.
    Uses atan2(|cross|, dot) where cross is the 2D scalar cross product.
    """
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


def calculate_vertical_angle(p1, p2, eps: float = 1e-8):
    """Angle between the segment p1->p2 and the vertical axis (3D), in degrees."""
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
    """MediaPipe landmarks usually have .visibility; if not present, returns default."""
    lm = landmarks.landmark[idx]
    vis = getattr(lm, 'visibility', None)
    try:
        return float(vis) if vis is not None else float(default)
    except Exception:
        return float(default)


def calculate_distance_2d(p1, p2):
    return float(np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2))


def calculate_front_angles(pose_landmarks):
    angles = {}

    # NOTE: MediaPipe indices: 11=LEFT shoulder, 13=LEFT elbow, 15=LEFT wrist
    #                        12=RIGHT shoulder,14=RIGHT elbow,16=RIGHT wrist
    # The keys below are kept for compatibility with the existing UI.

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
    """Angles for the profile (side) camera.

    Main improvement: compute elbow angle in 2D and automatically choose the
    better-visible arm side (left/right) based on MediaPipe visibility.
    """
    angles = {}

    # Candidate sides in MediaPipe:
    # LEFT:  shoulder=11, elbow=13, wrist=15
    # RIGHT: shoulder=12, elbow=14, wrist=16
    left_idxs = (11, 13, 15)
    right_idxs = (12, 14, 16)

    def side_score(idxs):
        # Conservative: if any joint is poorly visible, the whole side is unreliable.
        v = [get_visibility(pose_landmarks, i, default=0.0) for i in idxs]
        return min(v)

    def side_angle_2d(idxs):
        s, e, w = idxs
        shoulder = get_coords_2d(pose_landmarks, s)
        elbow = get_coords_2d(pose_landmarks, e)
        wrist = get_coords_2d(pose_landmarks, w)
        return calculate_angle_2d(shoulder, elbow, wrist)

    left_score = side_score(left_idxs)
    right_score = side_score(right_idxs)

    left_angle = side_angle_2d(left_idxs)
    right_angle = side_angle_2d(right_idxs)

    # Choose the most reliable:
    chosen = None
    if left_angle is None and right_angle is None:
        chosen = None
    elif left_angle is None:
        chosen = right_angle
    elif right_angle is None:
        chosen = left_angle
    else:
        # If visibility differs, trust the more visible side.
        chosen = left_angle if left_score >= right_score else right_angle

    angles['elbow'] = chosen
    return angles


def smooth_angle(prev_angle, new_angle, alpha=0.3):
    """Exponential smoothing that safely handles None values."""
    if new_angle is None or (isinstance(new_angle, float) and not np.isfinite(new_angle)):
        return prev_angle
    if prev_angle is None or (isinstance(prev_angle, float) and not np.isfinite(prev_angle)):
        return new_angle
    return float(alpha) * float(new_angle) + (1.0 - float(alpha)) * float(prev_angle)


def format_angle(angle):
    if angle is None:
        return "N/A"
    try:
        if not np.isfinite(angle):
            return "N/A"
        return f"{float(angle):.1f}°"
    except Exception:
        return "N/A"
