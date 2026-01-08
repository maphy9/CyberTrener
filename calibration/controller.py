from core.pose_analyzer import PoseAnalyzer
from exercises.bicep_curl.metrics import calculate_front_view, calculate_profile_view
from calibration.data import CalibrationData


class CalibrationController:
    def __init__(self):
        self.front_analyzer = PoseAnalyzer(calculate_front_view)
        self.profile_analyzer = PoseAnalyzer(calculate_profile_view)
        self.current_step = 'neutral'
        self.measurements = {}
        self.stable_frames = 0
        self.REQUIRED_STABLE_FRAMES = 30
    
    def get_instructions(self):
        instructions = {
            'neutral': 'Stań w pozycji neutralnej z ramionami wzdłuż ciała',
            'right_flex': 'Ugnij prawą rękę maksymalnie do góry',
            'right_extend': 'Wyprostuj prawą rękę całkowicie',
            'left_flex': 'Ugnij lewą rękę maksymalnie do góry',
            'left_extend': 'Wyprostuj lewą rękę całkowicie',
            'complete': 'Kalibracja zakończona!'
        }
        return instructions.get(self.current_step, '')
    
    def process_frames(self, front_results, profile_results):
        self.front_analyzer.process_frame(front_results)
        self.profile_analyzer.process_frame(profile_results)
        
        front_metrics = self.front_analyzer.get_metrics()
        profile_metrics = self.profile_analyzer.get_metrics()
        
        if self.current_step == 'neutral':
            trunk_angle = profile_metrics.get('trunk_angle')
            if trunk_angle and self._is_stable(trunk_angle, 'neutral_trunk'):
                self.measurements['neutral_trunk'] = trunk_angle
                self.current_step = 'right_flex'
                self.stable_frames = 0
                return True, "Dobrze! Teraz ugnij prawą rękę"
        
        elif self.current_step == 'right_flex':
            right_angle = front_metrics.get('right_angle')
            right_phase = front_metrics.get('right_phase')
            right_vert = front_metrics.get('right_verticality', 0)
            
            if right_phase == 'flexed' and self._is_stable(right_angle, 'right_flex_angle'):
                self.measurements['right_flex_angle'] = right_angle
                self.measurements['right_verticality'] = right_vert
                self.current_step = 'right_extend'
                self.stable_frames = 0
                return True, "Świetnie! Teraz wyprostuj prawą rękę"
        
        elif self.current_step == 'right_extend':
            right_angle = front_metrics.get('right_angle')
            right_phase = front_metrics.get('right_phase')
            
            if right_phase == 'extended' and self._is_stable(right_angle, 'right_extend_angle'):
                self.measurements['right_extend_angle'] = right_angle
                self.current_step = 'left_flex'
                self.stable_frames = 0
                return True, "Doskonale! Teraz ugnij lewą rękę"
        
        elif self.current_step == 'left_flex':
            left_angle = front_metrics.get('left_angle')
            left_phase = front_metrics.get('left_phase')
            left_vert = front_metrics.get('left_verticality', 0)
            
            if left_phase == 'flexed' and self._is_stable(left_angle, 'left_flex_angle'):
                self.measurements['left_flex_angle'] = left_angle
                self.measurements['left_verticality'] = left_vert
                self.current_step = 'left_extend'
                self.stable_frames = 0
                return True, "Rewelacja! Teraz wyprostuj lewą rękę"
        
        elif self.current_step == 'left_extend':
            left_angle = front_metrics.get('left_angle')
            left_phase = front_metrics.get('left_phase')
            
            if left_phase == 'extended' and self._is_stable(left_angle, 'left_extend_angle'):
                self.measurements['left_extend_angle'] = left_angle
                self.current_step = 'complete'
                self.stable_frames = 0
                return True, "Kalibracja ukończona!"
        
        return False, None
    
    def _is_stable(self, value, key):
        if value is None:
            return False
        
        if key not in self.measurements:
            self.measurements[key] = value
            self.stable_frames = 1
            return False
        
        if abs(value - self.measurements[key]) < 3:
            self.stable_frames += 1
        else:
            self.measurements[key] = value
            self.stable_frames = 1
        
        return self.stable_frames >= self.REQUIRED_STABLE_FRAMES
    
    def is_complete(self):
        return self.current_step == 'complete'
    
    def get_calibration_data(self):
        calibration = CalibrationData()
        calibration.calculate_thresholds(self.measurements)
        return calibration