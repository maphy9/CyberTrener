import cv2
import mediapipe as mp
import numpy as np

mp_pose = mp.solutions.pose # type: ignore
mp_drawing = mp.solutions.drawing_utils # type: ignore
landmark_spec = mp_drawing.DrawingSpec(
    color=(245, 117, 66), 
    thickness=1, 
    circle_radius=1
)

def calculate_angle(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

def get_landmark_coords(landmarks, landmark_id):
    landmark = landmarks.landmark[landmark_id]
    return [landmark.x, landmark.y]

def analyze_curl_form(landmarks, side):
    if side == 'left':
        shoulder = get_landmark_coords(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER)
        elbow = get_landmark_coords(landmarks, mp_pose.PoseLandmark.LEFT_ELBOW)
        wrist = get_landmark_coords(landmarks, mp_pose.PoseLandmark.LEFT_WRIST)
        hip = get_landmark_coords(landmarks, mp_pose.PoseLandmark.LEFT_HIP)
    else:
        shoulder = get_landmark_coords(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER)
        elbow = get_landmark_coords(landmarks, mp_pose.PoseLandmark.RIGHT_ELBOW)
        wrist = get_landmark_coords(landmarks, mp_pose.PoseLandmark.RIGHT_WRIST)
        hip = get_landmark_coords(landmarks, mp_pose.PoseLandmark.RIGHT_HIP)
    
    elbow_angle = calculate_angle(shoulder, elbow, wrist)
    upper_arm_angle = calculate_angle(hip, shoulder, elbow)
    
    return elbow_angle, upper_arm_angle

def detect_curl_phase(elbow_angle, prev_phase):
    if elbow_angle < 50:
        return 'contracted'
    elif elbow_angle > 140:
        return 'extended'
    else:
        return prev_phase

def check_elbow_stability(upper_arm_angle):
    return 70 < upper_arm_angle < 110

def process_single_frame(frame, pose, curl_state):
    frame = cv2.flip(frame, 1)
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image_rgb.flags.writeable = False
    results = pose.process(image_rgb)
    image_rgb.flags.writeable = True

    if not results.pose_landmarks:
        return frame
    
    mp_drawing.draw_landmarks(
        frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
        landmark_drawing_spec=landmark_spec
    )
    
    left_elbow_angle, left_upper_arm_angle = analyze_curl_form(results.pose_landmarks, 'left')
    right_elbow_angle, right_upper_arm_angle = analyze_curl_form(results.pose_landmarks, 'right')
    
    left_phase = detect_curl_phase(left_elbow_angle, curl_state['left_phase'])
    right_phase = detect_curl_phase(right_elbow_angle, curl_state['right_phase'])
    
    if left_phase == 'extended' and curl_state['left_phase'] == 'contracted':
        curl_state['left_reps'] += 1
    if right_phase == 'extended' and curl_state['right_phase'] == 'contracted':
        curl_state['right_reps'] += 1
        
    curl_state['left_phase'] = left_phase
    curl_state['right_phase'] = right_phase
    
    left_stable = check_elbow_stability(left_upper_arm_angle)
    right_stable = check_elbow_stability(right_upper_arm_angle)
    
    y_offset = 30
    cv2.putText(frame, f'L: {int(left_elbow_angle)}deg {curl_state["left_reps"]}reps', 
                (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, f'R: {int(right_elbow_angle)}deg {curl_state["right_reps"]}reps', 
                (10, y_offset + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    if not left_stable:
        cv2.putText(frame, 'L elbow moving!', (10, y_offset + 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    if not right_stable:
        cv2.putText(frame, 'R elbow moving!', (10, y_offset + 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
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

    curl_state = {
        'left_phase': 'extended',
        'right_phase': 'extended',
        'left_reps': 0,
        'right_reps': 0
    }

    while not stop_event.is_set():
        front_frame = front_stream.get()
        profile_frame = profile_stream.get()

        if front_frame is None or profile_frame is None:
            continue

        front_frame = process_single_frame(front_frame, front_pose, curl_state)
        profile_frame = process_single_frame(profile_frame, profile_pose, curl_state)

        _, front_img = cv2.imencode('.jpg', front_frame)
        _, profile_img = cv2.imencode('.jpg', profile_frame)

        socketio.emit('front-frame', front_img.tobytes())
        socketio.emit('profile-frame', profile_img.tobytes())

    front_stream.stop()
    profile_stream.stop()