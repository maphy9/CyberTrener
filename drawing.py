import cv2
from calculations import format_angle

ARM_LANDMARKS = [11, 12, 13, 14, 15, 16]
PROFILE_LANDMARKS = [11, 12, 13, 14, 15, 16]

ARM_CONNECTIONS = frozenset([
    (11, 13), (13, 15), (12, 14), (14, 16)
])
PROFILE_CONNECTIONS = frozenset([
    (11, 13), (13, 15),
    (12, 14), (14, 16),
])

def draw_arm_landmarks(frame, landmarks, landmark_indices, connections):
    h, w, _ = frame.shape

    for connection in connections:
        start_idx, end_idx = connection
        start_landmark = landmarks.landmark[start_idx]
        end_landmark = landmarks.landmark[end_idx]

        start_point = (int(start_landmark.x * w), int(start_landmark.y * h))
        end_point = (int(end_landmark.x * w), int(end_landmark.y * h))
        cv2.line(frame, start_point, end_point, (245, 117, 66), 2)

    for idx in landmark_indices:
        landmark = landmarks.landmark[idx]
        cx, cy = int(landmark.x * w), int(landmark.y * h)
        cv2.circle(frame, (cx, cy), 3, (245, 117, 66), -1)

def draw_front_text(frame, angles):
    y = 30
    cv2.putText(frame, "Front", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    y += 30
    cv2.putText(frame, f"R Shoulder: {format_angle(angles.get('right_shoulder'))}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    y += 25
    cv2.putText(frame, f"R Elbow: {format_angle(angles.get('right_elbow'))}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    y += 25
    cv2.putText(frame, f"L Shoulder: {format_angle(angles.get('left_shoulder'))}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    y += 25
    cv2.putText(frame, f"L Elbow: {format_angle(angles.get('left_elbow'))}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)


def draw_profile_text(frame, angles):
    y = 30
    cv2.putText(frame, "Profile", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    y += 30

    cv2.putText(frame, f"L Elbow: {format_angle(angles.get('left_elbow'))}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    y += 25
    cv2.putText(frame, f"R Elbow: {format_angle(angles.get('right_elbow'))}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    y += 25

    # Одна строка повторений без разделения на L/R
    reps_total = angles.get("reps")
    if reps_total is None:
        reps_l = angles.get("reps_left")
        reps_r = angles.get("reps_right")
        if reps_l is not None or reps_r is not None:
            reps_l = reps_l if reps_l is not None else 0
            reps_r = reps_r if reps_r is not None else 0
            reps_total = int(reps_l) + int(reps_r)

    if reps_total is not None:
        cv2.putText(frame, f"Reps: {int(reps_total)}", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
