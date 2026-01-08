from exercises.bicep_curl.constants import TRUNK_ANGLE_THRESHOLD, VERTICAL_STANCE_THRESHOLD, STABILITY_FRAMES


class AlternatingBicepCurlValidator:
    def __init__(self, calibration=None):
        self.calibration = calibration
        self.simultaneous_flex_frames = 0
        self.rep_history = []
        self.max_history = 10
        
        if calibration and calibration.calibrated:
            self.trunk_tolerance = calibration.trunk_tolerance
            self.vertical_tolerance = calibration.vertical_tolerance
            self.neutral_trunk_angle = calibration.neutral_trunk_angle
        else:
            self.trunk_tolerance = TRUNK_ANGLE_THRESHOLD
            self.vertical_tolerance = VERTICAL_STANCE_THRESHOLD
            self.neutral_trunk_angle = 180
    
    def check_simultaneous_flexion(self, front_metrics):
        right_rep_flag = front_metrics.get('right_rep_flag', False)
        left_rep_flag = front_metrics.get('left_rep_flag', False)
        
        if right_rep_flag and left_rep_flag:
            self.simultaneous_flex_frames += 1
        else:
            self.simultaneous_flex_frames = max(0, self.simultaneous_flex_frames - 1)
    
    def validate_rep(self, side, front_metrics, profile_metrics):
        right_verticality = front_metrics.get('right_verticality', 0)
        left_verticality = front_metrics.get('left_verticality', 0)
        
        right_stance_valid = right_verticality <= self.vertical_tolerance
        left_stance_valid = left_verticality <= self.vertical_tolerance
        
        trunk_angle = profile_metrics.get('trunk_angle')
        trunk_valid = True
        if trunk_angle is not None and abs(trunk_angle - self.neutral_trunk_angle) > self.trunk_tolerance:
            trunk_valid = False
        
        if not trunk_valid:
            return False, 'trunk_tilted', ['trunk']
        
        if side == 'right':
            if not right_stance_valid:
                return False, 'arm_not_vertical', ['right_arm']
        elif side == 'left':
            if not left_stance_valid:
                return False, 'arm_not_vertical', ['left_arm']
        
        if self.simultaneous_flex_frames >= STABILITY_FRAMES:
            self.simultaneous_flex_frames = 0
            return False, 'both_arms_flexed', ['left_arm', 'right_arm']
        
        if len(self.rep_history) > 0 and self.rep_history[-1] == side:
            return False, 'consecutive_same_side', [f'{side}_arm']
        
        return True, None, []
    
    def record_valid_rep(self, side):
        self.rep_history.append(side)
        if len(self.rep_history) > self.max_history:
            self.rep_history.pop(0)
    
    def reset(self):
        self.simultaneous_flex_frames = 0
        self.rep_history = []


ERROR_MESSAGES = {
    'trunk_tilted': 'Trzymaj plecy prosto',
    'arm_not_vertical': 'Trzymaj rękę pionowo',
    'both_arms_flexed': 'Nie pracuj obiema rękami jednocześnie',
    'consecutive_same_side': 'Zmieniaj ręce naprzemiennie',
}