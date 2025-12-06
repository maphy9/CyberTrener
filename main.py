import cv2
import mediapipe as mp
import time
from collections import deque
from camera import CameraThread

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_pose = mp.solutions.pose

with mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=1
    ) as pose:
    cv2.namedWindow('Body detection', cv2.WINDOW_NORMAL)

    frontal_camera = CameraThread(0, 320, 240)
    frontal_camera.start()
    
    while True:
        front_frame = frontal_camera.get()

        front_frame.flags.writeable = False
        front_frame = cv2.cvtColor(front_frame, cv2.COLOR_BGR2RGB)
        results = pose.process(front_frame)

        front_frame.flags.writeable = True
        front_frame = cv2.cvtColor(front_frame, cv2.COLOR_RGB2BGR)
        mp_drawing.draw_landmarks(
            front_frame,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing.DrawingSpec(color=(245,117,66), thickness=1, circle_radius=1),
            connection_drawing_spec=mp_drawing.DrawingSpec(color=(245,66,230), thickness=1, circle_radius=1)
        )
        front_frame = cv2.flip(front_frame, 1)

        cv2.imshow('Body detection', front_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    frontal_camera.stop()
    cv2.destroyAllWindows()