from threading import Thread
from queue import Queue
import cv2

class CameraThread(Thread):
    def __init__(self, camera_source, w=None, h=None):
        Thread.__init__(self)
        self.source = camera_source
        self.w = w
        self.h = h
        self.queue = Queue()
        self.stopped = False
        self.last_frame = None
        
    def run(self):
        cap = cv2.VideoCapture(self.source)
        if self.w is not None:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.w)
        if self.h is not None:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.h)
        while not self.stopped:
            ret, frame = cap.read()
            if ret:
                self.last_frame = frame
                self.queue.put(frame)
        cap.release()
    
    def get(self):
        if self.last_frame is None:
            self.last_frame = self.queue.get()
        else:
            try:
                self.last_frame = self.queue.get_nowait()
            except:
                pass
        return self.last_frame
    
    def stop(self):
        self.stopped = True