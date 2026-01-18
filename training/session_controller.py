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
    reps_per_set: int = 10
    rounds: int = 3
    
    @classmethod
    def from_dict(cls, data: dict) -> "TrainingSettings":
        return cls(
            exercises=data.get("exercises", ["bicep_curl", "overhead_press"]),
            reps_per_set=data.get("repsPerSet", 10),
            rounds=data.get("rounds", 3)
        )


@dataclass  
class SessionState:
    """Current state of the training session."""
    phase: SessionPhase = SessionPhase.CALIBRATION
    current_exercise_index: int = 0
    current_round: int = 1
    right_reps: int = 0
    left_reps: int = 0
    total_right_reps: int = 0
    total_left_reps: int = 0


EXERCISE_NAMES = {
    "bicep_curl": "Uginanie przedramion",
    "overhead_press": "Wyciskanie nad głowę"
}


class TrainingSessionController:
    """
    Manages the entire training session flow:
    1. Calibration (if needed)
    2. Multiple exercises with configurable reps
    3. Multiple rounds (podejścia)
    4. Voice command navigation
    """
    
    def __init__(self, settings: TrainingSettings, force_calibration: bool = False):
        self.settings = settings
        self.state = SessionState()
        self.calibration_data: Optional[CalibrationData] = None
        self.current_exercise_controller = None
        self._prev_right_reps = 0
        self._prev_left_reps = 0
        
        # Check if calibration is needed
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
        """Initialize the controller for the current exercise."""
        if self.state.current_exercise_index >= len(self.settings.exercises):
            return
            
        exercise_type = self.settings.exercises[self.state.current_exercise_index]
        
        if exercise_type == "bicep_curl":
            self.current_exercise_controller = BicepCurlController(self.calibration_data)
        elif exercise_type == "overhead_press":
            self.current_exercise_controller = OverheadPressController()
        else:
            # Default to bicep curl
            self.current_exercise_controller = BicepCurlController(self.calibration_data)
        
        # Reset rep counters for new exercise
        self.state.right_reps = 0
        self.state.left_reps = 0
        self._prev_right_reps = 0
        self._prev_left_reps = 0
    
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
        """
        Process a frame through the current exercise controller.
        Returns metrics and any state change events.
        """
        if self.state.phase != SessionPhase.EXERCISE or not self.current_exercise_controller:
            return {"right_reps": 0, "left_reps": 0, "errors": {}}
        
        metrics = self.current_exercise_controller.process_frames(front_results, profile_results)
        
        # Update rep counts
        self.state.right_reps = metrics.get("right_reps", 0)
        self.state.left_reps = metrics.get("left_reps", 0)
        
        return metrics
    
    def check_set_complete(self) -> bool:
        """Check if the current set (target reps) is complete."""
        # For exercises like overhead press, only check right_reps (which is total)
        exercise_type = self.get_current_exercise_type()
        
        if exercise_type == "overhead_press":
            return self.state.right_reps >= self.settings.reps_per_set
        else:
            # For bicep curl, check if both arms completed OR average
            return (self.state.right_reps >= self.settings.reps_per_set and 
                    self.state.left_reps >= self.settings.reps_per_set)
    
    def advance_to_next(self) -> Dict:
        """
        Advance to next exercise or round.
        Returns event info for announcements.
        """
        # Accumulate totals
        self.state.total_right_reps += self.state.right_reps
        self.state.total_left_reps += self.state.left_reps
        
        next_exercise_index = self.state.current_exercise_index + 1
        
        if next_exercise_index >= len(self.settings.exercises):
            # Finished all exercises in this round
            next_round = self.state.current_round + 1
            
            if next_round > self.settings.rounds:
                # Training complete!
                self.state.phase = SessionPhase.COMPLETED
                return {
                    "event": "training_complete",
                    "total_right_reps": self.state.total_right_reps,
                    "total_left_reps": self.state.total_left_reps
                }
            else:
                # Next round, back to first exercise
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
        return {
            "phase": self.state.phase.value,
            "currentExercise": self.get_current_exercise_name(),
            "currentExerciseType": self.get_current_exercise_type(),
            "exerciseIndex": self.state.current_exercise_index,
            "totalExercises": len(self.settings.exercises),
            "currentRound": self.state.current_round,
            "totalRounds": self.settings.rounds,
            "targetReps": self.settings.reps_per_set,
            "rightReps": self.state.right_reps,
            "leftReps": self.state.left_reps
        }
    
    def get_announcement_for_start(self) -> str:
        """Get the announcement text when starting current exercise."""
        exercise = self.get_current_exercise_name()
        round_num = self.state.current_round
        total_rounds = self.settings.rounds
        target = self.settings.reps_per_set
        
        return f"Runda {round_num} z {total_rounds}. {exercise}. {target} powtórzeń."
    
    def is_complete(self) -> bool:
        """Check if the entire training session is complete."""
        return self.state.phase == SessionPhase.COMPLETED


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
