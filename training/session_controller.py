"""
Unified Training Session Controller
Manages calibration-first flow, exercise queue, rounds, and rep tracking.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum
from calibration.data import CalibrationData
from exercises.bicep_curl.controller import BicepCurlController
from exercises.overhead_press.controller import OverheadPressController


class SessionPhase(Enum):
    CALIBRATION = "calibration"
    EXERCISE = "exercise"
    REST = "rest"
    COMPLETED = "completed"


@dataclass
class TrainingSettings:
    """Settings for a training session, loaded from frontend localStorage."""
    exercises: List[str] = field(default_factory=lambda: ["bicep_curl", "overhead_press"])
    reps_per_exercise: Dict[str, int] = field(default_factory=lambda: {"bicep_curl": 10, "overhead_press": 10})
    rounds: int = 3
    
    @classmethod
    def from_dict(cls, data: dict) -> "TrainingSettings":
        exercises = data.get("exercises", ["bicep_curl", "overhead_press"])
        
        # Support both old format (single repsPerSet) and new format (repsPerExercise dict)
        reps_data = data.get("repsPerExercise", {})
        if not reps_data:
            # Fallback to old single value for all exercises
            default_reps = data.get("repsPerSet", 10)
            reps_data = {ex: default_reps for ex in exercises}
        
        return cls(
            exercises=exercises,
            reps_per_exercise=reps_data,
            rounds=data.get("rounds", 3)
        )
    
    def get_reps_for_exercise(self, exercise_type: str) -> int:
        """Get the target reps for a specific exercise."""
        return self.reps_per_exercise.get(exercise_type, 10)


@dataclass  
class SessionState:
    phase: SessionPhase = SessionPhase.CALIBRATION
    current_exercise_index: int = 0
    current_round: int = 1
    right_reps: int = 0
    left_reps: int = 0
    total_right_reps: int = 0
    total_left_reps: int = 0
    waiting_for_neutral: bool = True
    neutral_frames: int = 0
    total_errors: int = 0
    exercise_stats: Dict = field(default_factory=dict)


EXERCISE_NAMES = {
    "bicep_curl": "Uginanie przedramion",
    "overhead_press": "Wyciskanie nad głowę"
}


class TrainingSessionController:
    
    def __init__(self, settings: TrainingSettings, force_calibration: bool = False):
        self.settings = settings
        self.state = SessionState()
        self.calibration_data: Optional[CalibrationData] = None
        self.current_exercise_controller = None
        self._prev_right_reps = 0
        self._prev_left_reps = 0
        
        for ex in settings.exercises:
            self.state.exercise_stats[ex] = {"reps": 0, "errors": 0}
        
        if not force_calibration:
            self.calibration_data = CalibrationData.load()
            if self.calibration_data and self.calibration_data.calibrated:
                self.state.phase = SessionPhase.EXERCISE
                self._init_current_exercise()
    
    def needs_calibration(self) -> bool:
        """Check if calibration is required before training."""
        return self.state.phase == SessionPhase.CALIBRATION
    
    def start_exercise_phase(self, calibration_data: CalibrationData):
        """Transition from calibration to exercise phase."""
        self.calibration_data = calibration_data
        self.state.phase = SessionPhase.EXERCISE
        self.state.current_exercise_index = 0
        self.state.current_round = 1
        self._init_current_exercise()
    
    def _init_current_exercise(self):
        if self.state.current_exercise_index >= len(self.settings.exercises):
            return
            
        exercise_type = self.settings.exercises[self.state.current_exercise_index]
        
        if exercise_type == "bicep_curl":
            self.current_exercise_controller = BicepCurlController(self.calibration_data)
        elif exercise_type == "overhead_press":
            self.current_exercise_controller = OverheadPressController()
        else:
            self.current_exercise_controller = BicepCurlController(self.calibration_data)
        
        self.state.right_reps = 0
        self.state.left_reps = 0
        self._prev_right_reps = 0
        self._prev_left_reps = 0
        self.state.waiting_for_neutral = True
        self.state.neutral_frames = 0
    
    def get_current_exercise_name(self) -> str:
        """Get the Polish name of the current exercise."""
        if self.state.current_exercise_index >= len(self.settings.exercises):
            return "Brak ćwiczenia"
        exercise_type = self.settings.exercises[self.state.current_exercise_index]
        return EXERCISE_NAMES.get(exercise_type, exercise_type)
    
    def get_current_exercise_type(self) -> str:
        """Get the type identifier of the current exercise."""
        if self.state.current_exercise_index >= len(self.settings.exercises):
            return ""
        return self.settings.exercises[self.state.current_exercise_index]
    
    def process_frame(self, front_results, profile_results) -> Dict:
        if self.state.phase != SessionPhase.EXERCISE or not self.current_exercise_controller:
            return {"right_reps": 0, "left_reps": 0, "errors": {}}
        
        if self.state.waiting_for_neutral:
            is_neutral = self._check_neutral_pose(front_results)
            if is_neutral:
                self.state.neutral_frames += 1
                if self.state.neutral_frames >= 15:
                    self.state.waiting_for_neutral = False
                    self.state.neutral_frames = 0
            else:
                self.state.neutral_frames = 0
            return {"right_reps": 0, "left_reps": 0, "errors": {}, "waiting_for_neutral": True}
        
        metrics = self.current_exercise_controller.process_frames(front_results, profile_results)
        
        self.state.right_reps = metrics.get("right_reps", 0)
        self.state.left_reps = metrics.get("left_reps", 0)
        
        if metrics.get("rep_detected") and not metrics.get("valid"):
            self.state.total_errors += 1
            exercise_type = self.get_current_exercise_type()
            if exercise_type in self.state.exercise_stats:
                self.state.exercise_stats[exercise_type]["errors"] += 1
        
        return metrics
    
    def _check_neutral_pose(self, front_results) -> bool:
        if not front_results or not front_results.pose_landmarks:
            return False
        
        landmarks = front_results.pose_landmarks.landmark
        
        try:
            r_shoulder = landmarks[12]
            r_elbow = landmarks[14]
            r_wrist = landmarks[16]
            l_shoulder = landmarks[11]
            l_elbow = landmarks[13]
            l_wrist = landmarks[15]
            
            import math
            
            def calc_angle(a, b, c):
                ba = (a.x - b.x, a.y - b.y)
                bc = (c.x - b.x, c.y - b.y)
                dot = ba[0]*bc[0] + ba[1]*bc[1]
                mag_ba = math.sqrt(ba[0]**2 + ba[1]**2)
                mag_bc = math.sqrt(bc[0]**2 + bc[1]**2)
                if mag_ba * mag_bc == 0:
                    return 180
                cos_angle = dot / (mag_ba * mag_bc)
                cos_angle = max(-1, min(1, cos_angle))
                return math.degrees(math.acos(cos_angle))
            
            right_angle = calc_angle(r_shoulder, r_elbow, r_wrist)
            left_angle = calc_angle(l_shoulder, l_elbow, l_wrist)
            
            return right_angle > 150 and left_angle > 150
            
        except (IndexError, AttributeError):
            return False
    
    def check_set_complete(self) -> bool:
        """Check if the current set (target reps) is complete."""
        exercise_type = self.get_current_exercise_type()
        target_reps = self.settings.get_reps_for_exercise(exercise_type)
        
        if exercise_type == "overhead_press":
            return self.state.right_reps >= target_reps
        else:
            # For bicep curl, check if both arms completed
            return (self.state.right_reps >= target_reps and 
                    self.state.left_reps >= target_reps)
    
    def advance_to_next(self) -> Dict:
        exercise_type = self.get_current_exercise_type()
        completed_reps = min(self.state.right_reps, self.state.left_reps) if exercise_type == "bicep_curl" else self.state.right_reps
        
        if exercise_type in self.state.exercise_stats:
            self.state.exercise_stats[exercise_type]["reps"] += completed_reps
        
        self.state.total_right_reps += self.state.right_reps
        self.state.total_left_reps += self.state.left_reps
        
        next_exercise_index = self.state.current_exercise_index + 1
        
        if next_exercise_index >= len(self.settings.exercises):
            next_round = self.state.current_round + 1
            
            if next_round > self.settings.rounds:
                self.state.phase = SessionPhase.COMPLETED
                return {
                    "event": "training_complete",
                    "total_right_reps": self.state.total_right_reps,
                    "total_left_reps": self.state.total_left_reps
                }
            else:
                self.state.current_round = next_round
                self.state.current_exercise_index = 0
                self._init_current_exercise()
                return {
                    "event": "new_round",
                    "round": next_round,
                    "total_rounds": self.settings.rounds,
                    "exercise": self.get_current_exercise_name()
                }
        else:
            # Next exercise in same round
            self.state.current_exercise_index = next_exercise_index
            self._init_current_exercise()
            return {
                "event": "new_exercise",
                "exercise": self.get_current_exercise_name(),
                "round": self.state.current_round,
                "total_rounds": self.settings.rounds
            }
    
    def go_to_previous(self) -> Dict:
        """Go back to the previous exercise."""
        if self.state.current_exercise_index > 0:
            self.state.current_exercise_index -= 1
            self._init_current_exercise()
            return {
                "event": "previous_exercise",
                "exercise": self.get_current_exercise_name(),
                "round": self.state.current_round
            }
        elif self.state.current_round > 1:
            # Go to last exercise of previous round
            self.state.current_round -= 1
            self.state.current_exercise_index = len(self.settings.exercises) - 1
            self._init_current_exercise()
            return {
                "event": "previous_round",
                "exercise": self.get_current_exercise_name(),
                "round": self.state.current_round
            }
        return {"event": "at_start"}
    
    def go_to_next(self) -> Dict:
        """Skip to the next exercise (voice command)."""
        return self.advance_to_next()
    
    def get_state_dict(self) -> Dict:
        """Get current state as a dictionary for socket emission."""
        exercise_type = self.get_current_exercise_type()
        return {
            "phase": self.state.phase.value,
            "currentExercise": self.get_current_exercise_name(),
            "currentExerciseType": exercise_type,
            "exerciseIndex": self.state.current_exercise_index,
            "totalExercises": len(self.settings.exercises),
            "currentRound": self.state.current_round,
            "totalRounds": self.settings.rounds,
            "targetReps": self.settings.get_reps_for_exercise(exercise_type),
            "rightReps": self.state.right_reps,
            "leftReps": self.state.left_reps
        }
    
    def get_announcement_for_start(self) -> str:
        """Get the announcement text when starting current exercise."""
        exercise = self.get_current_exercise_name()
        exercise_type = self.get_current_exercise_type()
        round_num = self.state.current_round
        total_rounds = self.settings.rounds
        target = self.settings.get_reps_for_exercise(exercise_type)
        
        return f"Runda {round_num} z {total_rounds}. {exercise}. {target} powtórzeń."
    
    def is_complete(self) -> bool:
        return self.state.phase == SessionPhase.COMPLETED
    
    def get_completion_stats(self) -> Dict:
        total_reps = sum(stats["reps"] for stats in self.state.exercise_stats.values())
        return {
            "totalReps": total_reps,
            "totalErrors": self.state.total_errors,
            "exerciseStats": {
                EXERCISE_NAMES.get(ex, ex): stats 
                for ex, stats in self.state.exercise_stats.items()
            }
        }


def get_reset_functions(exercise_type: str):
    """Get the appropriate reset functions for an exercise type."""
    from exercises.bicep_curl.metrics import reset_front_view_state as reset_bicep_front
    from exercises.bicep_curl.metrics import reset_profile_view_state as reset_bicep_profile
    from exercises.overhead_press.metrics import reset_front_view_state as reset_overhead_front
    from exercises.overhead_press.metrics import reset_profile_view_state as reset_overhead_profile
    
    if exercise_type == "overhead_press":
        return reset_overhead_front, reset_overhead_profile
    else:
        return reset_bicep_front, reset_bicep_profile
