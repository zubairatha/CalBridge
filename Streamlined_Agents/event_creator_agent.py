"""
Event Creator Agent - Creates calendar events via CalBridge API

This agent:
1. Creates calendar events from Time Allotment outputs
2. Stores task metadata in local SQLite database
3. Handles deletion (by id or parent_id with cascade)
4. Maintains event_map for tracking calendar events
"""
import sqlite3
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass


@dataclass
class CreateResult:
    """Result of create operation"""
    success: bool
    task_id: str
    calendar_event_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class DeleteResult:
    """Result of delete operation"""
    stage: str = "EC"
    kind: str = "delete"
    target: str = ""  # "id" or "parent_id"
    deleted: List[Dict[str, str]] = None
    skipped: List[Dict[str, str]] = None
    errors: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.deleted is None:
            self.deleted = []
        if self.skipped is None:
            self.skipped = []
        if self.errors is None:
            self.errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "kind": self.kind,
            "target": self.target,
            "deleted": self.deleted,
            "skipped": self.skipped,
            "errors": self.errors
        }


class EventCreatorAgent:
    """
    Event Creator Agent for creating and deleting calendar events
    
    Handles:
    - Simple tasks: Create 1 event
    - Complex tasks: Create events for subtasks only (no parent event)
    - Delete by id: Cascade delete if parent
    - Delete by parent_id: Delete all children + parent
    """
    
    def __init__(self, 
                 calbridge_base_url: str = "http://127.0.0.1:8765",
                 db_path: Optional[str] = None):
        """
        Initialize Event Creator Agent
        
        Args:
            calbridge_base_url: Base URL for CalBridge API
            db_path: Path to SQLite database (default: event_creator.db in current dir)
        """
        self.calbridge_base_url = calbridge_base_url
        
        # Set up database
        if db_path is None:
            db_path = str(Path(__file__).parent / "event_creator.db")
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with tasks and event_map tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                parent_id TEXT NULL
            )
        """)
        
        # Create event_map table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_map (
                task_id TEXT PRIMARY KEY,
                calendar_id TEXT NOT NULL,
                calendar_event_id TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                UNIQUE(calendar_id, calendar_event_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def _calbridge_post_with_retry(self, 
                                   payload: Dict[str, Any],
                                   max_retries: int = 3) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        POST to CalBridge with retry logic
        
        Args:
            payload: Request payload
            max_retries: Maximum number of retries
            
        Returns:
            (success, response_data, error_message)
        """
        backoff_delays = [0.1, 0.5, 2.0]  # 100ms, 500ms, 2s
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.calbridge_base_url}/add",
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return True, response.json(), None
                elif response.status_code < 500:
                    # 4xx errors - don't retry
                    return False, None, f"CalBridge error {response.status_code}: {response.text}"
                else:
                    # 5xx errors - retry
                    if attempt < max_retries - 1:
                        time.sleep(backoff_delays[attempt])
                        continue
                    return False, None, f"CalBridge server error {response.status_code}: {response.text}"
                    
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(backoff_delays[attempt])
                    continue
                return False, None, f"Network error: {e}"
        
        return False, None, "Max retries exceeded"
    
    def _calbridge_delete_with_retry(self,
                                    event_id: str,
                                    max_retries: int = 3) -> Tuple[bool, bool, Optional[str]]:
        """
        DELETE from CalBridge with retry logic
        
        Args:
            event_id: Calendar event ID to delete
            max_retries: Maximum number of retries
            
        Returns:
            (success, was_404, error_message)
            was_404: True if event was already deleted (404)
        """
        backoff_delays = [0.1, 0.5, 2.0]
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.calbridge_base_url}/delete",
                    params={"event_id": event_id},
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("deleted"):
                        return True, False, None
                    else:
                        # Event not found - treat as success (already deleted)
                        return True, True, None
                elif response.status_code == 404:
                    # Already deleted
                    return True, True, None
                elif response.status_code < 500:
                    # 4xx errors - don't retry
                    return False, False, f"CalBridge error {response.status_code}: {response.text}"
                else:
                    # 5xx errors - retry
                    if attempt < max_retries - 1:
                        time.sleep(backoff_delays[attempt])
                        continue
                    return False, False, f"CalBridge server error {response.status_code}: {response.text}"
                    
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(backoff_delays[attempt])
                    continue
                return False, False, f"Network error: {e}"
        
        return False, False, "Max retries exceeded"
    
    def _validate_simple_task(self, ta_output: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate simple task input"""
        if ta_output.get("type") != "simple":
            return False, f"Expected simple task, got type: {ta_output.get('type')}"
        
        if not ta_output.get("calendar"):
            return False, "Missing calendar ID"
        
        if not ta_output.get("title"):
            return False, "Missing title"
        
        slot = ta_output.get("slot")
        if not slot or len(slot) != 2:
            return False, "Missing or invalid slot (must have [start, end])"
        
        if not ta_output.get("id"):
            return False, "Missing task ID"
        
        if ta_output.get("parent_id") is not None:
            return False, "Simple task must have parent_id = null"
        
        # Validate start < end
        start = datetime.fromisoformat(slot[0].replace('Z', '+00:00'))
        end = datetime.fromisoformat(slot[1].replace('Z', '+00:00'))
        if start >= end:
            return False, f"Invalid slot: start >= end ({slot[0]} >= {slot[1]})"
        
        return True, None
    
    def _validate_complex_task(self, ta_output: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate complex task input"""
        if ta_output.get("type") != "complex":
            return False, f"Expected complex task, got type: {ta_output.get('type')}"
        
        if not ta_output.get("calendar"):
            return False, "Missing calendar ID"
        
        if not ta_output.get("title"):
            return False, "Missing title"
        
        if not ta_output.get("id"):
            return False, "Missing parent task ID"
        
        if ta_output.get("parent_id") is not None:
            return False, "Parent task must have parent_id = null"
        
        subtasks = ta_output.get("subtasks", [])
        if not subtasks or len(subtasks) < 1:
            return False, "Complex task must have at least 1 subtask"
        
        if len(subtasks) > 5:
            return False, "Complex task cannot have more than 5 subtasks"
        
        parent_id = ta_output.get("id")
        for i, subtask in enumerate(subtasks):
            if not subtask.get("title"):
                return False, f"Subtask {i+1} missing title"
            
            slot = subtask.get("slot")
            if not slot or len(slot) != 2:
                return False, f"Subtask {i+1} missing or invalid slot"
            
            if not subtask.get("id"):
                return False, f"Subtask {i+1} missing ID"
            
            if subtask.get("parent_id") != parent_id:
                return False, f"Subtask {i+1} parent_id must match parent ID"
            
            # Validate start < end
            start = datetime.fromisoformat(slot[0].replace('Z', '+00:00'))
            end = datetime.fromisoformat(slot[1].replace('Z', '+00:00'))
            if start >= end:
                return False, f"Subtask {i+1} invalid slot: start >= end"
        
        return True, None
    
    def create_simple_task(self, ta_output: Dict[str, Any]) -> CreateResult:
        """
        Create a simple task event
        
        Args:
            ta_output: Time Allotment output for simple task
            
        Returns:
            CreateResult with success status and event ID
        """
        # Validate input
        is_valid, error = self._validate_simple_task(ta_output)
        if not is_valid:
            return CreateResult(success=False, task_id=ta_output.get("id", ""), error=error)
        
        task_id = ta_output["id"]
        calendar_id = ta_output["calendar"]
        title = ta_output["title"]
        slot = ta_output["slot"]
        
        # Build CalBridge POST payload
        payload = {
            "calendar_id": calendar_id,
            "title": title,
            "start_iso": slot[0],
            "end_iso": slot[1],
            "notes": f"id:{task_id}, parent_id:null"
        }
        
        # POST to CalBridge with retry
        success, response_data, error = self._calbridge_post_with_retry(payload)
        
        if not success:
            return CreateResult(success=False, task_id=task_id, error=error)
        
        calendar_event_id = response_data.get("id")
        if not calendar_event_id:
            return CreateResult(success=False, task_id=task_id, error="CalBridge did not return event ID")
        
        # Upsert to database
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Upsert task
            cursor.execute("""
                INSERT OR REPLACE INTO tasks (id, title, parent_id)
                VALUES (?, ?, ?)
            """, (task_id, title, None))
            
            # Upsert event_map
            cursor.execute("""
                INSERT OR REPLACE INTO event_map (task_id, calendar_id, calendar_event_id)
                VALUES (?, ?, ?)
            """, (task_id, calendar_id, calendar_event_id))
            
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            return CreateResult(success=False, task_id=task_id, error=f"Database error: {e}")
        finally:
            conn.close()
        
        return CreateResult(success=True, task_id=task_id, calendar_event_id=calendar_event_id)
    
    def create_complex_task(self, ta_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a complex task (subtasks only, no parent event)
        
        Args:
            ta_output: Time Allotment output for complex task
            
        Returns:
            Dict with created events and any failures
        """
        # Validate input
        is_valid, error = self._validate_complex_task(ta_output)
        if not is_valid:
            return {
                "success": False,
                "error": error,
                "created": [],
                "failed": []
            }
        
        parent_id = ta_output["id"]
        parent_title = ta_output["title"]
        calendar_id = ta_output["calendar"]
        subtasks = ta_output["subtasks"]
        
        created = []
        failed = []
        
        # Create events for each subtask
        for subtask in subtasks:
            subtask_id = subtask["id"]
            subtask_title = subtask["title"]
            slot = subtask["slot"]
            
            # Build CalBridge POST payload
            payload = {
                "calendar_id": calendar_id,
                "title": subtask_title,
                "start_iso": slot[0],
                "end_iso": slot[1],
                "notes": f"id:{subtask_id}, parent_id:{parent_id}"
            }
            
            # POST to CalBridge with retry
            success, response_data, error = self._calbridge_post_with_retry(payload)
            
            if success and response_data:
                calendar_event_id = response_data.get("id")
                if calendar_event_id:
                    created.append({
                        "task_id": subtask_id,
                        "calendar_event_id": calendar_event_id
                    })
                else:
                    failed.append({
                        "task_id": subtask_id,
                        "error": "CalBridge did not return event ID"
                    })
            else:
                failed.append({
                    "task_id": subtask_id,
                    "error": error or "Unknown error"
                })
        
        # Upsert to database (even if some subtasks failed)
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Upsert parent task (no event, just metadata)
            cursor.execute("""
                INSERT OR REPLACE INTO tasks (id, title, parent_id)
                VALUES (?, ?, ?)
            """, (parent_id, parent_title, None))
            
            # Upsert subtask tasks and event_map for successful creates
            for item in created:
                subtask_id = item["task_id"]
                calendar_event_id = item["calendar_event_id"]
                
                # Find subtask title
                subtask_title = next((st["title"] for st in subtasks if st["id"] == subtask_id), "")
                
                # Upsert subtask task
                cursor.execute("""
                    INSERT OR REPLACE INTO tasks (id, title, parent_id)
                    VALUES (?, ?, ?)
                """, (subtask_id, subtask_title, parent_id))
                
                # Upsert event_map
                cursor.execute("""
                    INSERT OR REPLACE INTO event_map (task_id, calendar_id, calendar_event_id)
                    VALUES (?, ?, ?)
                """, (subtask_id, calendar_id, calendar_event_id))
            
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            return {
                "success": False,
                "error": f"Database error: {e}",
                "created": created,
                "failed": failed
            }
        finally:
            conn.close()
        
        return {
            "success": len(failed) == 0,
            "created": created,
            "failed": failed
        }
    
    def delete_by_id(self, task_id: str) -> DeleteResult:
        """
        Delete task by ID (cascade if parent)
        
        Args:
            task_id: Task ID to delete
            
        Returns:
            DeleteResult with deletion status
        """
        result = DeleteResult(target="id")
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Check if task exists
        cursor.execute("SELECT id, title, parent_id FROM tasks WHERE id = ?", (task_id,))
        task_row = cursor.fetchone()
        
        if not task_row:
            result.skipped.append({
                "task_id": task_id,
                "reason": "not_found"
            })
            conn.close()
            return result
        
        # Check if this is a parent (has children)
        cursor.execute("SELECT id FROM tasks WHERE parent_id = ?", (task_id,))
        children = cursor.fetchall()
        
        if children:
            # This is a parent - delete all children first
            for child_row in children:
                child_id = child_row[0]
                child_result = self._delete_child_task(cursor, child_id)
                
                if child_result["success"]:
                    result.deleted.append({
                        "task_id": child_id,
                        "calendar_event_id": child_result.get("calendar_event_id", "")
                    })
                elif child_result.get("was_404"):
                    result.skipped.append({
                        "task_id": child_id,
                        "reason": "already_deleted"
                    })
                else:
                    result.errors.append({
                        "task_id": child_id,
                        "reason": child_result.get("error", "Unknown error")
                    })
            
            # Delete parent task row (no event_map for parent)
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        else:
            # This is a child - delete normally
            child_result = self._delete_child_task(cursor, task_id)
            
            if child_result["success"]:
                result.deleted.append({
                    "task_id": task_id,
                    "calendar_event_id": child_result.get("calendar_event_id", "")
                })
            elif child_result.get("was_404"):
                result.skipped.append({
                    "task_id": task_id,
                    "reason": "already_deleted"
                })
            else:
                result.errors.append({
                    "task_id": task_id,
                    "reason": child_result.get("error", "Unknown error")
                })
        
        conn.commit()
        conn.close()
        
        return result
    
    def delete_by_parent_id(self, parent_id: str) -> DeleteResult:
        """
        Delete all children of a parent task
        
        Args:
            parent_id: Parent task ID
            
        Returns:
            DeleteResult with deletion status
        """
        result = DeleteResult(target="parent_id")
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Get all children
        cursor.execute("SELECT id FROM tasks WHERE parent_id = ?", (parent_id,))
        children = cursor.fetchall()
        
        # Delete each child
        for child_row in children:
            child_id = child_row[0]
            child_result = self._delete_child_task(cursor, child_id)
            
            if child_result["success"]:
                result.deleted.append({
                    "task_id": child_id,
                    "calendar_event_id": child_result.get("calendar_event_id", "")
                })
            elif child_result.get("was_404"):
                result.skipped.append({
                    "task_id": child_id,
                    "reason": "already_deleted"
                })
            else:
                result.errors.append({
                    "task_id": child_id,
                    "reason": child_result.get("error", "Unknown error")
                })
        
        # Delete parent task row
        cursor.execute("DELETE FROM tasks WHERE id = ?", (parent_id,))
        
        conn.commit()
        conn.close()
        
        return result
    
    def _delete_child_task(self, cursor: sqlite3.Cursor, task_id: str) -> Dict[str, Any]:
        """
        Delete a child task (has event_map entry)
        
        Args:
            cursor: Database cursor
            task_id: Task ID to delete
            
        Returns:
            Dict with success, was_404, calendar_event_id, error
        """
        # Get event_map entry
        cursor.execute("""
            SELECT calendar_id, calendar_event_id 
            FROM event_map 
            WHERE task_id = ?
        """, (task_id,))
        
        event_map_row = cursor.fetchone()
        
        if not event_map_row:
            # No event_map - just delete task row
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return {"success": True, "was_404": False}
        
        calendar_id, calendar_event_id = event_map_row
        
        # Delete from CalBridge
        success, was_404, error = self._calbridge_delete_with_retry(calendar_event_id)
        
        if success:
            # Delete from event_map and tasks
            cursor.execute("DELETE FROM event_map WHERE task_id = ?", (task_id,))
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return {
                "success": True,
                "was_404": was_404,
                "calendar_event_id": calendar_event_id
            }
        else:
            return {
                "success": False,
                "was_404": False,
                "error": error
            }


# Example usage
if __name__ == "__main__":
    agent = EventCreatorAgent()
    
    # Test simple task
    print("Testing simple task creation...")
    ta_simple = {
        "calendar": "test_cal",
        "type": "simple",
        "title": "Call mom",
        "slot": ["2025-11-07T14:00:00-05:00", "2025-11-07T14:30:00-05:00"],
        "id": "test-id-123",
        "parent_id": None
    }
    
    result = agent.create_simple_task(ta_simple)
    print(f"Result: {result}")

