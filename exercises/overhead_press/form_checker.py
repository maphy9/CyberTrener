# Form checker for Overhead Press
from core.pose_analyzer import get_angle
from .constants import SHOULDER_ANGLE_THRESHOLD, ELBOW_ANGLE_THRESHOLD

class OverheadPressFormChecker:
    def check(self, pose):
        # Example: Check if arms are fully extended overhead
        left_shoulder_angle = get_angle(pose, 'left_shoulder', 'left_elbow', 'left_wrist')
        right_shoulder_angle = get_angle(pose, 'right_shoulder', 'right_elbow', 'right_wrist')
        left_elbow_angle = get_angle(pose, 'left_elbow', 'left_shoulder', 'left_hip')
        right_elbow_angle = get_angle(pose, 'right_elbow', 'right_shoulder', 'right_hip')

        is_shoulder_ok = left_shoulder_angle > SHOULDER_ANGLE_THRESHOLD and right_shoulder_angle > SHOULDER_ANGLE_THRESHOLD
        is_elbow_ok = left_elbow_angle > ELBOW_ANGLE_THRESHOLD and right_elbow_angle > ELBOW_ANGLE_THRESHOLD

        return {
            'shoulder_extended': is_shoulder_ok,
            'elbow_locked': is_elbow_ok,
            'form_ok': is_shoulder_ok and is_elbow_ok
        }
