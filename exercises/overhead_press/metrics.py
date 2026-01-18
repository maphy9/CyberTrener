# Metrics for Overhead Press
class OverheadPressMetrics:
    def calculate(self, pose_sequence):
        # Example: Count reps based on arm extension
        reps = 0
        in_press = False
        for pose in pose_sequence:
            form = pose['form']
            if form['form_ok'] and not in_press:
                reps += 1
                in_press = True
            elif not form['form_ok']:
                in_press = False
        return {'reps': reps}
