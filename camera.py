from threading import Thread
from queue import Queue, Empty
import cv2

class CameraThread(Thread):
    def __init__(self, source, w=None, h=None):
        super().__init__(daemon=True)
        self.source = source
        self.w = w
        self.h = h
        self.queue = Queue(maxsize=1)
        self.stopped = False

    def run(self):
        cap = cv2.VideoCapture(self.source)
        if self.w:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.w)
        if self.h:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.h)

        while not self.stopped:
            ret, frame = cap.read()
            if not ret:
                continue
            if not self.queue.empty():
                self.queue.get_nowait()
            self.queue.put(frame)

        cap.release()

    def get(self):
        try:
            return self.queue.get(timeout=1)
        except Empty:
            return None

    def stop(self):
        self.stopped = True
