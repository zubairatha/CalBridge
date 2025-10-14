"""
Smart Task Scheduler - Main Orchestrator
Combines all components to provide a complete smart task scheduling solution.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from user_memory import UserMemory
from task_decomposer import TaskDecomposer
from time_allotter import TimeAllotter
from task_scheduler import TaskScheduler


class SmartScheduler:
    """Main orchestrator for the smart task scheduling system."""
    
    def __init__(self, db_path: str = "task_scheduler.db", memory_file: str = "user_memory.json"):
        """Initialize the smart scheduler.
        
        Args:
            db_path: Path to SQLite database file
            memory_file: Path to user memory JSON file
        """
        self.user_memory = UserMemory(memory_file)
        self.task_decomposer = TaskDecomposer()
        self.time_allotter = TimeAllotter()
        self.task_scheduler = TaskScheduler(db_path)
    
    def schedule_task(self, task_description: str, deadline: Optional[datetime] = None,
                     auto_create_events: bool = True) -> Dict[str, Any]:
        """Complete smart scheduling workflow for a task.
        
        Args:
            task_description: Description of the task to schedule
            deadline: Optional deadline for the task
            auto_create_events: Whether to automatically create calendar events
            
        Returns:
            Dictionary containing scheduling results
        """
        try:
            print("\n" + "🚀" + "="*78 + "🚀")
            print("🎯 SMART TASK SCHEDULING SYSTEM - STARTING WORKFLOW")
            print("🚀" + "="*78 + "🚀")
            
            # Step 1: Decompose task using LLM
            print("\n📋 STEP 1: TASK DECOMPOSITION")
            print("-" * 50)
            print(f"📝 Task: {task_description}")
            if deadline:
                print(f"⏰ Deadline: {deadline.strftime('%Y-%m-%d %H:%M')}")
            
            user_memories = self.user_memory.get_memories_for_llm()
            print(f"🧠 Using {len(user_memories)} user memories for context")
            
            decomposed_task = self.task_decomposer.decompose_task(
                task_description, deadline, user_memories
            )
            
            print(f"\n✅ Task decomposed successfully!")
            print(f"   📊 Complexity: {decomposed_task.get('task_complexity', 'unknown')}")
            print(f"   📅 Calendar: {decomposed_task.get('calendar_assignment', 'unknown')}")
            print(f"   ⏱️  Estimated hours: {decomposed_task.get('estimated_total_hours', 0)}")
            print(f"   🔢 Subtasks: {len(decomposed_task.get('subtasks', []))}")
            
            # Step 2: Get available time slots
            print(f"\n⏰ STEP 2: AVAILABLE TIME SLOTS")
            print("-" * 50)
            
            # Calculate days until deadline (minimum 7, maximum 90)
            if deadline:
                days_until_deadline = max(7, min(90, (deadline - datetime.now()).days + 1))
            else:
                days_until_deadline = 30  # Default if no deadline
            
            available_slots = self.time_allotter.get_free_time_slots(days=days_until_deadline)
            print(f"📅 Found {len(available_slots)} available time slots in next {days_until_deadline} days")
            
            if available_slots:
                total_available_minutes = sum(slot['duration_minutes'] for slot in available_slots)
                total_available_hours = total_available_minutes / 60
                print(f"⏱️  Total available time: {total_available_hours:.1f} hours")
                
                # Show first few slots
                print(f"\n📋 First few available slots:")
                for i, slot in enumerate(available_slots[:3]):
                    start_str = slot['start'].strftime('%Y-%m-%d %H:%M')
                    duration_hours = slot['duration_minutes'] / 60
                    print(f"   {i+1}. {start_str} ({duration_hours:.1f}h)")
                if len(available_slots) > 3:
                    print(f"   ... and {len(available_slots) - 3} more slots")
            
            # Step 3: Allocate time slots using LLM
            print(f"\n🤖 STEP 3: TIME ALLOCATION")
            print("-" * 50)
            time_allocation = self.time_allotter.allot_time_slots(
                decomposed_task, available_slots, deadline
            )
            
            scheduled_count = len(time_allocation.get('allocations', []))
            unscheduled_count = len(time_allocation.get('unscheduled_subtasks', []))
            
            print(f"✅ Time allocation completed!")
            print(f"   📅 Scheduled subtasks: {scheduled_count}")
            print(f"   ⚠️  Unscheduled subtasks: {unscheduled_count}")
            
            # Step 4: Store task and subtasks in database
            print(f"\n💾 STEP 4: DATABASE STORAGE")
            print("-" * 50)
            task_id, subtask_ids = self.task_scheduler.create_task(
                decomposed_task, time_allocation
            )
            print(f"✅ Task stored in database!")
            print(f"   🆔 Task ID: {task_id}")
            print(f"   🔢 Subtask IDs: {subtask_ids}")
            
            # Step 5: Create calendar events (if requested)
            created_events = []
            if auto_create_events and time_allocation.get('allocations'):
                print(f"\n📅 STEP 5: CALENDAR EVENT CREATION")
                print("-" * 50)
                created_events = self.task_scheduler.create_calendar_events(
                    task_id, time_allocation
                )
                print(f"✅ Created {len(created_events)} calendar events!")
                
                for i, event_id in enumerate(created_events):
                    print(f"   📅 Event {i+1}: {event_id}")
            else:
                print(f"\n⏭️  STEP 5: SKIPPED (auto_create_events={auto_create_events})")
            
            # Update user memory with scheduling patterns
            self.user_memory.update_from_scheduling_pattern(time_allocation.get('allocations', []))
            
            print(f"\n🎉 WORKFLOW COMPLETED SUCCESSFULLY!")
            print("🚀" + "="*78 + "🚀")
            
            return {
                'success': True,
                'task_id': task_id,
                'subtask_ids': subtask_ids,
                'decomposed_task': decomposed_task,
                'time_allocation': time_allocation,
                'created_events': created_events,
                'available_slots_count': len(available_slots),
                'scheduled_subtasks': len(time_allocation.get('allocations', [])),
                'unscheduled_subtasks': len(time_allocation.get('unscheduled_subtasks', []))
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'task_description': task_description,
                'deadline': deadline.isoformat() if deadline else None
            }
    
    def get_scheduled_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all scheduled tasks.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of task dictionaries
        """
        return self.task_scheduler.get_all_tasks(status)
    
    def get_task_details(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific task.
        
        Args:
            task_id: Task ID to retrieve
            
        Returns:
            Task dictionary with subtasks or None if not found
        """
        return self.task_scheduler.get_task(task_id)
    
    def update_task_progress(self, subtask_id: int, status: str, 
                           actual_start: Optional[datetime] = None,
                           actual_end: Optional[datetime] = None) -> bool:
        """Update progress on a subtask.
        
        Args:
            subtask_id: Subtask ID to update
            status: New status ('in_progress', 'completed', 'blocked', etc.)
            actual_start: Optional actual start time
            actual_end: Optional actual end time
            
        Returns:
            True if updated successfully
        """
        return self.task_scheduler.update_subtask_status(
            subtask_id, status, actual_start, actual_end
        )
    
    def delete_task(self, task_id: int) -> bool:
        """Delete a task and all its associated data.
        
        Args:
            task_id: Task ID to delete
            
        Returns:
            True if deleted successfully
        """
        return self.task_scheduler.delete_task(task_id)
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Get current user preferences and scheduling constraints.
        
        Returns:
            Dictionary of user preferences
        """
        return {
            'memories': self.user_memory.memory,
            'constraints': self.user_memory.get_scheduling_constraints()
        }
    
    def add_user_memory(self, title: str, description: str, tags: str) -> bool:
        """Add a new memory item.
        
        Args:
            title: Title of the memory item
            description: Description of the memory item
            tags: Comma-separated tags
            
        Returns:
            True if added successfully
        """
        self.user_memory.add_memory(title, description, tags)
        return self.user_memory.save_memory()
    
    def get_memories_for_llm(self) -> List[Dict[str, str]]:
        """Get memories formatted for LLM (title and description only).
        
        Returns:
            List of memory items with only title and description
        """
        return self.user_memory.get_memories_for_llm()
    
    def get_memories_by_tag(self, tag: str) -> List[Dict[str, str]]:
        """Get memories that contain a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of matching memory items
        """
        return self.user_memory.get_memories_by_tag(tag)
    
    def reschedule_task(self, task_id: int, new_deadline: Optional[datetime] = None) -> Dict[str, Any]:
        """Reschedule an existing task with new time allocations.
        
        Args:
            task_id: Task ID to reschedule
            new_deadline: Optional new deadline
            
        Returns:
            Dictionary containing rescheduling results
        """
        try:
            # Get existing task
            task = self.task_scheduler.get_task(task_id)
            if not task:
                return {'success': False, 'error': f'Task {task_id} not found'}
            
            # Get available time slots
            available_slots = self.time_allotter.get_free_time_slots(days=30)
            
            # Create decomposed task structure from database
            decomposed_task = {
                'title': task['title'],
                'calendar_assignment': task['calendar_assignment'],
                'calendar_id': task['calendar_id'],
                'task_complexity': task['task_complexity'],
                'estimated_total_hours': task['estimated_total_hours'],
                'deadline': new_deadline or task['deadline'],
                'subtasks': [
                    {
                        'id': f"subtask_{subtask['subtask_id']}",
                        'title': subtask['title'],
                        'description': subtask['description'],
                        'estimated_hours': subtask['estimated_hours'],
                        'priority': subtask['priority'],
                        'difficulty': subtask['difficulty'],
                        'dependencies': subtask['dependencies']
                    }
                    for subtask in task['subtasks']
                ]
            }
            
            # Allocate new time slots
            time_allocation = self.time_allotter.allot_time_slots(
                decomposed_task, available_slots, new_deadline
            )
            
            # Create new calendar events
            created_events = self.task_scheduler.create_calendar_events(
                task_id, time_allocation
            )
            
            return {
                'success': True,
                'task_id': task_id,
                'time_allocation': time_allocation,
                'created_events': created_events,
                'scheduled_subtasks': len(time_allocation.get('allocations', []))
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'task_id': task_id
            }


# Example usage and testing
if __name__ == "__main__":
    try:
        scheduler = SmartScheduler()
        
        # Example task scheduling
        task_description = "Build a mobile app for tracking fitness goals"
        deadline = datetime.now() + timedelta(days=14)
        
        print("Starting smart task scheduling...")
        result = scheduler.schedule_task(task_description, deadline)
        
        if result['success']:
            print(f"Successfully scheduled task {result['task_id']}")
            print(f"Created {len(result['created_events'])} calendar events")
            print(f"Scheduled {result['scheduled_subtasks']} subtasks")
            
            # Get task details
            task_details = scheduler.get_task_details(result['task_id'])
            print(f"Task: {task_details['title']}")
            print(f"Subtasks: {len(task_details['subtasks'])}")
            
        else:
            print(f"Scheduling failed: {result['error']}")
        
    except Exception as e:
        print(f"Error: {e}")
