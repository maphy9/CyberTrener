import cv2
import mediapipe as mp
import time
from collections import deque

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_pose = mp.solutions.pose

# Initialize the window explicitly to allow resizing
cv2.namedWindow('MediaPipe Pose', cv2.WINDOW_NORMAL) 

with mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=1
    ) as pose:
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    fps_history = deque(maxlen=10)
    
    while cap.isOpened():
        frame_start_time = time.perf_counter()

        success, frame = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue

        frame.flags.writeable = False
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame)

        frame.flags.writeable = True
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        mp_drawing.draw_landmarks(
            frame,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing.DrawingSpec(color=(245,117,66), thickness=1, circle_radius=1),
            connection_drawing_spec=mp_drawing.DrawingSpec(color=(245,66,230), thickness=1, circle_radius=1)
        )
        frame = cv2.flip(frame, 1)

        frame_end_time = time.perf_counter()
        fps_time_diff = frame_end_time - frame_start_time
        fps = 1 / fps_time_diff if fps_time_diff != 0 else 30
        fps_history.append(fps)
        avg_fps = sum(fps_history) / len(fps_history)

        cv2.putText(frame, f'FPS: {int(avg_fps)}', (10, 30), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1)
        cv2.imshow('MediaPipe Pose', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()