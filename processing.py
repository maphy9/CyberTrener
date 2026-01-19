import cv2
import mediapipe as mp
from threading import Thread, Event, Lock
import time
from datetime import datetime
from audio import AudioHandler, listen_for_voice_commands, listen_for_voice_commands_unified
from core.pose_drawing import draw_pose_with_errors
from exercises.bicep_curl.controller import BicepCurlController
from exercises.bicep_curl.metrics import reset_front_view_state as reset_bicep_front
from exercises.bicep_curl.metrics import reset_profile_view_state as reset_bicep_profile
from exercises.overhead_press.controller import OverheadPressController
from exercises.overhead_press.metrics import reset_front_view_state as reset_overhead_front
from exercises.overhead_press.metrics import reset_profile_view_state as reset_overhead_profile
from calibration.controller import CalibrationController
from calibration.data import CalibrationData
from training.session_controller import TrainingSessionController, TrainingSettings, SessionPhase, get_reset_functions
from database.repository import TrainingRepository

mp_pose = mp.solutions.pose

CALIBRATION_PHRASES = [
    "Rozpoczynam kalibrację",
    "Stań w pozycji neutralnej z ramionami wzdłuż ciała",
    "Teraz ugnij prawą rękę",
    "Teraz wyprostuj prawą rękę",
    "Teraz ugnij lewą rękę",
    "Teraz wyprostuj lewą rękę",
    "Podnieś obie ręce na wysokość barków",
    "Wyciśnij ręce nad głowę",
    "Kalibracja zakończona",
    "Kalibracja zakończona. Zaczynamy trening."
]

TRAINING_PHRASES = [
    "Powiedz 'zacznij' aby rozpocząć",
    "Zaczynam",
    "Pauza",
    "Następne ćwiczenie",
    "Wracamy",
    "Uginanie przedramion",
    "Wyciskanie nad głowę",
    "Trening zakończony",
    "Trzymaj plecy prosto",
    "Trzymaj rękę pionowo",
    "Nie pracuj obiema rękami jednocześnie",
    "Zmieniaj ręce naprzemiennie",
    "Unoś obie ręce równomiernie",
]

for i in range(1, 11):
    TRAINING_PHRASES.append(f"Runda {i}")

for reps in [5, 10, 12, 15, 20, 25, 30]:
    TRAINING_PHRASES.append(f"{reps} powtórzeń")


def run_calibration_session(socketio, front_stream, profile_stream, stop_event):
    """
    Uruchamia sesję kalibracji użytkownika.
    Parametry:
    - socketio: instancja SocketIO do komunikacji
    - front_stream: strumień z kamery przedniej
    - profile_stream: strumień z kamery bocznej
    - stop_event: event zatrzymania
    """
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
    
    audio_handler.preload_speech(CALIBRATION_PHRASES)
    
    reset_bicep_front()
    reset_bicep_profile()
    
    audio_handler.queue_speech("Rozpoczynam kalibrację")
    audio_handler.queue_speech(calibration.get_instructions())
    
    socketio.emit('calibration-step', {
        'step': calibration.current_step,
        'instruction': calibration.get_instructions()
    })
    
    waiting_for_speech = True
    processing_enabled = False
    
    while not stop_event.is_set():
        front_frame, front_was_read = front_stream.get()
        profile_frame, profile_was_read = profile_stream.get()
        
        if front_frame is None or profile_frame is None:
            continue
        
        if waiting_for_speech:
            if audio_handler._speech_complete.is_set():
                waiting_for_speech = False
                processing_enabled = True
        
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
        
        if processing_enabled and front_results and profile_results:
            step_complete, message = calibration.process_frames(front_results, profile_results)
            
            if step_complete:
                processing_enabled = False
                
                if calibration.is_complete():
                    calibration_data = calibration.get_calibration_data()
                    calibration_data.save()
                    
                    audio_handler.queue_speech_priority("Kalibracja zakończona")
                    
                    socketio.emit('calibration-complete', {
                        'data': calibration_data.to_dict()
                    })
                    
                    audio_handler.wait_for_speech()
                    break
                else:
                    if message:
                        audio_handler.queue_speech_priority(message)
                        waiting_for_speech = True
                    
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


def process_camera_streams(socketio, front_stream, profile_stream, stop_event, analyzing_event, exercise_type='bicep_curl'):
    """
    Przetwarza strumienie kamer dla pojedynczego ćwiczenia.
    Parametry:
    - socketio: instancja SocketIO do komunikacji
    - front_stream: strumień z kamery przedniej
    - profile_stream: strumień z kamery bocznej
    - stop_event: event zatrzymania
    - analyzing_event: event analizy
    - exercise_type: typ ćwiczenia
    """
    front_pose = mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=1
    )
    profile_pose = mp_pose.Pose(
        """
        Uruchamia zintegrowaną sesję treningową (kalibracja + ćwiczenia).
        Parametry:
        - socketio: instancja SocketIO do komunikacji
        - front_stream: strumień z kamery przedniej
        - profile_stream: strumień z kamery bocznej
        - stop_event: event zatrzymania
        - analyzing_event: event analizy
        - training_settings: ustawienia treningu
        - force_calibration: wymuszenie kalibracji
        """
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=1
    )
    
    audio_handler = AudioHandler()
    
    audio_handler.queue_speech("Powiedz 'zacznij' aby rozpocząć")
    
    voice_thread = Thread(
        target=listen_for_voice_commands,
        args=(audio_handler, stop_event, analyzing_event),
        daemon=True
    )
    voice_thread.start()
    
    socketio.emit('status', {'state': 'waiting'})
    
    calibration_data = CalibrationData.load()
    
    if exercise_type == 'overhead_press':
        print("Initializing Overhead Press exercise")
        exercise = OverheadPressController(calibration_data)
        reset_overhead_front()
        reset_overhead_profile()
    else:
        print("Initializing Bicep Curl exercise")
        exercise = BicepCurlController(calibration_data)
        reset_bicep_front()
        reset_bicep_profile()
    
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


def run_unified_training_session(socketio, front_stream, profile_stream, stop_event, analyzing_event, training_settings, force_calibration=False):
    """
    Ujednolicona sesja treningowa obejmująca:
    1. Kalibrację (w razie potrzeby lub konieczności)
    2. Kilka ćwiczeń wykonywanych po kolei
    3. Kilka rund (podejść)
    4. Polecenia głosowe do nawigacji
    """
    
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
    
    audio_handler.preload_speech(CALIBRATION_PHRASES + TRAINING_PHRASES)
    
    calibration_data = CalibrationData.load()
    needs_calibration = True
    
    exercise_command_lock = Lock()
    pending_command = [None]
    
    def exercise_command_callback(command):
        with exercise_command_lock:
            pending_command[0] = command
    
    if needs_calibration:
        socketio.emit('session-phase', {'phase': 'calibration'})
        
        calibration = CalibrationController()
        reset_bicep_front()
        reset_bicep_profile()
        
        audio_handler.queue_speech("Rozpoczynam kalibrację")
        audio_handler.queue_speech(calibration.get_instructions())
        
        socketio.emit('calibration-step', {
            'step': calibration.current_step,
            'instruction': calibration.get_instructions()
        })
        
        waiting_for_speech = True
        processing_enabled = False
        
        while not stop_event.is_set():
            front_frame, front_was_read = front_stream.get()
            profile_frame, profile_was_read = profile_stream.get()
            
            if front_frame is None or profile_frame is None:
                continue
            
            if waiting_for_speech:
                if audio_handler._speech_complete.is_set():
                    waiting_for_speech = False
                    processing_enabled = True
            
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
            
            if processing_enabled and front_results and profile_results:
                step_complete, message = calibration.process_frames(front_results, profile_results)
                
                if step_complete:
                    processing_enabled = False
                    
                    if calibration.is_complete():
                        calibration_data = calibration.get_calibration_data()
                        calibration_data.save()
                        
                        audio_handler.queue_speech_priority("Kalibracja zakończona. Zaczynamy trening.")
                        
                        socketio.emit('calibration-complete', {
                            'data': calibration_data.to_dict()
                        })
                        
                        audio_handler.wait_for_speech()
                        break
                    else:
                        if message:
                            audio_handler.queue_speech_priority(message)
                            waiting_for_speech = True
                        
                        socketio.emit('calibration-step', {
                            'step': calibration.current_step,
                            'instruction': calibration.get_instructions()
                        })
            
            _, front_img = cv2.imencode('.jpg', front_frame)
            _, profile_img = cv2.imencode('.jpg', profile_frame)
            
            socketio.emit('front-frame', front_img.tobytes())
            socketio.emit('profile-frame', profile_img.tobytes())
        
        if stop_event.is_set():
            socketio.emit('session-ended')
            audio_handler.stop()
            front_stream.stop()
            profile_stream.stop()
            return
    
    socketio.emit('session-phase', {'phase': 'exercise'})
    session_start_time = time.time()
    
    settings = TrainingSettings.from_dict(training_settings)
    session = TrainingSessionController(settings)
    session.calibration_data = calibration_data
    session.state.phase = SessionPhase.EXERCISE
    session._init_current_exercise()
    
    reset_front, reset_profile = get_reset_functions(session.get_current_exercise_type())
    reset_front()
    reset_profile()
    
    voice_thread = Thread(
        target=listen_for_voice_commands_unified,
        args=(audio_handler, stop_event, analyzing_event, exercise_command_callback),
        daemon=True
    )
    voice_thread.start()
    
    audio_handler.queue_speech(session.get_announcement_for_start())
    
    socketio.emit('training-state', session.get_state_dict())
    socketio.emit('status', {'state': 'waiting'})
    
    error_states = {}
    last_error_spoken = {}
    ERROR_COOLDOWN = 3.0
    ERROR_DISPLAY_DURATION = 2.5
    
    prev_analyzing_state = False
    auto_advance_cooldown = 0
    
    while not stop_event.is_set():
        front_frame, front_was_read = front_stream.get()
        profile_frame, profile_was_read = profile_stream.get()
        
        if front_frame is None or profile_frame is None:
            continue
        
        with exercise_command_lock:
            command = pending_command[0]
            pending_command[0] = None
        
        if command:
            if command == 'next':
                event_result = session.go_to_next()
                _handle_exercise_transition(socketio, audio_handler, session, event_result, stop_event)
                reset_front, reset_profile = get_reset_functions(session.get_current_exercise_type())
                reset_front()
                reset_profile()
            elif command == 'previous':
                event_result = session.go_to_previous()
                if event_result['event'] != 'at_start':
                    _handle_exercise_transition(socketio, audio_handler, session, event_result, stop_event)
                    reset_front, reset_profile = get_reset_functions(session.get_current_exercise_type())
                    reset_front()
                    reset_profile()
        
        if session.is_complete():
            audio_handler.queue_speech_priority("Trening zakończony.")
            stats = session.get_completion_stats()
            
            detailed = session.get_detailed_results()
            session_data = {
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': int(time.time() - session_start_time),
                'total_reps': detailed['total_reps'],
                'total_errors': detailed['total_errors'],
                'rounds': detailed['settings']['rounds'],
                'exercises_config': detailed['settings'],
                'exercise_results': detailed['exercise_results']
            }
            TrainingRepository.save_session(session_data)
            
            socketio.emit('training-complete', stats)
            audio_handler.wait_for_speech(timeout=5)
            break
        
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
                result = session.process_frame(front_results, profile_results)
                
                if result.get('rep_detected'):
                    if result.get('valid'):
                        audio_handler.queue_beep()
                    else:
                        current_time = time.time()
                        message = result.get('error_message', '')
                        
                        if message:
                            last_spoken = last_error_spoken.get(message, 0)
                            if current_time - last_spoken >= ERROR_COOLDOWN:
                                audio_handler.queue_speech(message)
                                last_error_spoken[message] = current_time
                        
                        for part in result.get('error_parts', []):
                            error_states[part] = current_time + ERROR_DISPLAY_DURATION
                
                socketio.emit('metrics', {
                    'right_reps': session.state.right_reps,
                    'left_reps': session.state.left_reps,
                    'errors': []
                })
                
                socketio.emit('training-state', session.get_state_dict())
                
                current_time = time.time()
                if session.check_set_complete() and current_time > auto_advance_cooldown:
                    auto_advance_cooldown = current_time + 3.0
                    event_result = session.advance_to_next()
                    _handle_exercise_transition(socketio, audio_handler, session, event_result, stop_event)
                    if not session.is_complete():
                        reset_front, reset_profile = get_reset_functions(session.get_current_exercise_type())
                        reset_front()
                        reset_profile()
                
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


def _handle_exercise_transition(socketio, audio_handler, session, event_result, stop_event):
    """Obsługa komunikatów i aktualizacji interfejsu użytkownika podczas przejść między ćwiczeniami."""
    event = event_result.get('event')
    
    if event == 'training_complete':
        return
    
    elif event == 'new_round':
        round_num = event_result['round']
        total = event_result['total_rounds']
        exercise = event_result['exercise']
        audio_handler.queue_speech_priority(f"Runda {round_num}. {exercise}.")
        
    elif event == 'new_exercise':
        exercise = event_result['exercise']
        round_num = event_result['round']
        total = event_result['total_rounds']
        audio_handler.queue_speech_priority(f"Następne ćwiczenie. {exercise}.")
        
    elif event == 'previous_exercise':
        exercise = event_result['exercise']
        audio_handler.queue_speech_priority(f"Wracamy. {exercise}.")
        
    elif event == 'previous_round':
        exercise = event_result['exercise']
        round_num = event_result['round']
        audio_handler.queue_speech_priority(f"Runda {round_num}. {exercise}.")
    
    socketio.emit('training-state', session.get_state_dict())