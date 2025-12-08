import cv2
import numpy as np
from camera import CameraThread
from pose_detection import PoseDetectionThread

FRONT_WIDTH = 640
FRONT_HEIGHT = 360
PROFILE_WIDTH = 360
PROFILE_HEIGHT = 640
BORDER_PADDING = (PROFILE_HEIGHT - FRONT_HEIGHT) // 2

cv2.namedWindow('Body detection', cv2.WINDOW_NORMAL)

front_camera = CameraThread(0, FRONT_WIDTH, FRONT_HEIGHT)
profile_camera = CameraThread('http://192.168.2.23:8080/video', PROFILE_WIDTH, PROFILE_HEIGHT)
front_pose = PoseDetectionThread()
profile_pose = PoseDetectionThread()

front_camera.start()
profile_camera.start()
front_pose.start()
profile_pose.start()

while True:
    front_frame = front_camera.get()
    profile_frame = profile_camera.get()

    if front_frame is not None:
        front_pose.process(front_frame)

    if profile_frame is not None:
        profile_pose.process(profile_frame)

    front_result = front_pose.get_result()
    profile_result = profile_pose.get_result()

    if front_result is not None and profile_result is not None:
        front_result = cv2.copyMakeBorder(
            front_result, BORDER_PADDING, BORDER_PADDING, 0, 0,
            cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )

        combined_view = np.hstack((front_result, profile_result))
        cv2.imshow('Body detection', combined_view)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

front_camera.stop()
profile_camera.stop()
front_pose.stop()
profile_pose.stop()
cv2.destroyAllWindows()