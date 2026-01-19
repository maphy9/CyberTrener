from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from threading import Thread, Event
from camera import CameraStream
from core.constants import *
from processing import process_camera_streams, run_calibration_session, run_unified_training_session
from calibration.data import CalibrationData
from database.repository import TrainingRepository

processing_event = Event()
analyzing_event = Event()
processing_thread = None
exercise_command_event = Event()
exercise_command_type = [None]

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def handle_index():
    return render_template('index.html')

@app.route('/training')
def handle_training():
    return render_template('training.html')

@app.route('/history')
def handle_history():
    return render_template('history.html')

@app.route('/api/calibration-status')
def handle_calibration_status():
    calibration = CalibrationData.load()
    if calibration and calibration.calibrated:
        date_str = calibration.calibration_date[:10] if calibration.calibration_date else "Nieznana data"
        return jsonify({'calibrated': True, 'date': date_str})
    return jsonify({'calibrated': False, 'date': None})

@app.route('/api/training-history')
def handle_training_history():
    sort_order = request.args.get('sort', 'desc')
    date_from = request.args.get('dateFrom')
    date_to = request.args.get('dateTo')
    
    sessions = TrainingRepository.get_all_sessions(sort_order, date_from, date_to)
    return jsonify([s.to_dict() for s in sessions])

@app.route('/api/training-history/<int:session_id>')
def handle_training_detail(session_id):
    session = TrainingRepository.get_session_detail(session_id)
    if session:
        return jsonify(session.to_dict())
    return jsonify({'error': 'Session not found'}), 404

@app.route('/api/training-history/<int:session_id>', methods=['DELETE'])
def handle_delete_training(session_id):
    deleted = TrainingRepository.delete_session(session_id)
    if deleted:
        return jsonify({'success': True})
    return jsonify({'error': 'Session not found'}), 404

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    global processing_thread
    if processing_event.is_set():
        print('Tried to end a session that has not started')
        return
    processing_event.set()
    if processing_thread:
        processing_thread.join()
    print('Session ended')

@socketio.on('start-session')
def handle_start_session(data):
    global processing_thread
    if not processing_event.is_set():
        print('Server can handle one session at a time')
        return
    
    camera_config = data.get('cameras', data)
    session_mode = data.get('mode', 'unified')
    training_settings = data.get('trainingSettings', {
        'exercises': ['bicep_curl', 'overhead_press'],
        'repsPerSet': 10,
        'rounds': 3
    })
    force_calibration = training_settings.get('forceCalibration', False)
    
    print(f'New {session_mode} session started')
    print(f'Training settings: {training_settings}')
    print(f'Camera config: {camera_config}')
    processing_event.clear()

    try:
        front_config = camera_config.get('front', {})
        profile_config = camera_config.get('profile', {})
        
        front_source = front_config.get('value', 0)
        profile_source = profile_config.get('value', 0)
        
        front_camera_stream = CameraStream(
            front_source, 
            FRONT_CAMERA_WIDTH, 
            FRONT_CAMERA_HEIGHT
        ).start()
        
        profile_camera_stream = CameraStream(
            profile_source,
            PROFILE_CAMERA_WIDTH,
            PROFILE_CAMERA_HEIGHT
        ).start()
        
        if not front_camera_stream.is_connected or not profile_camera_stream.is_connected:
            if front_camera_stream:
                front_camera_stream.stop()
            if profile_camera_stream:
                profile_camera_stream.stop()
            processing_event.set()
            emit('connection-error', {'message': 'Nie można połączyć się z jedną lub obiema kamerami'})
            return

        if session_mode == 'calibration':
            target_fn = run_calibration_session
            args = (socketio, front_camera_stream, profile_camera_stream, processing_event)
        elif session_mode == 'unified':
            target_fn = run_unified_training_session
            args = (socketio, front_camera_stream, profile_camera_stream, processing_event, analyzing_event, training_settings, force_calibration)
        else:
            exercise_type = data.get('exerciseType', 'bicep_curl')
            target_fn = process_camera_streams
            args = (socketio, front_camera_stream, profile_camera_stream, processing_event, analyzing_event, exercise_type)

        processing_thread = Thread(
            target=target_fn,
            args=args,
            daemon=True
        )
        processing_thread.start()
        
    except Exception as e:
        print(f'Error starting camera streams: {e}')
        processing_event.set()
        emit('connection-error', {'message': f'Błąd inicjalizacji kamer: {str(e)}'})

@socketio.on('end-session')
def handle_end_session():
    global processing_thread
    if processing_event.is_set():
        print('Tried to end a session that has not started')
        return
    processing_event.set()
    analyzing_event.clear()
    if processing_thread:
        processing_thread.join()
    print('Session ended')

@socketio.on('start-analysis')
def handle_start_analysis():
    analyzing_event.set()
    print('Analysis started')

@socketio.on('stop-analysis')
def handle_stop_analysis():
    analyzing_event.clear()
    print('Analysis stopped')

if __name__ == '__main__':
    processing_event.set()
    socketio.run(app, host='0.0.0.0', port=5000)