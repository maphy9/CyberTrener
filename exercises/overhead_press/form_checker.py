
from exercises.overhead_press.constants import (
    TRUNK_ANGLE_THRESHOLD,
    ARM_SYNC_THRESHOLD,
    STABILITY_FRAMES
)


class OverheadPressValidator:
    def __init__(self, calibration=None):
        self.calibration = calibration
        
        if calibration:
            self.neutral_trunk_angle = calibration.neutral_trunk_angle
            self.trunk_tolerance = calibration.overhead_trunk_tolerance
            self.arm_sync_tolerance = calibration.overhead_arm_sync_tolerance
        else:
            self.neutral_trunk_angle = 180
            self.trunk_tolerance = TRUNK_ANGLE_THRESHOLD
            self.arm_sync_tolerance = ARM_SYNC_THRESHOLD
        
        self.trunk_error_frames = 0
        self.sync_error_frames = 0
        self.rep_history = []
        self.max_history = 10
    
    def validate_rep(self, front_metrics, profile_metrics):
        trunk_deviation = profile_metrics.get('trunk_deviation', 0)
        
        if trunk_deviation > self.trunk_tolerance:
            self.trunk_error_frames += 1
            if self.trunk_error_frames >= STABILITY_FRAMES:
                return False, 'trunk_tilted', ['trunk']
        else:
            self.trunk_error_frames = max(0, self.trunk_error_frames - 1)
        
        arm_sync_diff = front_metrics.get('arm_sync_diff', 0)
        if arm_sync_diff > self.arm_sync_tolerance:
            self.sync_error_frames += 1
            if self.sync_error_frames >= STABILITY_FRAMES:
                return False, 'arms_not_synchronized', ['left_arm', 'right_arm']
        else:
            self.sync_error_frames = max(0, self.sync_error_frames - 1)
        
        return True, None, []
    
    def check_realtime_form(self, front_metrics, profile_metrics):
        errors = {}
        
        if not front_metrics.get('in_active_zone', False):
            return None
        
        trunk_deviation = profile_metrics.get('trunk_deviation', 0)
        if trunk_deviation > self.trunk_tolerance:
            errors['trunk_tilted'] = {
                'message': ERROR_MESSAGES['trunk_tilted'],
                'parts': ['trunk'],
                'severity': min(1.0, trunk_deviation / (self.trunk_tolerance * 2))
            }
        
        arm_sync_diff = front_metrics.get('arm_sync_diff', 0)
        if arm_sync_diff > self.arm_sync_tolerance:
            errors['arms_not_synchronized'] = {
                'message': ERROR_MESSAGES['arms_not_synchronized'],
                'parts': ['left_arm', 'right_arm'],
                'severity': min(1.0, arm_sync_diff / (self.arm_sync_tolerance * 2))
            }
        
        return errors if errors else None
    
    def record_valid_rep(self):
        self.rep_history.append('overhead_press')
        if len(self.rep_history) > self.max_history:
            self.rep_history.pop(0)
    
    def reset(self):
        self.trunk_error_frames = 0
        self.sync_error_frames = 0
        self.rep_history = []


ERROR_MESSAGES = {
    'trunk_tilted': 'Trzymaj plecy prosto',
    'arms_not_synchronized': 'Unoś obie ręce równomiernie',
}