import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Database path
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "tasks.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_connection():
    """Get database connection with proper settings."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    return conn

def init_database():
    """Initialize database with all required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Main tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            deadline TIMESTAMP,
            calendar_target TEXT,  -- 'Work' or 'Home'
            status TEXT DEFAULT 'pending',  -- 'pending', 'scheduled', 'completed', 'cancelled'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            needs_subtasks BOOLEAN DEFAULT 1,
            estimated_minutes INTEGER,
            task_type TEXT  -- 'deep_work', 'meeting', 'quick_task', 'research'
        )
    """)
    
    # Subtasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subtasks (
            id TEXT PRIMARY KEY,
            parent_task_id TEXT NOT NULL,
            title TEXT NOT NULL,
            estimated_minutes INTEGER,
            actual_minutes INTEGER,  -- learned from completion
            order_index INTEGER,
            calendar_event_id TEXT,  -- link to Apple Calendar event
            status TEXT DEFAULT 'pending',  -- 'pending', 'scheduled', 'completed', 'cancelled'
            scheduled_start TIMESTAMP,
            scheduled_end TIMESTAMP,
            task_type TEXT,  -- 'deep_work', 'meeting', 'quick_task', 'research'
            FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """)
    
    # User persona/constraints
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS persona_constraints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            constraint_type TEXT NOT NULL,  -- 'recurring_block', 'work_hours', 'preference'
            data TEXT NOT NULL,  -- JSON string
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Learning: track actual vs estimated durations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS duration_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subtask_id TEXT,
            task_type TEXT,  -- for pattern matching
            estimated_minutes INTEGER,
            actual_minutes INTEGER,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subtask_id) REFERENCES subtasks(id)
        )
    """)
    
    # Chat sessions for frontend
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Chat messages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,  -- 'user' or 'assistant'
            content TEXT NOT NULL,
            task_id TEXT,  -- link to task if message created one
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)
    
    conn.commit()
    conn.close()
    
    # Insert default persona constraints if none exist
    _insert_default_persona()

def _insert_default_persona():
    """Insert default persona constraints if none exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if any constraints exist
    cursor.execute("SELECT COUNT(*) FROM persona_constraints")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    # Default work hours (9-5, weekdays only)
    work_hours = {
        "monday": ["09:00", "17:00"],
        "tuesday": ["09:00", "17:00"],
        "wednesday": ["09:00", "17:00"],
        "thursday": ["09:00", "17:00"],
        "friday": ["09:00", "17:00"],
        "saturday": None,
        "sunday": None
    }
    
    cursor.execute("""
        INSERT INTO persona_constraints (constraint_type, data)
        VALUES ('work_hours', ?)
    """, (json.dumps(work_hours),))
    
    # Default preferences
    preferences = {
        "deep_work_hours": ["09:00", "12:00"],
        "meeting_hours": ["14:00", "17:00"],
        "min_block_minutes": 30,
        "buffer_minutes": 15
    }
    
    cursor.execute("""
        INSERT INTO persona_constraints (constraint_type, data)
        VALUES ('preference', ?)
    """, (json.dumps(preferences),))
    
    conn.commit()
    conn.close()

def get_persona_constraints() -> Dict[str, Any]:
    """Get all active persona constraints."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT constraint_type, data FROM persona_constraints 
        WHERE active = 1
    """)
    
    constraints = {}
    for row in cursor.fetchall():
        constraints[row['constraint_type']] = json.loads(row['data'])
    
    conn.close()
    return constraints

def update_persona_constraints(constraints: Dict[str, Any]):
    """Update persona constraints."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clear existing constraints
    cursor.execute("DELETE FROM persona_constraints")
    
    # Insert new constraints
    for constraint_type, data in constraints.items():
        cursor.execute("""
            INSERT INTO persona_constraints (constraint_type, data)
            VALUES (?, ?)
        """, (constraint_type, json.dumps(data)))
    
    conn.commit()
    conn.close()

# Initialize database on import
init_database()
