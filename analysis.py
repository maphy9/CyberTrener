import numpy as np
from collections import deque
from calculations import get_coords_2d, calculate_distance_2d

error_buffer = {
    'elbows_flared': deque(maxlen=15),
    'wrist_bent': deque(maxlen=15),
    'lower_back_arched': deque(maxlen=15),
    'uncontrolled_movement': deque(maxlen=10),
    'insufficient_range': deque(maxlen=15),
}

prev_elbow_angle = None
rep_count = 0
in_rep = False

def check_elbows_flared(front_landmarks):
    left_shoulder = get_coords_2d(front_landmarks, 12)
    left_elbow = get_coords_2d(front_landmarks, 14)
    right_shoulder = get_coords_2d(front_landmarks, 11)
    right_elbow = get_coords_2d(front_landmarks, 13)
    
    shoulder_width = calculate_distance_2d(left_shoulder, right_shoulder)
    
    left_dist = abs(left_elbow[0] - left_shoulder[0])
    right_dist = abs(right_elbow[0] - right_shoulder[0])
    
    threshold = shoulder_width * 0.15
    
    return left_dist > threshold or right_dist > threshold

def check_wrist_bent(front_landmarks):
    left_elbow = get_coords_2d(front_landmarks, 14)
    left_wrist = get_coords_2d(front_landmarks, 16)
    right_elbow = get_coords_2d(front_landmarks, 13)
    right_wrist = get_coords_2d(front_landmarks, 15)
    
    left_vertical = abs(left_wrist[0] - left_elbow[0]) / (abs(left_wrist[1] - left_elbow[1]) + 0.001)
    right_vertical = abs(right_wrist[0] - right_elbow[0]) / (abs(right_wrist[1] - right_elbow[1]) + 0.001)
    
    threshold = 0.3
    
    return left_vertical > threshold or right_vertical > threshold

def check_lower_back_arched(profile_landmarks):
    shoulder = get_coords_2d(profile_landmarks, 11)
    hip = get_coords_2d(profile_landmarks, 23)
    
    horizontal_offset = abs(shoulder[0] - hip[0])
    vertical_distance = abs(shoulder[1] - hip[1])
    
    ratio = horizontal_offset / (vertical_distance + 0.001)
    threshold = 0.25
    
    return ratio > threshold

def check_uncontrolled_movement(current_elbow_angle):
    global prev_elbow_angle
    
    if prev_elbow_angle is None:
        prev_elbow_angle = current_elbow_angle
        return False
    
    angle_change = abs(current_elbow_angle - prev_elbow_angle)
    prev_elbow_angle = current_elbow_angle
    
    threshold = 15
    return angle_change > threshold

def check_insufficient_range(elbow_angle):
    if elbow_angle < 50:
        return False
    if elbow_angle > 140:
        return False
    return True

def count_reps(elbow_angle):
    global rep_count, in_rep
    
    if elbow_angle < 70 and not in_rep:
        in_rep = True
    elif elbow_angle > 130 and in_rep:
        in_rep = False
        rep_count += 1

def analyze_frame(front_landmarks, profile_landmarks, profile_angles):
    errors = {}
    
    if front_landmarks:
        elbows_flared = check_elbows_flared(front_landmarks)
        error_buffer['elbows_flared'].append(elbows_flared)
        errors['elbows_flared'] = sum(error_buffer['elbows_flared']) > 10
        
        wrist_bent = check_wrist_bent(front_landmarks)
        error_buffer['wrist_bent'].append(wrist_bent)
        errors['wrist_bent'] = sum(error_buffer['wrist_bent']) > 10
    
    if profile_landmarks:
        lower_back = check_lower_back_arched(profile_landmarks)
        error_buffer['lower_back_arched'].append(lower_back)
        errors['lower_back_arched'] = sum(error_buffer['lower_back_arched']) > 10
    
    if profile_angles and profile_angles.get('elbow'):
        elbow_angle = profile_angles['elbow']
        
        uncontrolled = check_uncontrolled_movement(elbow_angle)
        error_buffer['uncontrolled_movement'].append(uncontrolled)
        errors['uncontrolled_movement'] = sum(error_buffer['uncontrolled_movement']) > 6
        
        insufficient = check_insufficient_range(elbow_angle)
        error_buffer['insufficient_range'].append(insufficient)
        errors['insufficient_range'] = sum(error_buffer['insufficient_range']) > 10
        
        count_reps(elbow_angle)
    
    errors['rep_count'] = rep_count
    
    return errors

def get_error_messages(errors):
    messages = []
    
    if errors.get('elbows_flared'):
        messages.append("Łokcie oddalone od ciała")
    if errors.get('wrist_bent'):
        messages.append("Zginanie nadgarstków")
    if errors.get('lower_back_arched'):
        messages.append("Wyginanie dolnego odcinka pleców")
    if errors.get('uncontrolled_movement'):
        messages.append("Niekontrolowany ruch")
    if errors.get('insufficient_range'):
        messages.append("Niewystarczający zakres ruchu")
    
    return messages