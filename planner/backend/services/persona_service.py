import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, time
from pathlib import Path

from models import PersonaConstraints, WorkHours, RecurringBlock, Preferences
from database import get_persona_constraints, update_persona_constraints

class PersonaService:
    """Service for managing user persona and constraints."""
    
    def __init__(self):
        self.constraints_cache = None
    
    async def get_constraints(self) -> PersonaConstraints:
        """Get current persona constraints."""
        if self.constraints_cache is None:
            await self._load_constraints()
        return self.constraints_cache
    
    async def update_constraints(self, constraints: PersonaConstraints):
        """Update persona constraints."""
        # Convert to dict for storage
        constraints_dict = {
            "work_hours": constraints.work_hours.dict(),
            "recurring_blocks": [block.dict() for block in constraints.recurring_blocks],
            "preferences": constraints.preferences.dict()
        }
        
        update_persona_constraints(constraints_dict)
        self.constraints_cache = constraints
        return constraints
    
    async def _load_constraints(self):
        """Load constraints from database."""
        try:
            constraints_dict = get_persona_constraints()
            
            # Parse work hours
            work_hours_data = constraints_dict.get("work_hours", {})
            work_hours = WorkHours(**work_hours_data)
            
            # Parse recurring blocks
            recurring_blocks_data = constraints_dict.get("recurring_blocks", [])
            recurring_blocks = [RecurringBlock(**block) for block in recurring_blocks_data]
            
            # Parse preferences
            preferences_data = constraints_dict.get("preferences", {})
            preferences = Preferences(**preferences_data)
            
            self.constraints_cache = PersonaConstraints(
                work_hours=work_hours,
                recurring_blocks=recurring_blocks,
                preferences=preferences
            )
        except Exception as e:
            # Fall back to defaults if loading fails
            self.constraints_cache = self._get_default_constraints()
    
    def _get_default_constraints(self) -> PersonaConstraints:
        """Get default persona constraints."""
        work_hours = WorkHours(
            monday=["09:00", "17:00"],
            tuesday=["09:00", "17:00"],
            wednesday=["09:00", "17:00"],
            thursday=["09:00", "17:00"],
            friday=["09:00", "17:00"],
            saturday=None,
            sunday=None
        )
        
        preferences = Preferences(
            deep_work_hours=["09:00", "12:00"],
            meeting_hours=["14:00", "17:00"],
            min_block_minutes=30,
            buffer_minutes=15
        )
        
        return PersonaConstraints(
            work_hours=work_hours,
            recurring_blocks=[],
            preferences=preferences
        )
    
    async def parse_text_constraints(self, text: str) -> PersonaConstraints:
        """Parse constraints from natural language text."""
        constraints = await self.get_constraints()
        
        # Extract work hours
        work_hours = self._extract_work_hours(text)
        if work_hours:
            constraints.work_hours = work_hours
        
        # Extract recurring blocks
        recurring_blocks = self._extract_recurring_blocks(text)
        if recurring_blocks:
            constraints.recurring_blocks.extend(recurring_blocks)
        
        # Extract preferences
        preferences = self._extract_preferences(text)
        if preferences:
            constraints.preferences = preferences
        
        return constraints
    
    def _extract_work_hours(self, text: str) -> Optional[WorkHours]:
        """Extract work hours from text."""
        # Look for patterns like "work 9-5", "office hours 9am to 5pm", etc.
        work_hours_patterns = [
            r'work\s+(\d{1,2}):?(\d{2})?\s*[-–]\s*(\d{1,2}):?(\d{2})?',
            r'office\s+hours?\s+(\d{1,2}):?(\d{2})?\s*[-–]\s*(\d{1,2}):?(\d{2})?',
            r'(\d{1,2}):?(\d{2})?\s*[-–]\s*(\d{1,2}):?(\d{2})?\s*(?:work|office)',
        ]
        
        for pattern in work_hours_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                start_hour = int(groups[0])
                start_min = int(groups[1]) if groups[1] else 0
                end_hour = int(groups[2])
                end_min = int(groups[3]) if groups[3] else 0
                
                start_time = f"{start_hour:02d}:{start_min:02d}"
                end_time = f"{end_hour:02d}:{end_min:02d}"
                
                return WorkHours(
                    monday=[start_time, end_time],
                    tuesday=[start_time, end_time],
                    wednesday=[start_time, end_time],
                    thursday=[start_time, end_time],
                    friday=[start_time, end_time],
                    saturday=None,
                    sunday=None
                )
        
        return None
    
    def _extract_recurring_blocks(self, text: str) -> List[RecurringBlock]:
        """Extract recurring blocks from text."""
        blocks = []
        
        # Look for gym patterns
        gym_patterns = [
            r'gym\s+(?:on\s+)?(?:tuesday|thursday|tue|thu)',
            r'(?:tuesday|thursday|tue|thu)\s+gym',
            r'workout\s+(?:on\s+)?(?:tuesday|thursday|tue|thu)',
        ]
        
        for pattern in gym_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                blocks.append(RecurringBlock(
                    title="Gym",
                    days=["tuesday", "thursday"],
                    time=["17:00", "18:00"]
                ))
                break
        
        # Look for lunch patterns
        lunch_patterns = [
            r'lunch\s+(\d{1,2}):?(\d{2})?\s*[-–]\s*(\d{1,2}):?(\d{2})?',
            r'(\d{1,2}):?(\d{2})?\s*[-–]\s*(\d{1,2}):?(\d{2})?\s*lunch',
        ]
        
        for pattern in lunch_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                start_hour = int(groups[0])
                start_min = int(groups[1]) if groups[1] else 0
                end_hour = int(groups[2])
                end_min = int(groups[3]) if groups[3] else 0
                
                start_time = f"{start_hour:02d}:{start_min:02d}"
                end_time = f"{end_hour:02d}:{end_min:02d}"
                
                blocks.append(RecurringBlock(
                    title="Lunch",
                    days=["monday", "tuesday", "wednesday", "thursday", "friday"],
                    time=[start_time, end_time]
                ))
                break
        
        return blocks
    
    def _extract_preferences(self, text: str) -> Optional[Preferences]:
        """Extract preferences from text."""
        preferences = None
        
        # Look for deep work preferences
        deep_work_patterns = [
            r'deep\s+work\s+(\d{1,2}):?(\d{2})?\s*[-–]\s*(\d{1,2}):?(\d{2})?',
            r'focus\s+time\s+(\d{1,2}):?(\d{2})?\s*[-–]\s*(\d{1,2}):?(\d{2})?',
        ]
        
        for pattern in deep_work_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                start_hour = int(groups[0])
                start_min = int(groups[1]) if groups[1] else 0
                end_hour = int(groups[2])
                end_min = int(groups[3]) if groups[3] else 0
                
                start_time = f"{start_hour:02d}:{start_min:02d}"
                end_time = f"{end_hour:02d}:{end_min:02d}"
                
                if preferences is None:
                    preferences = Preferences()
                preferences.deep_work_hours = [start_time, end_time]
                break
        
        # Look for meeting preferences
        meeting_patterns = [
            r'meetings?\s+(\d{1,2}):?(\d{2})?\s*[-–]\s*(\d{1,2}):?(\d{2})?',
            r'calls?\s+(\d{1,2}):?(\d{2})?\s*[-–]\s*(\d{1,2}):?(\d{2})?',
        ]
        
        for pattern in meeting_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                start_hour = int(groups[0])
                start_min = int(groups[1]) if groups[1] else 0
                end_hour = int(groups[2])
                end_min = int(groups[3]) if groups[3] else 0
                
                start_time = f"{start_hour:02d}:{start_min:02d}"
                end_time = f"{end_hour:02d}:{end_min:02d}"
                
                if preferences is None:
                    preferences = Preferences()
                preferences.meeting_hours = [start_time, end_time]
                break
        
        return preferences
    
    async def is_work_time(self, dt: datetime) -> bool:
        """Check if a datetime falls within work hours."""
        constraints = await self.get_constraints()
        day_name = dt.strftime("%A").lower()
        
        work_hours = getattr(constraints.work_hours, day_name)
        if not work_hours:
            return False
        
        start_time = time.fromisoformat(work_hours[0])
        end_time = time.fromisoformat(work_hours[1])
        current_time = dt.time()
        
        return start_time <= current_time <= end_time
    
    async def is_recurring_block(self, dt: datetime) -> Optional[str]:
        """Check if a datetime falls within a recurring block."""
        constraints = await self.get_constraints()
        day_name = dt.strftime("%A").lower()
        current_time = dt.time()
        
        for block in constraints.recurring_blocks:
            if day_name in block.days:
                start_time = time.fromisoformat(block.time[0])
                end_time = time.fromisoformat(block.time[1])
                
                if start_time <= current_time <= end_time:
                    return block.title
        
        return None
    
    async def get_optimal_time_for_task_type(self, task_type: str, date: datetime) -> Optional[time]:
        """Get optimal time of day for a specific task type."""
        constraints = await self.get_constraints()
        
        if task_type == "deep_work":
            start_time = time.fromisoformat(constraints.preferences.deep_work_hours[0])
            return start_time
        elif task_type == "meeting":
            start_time = time.fromisoformat(constraints.preferences.meeting_hours[0])
            return start_time
        else:
            # For other task types, use work hours start
            day_name = date.strftime("%A").lower()
            work_hours = getattr(constraints.work_hours, day_name)
            if work_hours:
                return time.fromisoformat(work_hours[0])
        
        return None
