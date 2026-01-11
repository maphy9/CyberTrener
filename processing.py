import cv2
import mediapipe as mp
from threading import Thread, Event
import time
from audio import AudioHandler, listen_for_voice_commands
from core.pose_drawing import draw_pose_with_errors
from exercises.bicep_curl.controller import BicepCurlController
from exercises.bicep_curl.metrics import reset_front_view_state, reset_profile_view_state
from calibration.controller import CalibrationController
from calibration.data import CalibrationData

mp_pose = mp.solutions.pose # type: ignore


def run_calibration_session(socketio, front_stream, profile_stream, stop_event):
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
    calibration = CalibrationController()
    
    reset_front_view_state()
    reset_profile_view_state()
    
    audio_handler.queue_speech("Rozpoczynam kalibrację")
    audio_handler.queue_speech(calibration.get_instructions())
    
    socketio.emit('calibration-step', {
        'step': calibration.current_step,
        'instruction': calibration.get_instructions()
    })
    
    while not stop_event.is_set():
        front_frame, front_was_read = front_stream.get()
        profile_frame, profile_was_read = profile_stream.get()
        
        if front_frame is None or profile_frame is None:
            continue
        
        if not front_was_read:
            front_rgb = cv2.cvtColor(front_frame, cv2.COLOR_BGR2RGB)
            front_rgb.flags.writeable = False
            front_results = front_pose.process(front_rgb)
            front_rgb.flags.writeable = True
            draw_pose_with_errors(front_frame, front_results, {})
        else:
            front_results = None
        
        if not profile_was_read:
            profile_rgb = cv2.cvtColor(profile_frame, cv2.COLOR_BGR2RGB)
            profile_rgb.flags.writeable = False
            profile_results = profile_pose.process(profile_rgb)
            profile_rgb.flags.writeable = True
            draw_pose_with_errors(profile_frame, profile_results, {})
        else:
            profile_results = None
        
        if front_results and profile_results:
            step_complete, message = calibration.process_frames(front_results, profile_results)
            
            if step_complete:
                if message:
                    audio_handler.queue_speech(message)
                
                if calibration.is_complete():
                    calibration_data = calibration.get_calibration_data()
                    calibration_data.save()
                    
                    socketio.emit('calibration-complete', {
                        'data': calibration_data.to_dict()
                    })
                    break
                else:
                    socketio.emit('calibration-step', {
                        'step': calibration.current_step,
                        'instruction': calibration.get_instructions()
                    })
        
        _, front_img = cv2.imencode('.jpg', front_frame)
        _, profile_img = cv2.imencode('.jpg', profile_frame)
        
        socketio.emit('front-frame', front_img.tobytes())
        socketio.emit('profile-frame', profile_img.tobytes())
    
    socketio.emit('session-ended')
    audio_handler.stop()
    front_stream.stop()
    profile_stream.stop()


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
    
    audio_handler.queue_speech("Powiedz 'zacznij' aby rozpocząć")
    
    voice_thread = Thread(
        target=listen_for_voice_commands,
        args=(audio_handler, stop_event, analyzing_event),
        daemon=True
    )
    voice_thread.start()
    
    socketio.emit('status', {'state': 'waiting'})
    
    calibration_data = CalibrationData.load()
    exercise = BicepCurlController(calibration_data)
    
    reset_front_view_state()
    reset_profile_view_state()
    
    error_states = {}
    last_error_spoken = {}
    ERROR_COOLDOWN = 3.0
    ERROR_DISPLAY_DURATION = 2.5
    
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
                front_rgb = cv2.cvtColor(front_frame, cv2.COLOR_BGR2RGB)
                front_rgb.flags.writeable = False
                front_results = front_pose.process(front_rgb)
                front_rgb.flags.writeable = True
                draw_pose_with_errors(front_frame, front_results, error_states)
            else:
                front_results = None

            if not profile_was_read:
                profile_rgb = cv2.cvtColor(profile_frame, cv2.COLOR_BGR2RGB)
                profile_rgb.flags.writeable = False
                profile_results = profile_pose.process(profile_rgb)
                profile_rgb.flags.writeable = True
                draw_pose_with_errors(profile_frame, profile_results, error_states)
            else:
                profile_results = None
            
            if front_results and profile_results:
                result = exercise.process_frames(front_results, profile_results)
                
                if result['rep_detected']:
                    if result['valid']:
                        audio_handler.queue_beep()
                    else:
                        current_time = time.time()
                        message = result['error_message']
                        
                        last_spoken = last_error_spoken.get(message, 0)
                        if current_time - last_spoken >= ERROR_COOLDOWN:
                            audio_handler.queue_speech(message)
                            last_error_spoken[message] = current_time
                        
                        for part in result['error_parts']:
                            error_states[part] = current_time + ERROR_DISPLAY_DURATION
                
                socketio.emit('metrics', {
                    'right_reps': result['right_reps'],
                    'left_reps': result['left_reps'],
                    'errors': []
                })
                
        else:
            if prev_analyzing_state:
                socketio.emit('status', {'state': 'waiting'})
                prev_analyzing_state = False
            
            front_rgb = cv2.cvtColor(front_frame, cv2.COLOR_BGR2RGB)
            front_rgb.flags.writeable = False
            front_results = front_pose.process(front_rgb)
            front_rgb.flags.writeable = True
            draw_pose_with_errors(front_frame, front_results, {})
            
            profile_rgb = cv2.cvtColor(profile_frame, cv2.COLOR_BGR2RGB)
            profile_rgb.flags.writeable = False
            profile_results = profile_pose.process(profile_rgb)
            profile_rgb.flags.writeable = True
            draw_pose_with_errors(profile_frame, profile_results, {})

        _, front_img = cv2.imencode('.jpg', front_frame)
        _, profile_img = cv2.imencode('.jpg', profile_frame)

        socketio.emit('front-frame', front_img.tobytes())
        socketio.emit('profile-frame', profile_img.tobytes())

    socketio.emit('session-ended')
    audio_handler.stop()
    front_stream.stop()
    profile_stream.stop()