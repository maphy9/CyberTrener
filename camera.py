import time
import cv2
from threading import Thread, Lock

class CameraStream:
    def __init__(self, source, width, height):
        self.stream = cv2.VideoCapture(source)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.frame = None
        self.lock = Lock()
        self.running = False
        self.thread = None
        self.is_connected = True
        self.consecutive_failures = 0
        self.was_read = True
    
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
                    self.was_read = False
            else:
                self.consecutive_failures += 1
                if self.consecutive_failures > 60:
                    self.is_connected = False
                    self.running = False
    
    def get(self):
        with self.lock:
            previous_was_read = self.was_read
            self.was_read = True
            return self.frame, previous_was_read
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.stream.release()