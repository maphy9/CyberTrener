import cv2
import mediapipe as mp
from threading import Thread
from queue import Queue, Empty

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

class PoseDetectionThread(Thread):
    def __init__(self):
        super().__init__(daemon=True)

        self.input_queue = Queue(maxsize=1)
        self.output_frame = None
        self.stopped = False

        self.pose = mp_pose.Pose()
        self.landmark_spec = mp_drawing.DrawingSpec(color=(245,117,66), thickness=1)
        self.connection_spec = mp_drawing.DrawingSpec(color=(245,66,230), thickness=1)

    def run(self):
        while not self.stopped:
            try:
                frame = self.input_queue.get(timeout=1)
            except Empty:
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb)
            frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

            if results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    self.landmark_spec,
                    self.connection_spec
                )

            frame = cv2.flip(frame, 1)
            self.output_frame = frame

    def process(self, frame):
        if not self.input_queue.empty():
            self.input_queue.get_nowait()
        self.input_queue.put(frame)

    def get_result(self):
        return self.output_frame

    def stop(self):
        self.stopped = True
        self.pose.close()
