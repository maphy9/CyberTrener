
from exercises.overhead_press.constants import (
    TRUNK_ANGLE_THRESHOLD,
    ARM_SYNC_THRESHOLD,
    ELBOW_FORWARD_MIN,
    STABILITY_FRAMES
)


class OverheadPressValidator:
    def __init__(self):
        self.neutral_trunk_angle = 180  
        self.trunk_error_frames = 0
        self.rep_history = []
        self.max_history = 10
    
    def validate_rep(self, front_metrics, profile_metrics):
        """
        Validate overhead press form for a single rep.
        Returns: (valid, error_code, error_parts)
        """
        
        trunk_angle = profile_metrics.get('trunk_angle')
        trunk_valid = True
        if trunk_angle is not None:
            trunk_deviation = abs(trunk_angle - self.neutral_trunk_angle)
            if trunk_deviation > TRUNK_ANGLE_THRESHOLD:
                trunk_valid = False
                self.trunk_error_frames += 1
            else:
                self.trunk_error_frames = max(0, self.trunk_error_frames - 1)
        
        # Trunk error needs to be consistent
        if not trunk_valid and self.trunk_error_frames >= STABILITY_FRAMES:
            return False, 'trunk_tilted', ['trunk']
        
        # Check arm synchronization (both arms should move together)
        arm_sync_diff = front_metrics.get('arm_sync_diff', 0)
        if arm_sync_diff > ARM_SYNC_THRESHOLD:
            return False, 'arms_not_synchronized', ['left_arm', 'right_arm']
        
        # Check elbow position (elbows should be forward, not flaring to sides)
        elbow_forward_angle = profile_metrics.get('elbow_forward_angle', 0)
        if elbow_forward_angle < ELBOW_FORWARD_MIN:
            return False, 'elbows_too_wide', ['right_arm']
        
        # Check for full lockout at top
        avg_angle = front_metrics.get('avg_angle', 0)
        phase = front_metrics.get('phase', '')
        if phase == 'extended' and avg_angle < 160:
            return False, 'incomplete_lockout', ['left_arm', 'right_arm']
        
        return True, None, []
    
    def record_valid_rep(self):
        """Record a valid rep in history"""
        self.rep_history.append('overhead_press')
        if len(self.rep_history) > self.max_history:
            self.rep_history.pop(0)
    
    def reset(self):
        """Reset validator state"""
        self.trunk_error_frames = 0
        self.rep_history = []


ERROR_MESSAGES = {
    'trunk_tilted': 'Trzymaj plecy prosto',
    'arms_not_synchronized': 'Unoś obie ręce równomiernie',
    'elbows_too_wide': 'Trzymaj łokcie do przodu',
    'incomplete_lockout': 'Wyprostuj ręce całkowicie na górze',
    'back_arch_excessive': 'Nie wyginaj pleców',
}