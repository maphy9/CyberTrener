import json
import os
from datetime import datetime


CALIBRATION_FILE = 'user_calibration.json'


class CalibrationData:
    def __init__(self):
        self.neutral_trunk_angle = 180
        self.right_min_angle = 30
        self.right_max_angle = 170
        self.left_min_angle = 30
        self.left_max_angle = 170
        self.vertical_tolerance = 25
        self.trunk_tolerance = 20
        
        self.overhead_start_angle = 90
        self.overhead_top_angle = 170
        self.overhead_start_wrist_y = 0.4
        self.overhead_top_wrist_y = 0.2
        self.overhead_arm_sync_tolerance = 25
        self.overhead_trunk_tolerance = 20
        
        self.calibrated = False
        self.calibration_date = None
    
    def calculate_thresholds(self, measurements):
        self.neutral_trunk_angle = measurements.get('neutral_trunk', 180)
        
        right_flex = measurements.get('right_flex_angle', 30)
        right_extend = measurements.get('right_extend_angle', 170)
        left_flex = measurements.get('left_flex_angle', 30)
        left_extend = measurements.get('left_extend_angle', 170)
        
        self.right_min_angle = right_flex + 15
        self.right_max_angle = right_extend - 10
        self.left_min_angle = left_flex + 15
        self.left_max_angle = left_extend - 10
        
        right_verticality = measurements.get('right_verticality', 0)
        left_verticality = measurements.get('left_verticality', 0)
        avg_verticality = (right_verticality + left_verticality) / 2
        self.vertical_tolerance = max(20, avg_verticality + 5)
        
        trunk_deviation = abs(self.neutral_trunk_angle - 180)
        self.trunk_tolerance = max(20, trunk_deviation + 10)
        
        overhead_start = measurements.get('overhead_start_angle', 90)
        overhead_top = measurements.get('overhead_top_angle', 170)
        
        self.overhead_start_angle = overhead_start + 10
        self.overhead_top_angle = overhead_top - 10
        
        self.overhead_start_wrist_y = measurements.get('overhead_start_wrist_y', 0.4)
        self.overhead_top_wrist_y = measurements.get('overhead_top_wrist_y', 0.2)
        
        overhead_sync = measurements.get('overhead_arm_sync', 10)
        self.overhead_arm_sync_tolerance = max(15, overhead_sync + 10)
        
        overhead_trunk = measurements.get('overhead_trunk_deviation', 0)
        self.overhead_trunk_tolerance = max(15, overhead_trunk + 10)
        
        self.calibrated = True
        self.calibration_date = datetime.now().isoformat()
    
    def to_dict(self):
        return {
            'neutral_trunk_angle': self.neutral_trunk_angle,
            'right_min_angle': self.right_min_angle,
            'right_max_angle': self.right_max_angle,
            'left_min_angle': self.left_min_angle,
            'left_max_angle': self.left_max_angle,
            'vertical_tolerance': self.vertical_tolerance,
            'trunk_tolerance': self.trunk_tolerance,
            'overhead_start_angle': self.overhead_start_angle,
            'overhead_top_angle': self.overhead_top_angle,
            'overhead_start_wrist_y': self.overhead_start_wrist_y,
            'overhead_top_wrist_y': self.overhead_top_wrist_y,
            'overhead_arm_sync_tolerance': self.overhead_arm_sync_tolerance,
            'overhead_trunk_tolerance': self.overhead_trunk_tolerance,
            'calibrated': self.calibrated,
            'calibration_date': self.calibration_date
        }
    
    def from_dict(self, data):
        self.neutral_trunk_angle = data.get('neutral_trunk_angle', 180)
        self.right_min_angle = data.get('right_min_angle', 30)
        self.right_max_angle = data.get('right_max_angle', 170)
        self.left_min_angle = data.get('left_min_angle', 30)
        self.left_max_angle = data.get('left_max_angle', 170)
        self.vertical_tolerance = data.get('vertical_tolerance', 25)
        self.trunk_tolerance = data.get('trunk_tolerance', 15)
        self.overhead_start_angle = data.get('overhead_start_angle', 90)
        self.overhead_top_angle = data.get('overhead_top_angle', 170)
        self.overhead_start_wrist_y = data.get('overhead_start_wrist_y', 0.4)
        self.overhead_top_wrist_y = data.get('overhead_top_wrist_y', 0.2)
        self.overhead_arm_sync_tolerance = data.get('overhead_arm_sync_tolerance', 25)
        self.overhead_trunk_tolerance = data.get('overhead_trunk_tolerance', 20)
        self.calibrated = data.get('calibrated', False)
        self.calibration_date = data.get('calibration_date')
    
    def save(self):
        with open(CALIBRATION_FILE, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @staticmethod
    def load():
        if not os.path.exists(CALIBRATION_FILE):
            return None
        
        try:
            with open(CALIBRATION_FILE, 'r') as f:
                data = json.load(f)
            
            calibration = CalibrationData()
            calibration.from_dict(data)
            return calibration
        except Exception as e:
            print(f"Error loading calibration: {e}")
            return None