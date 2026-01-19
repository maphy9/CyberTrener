from collections import deque


class PoseAnalyzer:
    """Analizuje pozycję na podstawie klatek."""
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


class EnhancedPoseAnalyzer:
    """Zaawansowana analiza pozycji z interpolacją i stabilnością."""
    def __init__(self, calculation_fn, max_history=30, max_interpolation_frames=5):
        self.calculation_fn = calculation_fn
        self.history = deque(maxlen=max_history)
        self.confidence_history = deque(maxlen=max_history)
        self.frames_since_valid = 0
        self.max_interpolation_frames = max_interpolation_frames
        self.numeric_keys = set()
    
    def process_frame(self, results):
        metrics = self.calculation_fn(results, self.history)
        
        if metrics:
            confidence = metrics.get('confidence', 1.0)
            metrics['_interpolated'] = False
            metrics['_frames_interpolated'] = 0
            self.history.append(metrics)
            self.confidence_history.append(confidence)
            self.frames_since_valid = 0
            
            if not self.numeric_keys:
                self._detect_numeric_keys(metrics)
        
        elif self.history and self.frames_since_valid < self.max_interpolation_frames:
            interpolated = self._interpolate_metrics()
            if interpolated:
                interpolated['_interpolated'] = True
                interpolated['_frames_interpolated'] = self.frames_since_valid + 1
                interpolated['confidence'] = max(0.0, 0.5 - self.frames_since_valid * 0.1)
                self.history.append(interpolated)
                self.confidence_history.append(interpolated['confidence'])
            self.frames_since_valid += 1
        else:
            self.frames_since_valid += 1
    
    def _detect_numeric_keys(self, metrics):
        for key, value in metrics.items():
            if key.startswith('_'):
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                self.numeric_keys.add(key)
    
    def _interpolate_metrics(self):
        if len(self.history) < 2:
            if self.history:
                return dict(self.history[-1])
            return None
        
        last = self.history[-1]
        prev = self.history[-2]
        interpolated = {}
        
        for key, value in last.items():
            if key.startswith('_'):
                continue
            
            if key in self.numeric_keys and key in prev:
                prev_val = prev.get(key)
                if prev_val is not None and value is not None:
                    delta = value - prev_val
                    interpolated[key] = value + delta * 0.3
                else:
                    interpolated[key] = value
            else:
                interpolated[key] = value
        
        return interpolated
    
    def get_metrics(self):
        if not self.history:
            return {}
        return self.history[-1]
    
    def get_average_confidence(self, frames=10):
        if not self.confidence_history:
            return 0.0
        recent = list(self.confidence_history)[-frames:]
        return sum(recent) / len(recent)
    
    def is_metric_stable(self, key, threshold=2.0, frames=5):
        if len(self.history) < frames:
            return False
        
        recent_values = []
        for h in list(self.history)[-frames:]:
            val = h.get(key)
            if val is not None:
                recent_values.append(val)
        
        if len(recent_values) < frames:
            return False
        
        return max(recent_values) - min(recent_values) <= threshold
    
    def is_interpolating(self):
        return self.frames_since_valid > 0
    
    def get_interpolation_count(self):
        return self.frames_since_valid
    
    def reset(self):
        self.history.clear()
        self.confidence_history.clear()
        self.frames_since_valid = 0
        self.numeric_keys.clear()