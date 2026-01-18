import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'training_history.db')


@dataclass
class ExerciseResult:
    exercise_type: str
    exercise_name: str
    reps: int
    errors: int
    error_details: Dict[str, int] = field(default_factory=dict)
    reps_improvement: Optional[float] = None
    errors_improvement: Optional[float] = None


@dataclass
class TrainingSession:
    id: Optional[int] = None
    timestamp: str = ""
    duration_seconds: int = 0
    total_reps: int = 0
    total_errors: int = 0
    rounds: int = 0
    exercises_config: str = ""
    exercise_results: List[ExerciseResult] = field(default_factory=list)
    overall_reps_improvement: Optional[float] = None
    overall_errors_improvement: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "total_reps": self.total_reps,
            "total_errors": self.total_errors,
            "rounds": self.rounds,
            "exercises_config": self.exercises_config,
            "overall_reps_improvement": self.overall_reps_improvement,
            "overall_errors_improvement": self.overall_errors_improvement,
            "exercise_results": [
                {
                    "exercise_type": r.exercise_type,
                    "exercise_name": r.exercise_name,
                    "reps": r.reps,
                    "errors": r.errors,
                    "error_details": r.error_details,
                    "reps_improvement": r.reps_improvement,
                    "errors_improvement": r.errors_improvement
                }
                for r in self.exercise_results
            ]
        }


def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            total_reps INTEGER NOT NULL,
            total_errors INTEGER NOT NULL,
            rounds INTEGER NOT NULL,
            exercises_config TEXT NOT NULL,
            overall_reps_improvement REAL,
            overall_errors_improvement REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercise_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            exercise_type TEXT NOT NULL,
            exercise_name TEXT NOT NULL,
            reps INTEGER NOT NULL,
            errors INTEGER NOT NULL,
            reps_improvement REAL,
            errors_improvement REAL,
            FOREIGN KEY (session_id) REFERENCES training_sessions(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercise_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_result_id INTEGER NOT NULL,
            error_type TEXT NOT NULL,
            error_count INTEGER NOT NULL,
            FOREIGN KEY (exercise_result_id) REFERENCES exercise_results(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()


init_database()
