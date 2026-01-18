import numpy as np
from core.pose_analyzer import PoseAnalyzer
from exercises.bicep_curl.metrics import calculate_front_view, calculate_profile_view
from exercises.overhead_press.metrics import (
    calculate_front_view as calculate_overhead_front,
    calculate_profile_view as calculate_overhead_profile
)
from calibration.data import CalibrationData


class MeasurementBuffer:
    def __init__(self, buffer_size=20, max_std_dev=3.0):
        self.buffer_size = buffer_size
        self.max_std_dev = max_std_dev
        self.buffers = {}
    
    def add(self, key, value):
        if value is None:
            return None, False
        
        if key not in self.buffers:
            self.buffers[key] = []
        
        self.buffers[key].append(value)
        
        if len(self.buffers[key]) >= self.buffer_size:
            values = np.array(self.buffers[key])
            mean = np.mean(values)
            std = np.std(values)
            
            filtered = values[np.abs(values - mean) <= 2 * std]
            
            if len(filtered) >= self.buffer_size // 2 and np.std(filtered) <= self.max_std_dev:
                return float(np.mean(filtered)), True
            else:
                self.buffers[key] = self.buffers[key][-10:]
                return None, False
        
        return None, False
    
    def clear(self, key=None):
        if key:
            self.buffers.pop(key, None)
        else:
            self.buffers = {}
    
    def get_progress(self, key):
        if key not in self.buffers:
            return 0.0
        return len(self.buffers[key]) / self.buffer_size


class CalibrationController:
    def __init__(self):
        # Bicep curl analyzers
        self.front_analyzer = PoseAnalyzer(calculate_front_view)
        self.profile_analyzer = PoseAnalyzer(calculate_profile_view)
        # Overhead press analyzers
        self.overhead_front_analyzer = PoseAnalyzer(calculate_overhead_front)
        self.overhead_profile_analyzer = PoseAnalyzer(calculate_overhead_profile)
        
        self.current_step = 'neutral'
        self.measurements = {}
        self.measurement_buffer = MeasurementBuffer(buffer_size=20, max_std_dev=3.0)
        self.stable_frames = 0
        self.REQUIRED_STABLE_FRAMES = 30
    
    def get_instructions(self):
        instructions = {
            'neutral': 'Stań w pozycji neutralnej z ramionami wzdłuż ciała',
            'right_flex': 'Ugnij prawą rękę maksymalnie do góry',
            'right_extend': 'Wyprostuj prawą rękę całkowicie',
            'left_flex': 'Ugnij lewą rękę maksymalnie do góry',
            'left_extend': 'Wyprostuj lewą rękę całkowicie',
            'overhead_start': 'Podnieś obie ręce na wysokość barków',
            'overhead_top': 'Wyciśnij ręce nad głowę',
            'complete': 'Kalibracja zakończona!'
        }
        return instructions.get(self.current_step, '')
    
    def get_current_progress(self):
        progress_keys = {
            'neutral': 'neutral_trunk',
            'right_flex': 'right_flex_angle',
            'right_extend': 'right_extend_angle',
            'left_flex': 'left_flex_angle',
            'left_extend': 'left_extend_angle',
            'overhead_start': 'overhead_start_angle',
            'overhead_top': 'overhead_top_angle'
        }
        key = progress_keys.get(self.current_step)
        if key:
            return self.measurement_buffer.get_progress(key)
        return 1.0 if self.current_step == 'complete' else 0.0
    
    def process_frames(self, front_results, profile_results):
        # Process bicep curl metrics
        self.front_analyzer.process_frame(front_results)
        self.profile_analyzer.process_frame(profile_results)
        
        # Process overhead press metrics
        self.overhead_front_analyzer.process_frame(front_results)
        self.overhead_profile_analyzer.process_frame(profile_results)
        
        front_metrics = self.front_analyzer.get_metrics()
        profile_metrics = self.profile_analyzer.get_metrics()
        overhead_front_metrics = self.overhead_front_analyzer.get_metrics()
        overhead_profile_metrics = self.overhead_profile_analyzer.get_metrics()
        
        if self.current_step == 'neutral':
            trunk_angle = profile_metrics.get('trunk_angle')
            mean_value, is_stable = self.measurement_buffer.add('neutral_trunk', trunk_angle)
            if is_stable:
                self.measurements['neutral_trunk'] = mean_value
                self.measurement_buffer.clear()
                self.current_step = 'right_flex'
                return True, "Teraz ugnij prawą rękę"
        
        elif self.current_step == 'right_flex':
            right_angle = front_metrics.get('right_angle')
            right_phase = front_metrics.get('right_phase')
            right_vert = front_metrics.get('right_verticality', 0)
            
            if right_phase == 'flexed':
                mean_value, is_stable = self.measurement_buffer.add('right_flex_angle', right_angle)
                if is_stable:
                    self.measurements['right_flex_angle'] = mean_value
                    self.measurements['right_verticality'] = right_vert
                    self.measurement_buffer.clear()
                    self.current_step = 'right_extend'
                    return True, "Teraz wyprostuj prawą rękę"
        
        elif self.current_step == 'right_extend':
            right_angle = front_metrics.get('right_angle')
            right_phase = front_metrics.get('right_phase')
            
            if right_phase == 'extended':
                mean_value, is_stable = self.measurement_buffer.add('right_extend_angle', right_angle)
                if is_stable:
                    self.measurements['right_extend_angle'] = mean_value
                    self.measurement_buffer.clear()
                    self.current_step = 'left_flex'
                    return True, "Teraz ugnij lewą rękę"
        
        elif self.current_step == 'left_flex':
            left_angle = front_metrics.get('left_angle')
            left_phase = front_metrics.get('left_phase')
            left_vert = front_metrics.get('left_verticality', 0)
            
            if left_phase == 'flexed':
                mean_value, is_stable = self.measurement_buffer.add('left_flex_angle', left_angle)
                if is_stable:
                    self.measurements['left_flex_angle'] = mean_value
                    self.measurements['left_verticality'] = left_vert
                    self.measurement_buffer.clear()
                    self.current_step = 'left_extend'
                    return True, "Teraz wyprostuj lewą rękę"
        
        elif self.current_step == 'left_extend':
            left_angle = front_metrics.get('left_angle')
            left_phase = front_metrics.get('left_phase')
            
            if left_phase == 'extended':
                mean_value, is_stable = self.measurement_buffer.add('left_extend_angle', left_angle)
                if is_stable:
                    self.measurements['left_extend_angle'] = mean_value
                    self.measurement_buffer.clear()
                    self.current_step = 'overhead_start'
                    return True, "Teraz podnieś obie ręce na wysokość barków"
        
        elif self.current_step == 'overhead_start':
            # Check if arms are at shoulder level (around 90 degrees elbow angle)
            avg_angle = overhead_front_metrics.get('avg_angle', 180)
            right_wrist_y = overhead_front_metrics.get('right_wrist_y', 0.5)
            left_wrist_y = overhead_front_metrics.get('left_wrist_y', 0.5)
            arm_sync_diff = overhead_front_metrics.get('arm_sync_diff', 0)
            trunk_angle = overhead_profile_metrics.get('trunk_angle', 180)
            
            # Arms should be bent at roughly 90 degrees (at shoulder level)
            if 70 <= avg_angle <= 110:
                mean_angle, angle_stable = self.measurement_buffer.add('overhead_start_angle', avg_angle)
                
                if angle_stable:
                    self.measurements['overhead_start_angle'] = mean_angle
                    # Store wrist Y positions (average of both wrists)
                    self.measurements['overhead_start_wrist_y'] = (right_wrist_y + left_wrist_y) / 2
                    self.measurements['overhead_arm_sync'] = arm_sync_diff
                    self.measurements['overhead_trunk_deviation'] = abs(trunk_angle - 180)
                    self.measurement_buffer.clear()
                    self.current_step = 'overhead_top'
                    return True, "Teraz wyciśnij ręce maksymalnie nad głowę"
        
        elif self.current_step == 'overhead_top':
            # Check if arms are fully extended overhead
            avg_angle = overhead_front_metrics.get('avg_angle', 90)
            right_wrist_y = overhead_front_metrics.get('right_wrist_y', 0.5)
            left_wrist_y = overhead_front_metrics.get('left_wrist_y', 0.5)
            
            # Arms should be nearly straight (extended overhead)
            if avg_angle >= 155:
                mean_angle, angle_stable = self.measurement_buffer.add('overhead_top_angle', avg_angle)
                
                if angle_stable:
                    self.measurements['overhead_top_angle'] = mean_angle
                    # Store wrist Y position at top
                    self.measurements['overhead_top_wrist_y'] = (right_wrist_y + left_wrist_y) / 2
                    self.measurement_buffer.clear()
                    self.current_step = 'complete'
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