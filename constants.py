from dotenv import load_dotenv
from os import getenv

load_dotenv()


# ===============
# CAMERA SETTINGS
# ===============

CAMERA_FPS_LIMIT = 30   # The minimum fps for front and profile cameras
FRONT_CAMERA_WIDTH = 640
FRONT_CAMERA_HEIGHT = 360
PROFILE_CAMERA_WIDTH = 360
PROFILE_CAMERA_HEIGHT = 640

PROFILE_CAMERA_IP = getenv('PROFILE_CAMERA_IP')
PROFILE_CAMERA_PORT = getenv('PROFILE_CAMERA_PORT')
PROFILE_CAMERA_URL = f'http://{PROFILE_CAMERA_IP}:{PROFILE_CAMERA_PORT}/video'