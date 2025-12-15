import time
import cv2
from threading import Thread, Lock

class CameraStream:
    def __init__(self, source, width, height):
        self.stream = cv2.VideoCapture(source)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.frame = None
        self.lock = Lock()
        self.running = False
        self.thread = None
        self.is_connected = True
        self.consecutive_failures = 0
    
    def start(self):
        self.running = True
        self.thread = Thread(target=self._read_video_stream, daemon=True)
        self.thread.start()
        return self

    def _read_video_stream(self):
        while self.running:
            ret, frame = self.stream.read()
            if ret:
                with self.lock:
                    self.frame = frame
                    self.consecutive_failures = 0
            else:
                self.consecutive_failures += 1
                if self.consecutive_failures > 30:
                    self.is_connected = False
                    self.running = False
            time.sleep(0.01)
    
    def get(self):
        with self.lock:
            return self.frame
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.stream.release()