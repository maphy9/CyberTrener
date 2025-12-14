import cv2
import mediapipe as mp

mp_pose = mp.solutions.pose # type: ignore
mp_drawing = mp.solutions.drawing_utils # type: ignore
landmark_spec = mp_drawing.DrawingSpec(
    color=(245, 117, 66), 
    thickness=1, 
    circle_radius=1
)

def process_front_frame(frame, pose):
    frame = cv2.flip(frame, 1)
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image_rgb.flags.writeable = False
    results = pose.process(image_rgb)
    image_rgb.flags.writeable = True
    mp_drawing.draw_landmarks(
        frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
        landmark_drawing_spec=landmark_spec
    )
    return frame


def process_profile_frame(frame, pose):
    frame = cv2.flip(frame, 1)
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image_rgb.flags.writeable = False
    results = pose.process(image_rgb)
    image_rgb.flags.writeable = True
    mp_drawing.draw_landmarks(
        frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
        landmark_drawing_spec=landmark_spec
    )
    return frame


def process_camera_streams(socketio, front_stream, profile_stream, stop_event):
    front_pose = mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=0    
    )
    profile_pose = mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=0    
    )

    while not stop_event.is_set():
        front_frame = front_stream.get()
        profile_frame = profile_stream.get()

        if front_frame is None or profile_frame is None:
            continue

        front_frame = process_front_frame(front_frame, front_pose)
        profile_frame = process_profile_frame(profile_frame, profile_pose)

        _, front_img = cv2.imencode('.jpg', front_frame)
        _, profile_img = cv2.imencode('.jpg', profile_frame)

        socketio.emit('front-frame', front_img.tobytes())
        socketio.emit('profile-frame', profile_img.tobytes())

    front_stream.stop()
    profile_stream.stop()