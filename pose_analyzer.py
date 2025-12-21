from collections import deque


class PoseAnalyzer:
    def __init__(self, calculation_fn, validation_fn, max_history=30):
        self.calculation_fn = calculation_fn
        self.validation_fn = validation_fn
        self.history = deque(maxlen=max_history)
        self.last_validation_error = None
    
    def process_frame(self, results):
        metrics = self.calculation_fn(results, self.history)
        if metrics:
            self.history.append(metrics)
    
    def get_metrics(self):
        if not self.history:
            return {}
        metrics = self.history[-1]
        self.last_validation_error = self.validation_fn(metrics)
        return metrics
    
    def get_validation_error(self):
        return self.last_validation_error