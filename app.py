from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from threading import Thread, Event
from camera import CameraStream
from constants import *
from processing import process_camera_streams

processing_event = Event()
processing_thread = None

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def handle_index():
    return render_template('index.html')

@app.route('/training')
def handle_training():
    return render_template('training.html')

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
def handle_start_session(camera_config):
    global processing_thread
    if not processing_event.is_set():
        print('Server can handle one session at a time')
        return
    print('New session started')
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

        processing_thread = Thread(
            target=process_camera_streams,
            args=(socketio, front_camera_stream, profile_camera_stream, processing_event),
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
    if processing_thread:
        processing_thread.join()
    print('Session ended')

if __name__ == '__main__':
    processing_event.set()
    socketio.run(app, host='0.0.0.0', port=5000)