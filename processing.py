import cv2
import time

def process_camera_streams(socketio, front_stream, profile_stream, stop_event):
    while not stop_event.is_set():
        front_frame = front_stream.get()
        profile_frame = profile_stream.get()

        if front_frame is None or profile_frame is None:
            continue

        _, front_img = cv2.imencode('.jpg', front_frame)
        _, profile_img = cv2.imencode('.jpg', profile_frame)

        socketio.emit('front-frame', front_img.tobytes())
        socketio.emit('profile-frame', profile_img.tobytes())

        time.sleep(0.1)

    front_stream.stop()
    profile_stream.stop()
    