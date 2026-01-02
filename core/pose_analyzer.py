from collections import deque


class PoseAnalyzer:
    def __init__(self, calculation_fn, max_history=30):
        self.calculation_fn = calculation_fn
        self.history = deque(maxlen=max_history)
    
    def process_frame(self, results):
        metrics = self.calculation_fn(results, self.history)
        if metrics:
            self.history.append(metrics)
    
    def get_metrics(self):
        if not self.history:
            return {}
        return self.history[-1]