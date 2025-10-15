"""
Time Allotment Agent

This module provides a time allotment agent that:
1. Extracts free time slots from the calendar until the deadline (excluding holidays)
2. Uses the task_scheduler from task_scheduler/ to schedule the tasks
3. Ensures time slots are calculated only until the deadline and not beyond
4. Returns output in the exact format required by CalBridge API
"""

import requests
import sys
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

# Import the task scheduler from the parent directory
sys.path.append(str(Path(__file__).parent.parent / "task_scheduler"))
from task_scheduler import schedule_ordered_with_constraints, Assignment, ScheduleOptions, ConstraintAdder


@dataclass
class TimeSlot:
    """Represents a free time slot"""
    start_iso: str
    end_iso: str


@dataclass
class ScheduledTask:
    """Represents a scheduled task with timing"""
    task_id: int
    title: str
    duration_minutes: int
    start_iso: str
    end_iso: str
    day: str
    calendar_type: str


class TimeAllotmentAgent:
    """
    Time allotment agent that extracts free time slots and schedules tasks
    
    This agent:
    - Fetches calendar events from CalBridge API
    - Excludes holidays from busy time calculation
    - Extracts free time slots until deadline
    - Uses task_scheduler to optimally schedule tasks
    - Returns scheduled tasks in CalBridge API format
    """
    
    def __init__(self, 
                 calbridge_base: str = "http://127.0.0.1:8765",
                 work_start_hour: int = 6,
                 work_end_hour: int = 23):
        """
        Initialize the Time Allotment Agent
        
        Args:
            calbridge_base: Base URL for CalBridge API
            work_start_hour: Start of work day (24-hour format)
            work_end_hour: End of work day (24-hour format)
        """
        self.calbridge_base = calbridge_base
        self.schedule_options = ScheduleOptions(
            work_start_hour=work_start_hour,
            work_end_hour=work_end_hour
        )
    
    def _is_holiday(self, event: Dict) -> bool:
        """Check if an event is a holiday (should be excluded from busy time)"""
        calendar_name = (event.get("calendar") or "").lower()
        return "holiday" in calendar_name
    
    def _fetch_events_until_deadline(self, deadline: str) -> List[Dict]:
        """
        Fetch all events from now until the deadline, excluding holidays
        
        Args:
            deadline: ISO format deadline string
            
        Returns:
            List of non-holiday events
        """
        try:
            # Calculate days from now to deadline
            now = datetime.now().astimezone()
            deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
            days_until_deadline = (deadline_dt - now).days + 1
            
            # Ensure we don't fetch too far into the future (max 365 days)
            days_to_fetch = min(days_until_deadline, 365)
            
            # Fetch events
            response = requests.get(
                f"{self.calbridge_base}/events",
                params={"days": days_to_fetch},
                timeout=20
            )
            response.raise_for_status()
            
            events = response.json()
            
            # Filter out holidays and events beyond deadline
            filtered_events = []
            for event in events:
                if not self._is_holiday(event):
                    # Check if event is before deadline
                    event_start = datetime.fromisoformat(event["start_iso"].replace('Z', '+00:00'))
                    if event_start <= deadline_dt:
                        filtered_events.append(event)
            
            return filtered_events
            
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch events from CalBridge: {e}")
    
    def _calculate_free_slots(self, events: List[Dict], deadline: str) -> List[TimeSlot]:
        """
        Calculate free time slots from events until deadline
        
        Args:
            events: List of non-holiday events
            deadline: ISO format deadline string
            
        Returns:
            List of free time slots
        """
        now = datetime.now().astimezone()
        deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
        
        # Sort events by start time
        sorted_events = sorted(events, key=lambda x: x["start_iso"])
        
        free_slots = []
        current_time = now
        
        for event in sorted_events:
            event_start = datetime.fromisoformat(event["start_iso"].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event["end_iso"].replace('Z', '+00:00'))
            
            # If there's a gap before this event, it's a free slot
            if current_time < event_start:
                # Don't extend beyond deadline
                slot_end = min(event_start, deadline_dt)
                if current_time < slot_end:
                    free_slots.append(TimeSlot(
                        start_iso=current_time.isoformat(),
                        end_iso=slot_end.isoformat()
                    ))
            
            # Move current time to end of this event
            current_time = max(current_time, event_end)
        
        # Add final slot from last event to deadline if there's time
        if current_time < deadline_dt:
            free_slots.append(TimeSlot(
                start_iso=current_time.isoformat(),
                end_iso=deadline_dt.isoformat()
            ))
        
        return free_slots
    
    def _schedule_tasks(self, 
                       task_durations: List[int], 
                       free_slots: List[TimeSlot], 
                       deadline: str,
                       constraints: Optional[ConstraintAdder] = None) -> List[Assignment]:
        """
        Schedule tasks using the task_scheduler module
        
        Args:
            task_durations: List of task durations in minutes
            free_slots: List of free time slots
            deadline: ISO format deadline string
            constraints: Optional scheduling constraints
            
        Returns:
            List of scheduled assignments
        """
        # Convert TimeSlots to the format expected by task_scheduler
        # Ensure all datetimes are timezone-naive for task_scheduler compatibility
        raw_slots = []
        for slot in free_slots:
            start_dt = datetime.fromisoformat(slot.start_iso.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(slot.end_iso.replace('Z', '+00:00'))
            # Convert to timezone-naive
            start_naive = start_dt.replace(tzinfo=None)
            end_naive = end_dt.replace(tzinfo=None)
            raw_slots.append((start_naive.isoformat(), end_naive.isoformat()))
        
        try:
            # Ensure deadline is also timezone-naive
            deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
            deadline_naive = deadline_dt.replace(tzinfo=None).isoformat()
            
            assignments, _ = schedule_ordered_with_constraints(
                tasks_min=task_durations,
                raw_slots=raw_slots,
                deadline_iso=deadline_naive,
                constraints=constraints,
                options=self.schedule_options
            )
            return assignments
            
        except RuntimeError as e:
            raise RuntimeError(f"Task scheduling failed: {e}")
    
    def schedule_tasks(self, 
                      task_titles: List[str],
                      task_durations: List[int],
                      deadline: str,
                      calendar_type: str,
                      constraints: Optional[ConstraintAdder] = None) -> List[ScheduledTask]:
        """
        Main method to schedule tasks into free time slots
        
        Args:
            task_titles: List of task titles
            task_durations: List of task durations in minutes
            deadline: ISO format deadline string
            calendar_type: "Work" or "Home"
            constraints: Optional scheduling constraints
            
        Returns:
            List of scheduled tasks in CalBridge API format
        """
        if len(task_titles) != len(task_durations):
            raise ValueError("Number of task titles must match number of durations")
        
        # Fetch events and calculate free slots
        events = self._fetch_events_until_deadline(deadline)
        free_slots = self._calculate_free_slots(events, deadline)
        
        if not free_slots:
            raise RuntimeError("No free time slots available before deadline")
        
        # Schedule tasks
        assignments = self._schedule_tasks(task_durations, free_slots, deadline, constraints)
        
        # Convert assignments to ScheduledTask objects
        scheduled_tasks = []
        for assignment in assignments:
            if assignment.task_id < len(task_titles):
                scheduled_tasks.append(ScheduledTask(
                    task_id=assignment.task_id,
                    title=task_titles[assignment.task_id],
                    duration_minutes=assignment.duration_min,
                    start_iso=assignment.start.isoformat(),
                    end_iso=assignment.end.isoformat(),
                    day=assignment.day.isoformat(),
                    calendar_type=calendar_type
                ))
        
        return scheduled_tasks
    
    def get_free_slots_summary(self, deadline: str) -> Dict:
        """
        Get a summary of free time slots without scheduling tasks
        
        Args:
            deadline: ISO format deadline string
            
        Returns:
            Dictionary with free slots summary
        """
        events = self._fetch_events_until_deadline(deadline)
        free_slots = self._calculate_free_slots(events, deadline)
        
        total_free_minutes = sum(
            (datetime.fromisoformat(slot.end_iso) - datetime.fromisoformat(slot.start_iso)).total_seconds() / 60
            for slot in free_slots
        )
        
        return {
            "total_events": len(events),
            "total_free_slots": len(free_slots),
            "total_free_minutes": int(total_free_minutes),
            "free_slots": [
                {
                    "start": slot.start_iso,
                    "end": slot.end_iso,
                    "duration_minutes": int((datetime.fromisoformat(slot.end_iso) - datetime.fromisoformat(slot.start_iso)).total_seconds() / 60)
                }
                for slot in free_slots
            ]
        }


def main():
    """Test the Time Allotment Agent"""
    agent = TimeAllotmentAgent()
    
    # Test deadline
    deadline = "2025-11-01T23:59:00"
    
    print(f"=== Free Slots Summary (until {deadline}) ===")
    try:
        summary = agent.get_free_slots_summary(deadline)
        print(f"Total events: {summary['total_events']}")
        print(f"Total free slots: {summary['total_free_slots']}")
        print(f"Total free minutes: {summary['total_free_minutes']}")
        
        print("\nFree slots:")
        for i, slot in enumerate(summary['free_slots'][:5]):  # Show first 5
            print(f"  {i+1}. {slot['start']} → {slot['end']} ({slot['duration_minutes']} min)")
        
        if len(summary['free_slots']) > 5:
            print(f"  ... and {len(summary['free_slots']) - 5} more slots")
            
    except Exception as e:
        print(f"Error getting free slots: {e}")
    
    # Test task scheduling
    print(f"\n=== Task Scheduling Test ===")
    task_titles = ["Research phase", "Writing phase", "Review phase"]
    task_durations = [120, 180, 90]  # 2h, 3h, 1.5h
    calendar_type = "Work"
    
    try:
        scheduled = agent.schedule_tasks(task_titles, task_durations, deadline, calendar_type)
        
        print(f"Scheduled {len(scheduled)} tasks:")
        for task in scheduled:
            print(f"  {task.task_id}: {task.title}")
            print(f"    {task.start_iso} → {task.end_iso} ({task.duration_minutes} min)")
            print(f"    Calendar: {task.calendar_type}")
            
    except Exception as e:
        print(f"Error scheduling tasks: {e}")


if __name__ == "__main__":
    main()
