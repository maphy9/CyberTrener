import time
import cv2
from threading import Thread, Lock

class CameraStream:
    def __init__(self, source, width, height):
        self.stream = cv2.VideoCapture(source)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, height)
        self.frame = None
        self.lock = Lock()
        self.running = False
    
    def start(self):
        self.running = True
        Thread(target=self._read_video_stream, daemon=True).start()
        return self

    def _read_video_stream(self):
        while self.running:
            ret, frame = self.stream.read()
            if ret:
                with self.lock:
                    self.frame = frame
            time.sleep(0.01)
    
    def get(self):
        with self.lock:
            return self.frame
        
    def stop(self):
        self.running = False
        self.stream.release()