"""
Time Allotment Agent - Schedules tasks into calendar slots using task_scheduler

This agent:
1. Fetches free/busy slots from CalBridge API
2. Uses task_scheduler to optimally schedule tasks/subtasks
3. Validates scheduled slots
4. Generates IDs and formats output according to spec
"""
import sys
import uuid
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Import task_scheduler from parent directory
sys.path.append(str(Path(__file__).parent.parent / "task_scheduler"))
from task_scheduler import (
    schedule_ordered_with_constraints,
    Assignment,
    ScheduleOptions,
    ConstraintAdder
)


@dataclass
class ScheduledSimpleTask:
    """Scheduled simple task output"""
    calendar: str
    type: str  # "simple"
    title: str
    slot: List[str]  # [start_iso, end_iso]
    id: str  # uuid4
    parent_id: Optional[str] = None  # Always null for simple tasks
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "calendar": self.calendar,
            "type": self.type,
            "title": self.title,
            "slot": self.slot,
            "id": self.id,
            "parent_id": self.parent_id
        }


@dataclass
class ScheduledSubtask:
    """Scheduled subtask output"""
    title: str
    slot: List[str]  # [start_iso, end_iso]
    parent_id: str
    id: str  # uuid4
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "slot": self.slot,
            "parent_id": self.parent_id,
            "id": self.id
        }


@dataclass
class ScheduledComplexTask:
    """Scheduled complex task output"""
    calendar: str
    type: str  # "complex"
    title: str
    id: str  # uuid4
    parent_id: Optional[str] = None  # Always null for parent
    subtasks: List[ScheduledSubtask] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "calendar": self.calendar,
            "type": self.type,
            "title": self.title,
            "id": self.id,
            "parent_id": self.parent_id,
            "subtasks": [st.to_dict() for st in (self.subtasks or [])]
        }


class TimeAllotmentAgent:
    """
    Time Allotment Agent that schedules tasks into calendar slots
    
    Handles two paths:
    - SIMPLE: TD.output + TS.output → single task scheduling
    - COMPLEX: LD.output + TS.output → multiple subtasks scheduling
    """
    
    DEFAULT_SIMPLE_DURATION = "PT30M"  # Default when TS.duration is null
    
    def __init__(self, 
                 calbridge_base_url: str = "http://127.0.0.1:8765",
                 work_start_hour: int = 6,
                 work_end_hour: int = 23):
        """
        Initialize Time Allotment Agent
        
        Args:
            calbridge_base_url: Base URL for CalBridge API
            work_start_hour: Start of work day (24-hour format, default 6 AM)
            work_end_hour: End of work day (24-hour format, default 11 PM)
        """
        self.calbridge_base_url = calbridge_base_url
        self.schedule_options = ScheduleOptions(
            work_start_hour=work_start_hour,
            work_end_hour=work_end_hour
        )
    
    def _is_holiday(self, event: Dict) -> bool:
        """Check if an event is a holiday (should be excluded from busy time)"""
        calendar_name = (event.get("calendar") or "").lower()
        return "holiday" in calendar_name or "holidays" in calendar_name
    
    def _fetch_events_for_window(self, calendar_id: str, start_iso: str, end_iso: str) -> List[Dict]:
        """
        Fetch events from CalBridge for a specific calendar and time window
        
        Args:
            calendar_id: Calendar ID to fetch events from
            start_iso: Start of time window (ISO format)
            end_iso: End of time window (ISO format)
            
        Returns:
            List of non-holiday events in the window
        """
        try:
            # Calculate days from start to end
            start_dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
            
            days_span = (end_dt - start_dt).days + 1
            days_to_fetch = min(max(days_span, 1), 365)  # Cap at 365 days
            
            # Fetch events
            response = requests.get(
                f"{self.calbridge_base_url}/events",
                params={"days": days_to_fetch, "calendar_id": calendar_id},
                timeout=20
            )
            response.raise_for_status()
            
            events = response.json()
            
            # Filter events in window and exclude holidays
            filtered_events = []
            for event in events:
                if self._is_holiday(event):
                    continue
                
                event_start = datetime.fromisoformat(event["start_iso"].replace('Z', '+00:00'))
                event_end = datetime.fromisoformat(event["end_iso"].replace('Z', '+00:00'))
                
                # Check if event overlaps with window
                if event_start < end_dt and event_end > start_dt:
                    filtered_events.append(event)
            
            return filtered_events
            
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch events from CalBridge: {e}")
    
    def _calculate_free_slots(self, events: List[Dict], start_iso: str, end_iso: str) -> List[Tuple[str, str]]:
        """
        Calculate free time slots from events within the window
        
        Args:
            events: List of events (busy times)
            start_iso: Start of window (ISO format)
            end_iso: End of window (ISO format)
            
        Returns:
            List of free slot tuples (start_iso, end_iso)
        """
        start_dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
        
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        
        # Sort events by start time
        sorted_events = sorted(events, key=lambda x: x["start_iso"])
        
        free_slots = []
        current_time = start_dt
        
        for event in sorted_events:
            event_start = datetime.fromisoformat(event["start_iso"].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event["end_iso"].replace('Z', '+00:00'))
            
            # Skip events completely before current time
            if event_end <= current_time:
                continue
            
            # If there's a gap before this event, it's a free slot
            if current_time < event_start:
                # Don't extend beyond window end
                slot_end = min(event_start, end_dt)
                if current_time < slot_end:
                    free_slots.append((
                        current_time.isoformat(),
                        slot_end.isoformat()
                    ))
            
            # Move current time to end of this event
            current_time = max(current_time, event_end)
        
        # Add final slot from last event to window end if there's time
        if current_time < end_dt:
            free_slots.append((
                current_time.isoformat(),
                end_dt.isoformat()
            ))
        
        return free_slots
    
    def _iso8601_to_minutes(self, duration: str) -> int:
        """
        Convert ISO-8601 duration to minutes
        
        Args:
            duration: ISO-8601 duration (e.g., "PT30M", "PT1H30M", "PT2H")
            
        Returns:
            Duration in minutes
        """
        import re
        
        duration = duration.upper()
        hours = 0
        minutes = 0
        
        hours_match = re.search(r'(\d+)H', duration)
        if hours_match:
            hours = int(hours_match.group(1))
        
        minutes_match = re.search(r'(\d+)M', duration)
        if minutes_match:
            minutes = int(minutes_match.group(1))
        
        return hours * 60 + minutes
    
    def _validate_scheduled_slot(self, 
                                 slot_start: str, 
                                 slot_end: str, 
                                 required_duration_min: int,
                                 window_start: str,
                                 window_end: str,
                                 busy_events: List[Dict]) -> Tuple[bool, Optional[str]]:
        """
        Validate a scheduled slot against constraints
        
        Args:
            slot_start: Scheduled start time (ISO)
            slot_end: Scheduled end time (ISO)
            required_duration_min: Required duration in minutes
            window_start: Window start (ISO)
            window_end: Window end (ISO)
            busy_events: List of busy events
            
        Returns:
            (is_valid, error_message)
        """
        slot_start_dt = datetime.fromisoformat(slot_start.replace('Z', '+00:00'))
        slot_end_dt = datetime.fromisoformat(slot_end.replace('Z', '+00:00'))
        window_start_dt = datetime.fromisoformat(window_start.replace('Z', '+00:00'))
        window_end_dt = datetime.fromisoformat(window_end.replace('Z', '+00:00'))
        
        # Normalize timezones
        if slot_start_dt.tzinfo is None:
            slot_start_dt = slot_start_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        if slot_end_dt.tzinfo is None:
            slot_end_dt = slot_end_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        if window_start_dt.tzinfo is None:
            window_start_dt = window_start_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        if window_end_dt.tzinfo is None:
            window_end_dt = window_end_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        
        # Check bounds
        if slot_start_dt < window_start_dt:
            return False, f"Slot starts before window: {slot_start} < {window_start}"
        if slot_end_dt > window_end_dt:
            return False, f"Slot ends after window: {slot_end} > {window_end}"
        if slot_start_dt >= slot_end_dt:
            return False, f"Invalid slot: start >= end"
        
        # Check duration match
        actual_duration_min = int((slot_end_dt - slot_start_dt).total_seconds() / 60)
        if actual_duration_min != required_duration_min:
            return False, f"Duration mismatch: expected {required_duration_min} min, got {actual_duration_min} min"
        
        # Check busy compliance
        for event in busy_events:
            event_start = datetime.fromisoformat(event["start_iso"].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event["end_iso"].replace('Z', '+00:00'))
            
            if event_start.tzinfo is None:
                event_start = event_start.replace(tzinfo=datetime.now().astimezone().tzinfo)
            if event_end.tzinfo is None:
                event_end = event_end.replace(tzinfo=datetime.now().astimezone().tzinfo)
            
            # Check overlap
            if slot_start_dt < event_end and slot_end_dt > event_start:
                return False, f"Overlaps with busy event: {event.get('title', 'unknown')}"
        
        return True, None
    
    def schedule_simple_task(self,
                            td_output: Dict[str, Any],
                            ts_output: Dict[str, Any]) -> ScheduledSimpleTask:
        """
        Schedule a simple task
        
        Args:
            td_output: Task Difficulty Analysis output (type="simple")
            ts_output: Time Standardization output
            
        Returns:
            ScheduledSimpleTask with assigned slot
        """
        # Validate inputs
        if td_output.get("type") != "simple":
            raise ValueError(f"Expected simple task, got type: {td_output.get('type')}")
        
        calendar_id = td_output.get("calendar")
        if not calendar_id:
            raise ValueError("Calendar ID is required")
        
        title = td_output.get("title", "")
        if not title:
            raise ValueError("Task title is required")
        
        window_start = ts_output.get("start")
        window_end = ts_output.get("end")
        if not window_start or not window_end:
            raise ValueError("TS output must have start and end")
        
        # Determine duration
        duration_iso = ts_output.get("duration") or td_output.get("duration") or self.DEFAULT_SIMPLE_DURATION
        duration_min = self._iso8601_to_minutes(duration_iso)
        
        # Fetch events and calculate free slots
        events = self._fetch_events_for_window(calendar_id, window_start, window_end)
        free_slots = self._calculate_free_slots(events, window_start, window_end)
        
        if not free_slots:
            raise RuntimeError("No free time slots available within window")
        
        # Convert free slots to task_scheduler format (timezone-naive)
        raw_slots = []
        for slot_start, slot_end in free_slots:
            start_dt = datetime.fromisoformat(slot_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(slot_end.replace('Z', '+00:00'))
            # Convert to timezone-naive for task_scheduler
            raw_slots.append((start_dt.replace(tzinfo=None).isoformat(), 
                            end_dt.replace(tzinfo=None).isoformat()))
        
        # Convert deadline to timezone-naive
        deadline_dt = datetime.fromisoformat(window_end.replace('Z', '+00:00'))
        deadline_naive = deadline_dt.replace(tzinfo=None).isoformat()
        
        # Schedule task
        try:
            assignments, _ = schedule_ordered_with_constraints(
                tasks_min=[duration_min],
                raw_slots=raw_slots,
                deadline_iso=deadline_naive,
                constraints=None,
                options=self.schedule_options
            )
            
            if not assignments or len(assignments) != 1:
                raise RuntimeError("Scheduler did not return exactly one assignment")
            
            assignment = assignments[0]
            
            # Convert back to timezone-aware ISO format
            # Preserve timezone from window_start
            window_start_dt = datetime.fromisoformat(window_start.replace('Z', '+00:00'))
            if window_start_dt.tzinfo is None:
                window_start_dt = window_start_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
            
            # Apply timezone to scheduler output (which is timezone-naive)
            slot_start_dt = assignment.start.replace(tzinfo=window_start_dt.tzinfo)
            slot_end_dt = assignment.end.replace(tzinfo=window_start_dt.tzinfo)
            
            slot_start_iso = slot_start_dt.isoformat()
            slot_end_iso = slot_end_dt.isoformat()
            
            # Validate the scheduled slot
            is_valid, error_msg = self._validate_scheduled_slot(
                slot_start_iso,
                slot_end_iso,
                duration_min,
                window_start,
                window_end,
                events
            )
            
            if not is_valid:
                raise RuntimeError(f"Validation failed: {error_msg}")
            
            # Generate ID
            task_id = str(uuid.uuid4())
            
            return ScheduledSimpleTask(
                calendar=calendar_id,
                type="simple",
                title=title,
                slot=[slot_start_iso, slot_end_iso],
                id=task_id,
                parent_id=None
            )
            
        except RuntimeError as e:
            raise RuntimeError(f"Failed to schedule simple task: {e}")
    
    def schedule_complex_task(self,
                              ld_output: Dict[str, Any],
                              ts_output: Dict[str, Any]) -> ScheduledComplexTask:
        """
        Schedule a complex task with subtasks
        
        Args:
            ld_output: LLM Decomposer output (type="complex" with subtasks)
            ts_output: Time Standardization output
            
        Returns:
            ScheduledComplexTask with scheduled subtasks
        """
        # Validate inputs
        if ld_output.get("type") != "complex":
            raise ValueError(f"Expected complex task, got type: {ld_output.get('type')}")
        
        subtasks = ld_output.get("subtasks", [])
        if not subtasks or len(subtasks) < 2:
            raise ValueError("Complex task must have at least 2 subtasks")
        
        calendar_id = ld_output.get("calendar")
        if not calendar_id:
            raise ValueError("Calendar ID is required")
        
        title = ld_output.get("title", "")
        if not title:
            raise ValueError("Task title is required")
        
        window_start = ts_output.get("start")
        window_end = ts_output.get("end")
        if not window_start or not window_end:
            raise ValueError("TS output must have start and end")
        
        # Extract subtask durations
        subtask_durations_min = []
        subtask_titles = []
        for subtask in subtasks:
            duration_iso = subtask.get("duration")
            if not duration_iso:
                raise ValueError(f"Subtask '{subtask.get('title')}' missing duration")
            subtask_durations_min.append(self._iso8601_to_minutes(duration_iso))
            subtask_titles.append(subtask.get("title", ""))
        
        # Fetch events and calculate free slots
        events = self._fetch_events_for_window(calendar_id, window_start, window_end)
        free_slots = self._calculate_free_slots(events, window_start, window_end)
        
        if not free_slots:
            raise RuntimeError("No free time slots available within window")
        
        # Convert free slots to task_scheduler format (timezone-naive)
        raw_slots = []
        for slot_start, slot_end in free_slots:
            start_dt = datetime.fromisoformat(slot_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(slot_end.replace('Z', '+00:00'))
            raw_slots.append((start_dt.replace(tzinfo=None).isoformat(), 
                            end_dt.replace(tzinfo=None).isoformat()))
        
        # Convert deadline to timezone-naive
        deadline_dt = datetime.fromisoformat(window_end.replace('Z', '+00:00'))
        deadline_naive = deadline_dt.replace(tzinfo=None).isoformat()
        
        # Add constraints for precedence (min gap between subtasks)
        constraints = ConstraintAdder()
        constraints.set_min_gap_minutes(5)  # 5 minute gap between subtasks
        
        # Schedule subtasks
        try:
            assignments, _ = schedule_ordered_with_constraints(
                tasks_min=subtask_durations_min,
                raw_slots=raw_slots,
                deadline_iso=deadline_naive,
                constraints=constraints,
                options=self.schedule_options
            )
            
            if not assignments or len(assignments) != len(subtasks):
                raise RuntimeError(f"Scheduler returned {len(assignments) if assignments else 0} assignments, expected {len(subtasks)}")
            
            # Sort assignments by task_id to maintain order
            assignments.sort(key=lambda a: a.task_id)
            
            # Validate all scheduled slots
            for i, assignment in enumerate(assignments):
                slot_start_iso = assignment.start.isoformat()
                slot_end_iso = assignment.end.isoformat()
                
                is_valid, error_msg = self._validate_scheduled_slot(
                    slot_start_iso,
                    slot_end_iso,
                    subtask_durations_min[i],
                    window_start,
                    window_end,
                    events
                )
                
                if not is_valid:
                    raise RuntimeError(f"Validation failed for subtask {i}: {error_msg}")
            
            # Validate order (precedence: each starts >= previous ends)
            for i in range(1, len(assignments)):
                prev_end = datetime.fromisoformat(assignments[i-1].end.isoformat())
                curr_start = datetime.fromisoformat(assignments[i].start.isoformat())
                if prev_end.tzinfo is None:
                    prev_end = prev_end.replace(tzinfo=datetime.now().astimezone().tzinfo)
                if curr_start.tzinfo is None:
                    curr_start = curr_start.replace(tzinfo=datetime.now().astimezone().tzinfo)
                
                if curr_start < prev_end:
                    raise RuntimeError(f"Precedence violation: subtask {i} starts before subtask {i-1} ends")
            
            # Validate non-overlap
            for i in range(len(assignments)):
                for j in range(i + 1, len(assignments)):
                    slot_i_start = datetime.fromisoformat(assignments[i].start.isoformat())
                    slot_i_end = datetime.fromisoformat(assignments[i].end.isoformat())
                    slot_j_start = datetime.fromisoformat(assignments[j].start.isoformat())
                    slot_j_end = datetime.fromisoformat(assignments[j].end.isoformat())
                    
                    if slot_i_start.tzinfo is None:
                        slot_i_start = slot_i_start.replace(tzinfo=datetime.now().astimezone().tzinfo)
                    if slot_i_end.tzinfo is None:
                        slot_i_end = slot_i_end.replace(tzinfo=datetime.now().astimezone().tzinfo)
                    if slot_j_start.tzinfo is None:
                        slot_j_start = slot_j_start.replace(tzinfo=datetime.now().astimezone().tzinfo)
                    if slot_j_end.tzinfo is None:
                        slot_j_end = slot_j_end.replace(tzinfo=datetime.now().astimezone().tzinfo)
                    
                    if slot_i_start < slot_j_end and slot_i_end > slot_j_start:
                        raise RuntimeError(f"Overlap detected between subtasks {i} and {j}")
            
            # Generate IDs
            parent_id = str(uuid.uuid4())
            scheduled_subtasks = []
            
            # Preserve timezone from window_start
            window_start_dt = datetime.fromisoformat(window_start.replace('Z', '+00:00'))
            if window_start_dt.tzinfo is None:
                window_start_dt = window_start_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
            
            for i, assignment in enumerate(assignments):
                subtask_id = str(uuid.uuid4())
                # Apply timezone to scheduler output (which is timezone-naive)
                slot_start_dt = assignment.start.replace(tzinfo=window_start_dt.tzinfo)
                slot_end_dt = assignment.end.replace(tzinfo=window_start_dt.tzinfo)
                slot_start_iso = slot_start_dt.isoformat()
                slot_end_iso = slot_end_dt.isoformat()
                
                scheduled_subtasks.append(ScheduledSubtask(
                    title=subtask_titles[i],
                    slot=[slot_start_iso, slot_end_iso],
                    parent_id=parent_id,
                    id=subtask_id
                ))
            
            return ScheduledComplexTask(
                calendar=calendar_id,
                type="complex",
                title=title,
                id=parent_id,
                parent_id=None,
                subtasks=scheduled_subtasks
            )
            
        except RuntimeError as e:
            raise RuntimeError(f"Failed to schedule complex task: {e}")


# Example usage
if __name__ == "__main__":
    agent = TimeAllotmentAgent()
    
    # Test simple task
    print("Testing simple task scheduling...")
    td_simple = {
        "calendar": "work_1",
        "type": "simple",
        "title": "Call mom",
        "duration": "PT30M"
    }
    ts_simple = {
        "start": "2025-11-05T00:00:00-05:00",
        "end": "2025-11-05T23:59:59-05:00",
        "duration": "PT30M"
    }
    
    try:
        result = agent.schedule_simple_task(td_simple, ts_simple)
        print(f"✅ Scheduled: {result.to_dict()}")
    except Exception as e:
        print(f"❌ Error: {e}")

