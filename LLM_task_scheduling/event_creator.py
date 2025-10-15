"""
Event Creator

This module provides the task scheduler and event creator that:
1. Generates unique IDs for all events (event_id for every event)
2. Creates events with proper parent-child relationships for subtasks
3. Stores parent_id in notes for subtasks, NULL for main tasks
4. Creates events using the CalBridge API
5. Handles both main tasks and subtasks with proper relationships
"""

import uuid
import requests
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from .time_allotment import ScheduledTask
from .llm_decomposer import TaskDecomposition, Subtask


@dataclass
class EventData:
    """Represents event data for CalBridge API"""
    title: str
    start_iso: str
    end_iso: str
    notes: str
    calendar_id: Optional[str] = None
    calendar_title: Optional[str] = None


@dataclass
class CreatedEvent:
    """Represents a created event with its ID and relationships"""
    event_id: str
    title: str
    start_iso: str
    end_iso: str
    calendar: str
    parent_id: Optional[str] = None
    notes: str = ""


@dataclass
class EventCreationResult:
    """Result of event creation process"""
    main_event: Optional[CreatedEvent]
    subtask_events: List[CreatedEvent]
    total_events_created: int
    errors: List[str]


class EventCreator:
    """
    Event creator that generates IDs and creates calendar events
    
    This class:
    - Generates unique event IDs
    - Creates main events and subtask events
    - Manages parent-child relationships
    - Handles event creation via CalBridge API
    """
    
    def __init__(self, 
                 calbridge_base: str = "http://127.0.0.1:8765",
                 calendar_config_path: Optional[str] = None):
        """
        Initialize the Event Creator
        
        Args:
            calbridge_base: Base URL for CalBridge API
            calendar_config_path: Path to calendar configuration
        """
        self.calbridge_base = calbridge_base
        self.calendar_config = self._load_calendar_config(calendar_config_path)
    
    def _load_calendar_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load calendar configuration"""
        if config_path is None:
            from pathlib import Path
            config_path = Path(__file__).parent.parent / "config" / "calendars.json"
        
        try:
            import json
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback configuration
            return {
                "default_work_title": "Work",
                "default_home_title": "Home",
                "calendars": [
                    {"id": "work_id", "title": "Work", "writable": True},
                    {"id": "home_id", "title": "Home", "writable": True}
                ]
            }
    
    def _generate_event_id(self) -> str:
        """Generate a unique event ID"""
        return str(uuid.uuid4())
    
    def _get_calendar_id(self, calendar_type: str) -> Optional[str]:
        """
        Get calendar ID for the given calendar type
        
        Args:
            calendar_type: "Work" or "Home"
            
        Returns:
            Calendar ID or None if not found
        """
        calendars = self.calendar_config.get("calendars", [])
        for cal in calendars:
            if cal.get("title", "").lower() == calendar_type.lower() and cal.get("writable", False):
                return cal.get("id")
        return None
    
    def _create_event_via_api(self, event_data: EventData) -> CreatedEvent:
        """
        Create an event via CalBridge API
        
        Args:
            event_data: Event data to create
            
        Returns:
            Created event with ID
        """
        payload = {
            "title": event_data.title,
            "start_iso": event_data.start_iso,
            "end_iso": event_data.end_iso,
            "notes": event_data.notes
        }
        
        if event_data.calendar_id:
            payload["calendar_id"] = event_data.calendar_id
        elif event_data.calendar_title:
            payload["calendar_title"] = event_data.calendar_title
        
        try:
            response = requests.post(
                f"{self.calbridge_base}/add",
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            
            result = response.json()
            
            return CreatedEvent(
                event_id=result["id"],
                title=result["title"],
                start_iso=result["start_iso"],
                end_iso=result["end_iso"],
                calendar=result["calendar"],
                notes=event_data.notes
            )
            
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to create event via CalBridge API: {e}")
    
    def create_main_event(self, 
                         task_title: str,
                         scheduled_task: ScheduledTask,
                         parent_id: Optional[str] = None) -> CreatedEvent:
        """
        Create a main event (either the primary task or a subtask)
        
        Args:
            task_title: Title of the task
            scheduled_task: Scheduled task data
            parent_id: Parent event ID (None for main tasks)
            
        Returns:
            Created event
        """
        # Generate unique event ID
        event_id = self._generate_event_id()
        
        # Prepare notes
        notes_parts = []
        if parent_id:
            notes_parts.append(f"parent_id: {parent_id}")
        else:
            notes_parts.append("parent_id: NULL")
        
        notes_parts.append(f"source: LLM_task_scheduling")
        notes_parts.append(f"created_at: {datetime.now().astimezone().isoformat()}")
        
        notes = "; ".join(notes_parts)
        
        # Get calendar ID
        calendar_id = self._get_calendar_id(scheduled_task.calendar_type)
        
        # Create event data
        event_data = EventData(
            title=task_title,
            start_iso=scheduled_task.start_iso,
            end_iso=scheduled_task.end_iso,
            notes=notes,
            calendar_id=calendar_id
        )
        
        # Create event via API
        created_event = self._create_event_via_api(event_data)
        created_event.parent_id = parent_id
        
        return created_event
    
    def create_events_from_decomposition(self, 
                                       task_description: str,
                                       decomposition: TaskDecomposition,
                                       scheduled_tasks: List[ScheduledTask]) -> EventCreationResult:
        """
        Create events from task decomposition and scheduled tasks
        
        Args:
            task_description: Original task description
            decomposition: Task decomposition result
            scheduled_tasks: List of scheduled tasks
            
        Returns:
            Event creation result with all created events
        """
        errors = []
        main_event = None
        subtask_events = []
        
        try:
            if decomposition.subtasks:
                # Generate parent task ID first (for reference, but don't create event)
                parent_task_id = self._generate_event_id()
                
                # Create subtask events with proper parent_id
                for i, subtask in enumerate(decomposition.subtasks):
                    if i < len(scheduled_tasks):
                        subtask_scheduled = scheduled_tasks[i]
                        subtask_event = self.create_main_event(
                            task_title=subtask.title,
                            scheduled_task=subtask_scheduled,
                            parent_id=parent_task_id  # Subtasks reference the parent task ID
                        )
                        subtask_events.append(subtask_event)
                    else:
                        errors.append(f"No scheduled time for subtask: {subtask.title}")
            else:
                # No subtasks - create single main event
                if scheduled_tasks:
                    main_event = self.create_main_event(
                        task_title=task_description,
                        scheduled_task=scheduled_tasks[0],
                        parent_id=None
                    )
                else:
                    errors.append("No scheduled tasks provided for main event")
            
        except Exception as e:
            errors.append(f"Error creating events: {e}")
        
        return EventCreationResult(
            main_event=main_event,
            subtask_events=subtask_events,
            total_events_created=len([e for e in [main_event] + subtask_events if e is not None]),
            errors=errors
        )
    
    def create_simple_event(self, 
                           task_title: str,
                           scheduled_task: ScheduledTask) -> CreatedEvent:
        """
        Create a simple event without decomposition
        
        Args:
            task_title: Title of the task
            scheduled_task: Scheduled task data
            
        Returns:
            Created event
        """
        return self.create_main_event(
            task_title=task_title,
            scheduled_task=scheduled_task,
            parent_id=None
        )
    
    def delete_event(self, event_id: str) -> bool:
        """
        Delete an event by ID
        
        Args:
            event_id: ID of the event to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            response = requests.post(
                f"{self.calbridge_base}/delete",
                params={"event_id": event_id},
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("deleted", False)
            
        except requests.RequestException as e:
            print(f"Error deleting event {event_id}: {e}")
            return False
    
    def cleanup_events(self, events: List[CreatedEvent]) -> int:
        """
        Clean up (delete) a list of events
        
        Args:
            events: List of events to delete
            
        Returns:
            Number of events successfully deleted
        """
        deleted_count = 0
        
        for event in events:
            if self.delete_event(event.event_id):
                deleted_count += 1
        
        return deleted_count


def main():
    """Test the Event Creator"""
    creator = EventCreator()
    
    # Test creating a simple event
    print("=== Testing Simple Event Creation ===")
    
    # Mock scheduled task
    from .time_allotment import ScheduledTask
    from datetime import datetime, timedelta
    
    start_time = datetime.now().astimezone() + timedelta(hours=1)
    end_time = start_time + timedelta(minutes=30)
    
    scheduled_task = ScheduledTask(
        task_id=0,
        title="Test Task",
        duration_minutes=30,
        start_iso=start_time.isoformat(),
        end_iso=end_time.isoformat(),
        day=start_time.date().isoformat(),
        calendar_type="Home"
    )
    
    try:
        created_event = creator.create_simple_event("Test Simple Task", scheduled_task)
        print(f"Created event: {created_event.event_id}")
        print(f"Title: {created_event.title}")
        print(f"Time: {created_event.start_iso} → {created_event.end_iso}")
        print(f"Calendar: {created_event.calendar}")
        print(f"Notes: {created_event.notes}")
        
        # Clean up
        if creator.delete_event(created_event.event_id):
            print("Event deleted successfully")
        else:
            print("Failed to delete event")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # Test event ID generation
    print(f"\n=== Testing Event ID Generation ===")
    for i in range(3):
        event_id = creator._generate_event_id()
        print(f"Generated ID {i+1}: {event_id}")


if __name__ == "__main__":
    main()
