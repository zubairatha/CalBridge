"""
Task Scheduler and Event Creator
Manages task and subtask storage in SQL database and creates calendar events.
"""

import sqlite3
import json
import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Default configuration
CALBRIDGE_BASE = os.getenv("CALBRIDGE_BASE", "http://127.0.0.1:8765")


class TaskScheduler:
    """Manages task storage and calendar event creation."""
    
    def __init__(self, db_path: str = "task_scheduler.db"):
        """Initialize the task scheduler.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    calendar_assignment TEXT,
                    calendar_id TEXT,
                    task_complexity TEXT,
                    estimated_total_hours REAL,
                    deadline DATETIME,
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create subtasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subtasks (
                    subtask_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_task_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    estimated_hours REAL,
                    difficulty TEXT,
                    priority INTEGER,
                    dependencies TEXT,  -- JSON array of subtask IDs
                    status TEXT DEFAULT 'pending',
                    scheduled_start DATETIME,
                    scheduled_end DATETIME,
                    actual_start DATETIME,
                    actual_end DATETIME,
                    calendar_event_id TEXT,  -- ID of created calendar event
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_task_id) REFERENCES tasks (task_id) ON DELETE CASCADE
                )
            """)
            
            # Create calendar_events table to track created events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calendar_events (
                    event_id TEXT PRIMARY KEY,
                    subtask_id INTEGER,
                    task_id INTEGER,
                    title TEXT NOT NULL,
                    start_iso TEXT NOT NULL,
                    end_iso TEXT NOT NULL,
                    calendar_id TEXT,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subtask_id) REFERENCES subtasks (subtask_id) ON DELETE CASCADE,
                    FOREIGN KEY (task_id) REFERENCES tasks (task_id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
    
    def create_task(self, decomposed_task: Dict[str, Any], 
                   time_allocation: Optional[Dict[str, Any]] = None) -> Tuple[int, List[int]]:
        """Create a task and its subtasks in the database.
        
        Args:
            decomposed_task: Task decomposition result
            time_allocation: Optional time allocation result
            
        Returns:
            Tuple of (task_id, list of subtask_ids)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert main task
            cursor.execute("""
                INSERT INTO tasks (
                    title, description, calendar_assignment, calendar_id,
                    task_complexity, estimated_total_hours, deadline, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decomposed_task.get('title', 'Untitled Task'),
                decomposed_task.get('notes', ''),
                decomposed_task.get('calendar_assignment', 'work'),
                decomposed_task.get('calendar_id'),
                decomposed_task.get('task_complexity', 'medium'),
                decomposed_task.get('estimated_total_hours', 1.0),
                decomposed_task.get('deadline'),
                'pending'
            ))
            
            task_id = cursor.lastrowid
            subtask_ids = []
            
            # Insert subtasks
            for subtask_data in decomposed_task.get('subtasks', []):
                # Find time allocation for this subtask if available
                scheduled_start = None
                scheduled_end = None
                
                if time_allocation:
                    for allocation in time_allocation.get('allocations', []):
                        if allocation.get('subtask_id') == subtask_data['id']:
                            scheduled_start = allocation.get('scheduled_start')
                            scheduled_end = allocation.get('scheduled_end')
                            break
                
                # Convert dependencies to JSON string
                dependencies_json = json.dumps(subtask_data.get('dependencies', []))
                
                cursor.execute("""
                    INSERT INTO subtasks (
                        parent_task_id, title, description, estimated_hours,
                        difficulty, priority, dependencies, scheduled_start, scheduled_end, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id,
                    subtask_data['title'],
                    subtask_data.get('description', ''),
                    subtask_data['estimated_hours'],
                    subtask_data['difficulty'],
                    subtask_data['priority'],
                    dependencies_json,
                    scheduled_start,
                    scheduled_end,
                    'pending'
                ))
                
                subtask_ids.append(cursor.lastrowid)
            
            conn.commit()
            return task_id, subtask_ids
    
    def create_calendar_events(self, task_id: int, time_allocation: Dict[str, Any]) -> List[str]:
        """Create calendar events for scheduled subtasks.
        
        Args:
            task_id: ID of the parent task
            time_allocation: Time allocation result
            
        Returns:
            List of created event IDs
        """
        created_events = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get task details
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            task = cursor.fetchone()
            if not task:
                raise Exception(f"Task {task_id} not found")
            
            # Get subtasks for this task
            cursor.execute("SELECT * FROM subtasks WHERE parent_task_id = ?", (task_id,))
            subtasks = cursor.fetchall()
            
            # Create mapping from subtask data ID to database subtask
            subtask_mapping = {}
            for subtask in subtasks:
                subtask_id = subtask[0]  # subtask_id is first column
                # We need to match by title since we don't store the original ID
                subtask_mapping[subtask[2]] = subtask  # title is third column
            
            # Create events for each allocation
            for allocation in time_allocation.get('allocations', []):
                subtask_title = allocation.get('subtask_id')
                
                # Find matching subtask
                matching_subtask = None
                for title, subtask in subtask_mapping.items():
                    if subtask_title in title or title in subtask_title:
                        matching_subtask = subtask
                        break
                
                if not matching_subtask:
                    print(f"Warning: Could not find subtask for allocation {subtask_title}")
                    continue
                
                subtask_id = matching_subtask[0]
                
                # Create calendar event
                event_data = {
                    "title": f"{subtask_title}: {matching_subtask[2]}",  # subtask title
                    "start_iso": allocation['scheduled_start'],
                    "end_iso": allocation['scheduled_end'],
                    "notes": self._create_event_notes(task_id, subtask_id, allocation),
                    "calendar_id": task[4]  # calendar_id from task
                }
                
                try:
                    response = requests.post(
                        f"{CALBRIDGE_BASE}/add",
                        json=event_data,
                        timeout=15
                    )
                    response.raise_for_status()
                    
                    event_result = response.json()
                    event_id = event_result.get('id')
                    
                    if event_id:
                        # Update subtask with event ID
                        cursor.execute("""
                            UPDATE subtasks 
                            SET calendar_event_id = ?, status = 'scheduled'
                            WHERE subtask_id = ?
                        """, (event_id, subtask_id))
                        
                        # Record calendar event
                        cursor.execute("""
                            INSERT INTO calendar_events (
                                event_id, subtask_id, task_id, title, start_iso, end_iso, calendar_id, notes
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            event_id, subtask_id, task_id, event_data['title'],
                            allocation['scheduled_start'], allocation['scheduled_end'],
                            task[4], event_data['notes']
                        ))
                        
                        created_events.append(event_id)
                        print(f"Created calendar event: {event_data['title']} at {allocation['scheduled_start']}")
                    
                except requests.exceptions.RequestException as e:
                    print(f"Failed to create calendar event for {subtask_title}: {e}")
            
            conn.commit()
        
        return created_events
    
    def _create_event_notes(self, task_id: int, subtask_id: int, allocation: Dict[str, Any]) -> str:
        """Create notes for calendar event.
        
        Args:
            task_id: Parent task ID
            subtask_id: Subtask ID
            allocation: Time allocation data
            
        Returns:
            Formatted notes string
        """
        notes_parts = [
            f"parent_id: {task_id}",
            f"subtask_id: {subtask_id}"
        ]
        
        if allocation.get('reasoning'):
            notes_parts.append(f"reasoning: {allocation['reasoning']}")
        
        # Add any additional notes from allocation
        if allocation.get('notes'):
            notes_parts.append(allocation['notes'])
        
        return "; ".join(notes_parts)
    
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get task details with subtasks.
        
        Args:
            task_id: Task ID to retrieve
            
        Returns:
            Task dictionary with subtasks or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get task
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            task_row = cursor.fetchone()
            if not task_row:
                return None
            
            # Get subtasks
            cursor.execute("SELECT * FROM subtasks WHERE parent_task_id = ? ORDER BY priority", (task_id,))
            subtask_rows = cursor.fetchall()
            
            # Convert to dictionaries
            task = {
                'task_id': task_row[0],
                'title': task_row[1],
                'description': task_row[2],
                'calendar_assignment': task_row[3],
                'calendar_id': task_row[4],
                'task_complexity': task_row[5],
                'estimated_total_hours': task_row[6],
                'deadline': task_row[7],
                'status': task_row[8],
                'created_at': task_row[9],
                'updated_at': task_row[10],
                'subtasks': []
            }
            
            for subtask_row in subtask_rows:
                subtask = {
                    'subtask_id': subtask_row[0],
                    'parent_task_id': subtask_row[1],
                    'title': subtask_row[2],
                    'description': subtask_row[3],
                    'estimated_hours': subtask_row[4],
                    'difficulty': subtask_row[5],
                    'priority': subtask_row[6],
                    'dependencies': json.loads(subtask_row[7] or '[]'),
                    'status': subtask_row[8],
                    'scheduled_start': subtask_row[9],
                    'scheduled_end': subtask_row[10],
                    'actual_start': subtask_row[11],
                    'actual_end': subtask_row[12],
                    'calendar_event_id': subtask_row[13],
                    'notes': subtask_row[14],
                    'created_at': subtask_row[15],
                    'updated_at': subtask_row[16]
                }
                task['subtasks'].append(subtask)
            
            return task
    
    def get_all_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all tasks, optionally filtered by status.
        
        Args:
            status: Optional status filter ('pending', 'scheduled', 'completed', etc.)
            
        Returns:
            List of task dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute("SELECT task_id FROM tasks WHERE status = ? ORDER BY created_at DESC", (status,))
            else:
                cursor.execute("SELECT task_id FROM tasks ORDER BY created_at DESC")
            
            task_ids = [row[0] for row in cursor.fetchall()]
            
            return [self.get_task(task_id) for task_id in task_ids if self.get_task(task_id)]
    
    def update_subtask_status(self, subtask_id: int, status: str, 
                            actual_start: Optional[datetime] = None,
                            actual_end: Optional[datetime] = None) -> bool:
        """Update subtask status and timing.
        
        Args:
            subtask_id: Subtask ID to update
            status: New status
            actual_start: Optional actual start time
            actual_end: Optional actual end time
            
        Returns:
            True if updated successfully
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE subtasks 
                SET status = ?, actual_start = ?, actual_end = ?, updated_at = CURRENT_TIMESTAMP
                WHERE subtask_id = ?
            """, (status, actual_start, actual_end, subtask_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_task(self, task_id: int) -> bool:
        """Delete a task and all its subtasks.
        
        Args:
            task_id: Task ID to delete
            
        Returns:
            True if deleted successfully
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete calendar events first (they have foreign keys)
            cursor.execute("DELETE FROM calendar_events WHERE task_id = ?", (task_id,))
            
            # Delete subtasks (will cascade from tasks table)
            cursor.execute("DELETE FROM subtasks WHERE parent_task_id = ?", (task_id,))
            
            # Delete main task
            cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            
            conn.commit()
            return cursor.rowcount > 0


# Example usage and testing
if __name__ == "__main__":
    try:
        scheduler = TaskScheduler()
        
        # Example decomposed task
        decomposed_task = {
            "title": "Build a mobile app for tracking fitness goals",
            "calendar_assignment": "work",
            "calendar_id": "some-calendar-id",
            "task_complexity": "medium",
            "estimated_total_hours": 4.0,
            "subtasks": [
                {
                    "id": "subtask_1",
                    "title": "Research requirements",
                    "description": "Research user requirements and app features",
                    "estimated_hours": 1.0,
                    "priority": 1,
                    "difficulty": "low"
                },
                {
                    "id": "subtask_2",
                    "title": "Design system architecture",
                    "description": "Create system architecture and database design",
                    "estimated_hours": 2.0,
                    "priority": 2,
                    "difficulty": "high",
                    "dependencies": ["subtask_1"]
                }
            ],
            "notes": "Mobile app development project"
        }
        
        # Create task
        task_id, subtask_ids = scheduler.create_task(decomposed_task)
        print(f"Created task {task_id} with subtasks {subtask_ids}")
        
        # Get task details
        task = scheduler.get_task(task_id)
        print(f"Retrieved task: {task['title']}")
        
        # Get all tasks
        all_tasks = scheduler.get_all_tasks()
        print(f"Total tasks: {len(all_tasks)}")
        
    except Exception as e:
        print(f"Error: {e}")
