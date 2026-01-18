
from exercises.overhead_press.constants import (
    TRUNK_ANGLE_THRESHOLD,
    ARM_SYNC_THRESHOLD,
    ELBOW_FORWARD_MIN,
    STABILITY_FRAMES
)


class OverheadPressValidator:
    def __init__(self, calibration=None):
        self.calibration = calibration
        
        # Use calibration values if available, otherwise defaults
        if calibration:
            self.neutral_trunk_angle = calibration.neutral_trunk_angle
            self.trunk_tolerance = calibration.overhead_trunk_tolerance
            self.arm_sync_tolerance = calibration.overhead_arm_sync_tolerance
            self.start_angle = calibration.overhead_start_angle
            self.top_angle = calibration.overhead_top_angle
        else:
            self.neutral_trunk_angle = 180
            self.trunk_tolerance = TRUNK_ANGLE_THRESHOLD
            self.arm_sync_tolerance = ARM_SYNC_THRESHOLD
            self.start_angle = 90
            self.top_angle = 160
        
        self.trunk_error_frames = 0
        self.sync_error_frames = 0
        self.rep_history = []
        self.max_history = 10
        
        # Track form during the entire movement
        self.movement_trunk_errors = 0
        self.movement_sync_errors = 0
        self.movement_frame_count = 0
    
    def validate_rep(self, front_metrics, profile_metrics):
        """
        Validate overhead press form for a single rep.
        Returns: (valid, error_code, error_parts)
        """
        
        # Check trunk angle (back should stay straight)
        trunk_angle = profile_metrics.get('trunk_angle')
        trunk_deviation = profile_metrics.get('trunk_deviation', 0)
        trunk_valid = True
        
        if trunk_angle is not None:
            if trunk_deviation > self.trunk_tolerance:
                trunk_valid = False
                self.trunk_error_frames += 1
            else:
                self.trunk_error_frames = max(0, self.trunk_error_frames - 1)
        
        # Trunk error needs to be consistent
        if not trunk_valid and self.trunk_error_frames >= STABILITY_FRAMES:
            return False, 'trunk_tilted', ['trunk']
        
        # Check arm synchronization (both arms should move together)
        arm_sync_diff = front_metrics.get('arm_sync_diff', 0)
        if arm_sync_diff > self.arm_sync_tolerance:
            self.sync_error_frames += 1
            if self.sync_error_frames >= STABILITY_FRAMES:
                return False, 'arms_not_synchronized', ['left_arm', 'right_arm']
        else:
            self.sync_error_frames = max(0, self.sync_error_frames - 1)
        
        # Check elbow position (elbows should be forward, not flaring to sides)
        elbow_forward_angle = profile_metrics.get('elbow_forward_angle', 90)
        if elbow_forward_angle < ELBOW_FORWARD_MIN:
            return False, 'elbows_too_wide', ['right_arm']
        
        # Check for full lockout at top
        avg_angle = front_metrics.get('avg_angle', 0)
        phase = front_metrics.get('phase', '')
        if phase == 'extended' and avg_angle < self.top_angle:
            return False, 'incomplete_lockout', ['left_arm', 'right_arm']
        
        # Check that movement started from proper start position
        # This is already enforced by active zone, but double-check here
        in_active_zone = front_metrics.get('in_active_zone', False)
        if not in_active_zone:
            return False, 'not_in_position', ['left_arm', 'right_arm']
        
        return True, None, []
    
    def check_realtime_form(self, front_metrics, profile_metrics):
        """
        Check form in real-time (not just at rep completion).
        Returns error dict or None if form is good.
        """
        errors = {}
        
        # Only check if in active zone
        if not front_metrics.get('in_active_zone', False):
            return None
        
        # Check trunk
        trunk_deviation = profile_metrics.get('trunk_deviation', 0)
        if trunk_deviation > self.trunk_tolerance:
            errors['trunk_tilted'] = {
                'message': ERROR_MESSAGES['trunk_tilted'],
                'parts': ['trunk'],
                'severity': min(1.0, trunk_deviation / (self.trunk_tolerance * 2))
            }
        
        # Check arm sync
        arm_sync_diff = front_metrics.get('arm_sync_diff', 0)
        if arm_sync_diff > self.arm_sync_tolerance:
            errors['arms_not_synchronized'] = {
                'message': ERROR_MESSAGES['arms_not_synchronized'],
                'parts': ['left_arm', 'right_arm'],
                'severity': min(1.0, arm_sync_diff / (self.arm_sync_tolerance * 2))
            }
        
        # Check if back is arching excessively (during the press)
        trunk_angle = profile_metrics.get('trunk_angle', 180)
        if trunk_angle > 180 + self.trunk_tolerance:  # Backward lean
            errors['back_arch_excessive'] = {
                'message': ERROR_MESSAGES['back_arch_excessive'],
                'parts': ['trunk'],
                'severity': min(1.0, (trunk_angle - 180) / (self.trunk_tolerance * 2))
            }
        
        return errors if errors else None
    
    def record_valid_rep(self):
        """Record a valid rep in history"""
        self.rep_history.append('overhead_press')
        if len(self.rep_history) > self.max_history:
            self.rep_history.pop(0)
        # Reset movement tracking
        self.movement_trunk_errors = 0
        self.movement_sync_errors = 0
        self.movement_frame_count = 0
    
    def reset(self):
        """Reset validator state"""
        self.trunk_error_frames = 0
        self.sync_error_frames = 0
        self.rep_history = []
        self.movement_trunk_errors = 0
        self.movement_sync_errors = 0
        self.movement_frame_count = 0


ERROR_MESSAGES = {
    'trunk_tilted': 'Trzymaj plecy prosto',
    'arms_not_synchronized': 'Unoś obie ręce równomiernie',
    'elbows_too_wide': 'Trzymaj łokcie do przodu',
    'incomplete_lockout': 'Wyprostuj ręce całkowicie na górze',
    'back_arch_excessive': 'Nie wyginaj pleców do tyłu',
    'not_in_position': 'Zacznij z rąk na wysokości barków',
}