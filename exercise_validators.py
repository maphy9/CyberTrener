def validate_front_bicep_curl(metrics):
    right_phase = metrics.get('right_phase')
    left_phase = metrics.get('left_phase')
    
    if right_phase == left_phase == 'flexed':
        return "Pracuj na zmianę"
    
    return None


def validate_profile_bicep_curl(metrics):
    trunk_angle = metrics.get('trunk_angle')
    
    if trunk_angle is None:
        return None
    
    if abs(trunk_angle - 180) > 20:
        return "Trzymaj plecy prosto"
    
    return None