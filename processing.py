import cv2
import mediapipe as mp
from calculations import calculate_front_angles, calculate_profile_angles, smooth_angle
from drawing import draw_arm_landmarks, draw_front_text, draw_profile_text, ARM_LANDMARKS, ARM_CONNECTIONS, PROFILE_LANDMARKS, PROFILE_CONNECTIONS

mp_pose = mp.solutions.pose # type: ignore
mp_drawing = mp.solutions.drawing_utils # type: ignore

def process_single_frame(frame, pose, calc_fn, draw_fn, prev_angles, landmark_indices, connections):
    frame = cv2.flip(frame, 1)
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image_rgb.flags.writeable = False
    results = pose.process(image_rgb)
    image_rgb.flags.writeable = True
    
    if not results.pose_landmarks:
        return frame, results, prev_angles
    
    draw_arm_landmarks(frame, results.pose_landmarks, landmark_indices, connections)
    angles = calc_fn(results.pose_landmarks)
    
    smoothed = {}
    for key, val in angles.items():
        smoothed[key] = smooth_angle(prev_angles.get(key), val)
    
    draw_fn(frame, smoothed)
    
    return frame, results, smoothed

def process_camera_streams(socketio, front_stream, profile_stream, stop_event):
    front_pose = mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=1
    )
    profile_pose = mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=1
    )
    
    prev_front = {}
    prev_profile = {}

    while not stop_event.is_set():
        front_frame = front_stream.get()
        profile_frame = profile_stream.get()

        if front_frame is None or profile_frame is None:
            continue

        front_frame, _, prev_front = process_single_frame(
            front_frame, front_pose, calculate_front_angles, draw_front_text, prev_front, ARM_LANDMARKS, ARM_CONNECTIONS
        )
        profile_frame, _, prev_profile = process_single_frame(
            profile_frame, profile_pose, calculate_profile_angles, draw_profile_text, prev_profile, PROFILE_LANDMARKS, PROFILE_CONNECTIONS
        )

        _, front_img = cv2.imencode('.jpg', front_frame)
        _, profile_img = cv2.imencode('.jpg', profile_frame)

        socketio.emit('front-frame', front_img.tobytes())
        socketio.emit('profile-frame', profile_img.tobytes())

    front_stream.stop()
    profile_stream.stop()