import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, time
from dataclasses import dataclass

from models import (
    TaskResponse, SubtaskResponse, ScheduleProposal, TimeSlot, 
    FreeSlotRequest, FreeSlotResponse, CalendarTarget, TaskType
)
from .calendar_service import CalendarService
from .persona_service import PersonaService

@dataclass
class SlotScore:
    """Represents a time slot with its score and reasoning."""
    start: datetime
    end: datetime
    score: float
    reason: str
    task_type: TaskType
    energy_level: float

class SchedulerService:
    """Smart scheduling service that considers persona constraints and task types."""
    
    def __init__(self, calendar_service: CalendarService, persona_service: PersonaService):
        self.calendar_service = calendar_service
        self.persona_service = persona_service
    
    async def generate_schedule_proposal(self, task: TaskResponse) -> ScheduleProposal:
        """Generate a schedule proposal for a task."""
        try:
            # Get persona constraints
            constraints = await self.persona_service.get_constraints()
            
            # Determine scheduling window
            start_date = datetime.now()
            end_date = task.deadline if task.deadline else start_date + timedelta(days=7)
            
            # Ensure timezone-naive for consistency
            if start_date.tzinfo is not None:
                start_date = start_date.replace(tzinfo=None)
            if end_date.tzinfo is not None:
                end_date = end_date.replace(tzinfo=None)
            
            # If task has a specific deadline, prioritize scheduling at that exact time
            if task.deadline:
                # Create a priority slot at the deadline time
                duration_minutes = task.estimated_minutes or 30
                priority_slot = SlotScore(
                    start=end_date - timedelta(minutes=duration_minutes),
                    end=end_date,
                    score=3.0,  # Much higher score for exact deadline match
                    reason=f"Exact time requested: {end_date.strftime('%Y-%m-%d %H:%M')}",
                    task_type=task.task_type or TaskType.QUICK_TASK,
                    energy_level=1.0
                )
                
                # Find other available slots
                free_slots = await self._find_optimal_slots(
                    task, start_date, end_date, constraints
                )
                
                # Add priority slot at the beginning and return early
                free_slots.insert(0, priority_slot)
                
                # Score and rank slots (priority slot will be first)
                scored_slots = await self._score_slots(free_slots, task, constraints)
                
                # Create time slots for subtasks
                time_slots = []
                conflicts = []
                
                if task.needs_subtasks and task.subtasks:
                    # Schedule subtasks
                    time_slots, conflicts = await self._schedule_subtasks(
                        task.subtasks, scored_slots, constraints
                    )
                else:
                    # Schedule single task - use the priority slot
                    if scored_slots:
                        best_slot = scored_slots[0]
                        duration = timedelta(minutes=task.estimated_minutes or 30)
                        time_slots.append(TimeSlot(
                            start=best_slot.start,
                            end=best_slot.start + duration,
                            score=best_slot.score,
                            reason=best_slot.reason
                        ))
                    else:
                        conflicts.append("No suitable time slots found")
                
                return ScheduleProposal(
                    task_id=task.id,
                    subtasks=task.subtasks,
                    time_slots=time_slots,
                    total_estimated_minutes=sum(st.estimated_minutes for st in task.subtasks) if task.subtasks else (task.estimated_minutes or 30),
                    conflicts=conflicts
                )
            else:
                # Find free slots normally
                free_slots = await self._find_optimal_slots(
                    task, start_date, end_date, constraints
                )
            
            # Score and rank slots
            scored_slots = await self._score_slots(free_slots, task, constraints)
            
            # Create time slots for subtasks
            time_slots = []
            conflicts = []
            
            if task.needs_subtasks and task.subtasks:
                # Schedule subtasks
                time_slots, conflicts = await self._schedule_subtasks(
                    task.subtasks, scored_slots, constraints
                )
            else:
                # Schedule single task
                if scored_slots:
                    best_slot = scored_slots[0]
                    duration = timedelta(minutes=task.estimated_minutes or 30)
                    time_slots.append(TimeSlot(
                        start=best_slot.start,
                        end=best_slot.start + duration,
                        score=best_slot.score,
                        reason=best_slot.reason
                    ))
                else:
                    conflicts.append("No suitable time slots found")
            
            return ScheduleProposal(
                task_id=task.id,
                subtasks=task.subtasks,
                time_slots=time_slots,
                total_estimated_minutes=sum(st.estimated_minutes for st in task.subtasks) if task.subtasks else (task.estimated_minutes or 30),
                conflicts=conflicts
            )
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Scheduling error: {e}")
            print(f"Error details: {error_details}")
            return ScheduleProposal(
                task_id=task.id,
                subtasks=task.subtasks,
                time_slots=[],
                total_estimated_minutes=0,
                conflicts=[f"Scheduling failed: {e}"]
            )
    
    async def find_free_slots(self, request: FreeSlotRequest) -> List[FreeSlotResponse]:
        """Find available calendar windows."""
        try:
            # Get calendar events
            days = (request.end - request.start).days + 1
            events = await self.calendar_service.get_events(
                days=days,
                calendar_title=request.calendar_target.value if request.calendar_target else None
            )
            
            # Find gaps
            free_slots = await self._find_gaps_in_schedule(
                request.start, request.end, events, request.duration_minutes
            )
            
            # Convert to response format
            responses = []
            for slot in free_slots:
                responses.append(FreeSlotResponse(
                    start=slot.start,
                    end=slot.end,
                    duration_minutes=request.duration_minutes,
                    score=slot.score,
                    reason=slot.reason
                ))
            
            return responses
            
        except Exception as e:
            raise Exception(f"Failed to find free slots: {e}")
    
    async def _find_optimal_slots(
        self, 
        task: TaskResponse, 
        start_date: datetime, 
        end_date: datetime,
        constraints: Any
    ) -> List[SlotScore]:
        """Find optimal time slots for a task."""
        # Get calendar events
        days = (end_date - start_date).days + 1
        events = await self.calendar_service.get_events(days=days)
        
        # Filter events by calendar if specified
        if task.calendar_target:
            events = [e for e in events if e.calendar == task.calendar_target.value]
        
        # Find gaps
        gaps = await self._find_gaps_in_schedule(
            start_date, end_date, events, 
            task.estimated_minutes or 30
        )
        
        return gaps
    
    async def _find_gaps_in_schedule(
        self, 
        start: datetime, 
        end: datetime, 
        events: List, 
        min_duration_minutes: int
    ) -> List[SlotScore]:
        """Find gaps in the schedule that can accommodate the minimum duration."""
        # Convert events to datetime blocks
        event_blocks = []
        for event in events:
            event_start = datetime.fromisoformat(event.start_iso)
            event_end = datetime.fromisoformat(event.end_iso)
            
            # Convert to timezone-naive if needed for comparison
            if event_start.tzinfo is not None:
                event_start = event_start.replace(tzinfo=None)
            if event_end.tzinfo is not None:
                event_end = event_end.replace(tzinfo=None)
            
            # Only include events that overlap with our search window
            if event_start < end and event_end > start:
                event_blocks.append((event_start, event_end))
        
        # Sort events by start time
        event_blocks.sort(key=lambda x: x[0])
        
        # Find gaps
        gaps = []
        current_time = start
        
        for event_start, event_end in event_blocks:
            # Check if there's a gap before this event
            if current_time < event_start:
                gap_duration = (event_start - current_time).total_seconds() / 60
                if gap_duration >= min_duration_minutes:
                    gaps.append(SlotScore(
                        start=current_time,
                        end=event_start,
                        score=1.0,  # Will be refined by scoring
                        reason="Available gap between events",
                        task_type=TaskType.QUICK_TASK,  # Will be refined
                        energy_level=0.5  # Will be refined
                    ))
            
            # Move current time to end of this event
            current_time = max(current_time, event_end)
        
        # Check for gap after last event
        if current_time < end:
            gap_duration = (end - current_time).total_seconds() / 60
            if gap_duration >= min_duration_minutes:
                gaps.append(SlotScore(
                    start=current_time,
                    end=end,
                    score=1.0,
                    reason="Available time after last event",
                    task_type=TaskType.QUICK_TASK,
                    energy_level=0.5
                ))
        
        return gaps
    
    async def _score_slots(
        self, 
        slots: List[SlotScore], 
        task: TaskResponse, 
        constraints: Any
    ) -> List[SlotScore]:
        """Score time slots based on task type, persona constraints, and energy levels."""
        scored_slots = []
        
        for slot in slots:
            score = 1.0
            reasons = []
            
            # Check work hours
            if not await self.persona_service.is_work_time(slot.start):
                score *= 0.1
                reasons.append("Outside work hours")
            
            # Check recurring blocks
            recurring_block = await self.persona_service.is_recurring_block(slot.start)
            if recurring_block:
                score *= 0.0
                reasons.append(f"Conflicts with {recurring_block}")
            
            # Score based on task type and time of day
            time_score = await self._score_time_for_task_type(slot.start, task.task_type or TaskType.QUICK_TASK, constraints)
            score *= time_score
            reasons.append(f"Time-of-day score: {time_score:.2f}")
            
            # Score based on energy levels
            energy_score = await self._calculate_energy_level(slot.start, constraints)
            score *= energy_score
            reasons.append(f"Energy level: {energy_score:.2f}")
            
            # Prefer longer slots for complex tasks
            if task.needs_subtasks and len(task.subtasks) > 3:
                slot_duration = (slot.end - slot.start).total_seconds() / 60
                if slot_duration >= 120:  # 2+ hours
                    score *= 1.2
                    reasons.append("Long slot for complex task")
            
            # Update slot with calculated values
            slot.score = score
            slot.reason = "; ".join(reasons)
            slot.task_type = task.task_type or TaskType.QUICK_TASK
            slot.energy_level = energy_score
            
            scored_slots.append(slot)
        
        # Sort by score (highest first)
        scored_slots.sort(key=lambda x: x.score, reverse=True)
        
        return scored_slots
    
    async def _score_time_for_task_type(
        self, 
        dt: datetime, 
        task_type: TaskType, 
        constraints: Any
    ) -> float:
        """Score how well a time slot matches the task type."""
        current_time = dt.time()
        
        if task_type == TaskType.DEEP_WORK:
            # Prefer morning hours for deep work
            deep_work_start = time.fromisoformat(constraints.preferences.deep_work_hours[0])
            deep_work_end = time.fromisoformat(constraints.preferences.deep_work_hours[1])
            
            if deep_work_start <= current_time <= deep_work_end:
                return 1.0
            else:
                # Calculate distance from optimal time
                optimal_time = time.fromisoformat("10:00")  # Peak morning
                time_diff = abs((current_time.hour * 60 + current_time.minute) - 
                               (optimal_time.hour * 60 + optimal_time.minute))
                return max(0.3, 1.0 - (time_diff / 180))  # Decay over 3 hours
        
        elif task_type == TaskType.MEETING:
            # Prefer afternoon for meetings
            meeting_start = time.fromisoformat(constraints.preferences.meeting_hours[0])
            meeting_end = time.fromisoformat(constraints.preferences.meeting_hours[1])
            
            if meeting_start <= current_time <= meeting_end:
                return 1.0
            else:
                return 0.7
        
        elif task_type == TaskType.RESEARCH:
            # Prefer morning for research
            return await self._score_time_for_task_type(dt, TaskType.DEEP_WORK, constraints)
        
        else:  # QUICK_TASK
            # Quick tasks can be scheduled anywhere
            return 0.8
    
    async def _calculate_energy_level(self, dt: datetime, constraints: Any) -> float:
        """Calculate energy level for a given time."""
        current_time = dt.time()
        hour = current_time.hour
        
        # Simple energy curve: high in morning, dip after lunch, recovery in afternoon
        if 9 <= hour <= 11:
            return 1.0  # Peak morning energy
        elif 12 <= hour <= 13:
            return 0.6  # Lunch dip
        elif 14 <= hour <= 16:
            return 0.8  # Afternoon recovery
        elif 17 <= hour <= 18:
            return 0.7  # End of day
        else:
            return 0.4  # Outside normal hours
    
    async def _schedule_subtasks(
        self, 
        subtasks: List[SubtaskResponse], 
        available_slots: List[SlotScore], 
        constraints: Any
    ) -> Tuple[List[TimeSlot], List[str]]:
        """Schedule subtasks into available time slots."""
        time_slots = []
        conflicts = []
        
        # Sort subtasks by order and type
        sorted_subtasks = sorted(subtasks, key=lambda x: (x.order_index, x.task_type))
        
        slot_index = 0
        for subtask in sorted_subtasks:
            # Find best slot for this subtask
            best_slot = None
            best_score = 0
            
            for i, slot in enumerate(available_slots[slot_index:], slot_index):
                # Check if slot is long enough
                slot_duration = (slot.end - slot.start).total_seconds() / 60
                if slot_duration >= subtask.estimated_minutes:
                    # Score this slot for this subtask
                    score = await self._score_slot_for_subtask(slot, subtask, constraints)
                    if score > best_score:
                        best_slot = slot
                        best_score = score
                        slot_index = i + 1
            
            if best_slot:
                # Create time slot for this subtask
                duration = timedelta(minutes=subtask.estimated_minutes)
                time_slots.append(TimeSlot(
                    start=best_slot.start,
                    end=best_slot.start + duration,
                    score=best_score,
                    reason=f"Scheduled {subtask.title} in optimal slot"
                ))
                
                # Update slot start time for next subtask
                best_slot.start += duration
            else:
                conflicts.append(f"No suitable slot found for: {subtask.title}")
        
        return time_slots, conflicts
    
    async def _score_slot_for_subtask(
        self, 
        slot: SlotScore, 
        subtask: SubtaskResponse, 
        constraints: Any
    ) -> float:
        """Score how well a slot matches a specific subtask."""
        base_score = slot.score
        
        # Adjust based on subtask type
        if subtask.task_type == TaskType.DEEP_WORK:
            # Prefer longer, uninterrupted slots
            slot_duration = (slot.end - slot.start).total_seconds() / 60
            if slot_duration >= 60:  # 1+ hour
                base_score *= 1.2
        elif subtask.task_type == TaskType.MEETING:
            # Meetings can be shorter
            base_score *= 1.0
        elif subtask.task_type == TaskType.QUICK_TASK:
            # Quick tasks are flexible
            base_score *= 0.9
        
        return base_score
