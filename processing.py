import time
import sys
from threading import Thread, Lock

import cv2
import mediapipe as mp

from calculations import calculate_front_angles, calculate_profile_angles, smooth_angle
from drawing import (
    draw_arm_landmarks,
    draw_front_text,
    draw_profile_text,
    ARM_LANDMARKS,
    ARM_CONNECTIONS,
    PROFILE_LANDMARKS,
    PROFILE_CONNECTIONS
)

mp_pose = mp.solutions.pose  # type: ignore


# Audio
class BeepLimiter:
    def __init__(self):
        self._lock = Lock()
        self._last = {"left": 0.0, "right": 0.0}

    def _beep_blocking(self, freq_hz: int = 880, duration_ms: int = 120) -> None:
        try:
            import winsound  # type: ignore
            winsound.Beep(int(freq_hz), int(duration_ms))
            return
        except Exception:
            pass

        try:
            sys.stdout.write("\a")
            sys.stdout.flush()
        except Exception:
            pass

    def beep(self, arm: str, min_interval_s: float = 0.9, freq_hz: int = 880, duration_ms: int = 120) -> bool:
        arm = "left" if arm == "left" else "right"
        now = time.monotonic()

        if now - self._last[arm] < float(min_interval_s):
            return False

        if not self._lock.acquire(blocking=False):
            return False

        self._last[arm] = now

        def _run():
            try:
                self._beep_blocking(freq_hz=freq_hz, duration_ms=duration_ms)
            finally:
                try:
                    self._lock.release()
                except Exception:
                    pass

        Thread(target=_run, daemon=True).start()
        return True


def _stable_zone(value: float, threshold: float, hysteresis: float) -> str:
    if value <= threshold - hysteresis:
        return "below"
    if value >= threshold + hysteresis:
        return "above"
    return "mid"


def process_single_frame(frame, pose, calc_fn, draw_fn, prev_angles, landmark_indices, connections):
    frame = cv2.flip(frame, 1)
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image_rgb.flags.writeable = False
    results = pose.process(image_rgb)
    image_rgb.flags.writeable = True

    if not results.pose_landmarks:
        return frame, results, prev_angles

    draw_arm_landmarks(frame, results.pose_landmarks, landmark_indices, connections)
    angles = calc_fn(results.pose_landmarks)

    smoothed = {}
    for key, val in angles.items():
        smoothed[key] = smooth_angle(prev_angles.get(key), val)

    draw_fn(frame, smoothed)
    return frame, results, smoothed

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

    prev_front = {}
    prev_profile = {}


    # Alternating reps: R, L, R...
    ELBOW_THRESHOLD = 70.0
    ELBOW_HYST = 2.0
    FULL_EXTENSION = 130.0
    FULL_EXTENSION_HYST = 2.0

    in_rep = {"left": False, "right": False}
    last_zone = {"left": None, "right": None}

    reps_total = 0
    expected_arm = "right"  # порядок: правая, левая, правая, ...

    beeper = BeepLimiter()

    while not stop_event.is_set():
        front_frame = front_stream.get()
        profile_frame = profile_stream.get()

        if front_frame is None or profile_frame is None:
            continue

        front_frame, _, prev_front = process_single_frame(
            front_frame,
            front_pose,
            calculate_front_angles,
            draw_front_text,
            prev_front,
            ARM_LANDMARKS,
            ARM_CONNECTIONS
        )

        profile_frame = cv2.flip(profile_frame, 1)
        image_rgb = cv2.cvtColor(profile_frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        results = profile_pose.process(image_rgb)
        image_rgb.flags.writeable = True

        if results.pose_landmarks:
            draw_arm_landmarks(profile_frame, results.pose_landmarks, PROFILE_LANDMARKS, PROFILE_CONNECTIONS)
            raw_angles = calculate_profile_angles(results.pose_landmarks)

            smoothed = {}
            for key, val in raw_angles.items():
                smoothed[key] = smooth_angle(prev_profile.get(key), val)
            prev_profile = smoothed

            for arm, key in (("left", "left_elbow"), ("right", "right_elbow")):
                angle = prev_profile.get(key)
                if angle is None:
                    continue

                try:
                    a = float(angle)
                except Exception:
                    continue

                if a <= (ELBOW_THRESHOLD - ELBOW_HYST) and not in_rep[arm]:
                    in_rep[arm] = True

                if a >= (FULL_EXTENSION + FULL_EXTENSION_HYST) and in_rep[arm]:
                    in_rep[arm] = False

                    if arm == expected_arm:
                        reps_total += 1
                        expected_arm = "left" if expected_arm == "right" else "right"

                zone = _stable_zone(a, ELBOW_THRESHOLD, ELBOW_HYST)
                if zone in ("below", "above"):
                    if last_zone[arm] is None:
                        last_zone[arm] = zone
                    elif zone != last_zone[arm]:
                        if zone == "below" and arm == expected_arm:
                            # анти-спам: cooldown + lock
                            beeper.beep(arm=arm, min_interval_s=0.9, freq_hz=880, duration_ms=120)
                        last_zone[arm] = zone

            draw_profile_text(profile_frame, {
                **prev_profile,
                "reps": reps_total
            })

        else:
            draw_profile_text(profile_frame, {
                "left_elbow": prev_profile.get("left_elbow"),
                "right_elbow": prev_profile.get("right_elbow"),
                "reps": reps_total
            })

        _, front_img = cv2.imencode(".jpg", front_frame)
        _, profile_img = cv2.imencode(".jpg", profile_frame)

        socketio.emit("front-frame", front_img.tobytes())
        socketio.emit("profile-frame", profile_img.tobytes())

    front_stream.stop()
    profile_stream.stop()