import cv2
import mediapipe as mp
from threading import Thread

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

class PoseDetectionThread(Thread):
    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5, 
                 model_complexity=1, flip_output=True):
        Thread.__init__(self)
        self.input_frame = None
        self.output_frame = None
        self.stopped = False
        self.flip_output = flip_output
        
        self.pose = mp_pose.Pose(
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            model_complexity=model_complexity
        )
        
        self.landmark_spec = mp_drawing.DrawingSpec(
            color=(245, 117, 66), 
            thickness=1, 
            circle_radius=1
        )
        self.connection_spec = mp_drawing.DrawingSpec(
            color=(245, 66, 230), 
            thickness=1, 
            circle_radius=1
        )
        
    def run(self):
        while not self.stopped:
            if self.input_frame is None:
                continue
                
            frame = self.input_frame
            frame.flags.writeable = False
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)
            
            frame.flags.writeable = True
            frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.landmark_spec,
                    connection_drawing_spec=self.connection_spec
                )
            
            if self.flip_output:
                frame = cv2.flip(frame, 1)
                
            self.output_frame = frame
                
    def process(self, frame):
        self.input_frame = frame
        
    def get_result(self):
        return self.output_frame
        
    def stop(self):
        self.stopped = True
        self.pose.close()