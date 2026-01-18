# Controller for Overhead Press
from .form_checker import OverheadPressFormChecker
from .metrics import OverheadPressMetrics

class OverheadPressController:
    def __init__(self):
        self.form_checker = OverheadPressFormChecker()
        self.metrics = OverheadPressMetrics()

    def check_form(self, pose):
        return self.form_checker.check(pose)

    def calculate_metrics(self, pose_sequence):
        return self.metrics.calculate(pose_sequence)
