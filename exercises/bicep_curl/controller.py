from core.pose_analyzer import EnhancedPoseAnalyzer
from exercises.bicep_curl.metrics import calculate_front_view, calculate_profile_view
from exercises.bicep_curl.form_checker import AlternatingBicepCurlValidator, ERROR_MESSAGES


class BicepCurlController:
    def __init__(self, calibration=None):
        self.front_analyzer = EnhancedPoseAnalyzer(calculate_front_view)
        self.profile_analyzer = EnhancedPoseAnalyzer(calculate_profile_view)
        self.validator = AlternatingBicepCurlValidator(calibration)
        
        self.prev_right_reps = 0
        self.prev_left_reps = 0
        self.valid_right_reps = 0
        self.valid_left_reps = 0
        
        if calibration:
            print(f"Using calibration: flex {calibration.right_min_angle}-{calibration.right_max_angle}, vertical tol: {calibration.vertical_tolerance}")
    
    def process_frames(self, front_results, profile_results):
        self.front_analyzer.process_frame(front_results)
        self.profile_analyzer.process_frame(profile_results)
        
        front_metrics = self.front_analyzer.get_metrics()
        profile_metrics = self.profile_analyzer.get_metrics()
        
        self.validator.check_simultaneous_flexion(front_metrics)
        
        analyzer_right_reps = max(
            front_metrics.get('right_reps', 0),
            profile_metrics.get('right_reps', 0)
        )
        analyzer_left_reps = front_metrics.get('left_reps', 0)
        
        right_rep_detected = analyzer_right_reps > self.prev_right_reps
        left_rep_detected = analyzer_left_reps > self.prev_left_reps
        
        result = {
            'rep_detected': False,
            'valid': False,
            'error_message': None,
            'error_parts': [],
            'right_reps': self.valid_right_reps,
            'left_reps': self.valid_left_reps
        }
        
        if right_rep_detected and left_rep_detected:
            self.prev_right_reps = analyzer_right_reps
            self.prev_left_reps = analyzer_left_reps
            result['rep_detected'] = True
            result['valid'] = False
            result['error_type'] = 'both_arms_flexed'
            result['error_message'] = ERROR_MESSAGES['both_arms_flexed']
            result['error_parts'] = ['left_arm', 'right_arm']
            result['right_reps'] = self.valid_right_reps
            result['left_reps'] = self.valid_left_reps
            
        elif right_rep_detected:
            self.prev_right_reps = analyzer_right_reps
            result['rep_detected'] = True
            
            valid, error_code, error_parts = self.validator.validate_rep(
                'right', front_metrics, profile_metrics
            )
            
            if valid:
                self.validator.record_valid_rep('right')
                self.valid_right_reps += 1
                result['valid'] = True
                result['right_reps'] = self.valid_right_reps
            else:
                result['error_type'] = error_code
                result['error_message'] = ERROR_MESSAGES.get(error_code, '')
                result['error_parts'] = error_parts
                
        elif left_rep_detected:
            self.prev_left_reps = analyzer_left_reps
            result['rep_detected'] = True
            
            valid, error_code, error_parts = self.validator.validate_rep(
                'left', front_metrics, profile_metrics
            )
            
            if valid:
                self.validator.record_valid_rep('left')
                self.valid_left_reps += 1
                result['valid'] = True
                result['left_reps'] = self.valid_left_reps
            else:
                result['error_type'] = error_code
                result['error_message'] = ERROR_MESSAGES.get(error_code, '')
                result['error_parts'] = error_parts
        
        return result