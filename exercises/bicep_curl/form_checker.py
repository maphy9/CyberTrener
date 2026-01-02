from exercises.bicep_curl.constants import TRUNK_ANGLE_THRESHOLD


class AlternatingBicepCurlValidator:
    def __init__(self):
        self.simultaneous_flex_occurred = False
        self.rep_history = []
        self.max_history = 10
    
    def check_simultaneous_flexion(self, front_metrics):
        right_phase = front_metrics.get('right_phase')
        left_phase = front_metrics.get('left_phase')
        
        if right_phase == 'flexed' and left_phase == 'flexed':
            self.simultaneous_flex_occurred = True
    
    def validate_rep(self, side, front_metrics, profile_metrics):
        right_stance_valid = front_metrics.get('right_stance_valid', True)
        left_stance_valid = front_metrics.get('left_stance_valid', True)
        
        trunk_angle = profile_metrics.get('trunk_angle')
        trunk_valid = True
        if trunk_angle is not None and abs(trunk_angle - 180) > TRUNK_ANGLE_THRESHOLD:
            trunk_valid = False
        
        if not trunk_valid:
            return False, 'trunk_tilted', ['trunk']
        
        if side == 'right':
            if not right_stance_valid:
                return False, 'arm_not_vertical', ['right_arm']
        elif side == 'left':
            if not left_stance_valid:
                return False, 'arm_not_vertical', ['left_arm']
        
        if self.simultaneous_flex_occurred:
            self.simultaneous_flex_occurred = False
            return False, 'both_arms_flexed', ['left_arm', 'right_arm']
        
        if len(self.rep_history) > 0 and self.rep_history[-1] == side:
            return False, 'consecutive_same_side', [f'{side}_arm']
        
        return True, None, []
    
    def record_valid_rep(self, side):
        self.rep_history.append(side)
        if len(self.rep_history) > self.max_history:
            self.rep_history.pop(0)
    
    def reset(self):
        self.simultaneous_flex_occurred = False
        self.rep_history = []


ERROR_MESSAGES = {
    'trunk_tilted': 'Trzymaj plecy prosto',
    'arm_not_vertical': 'Trzymaj rękę pionowo',
    'both_arms_flexed': 'Nie pracuj obiema rękami jednocześnie',
    'consecutive_same_side': 'Zmieniaj ręce naprzemiennie',
}