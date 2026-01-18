
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
        
        self.rep_history = []
        self.max_history = 10
        
        self.movement_trunk_errors = 0
        self.movement_sync_errors = 0
        self.movement_frames = 0
        
        self.trunk_error_streak = 0
        self.sync_error_streak = 0
    
    def track_movement(self, front_metrics, profile_metrics):
        in_active_zone = front_metrics.get('in_active_zone', False)
        if not in_active_zone:
            self.movement_trunk_errors = 0
            self.movement_sync_errors = 0
            self.movement_frames = 0
            self.trunk_error_streak = 0
            self.sync_error_streak = 0
            return
        
        self.movement_frames += 1
        
        trunk_deviation = profile_metrics.get('trunk_deviation', 0)
        if trunk_deviation > self.trunk_tolerance:
            self.trunk_error_streak += 1
            if self.trunk_error_streak >= STABILITY_FRAMES:
                self.movement_trunk_errors += 1
        else:
            self.trunk_error_streak = 0
        
        arm_sync_diff = front_metrics.get('arm_sync_diff', 0)
        wrist_y_diff = front_metrics.get('wrist_y_diff', 0)
        
        if arm_sync_diff > self.arm_sync_tolerance or wrist_y_diff > 0.08:
            self.sync_error_streak += 1
            if self.sync_error_streak >= STABILITY_FRAMES:
                self.movement_sync_errors += 1
        else:
            self.sync_error_streak = 0
    
    def validate_rep(self, front_metrics, profile_metrics):
        if self.movement_frames > 0:
            trunk_error_ratio = self.movement_trunk_errors / self.movement_frames
            sync_error_ratio = self.movement_sync_errors / self.movement_frames
            
            self.movement_trunk_errors = 0
            self.movement_sync_errors = 0
            self.movement_frames = 0
            self.trunk_error_streak = 0
            self.sync_error_streak = 0
            
            if trunk_error_ratio > 0.15:
                return False, 'trunk_tilted', ['trunk']
            
            if sync_error_ratio > 0.15:
                return False, 'arms_not_synchronized', ['left_arm', 'right_arm']
        
        return True, None, []
    
    def record_valid_rep(self):
        self.rep_history.append('overhead_press')
        if len(self.rep_history) > self.max_history:
            self.rep_history.pop(0)
    
    def reset(self):
        self.rep_history = []
        self.movement_trunk_errors = 0
        self.movement_sync_errors = 0
        self.movement_frames = 0


ERROR_MESSAGES = {
    'trunk_tilted': 'Trzymaj plecy prosto',
    'arms_not_synchronized': 'Unoś obie ręce równomiernie',
}