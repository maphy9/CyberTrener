import cv2
import mediapipe as mp
from pose_analyzer import FrontAnalyzer, ProfileAnalyzer

mp_pose = mp.solutions.pose # type: ignore
mp_drawing = mp.solutions.drawing_utils # type: ignore
landmark_spec = mp_drawing.DrawingSpec(
    color=(245, 117, 66), 
    thickness=1, 
    circle_radius=1
)

def draw_metrics_front(frame, metrics, x=10, y=30, font_scale=0.6):
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1
    color = (0, 0, 0)
    y_offset = y
    
    uncontrolled_r = "UNCONTROLLED" if metrics['right_uncontrolled'] else "OK"
    uncontrolled_l = "UNCONTROLLED" if metrics['left_uncontrolled'] else "OK"
    
    lines = [
        f"Right Arm: {metrics['right_angle']}deg ({metrics['right_phase']})",
        f"Right Reps: {metrics['right_reps']} [{uncontrolled_r}]",
        f"Left Arm: {metrics['left_angle']}deg ({metrics['left_phase']})",
        f"Left Reps: {metrics['left_reps']} [{uncontrolled_l}]",
        f"Trunk: {metrics['trunk_angle']}deg",
        f"R Elbow Dist: {metrics['right_elbow_dist']}",
        f"L Elbow Dist: {metrics['left_elbow_dist']}"
    ]
    
    for line in lines:
        cv2.putText(frame, line, (x, y_offset), font, font_scale, color, thickness)
        y_offset += 25

def draw_metrics_profile(frame, metrics, x=10, y=30, font_scale=0.6):
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1
    color = (0, 0, 0)
    y_offset = y
    
    uncontrolled_r = "UNCONTROLLED" if metrics['right_uncontrolled'] else "OK"
    
    lines = [
        f"Right Arm: {metrics['right_angle']}deg ({metrics['right_phase']})",
        f"Right Reps: {metrics['right_reps']} [{uncontrolled_r}]",
        f"Trunk: {metrics['trunk_angle']}deg",
        f"R Elbow Dist: {metrics['right_elbow_dist']}"
    ]
    
    for line in lines:
        cv2.putText(frame, line, (x, y_offset), font, font_scale, color, thickness)
        y_offset += 25

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
    draw_metrics_front(frame, metrics)
    
    return frame


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
    draw_metrics_profile(frame, metrics)
    
    return frame


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
    
    front_analyzer = FrontAnalyzer()
    profile_analyzer = ProfileAnalyzer()

    while not stop_event.is_set():
        front_frame = front_stream.get()
        profile_frame = profile_stream.get()

        if front_frame is None or profile_frame is None:
            continue

        front_frame = process_front_frame(front_frame, front_pose, front_analyzer)
        profile_frame = process_profile_frame(profile_frame, profile_pose, profile_analyzer)

        _, front_img = cv2.imencode('.jpg', front_frame)
        _, profile_img = cv2.imencode('.jpg', profile_frame)

        socketio.emit('front-frame', front_img.tobytes())
        socketio.emit('profile-frame', profile_img.tobytes())

    front_stream.stop()
    profile_stream.stop()