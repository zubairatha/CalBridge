"""
User Memory System
Simple JSON-based storage for user preferences and scheduling patterns.
Each memory element has: title, description, tags
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path


class UserMemory:
    """Manages simple user memory with title, description, and tags."""
    
    def __init__(self, memory_file: str = "user_memory.json"):
        """Initialize user memory system.
        
        Args:
            memory_file: Path to the JSON file storing user memory
        """
        self.memory_file = Path(memory_file)
        self.memory = self._load_memory()
    
    def _load_memory(self) -> List[Dict[str, str]]:
        """Load user memory from JSON file."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load user memory: {e}")
        
        # Return default memory with examples from TODO.txt
        return self._get_default_memory()
    
    def _get_default_memory(self) -> List[Dict[str, str]]:
        """Get default memory structure based on TODO.txt examples."""
        return [
            {
                "title": "Gym Schedule",
                "description": "Gym workout time is 1-2 PM",
                "tags": "gym, workout, schedule, 1pm, 2pm"
            },
            {
                "title": "Weekly Capstone Meeting", 
                "description": "Weekly capstone meeting Monday through Friday",
                "tags": "meeting, capstone, weekly, monday, tuesday, wednesday, thursday, friday"
            },
            {
                "title": "University Work Preference",
                "description": "Prefer university work early mornings",
                "tags": "university, uni, work, early, morning, preference"
            },
            {
                "title": "Side Projects Preference",
                "description": "Prefer side projects in the late evenings",
                "tags": "side, projects, late, evening, preference"
            },
            {
                "title": "Wake Up Time",
                "description": "Wake up at 6 AM",
                "tags": "wake, up, 6am, schedule"
            },
            {
                "title": "Sleep Time",
                "description": "Sleep at 11 PM",
                "tags": "sleep, 11pm, schedule"
            }
        ]
    
    def save_memory(self) -> bool:
        """Save current memory to file."""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving user memory: {e}")
            return False
    
    def add_memory(self, title: str, description: str, tags: str) -> None:
        """Add a new memory item.
        
        Args:
            title: Title of the memory item
            description: Description of the memory item
            tags: Comma-separated tags
        """
        self.memory.append({
            "title": title,
            "description": description,
            "tags": tags
        })
    
    def get_memories_for_llm(self) -> List[Dict[str, str]]:
        """Get memories formatted for LLM (title and description only).
        
        Returns:
            List of memory items with only title and description
        """
        return [
            {
                "title": memory["title"],
                "description": memory["description"]
            }
            for memory in self.memory
        ]
    
    def get_memories_by_tag(self, tag: str) -> List[Dict[str, str]]:
        """Get memories that contain a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of matching memory items
        """
        tag_lower = tag.lower()
        return [
            memory for memory in self.memory
            if tag_lower in memory["tags"].lower()
        ]
    
    def get_available_time_slots(self, start_date: datetime, end_date: datetime, 
                               existing_events: List[Dict]) -> List[Dict[str, Any]]:
        """Get available time slots between existing events.
        
        Args:
            start_date: Start of time range to check
            end_date: End of time range to check
            existing_events: List of existing events with 'start_iso' and 'end_iso'
            
        Returns:
            List of available time slots
        """
        # Ensure start_date and end_date are timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.astimezone()
        if end_date.tzinfo is None:
            end_date = end_date.astimezone()
        
        # Parse existing events and sort by start time
        events = []
        for event in existing_events:
            start = datetime.fromisoformat(event['start_iso'])
            end = datetime.fromisoformat(event['end_iso'])
            
            # Ensure event times are timezone-aware
            if start.tzinfo is None:
                start = start.astimezone()
            if end.tzinfo is None:
                end = end.astimezone()
                
            events.append({'start': start, 'end': end, 'title': event.get('title', '')})
        
        events.sort(key=lambda x: x['start'])
        
        # Find gaps between events (simple approach)
        available_slots = []
        current_time = start_date
        buffer_minutes = 15  # Simple 15-minute buffer
        buffer = timedelta(minutes=buffer_minutes)
        
        for event in events:
            # Check if there's a gap before this event
            if current_time + buffer < event['start']:
                slot_start = current_time
                slot_end = event['start'] - buffer
                
                if slot_start < slot_end:
                    available_slots.append({
                        'start': slot_start,
                        'end': slot_end,
                        'duration_minutes': int((slot_end - slot_start).total_seconds() / 60)
                    })
            
            current_time = max(current_time, event['end'])
        
        # Check for slot after last event
        if current_time + buffer < end_date:
            slot_start = current_time
            slot_end = end_date
            
            if slot_start < slot_end:
                available_slots.append({
                    'start': slot_start,
                    'end': slot_end,
                    'duration_minutes': int((slot_end - slot_start).total_seconds() / 60)
                })
        
        return available_slots
    
    def get_scheduling_constraints(self) -> Dict[str, str]:
        """Get basic scheduling constraints from memory.
        
        Returns:
            Dictionary of scheduling constraints
        """
        constraints = {}
        
        # Extract constraints from memory items
        for memory in self.memory:
            title_lower = memory["title"].lower()
            if "wake" in title_lower and "time" in title_lower:
                constraints['wake_up_time'] = "06:00"  # Default from TODO.txt
            elif "sleep" in title_lower and "time" in title_lower:
                constraints['sleep_time'] = "23:00"  # Default from TODO.txt
        
        # Set defaults if not found
        constraints.setdefault('wake_up_time', '06:00')
        constraints.setdefault('sleep_time', '23:00')
        
        return constraints
    
    def update_from_scheduling_pattern(self, allocations: List[Dict[str, Any]]) -> None:
        """Update memory based on scheduling patterns.
        
        Args:
            allocations: List of time allocations from the scheduler
        """
        # Simple pattern: if we scheduled work tasks in the evening, add that preference
        evening_work_count = 0
        morning_work_count = 0
        
        for allocation in allocations:
            start_time_str = allocation.get('scheduled_start', '')
            if start_time_str:
                try:
                    from datetime import datetime
                    start_time = datetime.fromisoformat(start_time_str)
                    hour = start_time.hour
                    
                    if 6 <= hour < 12:  # Morning
                        morning_work_count += 1
                    elif 18 <= hour < 23:  # Evening
                        evening_work_count += 1
                except:
                    continue
        
        # Add a memory entry if there's a clear pattern
        if evening_work_count > morning_work_count and evening_work_count > 0:
            self.add_memory(
                "Evening Work Preference", 
                "Prefer scheduling work tasks in the evening hours",
                "scheduling, preference, evening, work"
            )
        elif morning_work_count > evening_work_count and morning_work_count > 0:
            self.add_memory(
                "Morning Work Preference", 
                "Prefer scheduling work tasks in the morning hours",
                "scheduling, preference, morning, work"
            )


# Example usage and testing
if __name__ == "__main__":
    memory = UserMemory()
    
    # Test basic operations
    print("Current memories:")
    for mem in memory.memory:
        print(f"- {mem['title']}: {mem['description']}")
    
    # Test adding new memory
    memory.add_memory(
        "Coffee Break", 
        "Take coffee break at 10:30 AM", 
        "coffee, break, 10:30am, daily"
    )
    
    # Test getting memories for LLM
    llm_memories = memory.get_memories_for_llm()
    print(f"\nMemories for LLM ({len(llm_memories)} items):")
    for mem in llm_memories:
        print(f"- {mem['title']}: {mem['description']}")
    
    # Test getting memories by tag
    schedule_memories = memory.get_memories_by_tag("schedule")
    print(f"\nSchedule-related memories ({len(schedule_memories)} items):")
    for mem in schedule_memories:
        print(f"- {mem['title']}: {mem['description']}")
    
    # Test constraints
    constraints = memory.get_scheduling_constraints()
    print(f"\nScheduling constraints: {constraints}")
    
    # Save memory
    memory.save_memory()
    print("\nMemory saved successfully")
