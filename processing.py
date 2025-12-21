import cv2
import mediapipe as mp
from pose_analyzer import FrontAnalyzer, ProfileAnalyzer
from exercise_validators import validate_front_bicep_curl, validate_profile_bicep_curl
from audio import AudioHandler
import time

mp_pose = mp.solutions.pose # type: ignore
mp_drawing = mp.solutions.drawing_utils # type: ignore
landmark_spec = mp_drawing.DrawingSpec(
    color=(245, 117, 66), 
    thickness=1, 
    circle_radius=1
)

def process_front_frame(frame, pose, analyzer):
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image_rgb.flags.writeable = False
    results = pose.process(image_rgb)
    image_rgb.flags.writeable = True
    mp_drawing.draw_landmarks(
        frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
        landmark_drawing_spec=landmark_spec
    )
    
    analyzer.process_frame(results)
    metrics = analyzer.get_metrics()
    return frame, metrics


def process_profile_frame(frame, pose, analyzer):
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image_rgb.flags.writeable = False
    results = pose.process(image_rgb)
    image_rgb.flags.writeable = True
    mp_drawing.draw_landmarks(
        frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
        landmark_drawing_spec=landmark_spec
    )
    
    analyzer.process_frame(results)
    metrics = analyzer.get_metrics()
    return frame, metrics


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
    
    front_analyzer = FrontAnalyzer(validate_front_bicep_curl)
    profile_analyzer = ProfileAnalyzer(validate_profile_bicep_curl)
    audio_handler = AudioHandler()
    
    prev_right_reps = 0
    prev_left_reps = 0
    last_error_time = {}
    ERROR_REPEAT_DELAY = 5.0

    while not stop_event.is_set():
        front_frame = front_stream.get()
        profile_frame = profile_stream.get()
        if front_frame is None or profile_frame is None:
            continue

        front_frame, front_metrics = process_front_frame(front_frame, front_pose, front_analyzer)
        profile_frame, profile_metrics = process_profile_frame(profile_frame, profile_pose, profile_analyzer)

        _, front_img = cv2.imencode('.jpg', front_frame)
        _, profile_img = cv2.imencode('.jpg', profile_frame)

        right_reps = max(front_metrics['right_reps'], profile_metrics['right_reps'])
        left_reps = front_metrics['left_reps']
        
        if right_reps > prev_right_reps:
            audio_handler.queue_beep()
            prev_right_reps = right_reps
        
        if left_reps > prev_left_reps:
            audio_handler.queue_beep()
            prev_left_reps = left_reps
        
        errors = []
        if front_analyzer.get_validation_error():
            errors.append(front_analyzer.get_validation_error())
        if profile_analyzer.get_validation_error():
            errors.append(profile_analyzer.get_validation_error())
        
        current_time = time.time()
        for error in errors:
            last_time = last_error_time.get(error, 0)
            if current_time - last_time >= ERROR_REPEAT_DELAY:
                audio_handler.queue_speech(error)
                last_error_time[error] = current_time

        metrics_data = {
            'right_reps': right_reps,
            'left_reps': left_reps,
            'errors': errors
        }

        socketio.emit('front-frame', front_img.tobytes())
        socketio.emit('profile-frame', profile_img.tobytes())
        socketio.emit('metrics', metrics_data)

    audio_handler.stop()
    front_stream.stop()
    profile_stream.stop()