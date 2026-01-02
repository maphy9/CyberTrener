import cv2
import mediapipe as mp
from core.pose_analyzer import PoseAnalyzer
from exercises.bicep_curl.metrics import calculate_front_view, calculate_profile_view
from exercises.bicep_curl.form_checker import AlternatingBicepCurlValidator, ERROR_MESSAGES
from audio import AudioHandler
import speech_recognition as sr
from threading import Thread, Event
import time

mp_pose = mp.solutions.pose # type: ignore

RELEVANT_LANDMARKS = [11, 12, 13, 14, 15, 16, 23, 24]

RELEVANT_CONNECTIONS = [
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (11, 23),
    (12, 24),
    (23, 24),
]

LEFT_ARM_LANDMARKS = [11, 13, 15]
RIGHT_ARM_LANDMARKS = [12, 14, 16]
TRUNK_LANDMARKS = [11, 12, 23, 24]

LEFT_ARM_CONNECTIONS = [(11, 13), (13, 15)]
RIGHT_ARM_CONNECTIONS = [(12, 14), (14, 16)]
TRUNK_CONNECTIONS = [(11, 12), (11, 23), (12, 24), (23, 24)]

def draw_pose_with_errors(frame, results, error_states):
    if not results.pose_landmarks:
        return
    
    landmarks = results.pose_landmarks.landmark
    h, w, _ = frame.shape
    
    current_time = time.time()
    
    left_arm_error = error_states.get('left_arm', 0) > current_time
    right_arm_error = error_states.get('right_arm', 0) > current_time
    trunk_error = error_states.get('trunk', 0) > current_time
    
    for connection in RELEVANT_CONNECTIONS:
        start_idx, end_idx = connection
        start_landmark = landmarks[start_idx]
        end_landmark = landmarks[end_idx]
        
        if start_landmark.visibility > 0.5 and end_landmark.visibility > 0.5:
            start_point = (int(start_landmark.x * w), int(start_landmark.y * h))
            end_point = (int(end_landmark.x * w), int(end_landmark.y * h))
            
            color = (245, 117, 66)
            if connection in LEFT_ARM_CONNECTIONS and left_arm_error:
                color = (0, 0, 255)
            elif connection in RIGHT_ARM_CONNECTIONS and right_arm_error:
                color = (0, 0, 255)
            elif connection in TRUNK_CONNECTIONS and trunk_error:
                color = (0, 0, 255)
            
            cv2.line(frame, start_point, end_point, color, 2)
    
    for idx in RELEVANT_LANDMARKS:
        landmark = landmarks[idx]
        if landmark.visibility > 0.5:
            cx, cy = int(landmark.x * w), int(landmark.y * h)
            
            color = (245, 117, 66)
            if idx in LEFT_ARM_LANDMARKS and left_arm_error:
                color = (0, 0, 255)
            elif idx in RIGHT_ARM_LANDMARKS and right_arm_error:
                color = (0, 0, 255)
            elif idx in TRUNK_LANDMARKS and trunk_error:
                color = (0, 0, 255)
            
            cv2.circle(frame, (cx, cy), 3, color, -1)

def process_frame(frame, pose, analyzer, error_states):
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image_rgb.flags.writeable = False
    results = pose.process(image_rgb)
    image_rgb.flags.writeable = True
    draw_pose_with_errors(frame, results, error_states)
    
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
    
    front_analyzer = PoseAnalyzer(calculate_front_view)
    profile_analyzer = PoseAnalyzer(calculate_profile_view)
    validator = AlternatingBicepCurlValidator()
    
    prev_right_reps = 0
    prev_left_reps = 0
    valid_right_reps = 0
    valid_left_reps = 0
    last_error_spoken = {}
    ERROR_COOLDOWN = 3.0
    error_states = {}
    ERROR_DISPLAY_DURATION = 2.5
    
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
                front_frame, front_metrics = process_frame(front_frame, front_pose, front_analyzer, error_states)

            if not profile_was_read:
                profile_frame, profile_metrics = process_frame(profile_frame, profile_pose, profile_analyzer, error_states)

            analyzer_right_reps = max(front_metrics.get('right_reps', 0), profile_metrics.get('right_reps', 0))
            analyzer_left_reps = front_metrics.get('left_reps', 0)
            
            validator.check_simultaneous_flexion(front_metrics)
            
            right_rep_detected = analyzer_right_reps > prev_right_reps
            left_rep_detected = analyzer_left_reps > prev_left_reps
            
            current_time = time.time()
            
            def speak_error(error_code, error_parts):
                message = ERROR_MESSAGES.get(error_code, '')
                last_spoken = last_error_spoken.get(message, 0)
                if current_time - last_spoken >= ERROR_COOLDOWN:
                    audio_handler.queue_speech(message)
                    last_error_spoken[message] = current_time
                
                for part in error_parts:
                    error_states[part] = current_time + ERROR_DISPLAY_DURATION
            
            if right_rep_detected and left_rep_detected:
                speak_error('both_arms_flexed', ['left_arm', 'right_arm'])
                prev_right_reps = analyzer_right_reps
                prev_left_reps = analyzer_left_reps
            elif right_rep_detected:
                prev_right_reps = analyzer_right_reps
                
                valid, error_code, error_parts = validator.validate_rep('right', front_metrics, profile_metrics)
                
                if not valid:
                    speak_error(error_code, error_parts)
                else:
                    validator.record_valid_rep('right')
                    valid_right_reps += 1
                    audio_handler.queue_beep()
                    
            elif left_rep_detected:
                prev_left_reps = analyzer_left_reps
                
                valid, error_code, error_parts = validator.validate_rep('left', front_metrics, profile_metrics)
                
                if not valid:
                    speak_error(error_code, error_parts)
                else:
                    validator.record_valid_rep('left')
                    valid_left_reps += 1
                    audio_handler.queue_beep()

            metrics_data = {
                'right_reps': valid_right_reps,
                'left_reps': valid_left_reps,
                'errors': []
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
            draw_pose_with_errors(front_frame, front_results, {})
            
            profile_image_rgb = cv2.cvtColor(profile_frame, cv2.COLOR_BGR2RGB)
            profile_image_rgb.flags.writeable = False
            profile_results = profile_pose.process(profile_image_rgb)
            profile_image_rgb.flags.writeable = True
            draw_pose_with_errors(profile_frame, profile_results, {})

        _, front_img = cv2.imencode('.jpg', front_frame)
        _, profile_img = cv2.imencode('.jpg', profile_frame)

        socketio.emit('front-frame', front_img.tobytes())
        socketio.emit('profile-frame', profile_img.tobytes())

    socketio.emit('session-ended')
    audio_handler.stop()
    front_stream.stop()
    profile_stream.stop()