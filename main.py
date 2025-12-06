import cv2
import numpy as np
from camera import CameraThread
from pose_detection import PoseDetectionThread

cv2.namedWindow('Body detection', cv2.WINDOW_NORMAL)

front_camera = CameraThread(0, 640, 360)
profile_camera = CameraThread('http://192.168.2.23:8080/video', 360, 640)

front_pose = PoseDetectionThread()
profile_pose = PoseDetectionThread()

front_camera.start()
profile_camera.start()
front_pose.start()
profile_pose.start()

while True:
    front_frame = front_camera.get()
    profile_frame = profile_camera.get()
    
    front_pose.process(front_frame)
    profile_pose.process(profile_frame)
    
    front_result = front_pose.get_result()
    profile_result = profile_pose.get_result()
    
    if front_result is not None and profile_result is not None:
        front_result = cv2.copyMakeBorder(
            front_result, 80, 80, 0, 0, 
            cv2.BORDER_CONSTANT, 
            value=[0, 0, 0]
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