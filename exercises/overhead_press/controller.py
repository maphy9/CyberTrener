from core.pose_analyzer import EnhancedPoseAnalyzer
from exercises.overhead_press.metrics import calculate_front_view, calculate_profile_view
from exercises.overhead_press.form_checker import OverheadPressValidator, ERROR_MESSAGES


class OverheadPressController:
    def __init__(self, calibration=None):
        self.calibration = calibration
        
        def front_view_with_calibration(results, history):
            return calculate_front_view(results, history, calibration)
        
        def profile_view_with_calibration(results, history):
            return calculate_profile_view(results, history, calibration)
        
        self.front_analyzer = EnhancedPoseAnalyzer(front_view_with_calibration)
        self.profile_analyzer = EnhancedPoseAnalyzer(profile_view_with_calibration)
        self.validator = OverheadPressValidator(calibration)
        
        self.prev_reps = 0
        self.valid_reps = 0
        
        if calibration:
            print(f"Overhead Press using calibration: start angle {calibration.overhead_start_angle}, "
                  f"top angle {calibration.overhead_top_angle}, "
                  f"trunk tolerance {calibration.overhead_trunk_tolerance}")
        else:
            print("Overhead Press Controller initialized (no calibration)")
    
    def process_frames(self, front_results, profile_results):
        self.front_analyzer.process_frame(front_results)
        self.profile_analyzer.process_frame(profile_results)
        
        front_metrics = self.front_analyzer.get_metrics()
        profile_metrics = self.profile_analyzer.get_metrics()
        
        self.validator.track_movement(front_metrics, profile_metrics)
        
        analyzer_reps = front_metrics.get('reps', 0)
        
        rep_detected = analyzer_reps > self.prev_reps
        
        result = {
            'rep_detected': False,
            'valid': False,
            'error_message': None,
            'error_parts': [],
            'right_reps': self.valid_reps,
            'left_reps': 0,
        }
        
        if rep_detected:
            self.prev_reps = analyzer_reps
            result['rep_detected'] = True
            
            valid, error_code, error_parts = self.validator.validate_rep(
                front_metrics, profile_metrics
            )
            
            if valid:
                self.validator.record_valid_rep()
                self.valid_reps += 1
                result['valid'] = True
                result['right_reps'] = self.valid_reps
            else:
                result['error_type'] = error_code
                result['error_message'] = ERROR_MESSAGES.get(error_code, '')
                result['error_parts'] = error_parts
        
        return result