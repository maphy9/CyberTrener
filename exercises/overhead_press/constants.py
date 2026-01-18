# exercises/overhead_press/constants.py

# Angle thresholds for overhead press movement (default values, overridden by calibration)
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

# Form validation thresholds (defaults, overridden by calibration)
ARM_SYNC_THRESHOLD = 20        # Max angle difference between arms
TRUNK_ANGLE_THRESHOLD = 15     # Max trunk tilt from vertical
ELBOW_FORWARD_MIN = 30         # Min angle for elbows forward position

# Y-position thresholds for active exercise zone
# These define the vertical band where rep counting is active
# Wrist Y positions are relative (0 = top of frame, 1 = bottom)
ACTIVE_ZONE_WRIST_Y_MAX = 0.5   # Wrists must be above this Y to be in active zone (at or above shoulders)
ACTIVE_ZONE_WRIST_Y_MIN = 0.1   # Minimum Y position (very top of frame)

# Shoulder reference for determining active zone
SHOULDER_Y_OFFSET = 0.05  # Wrists should be at or above (shoulder_y - offset) to count

# Rep counting direction
# For overhead press: rep is counted when RETURNING to start position (flexed/90°)
REP_COUNT_AT_TOP = False

# Movement start detection
# User must start with arms in starting position (at shoulder level) before counting begins
REQUIRE_START_POSITION = True
START_POSITION_MIN_ANGLE = 70   # Arms bent at least this much
START_POSITION_MAX_ANGLE = 110  # Arms not more extended than this