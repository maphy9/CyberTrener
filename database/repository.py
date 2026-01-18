import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from database.models import DB_PATH, TrainingSession, ExerciseResult


class TrainingRepository:
    
    @staticmethod
    def _get_connection():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def _calculate_improvement(current: float, average: float, lower_is_better: bool = False) -> Optional[float]:
        if average == 0:
            return None
        if lower_is_better:
            improvement = ((average - current) / average) * 100
        else:
            improvement = ((current - average) / average) * 100
        return round(improvement, 1)
    
    @classmethod
    def get_averages(cls) -> Dict:
        conn = cls._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                AVG(total_reps) as avg_total_reps,
                AVG(total_errors) as avg_total_errors,
                COUNT(*) as session_count
            FROM training_sessions
        ''')
        overall = cursor.fetchone()
        
        cursor.execute('''
            SELECT 
                exercise_type,
                AVG(reps) as avg_reps,
                AVG(errors) as avg_errors
            FROM exercise_results
            GROUP BY exercise_type
        ''')
        exercise_rows = cursor.fetchall()
        
        exercise_averages = {}
        for row in exercise_rows:
            exercise_averages[row['exercise_type']] = {
                'avg_reps': row['avg_reps'] or 0,
                'avg_errors': row['avg_errors'] or 0
            }
        
        conn.close()
        
        return {
            'session_count': overall['session_count'] or 0,
            'avg_total_reps': overall['avg_total_reps'] or 0,
            'avg_total_errors': overall['avg_total_errors'] or 0,
            'exercise_averages': exercise_averages
        }
    
    @classmethod
    def save_session(cls, session_data: Dict) -> int:
        averages = cls.get_averages()
        
        overall_reps_improvement = None
        overall_errors_improvement = None
        
        if averages['session_count'] > 0:
            overall_reps_improvement = cls._calculate_improvement(
                session_data['total_reps'],
                averages['avg_total_reps'],
                lower_is_better=False
            )
            overall_errors_improvement = cls._calculate_improvement(
                session_data['total_errors'],
                averages['avg_total_errors'],
                lower_is_better=True
            )
        
        conn = cls._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO training_sessions 
            (timestamp, duration_seconds, total_reps, total_errors, rounds, exercises_config, overall_reps_improvement, overall_errors_improvement)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_data['timestamp'],
            session_data['duration_seconds'],
            session_data['total_reps'],
            session_data['total_errors'],
            session_data['rounds'],
            json.dumps(session_data['exercises_config']),
            overall_reps_improvement,
            overall_errors_improvement
        ))
        
        session_id = cursor.lastrowid
        
        for exercise in session_data['exercise_results']:
            exercise_type = exercise['exercise_type']
            
            reps_improvement = None
            errors_improvement = None
            
            if exercise_type in averages['exercise_averages']:
                ex_avg = averages['exercise_averages'][exercise_type]
                reps_improvement = cls._calculate_improvement(
                    exercise['reps'],
                    ex_avg['avg_reps'],
                    lower_is_better=False
                )
                errors_improvement = cls._calculate_improvement(
                    exercise['errors'],
                    ex_avg['avg_errors'],
                    lower_is_better=True
                )
            
            cursor.execute('''
                INSERT INTO exercise_results 
                (session_id, exercise_type, exercise_name, reps, errors, reps_improvement, errors_improvement)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                exercise_type,
                exercise['exercise_name'],
                exercise['reps'],
                exercise['errors'],
                reps_improvement,
                errors_improvement
            ))
            
            exercise_result_id = cursor.lastrowid
            
            for error_type, error_count in exercise.get('error_details', {}).items():
                if error_count > 0:
                    cursor.execute('''
                        INSERT INTO exercise_errors (exercise_result_id, error_type, error_count)
                        VALUES (?, ?, ?)
                    ''', (exercise_result_id, error_type, error_count))
        
        conn.commit()
        conn.close()
        
        return session_id or 0
    
    @classmethod
    def get_all_sessions(cls, sort_order: str = 'desc', date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[TrainingSession]:
        conn = cls._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM training_sessions WHERE 1=1'
        params = []
        
        if date_from:
            query += ' AND timestamp >= ?'
            params.append(date_from)
        if date_to:
            query += ' AND timestamp <= ?'
            params.append(date_to + 'T23:59:59')
        
        order = 'DESC' if sort_order == 'desc' else 'ASC'
        query += f' ORDER BY timestamp {order}'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        sessions = []
        for row in rows:
            session = TrainingSession(
                id=row['id'],
                timestamp=row['timestamp'],
                duration_seconds=row['duration_seconds'],
                total_reps=row['total_reps'],
                total_errors=row['total_errors'],
                rounds=row['rounds'],
                exercises_config=row['exercises_config'],
                overall_reps_improvement=row['overall_reps_improvement'],
                overall_errors_improvement=row['overall_errors_improvement']
            )
            sessions.append(session)
        
        conn.close()
        return sessions
    
    @classmethod
    def get_session_detail(cls, session_id: int) -> Optional[TrainingSession]:
        conn = cls._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM training_sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        session = TrainingSession(
            id=row['id'],
            timestamp=row['timestamp'],
            duration_seconds=row['duration_seconds'],
            total_reps=row['total_reps'],
            total_errors=row['total_errors'],
            rounds=row['rounds'],
            exercises_config=row['exercises_config'],
            overall_reps_improvement=row['overall_reps_improvement'],
            overall_errors_improvement=row['overall_errors_improvement']
        )
        
        cursor.execute('SELECT * FROM exercise_results WHERE session_id = ?', (session_id,))
        exercise_rows = cursor.fetchall()
        
        for ex_row in exercise_rows:
            cursor.execute('SELECT * FROM exercise_errors WHERE exercise_result_id = ?', (ex_row['id'],))
            error_rows = cursor.fetchall()
            
            error_details = {}
            for err_row in error_rows:
                error_details[err_row['error_type']] = err_row['error_count']
            
            exercise_result = ExerciseResult(
                exercise_type=ex_row['exercise_type'],
                exercise_name=ex_row['exercise_name'],
                reps=ex_row['reps'],
                errors=ex_row['errors'],
                error_details=error_details,
                reps_improvement=ex_row['reps_improvement'],
                errors_improvement=ex_row['errors_improvement']
            )
            session.exercise_results.append(exercise_result)
        
        conn.close()
        return session
    
    @classmethod
    def delete_session(cls, session_id: int) -> bool:
        conn = cls._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM exercise_results WHERE session_id = ?', (session_id,))
        exercise_ids = [row['id'] for row in cursor.fetchall()]
        
        for ex_id in exercise_ids:
            cursor.execute('DELETE FROM exercise_errors WHERE exercise_result_id = ?', (ex_id,))
        
        cursor.execute('DELETE FROM exercise_results WHERE session_id = ?', (session_id,))
        cursor.execute('DELETE FROM training_sessions WHERE id = ?', (session_id,))
        
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        
        return deleted
