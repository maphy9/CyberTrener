import cv2
import mediapipe as mp
from camera import CameraThread
import numpy as np
from threading import Thread

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

class PoseThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.input_frame = None
        self.output_frame = None
        self.stopped = False
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        
    def run(self):
        while not self.stopped:
            if self.input_frame is not None:
                frame = self.input_frame.copy()
                frame.flags.writeable = False
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.pose.process(frame)
                frame.flags.writeable = True
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing.DrawingSpec(color=(245,117,66), thickness=1, circle_radius=1),
                    connection_drawing_spec=mp_drawing.DrawingSpec(color=(245,66,230), thickness=1, circle_radius=1)
                )
                self.output_frame = cv2.flip(frame, 1)
                
    def process(self, frame):
        self.input_frame = frame
        
    def get_result(self):
        return self.output_frame
        
    def stop(self):
        self.stopped = True
        self.pose.close()

cv2.namedWindow('Body detection', cv2.WINDOW_NORMAL)

front_camera = CameraThread(0, 320, 240)
profile_camera = CameraThread('http://192.168.2.23:8080/video', 240, 320)

front_pose = PoseThread()
profile_pose = PoseThread()

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
        front_result = cv2.copyMakeBorder(front_result, 40, 40, 0, 0, cv2.BORDER_CONSTANT, value=[0,0,0])
        cv2.imshow('Body detection', np.hstack((front_result, profile_result)))
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

front_camera.stop()
profile_camera.stop()
front_pose.stop()
profile_pose.stop()
cv2.destroyAllWindows()