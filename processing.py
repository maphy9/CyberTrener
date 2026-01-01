import cv2
import mediapipe as mp
from pose_analyzer import PoseAnalyzer
from curl_metrics import calculate_front_bicep_curl, calculate_profile_bicep_curl
from exercise_validators import validate_front_bicep_curl, validate_profile_bicep_curl
from audio import AudioHandler
import speech_recognition as sr
from threading import Thread, Event
from collections import deque
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


def listen_for_commands(audio_handler, stop_event, analyzing_event):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
    
    while not stop_event.is_set():
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
            
            text = recognizer.recognize_google(audio, language="pl-PL").lower() # type: ignore
            
            if "start" in text and not analyzing_event.is_set():
                audio_handler.queue_speech("Rozpoczynam")
                analyzing_event.set()
            elif "stop" in text and analyzing_event.is_set():
                audio_handler.queue_speech("Zatrzymuję")
                analyzing_event.clear()
                
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except Exception as e:
            print(f"Speech recognition error: {e}")
            continue


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
    
    audio_handler = AudioHandler()
    analyzing_event = Event()
    
    audio_handler.queue_speech("Powiedz 'start' aby rozpocząć")
    
    speech_thread = Thread(
        target=listen_for_commands,
        args=(audio_handler, stop_event, analyzing_event),
        daemon=True
    )
    speech_thread.start()
    
    socketio.emit('status', {'state': 'waiting'})
    
    front_analyzer = PoseAnalyzer(calculate_front_bicep_curl, validate_front_bicep_curl)
    profile_analyzer = PoseAnalyzer(calculate_profile_bicep_curl, validate_profile_bicep_curl)
    
    prev_right_reps = 0
    prev_left_reps = 0
    valid_right_reps = 0
    valid_left_reps = 0
    rep_history = deque(maxlen=10)
    last_error_time = {}
    ERROR_REPEAT_DELAY = 5.0
    
    front_metrics = {}
    profile_metrics = {}
    
    prev_analyzing_state = False

    while not stop_event.is_set():
        front_frame, front_was_read = front_stream.get()
        profile_frame, profile_was_read = profile_stream.get()
        if front_frame is None or profile_frame is None:
            continue

        if analyzing_event.is_set():
            if not prev_analyzing_state:
                socketio.emit('status', {'state': 'analyzing'})
                prev_analyzing_state = True
            
            if not front_was_read:
                front_frame, front_metrics = process_front_frame(front_frame, front_pose, front_analyzer)

            if not profile_was_read:
                profile_frame, profile_metrics = process_profile_frame(profile_frame, profile_pose, profile_analyzer)

            analyzer_right_reps = max(front_metrics.get('right_reps', 0), profile_metrics.get('right_reps', 0))
            analyzer_left_reps = front_metrics.get('left_reps', 0)
            
            right_stance_valid = front_metrics.get('right_stance_valid', True)
            left_stance_valid = front_metrics.get('left_stance_valid', True)
            
            right_rep_detected = analyzer_right_reps > prev_right_reps
            left_rep_detected = analyzer_left_reps > prev_left_reps
            
            if right_rep_detected and left_rep_detected:
                audio_handler.queue_speech("Pracuj naprzemiennie")
                prev_right_reps = analyzer_right_reps
                prev_left_reps = analyzer_left_reps
            elif right_rep_detected:
                if not right_stance_valid:
                    audio_handler.queue_speech("Trzymaj rękę pionowo")
                    prev_right_reps = analyzer_right_reps
                elif rep_history and rep_history[-1] == 'right':
                    audio_handler.queue_speech("Pracuj naprzemiennie")
                    prev_right_reps = analyzer_right_reps
                else:
                    rep_history.append('right')
                    valid_right_reps += 1
                    audio_handler.queue_beep()
                    prev_right_reps = analyzer_right_reps
            elif left_rep_detected:
                if not left_stance_valid:
                    audio_handler.queue_speech("Trzymaj rękę pionowo")
                    prev_left_reps = analyzer_left_reps
                elif rep_history and rep_history[-1] == 'left':
                    audio_handler.queue_speech("Pracuj naprzemiennie")
                    prev_left_reps = analyzer_left_reps
                else:
                    rep_history.append('left')
                    valid_left_reps += 1
                    audio_handler.queue_beep()
                    prev_left_reps = analyzer_left_reps
            
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
                'right_reps': valid_right_reps,
                'left_reps': valid_left_reps,
                'errors': errors
            }
            socketio.emit('metrics', metrics_data)
        else:
            if prev_analyzing_state:
                socketio.emit('status', {'state': 'waiting'})
                prev_analyzing_state = False
            
            front_image_rgb = cv2.cvtColor(front_frame, cv2.COLOR_BGR2RGB)
            front_image_rgb.flags.writeable = False
            front_results = front_pose.process(front_image_rgb)
            front_image_rgb.flags.writeable = True
            mp_drawing.draw_landmarks(
                front_frame, front_results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=landmark_spec
            )
            
            profile_image_rgb = cv2.cvtColor(profile_frame, cv2.COLOR_BGR2RGB)
            profile_image_rgb.flags.writeable = False
            profile_results = profile_pose.process(profile_image_rgb)
            profile_image_rgb.flags.writeable = True
            mp_drawing.draw_landmarks(
                profile_frame, profile_results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=landmark_spec
            )

        _, front_img = cv2.imencode('.jpg', front_frame)
        _, profile_img = cv2.imencode('.jpg', profile_frame)

        socketio.emit('front-frame', front_img.tobytes())
        socketio.emit('profile-frame', profile_img.tobytes())

    socketio.emit('session-ended')
    audio_handler.stop()
    front_stream.stop()
    profile_stream.stop()