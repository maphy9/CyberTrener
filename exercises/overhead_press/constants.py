# exercises/overhead_press/constants.py

# Angle thresholds for overhead press movement
FRONT_FLEX_THRESHOLD = 90      # Bottom position (weights at shoulder level)
FRONT_EXTEND_THRESHOLD = 160   # Top position (weights overhead)
PROFILE_FLEX_THRESHOLD = 90
PROFILE_EXTEND_THRESHOLD = 160

# Stability requirements
STABILITY_FRAMES = 3

# Smoothing factors
FRONT_ANGLE_SMOOTHING = 0.9
PROFILE_ANGLE_SMOOTHING = 0.9
PROFILE_TRUNK_SMOOTHING = 0.5

# Form validation thresholds
ARM_SYNC_THRESHOLD = 20        # Max angle difference between arms
TRUNK_ANGLE_THRESHOLD = 15     # Max trunk tilt from vertical
ELBOW_FORWARD_MIN = 30         # Min angle for elbows forward position