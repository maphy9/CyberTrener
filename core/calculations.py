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
    """Calculate trunk angle. Returns ~180 for upright stance, <180 for forward lean, >180 for backward lean."""
    spine_vector = np.array([shoulder[0] - hip[0], shoulder[1] - hip[1]])
    
    spine_length = np.linalg.norm(spine_vector)
    if spine_length == 0:
        return 180
    
    # Calculate horizontal deviation (positive = forward lean, negative = backward)
    # In image coordinates, Y increases downward, so shoulder above hip means negative Y diff
    # X deviation: positive means shoulder is to the right of hip
    horizontal_deviation = spine_vector[0]  # X component
    
    # Calculate angle from vertical: atan2 gives signed angle
    # For upright: spine_vector ≈ (0, negative) -> angle ≈ 0
    angle_from_vertical = math.degrees(math.atan2(horizontal_deviation, -spine_vector[1]))
    
    # Return as 180 +/- deviation (180 = straight, <180 = forward, >180 = backward)
    return 180 + angle_from_vertical


def calculate_arm_verticality(shoulder, elbow):
    arm_vector = np.array([elbow[0] - shoulder[0], elbow[1] - shoulder[1]])
    vertical_axis = np.array([0, -1])
    
    arm_length = np.linalg.norm(arm_vector)
    if arm_length == 0:
        return 0
    
    cos_angle = np.clip(np.dot(arm_vector, vertical_axis) / arm_length, -1, 1)
    verticality = abs(180 - math.degrees(math.acos(cos_angle)))
    return verticality


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


def adaptive_smooth_value(current_value, previous_value, base_smoothing=0.25, velocity_threshold=5.0):
    """
    Adaptive smoothing that reduces lag during fast movements.
    - Slow movement: higher smoothing (more stable)
    - Fast movement: lower smoothing (more responsive)
    
    Returns:
        tuple: (smoothed_value, velocity)
    """
    if previous_value is None:
        return current_value, 0.0
    
    velocity = abs(current_value - previous_value)
    
    if velocity > velocity_threshold:
        # Fast movement: reduce smoothing for responsiveness
        adaptive_factor = max(0.5, base_smoothing * (velocity_threshold / velocity))
    else:
        # Slow movement: increase smoothing for stability
        adaptive_factor = min(0.15, base_smoothing * (1 - velocity / velocity_threshold * 0.5))
    
    smoothed = adaptive_factor * current_value + (1 - adaptive_factor) * previous_value
    return smoothed, velocity


def exponential_moving_average(current_value, ema_value, alpha=0.3):
    """Standard EMA for consistent smoothing."""
    if ema_value is None:
        return current_value
    return alpha * current_value + (1 - alpha) * ema_value


class AdaptiveSmoother:
    """
    Stateful adaptive smoother that tracks velocity and adjusts smoothing dynamically.
    Useful for per-joint smoothing with independent state.
    """
    
    def __init__(self, base_smoothing=0.25, velocity_threshold=5.0, velocity_smoothing=0.3):
        self.base_smoothing = base_smoothing
        self.velocity_threshold = velocity_threshold
        self.velocity_smoothing = velocity_smoothing
        self.previous_value = None
        self.smoothed_velocity = 0.0
    
    def update(self, current_value):
        """
        Update smoother with new value.
        
        Returns:
            float: Smoothed value
        """
        if self.previous_value is None:
            self.previous_value = current_value
            return current_value
        
        # Calculate instantaneous velocity
        instant_velocity = abs(current_value - self.previous_value)
        
        # Smooth the velocity to avoid jitter
        self.smoothed_velocity = (
            self.velocity_smoothing * instant_velocity + 
            (1 - self.velocity_smoothing) * self.smoothed_velocity
        )
        
        # Determine adaptive smoothing factor
        if self.smoothed_velocity > self.velocity_threshold:
            # Fast movement: more responsive (higher factor = less smoothing)
            ratio = min(2.0, self.smoothed_velocity / self.velocity_threshold)
            adaptive_factor = min(0.6, self.base_smoothing * ratio)
        else:
            # Slow movement: more stable (lower factor = more smoothing)
            ratio = self.smoothed_velocity / self.velocity_threshold
            adaptive_factor = max(0.1, self.base_smoothing * (0.5 + 0.5 * ratio))
        
        # Apply smoothing
        smoothed = adaptive_factor * current_value + (1 - adaptive_factor) * self.previous_value
        self.previous_value = smoothed
        
        return smoothed
    
    def reset(self):
        """Reset smoother state."""
        self.previous_value = None
        self.smoothed_velocity = 0.0
    
    def get_velocity(self):
        """Get current smoothed velocity."""
        return self.smoothed_velocity


def detect_phase(angle, flex_threshold=80, extend_threshold=120):
    if angle <= flex_threshold:
        return 'flexed'
    elif angle >= extend_threshold:
        return 'extended'
    return 'middle'