"""
Main LLM Task Scheduler

This module provides the main scheduler that orchestrates the entire process:
1. Uses LLM decomposer to break down tasks
2. Uses time allotment agent to schedule tasks
3. Uses event creator to create calendar events
4. Provides a unified interface for the complete workflow
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from .llm_decomposer import LLMTaskDecomposer, TaskDecomposition
from .time_allotment import TimeAllotmentAgent, ScheduledTask
from .event_creator import EventCreator, EventCreationResult, CreatedEvent


@dataclass
class SchedulingRequest:
    """Request for task scheduling"""
    task_description: str
    deadline: str
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class SchedulingResult:
    """Result of the complete scheduling process"""
    success: bool
    main_event: Optional[CreatedEvent]
    subtask_events: List[CreatedEvent]
    total_events_created: int
    decomposition: Optional[TaskDecomposition]
    scheduled_tasks: List[ScheduledTask]
    errors: List[str]
    warnings: List[str]


class LLMTaskScheduler:
    """
    Main LLM Task Scheduler that orchestrates the complete workflow
    
    This class coordinates:
    - LLM task decomposition
    - Time slot calculation and task scheduling
    - Calendar event creation
    - Error handling and result reporting
    """
    
    def __init__(self,
                 ollama_base: str = "http://127.0.0.1:11434",
                 calbridge_base: str = "http://127.0.0.1:8765",
                 model: str = "llama3",
                 work_start_hour: int = 6,
                 work_end_hour: int = 23):
        """
        Initialize the LLM Task Scheduler
        
        Args:
            ollama_base: Base URL for Ollama API
            calbridge_base: Base URL for CalBridge API
            model: LLM model name to use
            work_start_hour: Start of work day (24-hour format)
            work_end_hour: End of work day (24-hour format)
        """
        self.decomposer = LLMTaskDecomposer(ollama_base, model)
        self.time_agent = TimeAllotmentAgent(calbridge_base, work_start_hour, work_end_hour)
        self.event_creator = EventCreator(calbridge_base)
    
    def schedule_task(self, request: SchedulingRequest) -> SchedulingResult:
        """
        Schedule a task using the complete LLM workflow
        
        Args:
            request: Scheduling request with task description and deadline
            
        Returns:
            Complete scheduling result
        """
        errors = []
        warnings = []
        decomposition = None
        scheduled_tasks = []
        main_event = None
        subtask_events = []
        
        try:
            # Step 1: Decompose task using LLM
            print(f"Step 1: Decomposing task: {request.task_description}")
            decomposition = self.decomposer.decompose_task(
                request.task_description, 
                request.deadline
            )
            print(f"  Calendar: {decomposition.calendar_type}")
            print(f"  Subtasks: {len(decomposition.subtasks) if decomposition.subtasks else 0}")
            
            # Step 2: Prepare task data for scheduling
            if decomposition.subtasks:
                # Decomposed task - schedule only the subtasks
                task_titles = [subtask.title for subtask in decomposition.subtasks]
                task_durations = [subtask.duration_minutes for subtask in decomposition.subtasks]
            else:
                # Simple task - schedule the main task
                task_titles = [request.task_description]
                task_durations = [decomposition.total_duration_minutes or 30]  # Default 30 min
            
            # Step 3: Get free time summary first
            print(f"Step 2: Analyzing free time until deadline")
            free_time_summary = self.time_agent.get_free_slots_summary(request.deadline)
            print(f"  Total free time: {free_time_summary['total_free_minutes']} minutes ({free_time_summary['total_free_minutes']/60:.1f} hours)")
            print(f"  Available slots: {free_time_summary['total_free_slots']}")
            
            # Step 4: Schedule tasks using time allotment agent
            print(f"Step 3: Scheduling {len(task_titles)} tasks")
            scheduled_tasks = self.time_agent.schedule_tasks(
                task_titles=task_titles,
                task_durations=task_durations,
                deadline=request.deadline,
                calendar_type=decomposition.calendar_type,
                constraints=request.constraints
            )
            print(f"  Scheduled {len(scheduled_tasks)} tasks")
            
            # Step 5: Create calendar events
            print(f"Step 4: Creating calendar events")
            creation_result = self.event_creator.create_events_from_decomposition(
                task_description=request.task_description,
                decomposition=decomposition,
                scheduled_tasks=scheduled_tasks
            )
            
            main_event = creation_result.main_event
            subtask_events = creation_result.subtask_events
            errors.extend(creation_result.errors)
            
            print(f"  Created {creation_result.total_events_created} events")
            
            # Check for warnings
            if len(scheduled_tasks) != len(task_titles):
                warnings.append(f"Scheduled {len(scheduled_tasks)} tasks but expected {len(task_titles)}")
            
            if creation_result.total_events_created == 0:
                errors.append("No events were created")
            
        except Exception as e:
            errors.append(f"Scheduling failed: {e}")
        
        return SchedulingResult(
            success=len(errors) == 0,
            main_event=main_event,
            subtask_events=subtask_events,
            total_events_created=len([e for e in [main_event] + subtask_events if e is not None]),
            decomposition=decomposition,
            scheduled_tasks=scheduled_tasks,
            errors=errors,
            warnings=warnings
        )
    
    def schedule_simple_task(self, 
                           task_description: str, 
                           deadline: str,
                           duration_minutes: int = 30,
                           calendar_type: str = "Home") -> SchedulingResult:
        """
        Schedule a simple task without LLM decomposition
        
        Args:
            task_description: Description of the task
            deadline: ISO format deadline
            duration_minutes: Duration in minutes
            calendar_type: "Work" or "Home"
            
        Returns:
            Scheduling result
        """
        # Create a simple decomposition
        from .llm_decomposer import TaskDecomposition
        decomposition = TaskDecomposition(
            calendar_type=calendar_type,
            subtasks=None,
            total_duration_minutes=duration_minutes,
            reasoning="Simple task - no decomposition needed"
        )
        
        # Schedule the single task
        scheduled_tasks = self.time_agent.schedule_tasks(
            task_titles=[task_description],
            task_durations=[duration_minutes],
            deadline=deadline,
            calendar_type=calendar_type
        )
        
        # Create the event
        creation_result = self.event_creator.create_events_from_decomposition(
            task_description=task_description,
            decomposition=decomposition,
            scheduled_tasks=scheduled_tasks
        )
        
        return SchedulingResult(
            success=len(creation_result.errors) == 0,
            main_event=creation_result.main_event,
            subtask_events=creation_result.subtask_events,
            total_events_created=creation_result.total_events_created,
            decomposition=decomposition,
            scheduled_tasks=scheduled_tasks,
            errors=creation_result.errors,
            warnings=[]
        )
    
    def get_free_time_summary(self, deadline: str) -> Dict[str, Any]:
        """
        Get a summary of free time until deadline
        
        Args:
            deadline: ISO format deadline
            
        Returns:
            Free time summary
        """
        return self.time_agent.get_free_slots_summary(deadline)
    
    def cleanup_events(self, result: SchedulingResult) -> int:
        """
        Clean up events created by a scheduling result
        
        Args:
            result: Scheduling result to clean up
            
        Returns:
            Number of events deleted
        """
        events_to_delete = []
        
        if result.main_event:
            events_to_delete.append(result.main_event)
        
        events_to_delete.extend(result.subtask_events)
        
        return self.event_creator.cleanup_events(events_to_delete)
    
    def print_result(self, result: SchedulingResult) -> None:
        """
        Print a formatted scheduling result
        
        Args:
            result: Scheduling result to print
        """
        print(f"\n{'='*60}")
        print(f"LLM TASK SCHEDULING RESULT")
        print(f"{'='*60}")
        
        if result.success:
            print(f"✅ SUCCESS: Created {result.total_events_created} events")
        else:
            print(f"❌ FAILED: {len(result.errors)} errors")
        
        if result.decomposition:
            print(f"\n📋 TASK DECOMPOSITION:")
            print(f"  Calendar: {result.decomposition.calendar_type}")
            print(f"  Reasoning: {result.decomposition.reasoning}")
            
            if result.decomposition.subtasks:
                print(f"  Subtasks ({len(result.decomposition.subtasks)}):")
                for i, subtask in enumerate(result.decomposition.subtasks, 1):
                    print(f"    {i}. {subtask.title} ({subtask.duration_minutes} min)")
            else:
                print(f"  Simple task: {result.decomposition.total_duration_minutes} minutes")
        
        if result.scheduled_tasks:
            print(f"\n⏰ SCHEDULED TASKS:")
            for task in result.scheduled_tasks:
                print(f"  {task.task_id}: {task.title}")
                print(f"    {task.start_iso} → {task.end_iso} ({task.duration_minutes} min)")
        
        if result.main_event or result.subtask_events:
            print(f"\n📅 CREATED EVENTS:")
            if result.main_event:
                print(f"  Main Task: {result.main_event.title} (ID: {result.main_event.event_id[:8]}...)")
                print(f"    {result.main_event.start_iso} → {result.main_event.end_iso}")
                print(f"    Calendar: {result.main_event.calendar}")
                print(f"    Type: Simple task (no decomposition)")
            
            if result.subtask_events:
                print(f"  Subtasks ({len(result.subtask_events)}):")
                for event in result.subtask_events:
                    print(f"    {event.title} (ID: {event.event_id[:8]}...)")
                    print(f"      {event.start_iso} → {event.end_iso}")
                    print(f"      Calendar: {event.calendar}")
                    print(f"      Parent ID: {event.parent_id[:8] if event.parent_id else 'None'}...")
                    print(f"      Type: Decomposed subtask")
        
        if result.warnings:
            print(f"\n⚠️  WARNINGS:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        if result.errors:
            print(f"\n❌ ERRORS:")
            for error in result.errors:
                print(f"  - {error}")


def main():
    """Test the main LLM Task Scheduler"""
    scheduler = LLMTaskScheduler()
    
    # Test cases
    test_cases = [
        SchedulingRequest(
            task_description="Write a research paper on AI ethics",
            deadline="2025-11-15T23:59:00"
        ),
        SchedulingRequest(
            task_description="Call mom for 15 minutes",
            deadline="2025-10-20T18:00:00"
        ),
        SchedulingRequest(
            task_description="Plan company retreat",
            deadline="2025-12-01T23:59:00"
        )
    ]
    
    for i, request in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST CASE {i}: {request.task_description}")
        print(f"{'='*80}")
        
        try:
            result = scheduler.schedule_task(request)
            scheduler.print_result(result)
            
            # Clean up created events
            if result.total_events_created > 0:
                deleted = scheduler.cleanup_events(result)
                print(f"\n🧹 Cleaned up {deleted} events")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
        
        print(f"\n{'-'*80}")


if __name__ == "__main__":
    main()
