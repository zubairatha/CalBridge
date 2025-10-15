"""
Demo script for LLM Task Scheduling System

This script demonstrates the capabilities of the LLM task scheduling system
with various example tasks and scenarios.
"""

import sys
from datetime import datetime, timedelta
from .main_scheduler import LLMTaskScheduler, SchedulingRequest


def demo_simple_tasks():
    """Demo simple task scheduling"""
    print("🎯 DEMO: Simple Task Scheduling")
    print("=" * 50)
    
    scheduler = LLMTaskScheduler()
    
    # Simple tasks that don't need decomposition
    simple_tasks = [
        ("Call mom for 15 minutes", "+1d", 15, "Home"),
        ("Buy groceries", "+2d", 45, "Home"),
        ("Team standup meeting", "+1d", 30, "Work"),
        ("Doctor appointment", "+3d", 60, "Home")
    ]
    
    for task, deadline, duration, calendar in simple_tasks:
        print(f"\n📋 Task: {task}")
        print(f"   Deadline: {deadline}")
        print(f"   Duration: {duration} minutes")
        print(f"   Calendar: {calendar}")
        
        try:
            result = scheduler.schedule_simple_task(task, deadline, duration, calendar)
            
            if result.success:
                print(f"   ✅ Success: Created {result.total_events_created} event(s)")
                if result.main_event:
                    print(f"   📅 Event: {result.main_event.title}")
                    print(f"   ⏰ Time: {result.main_event.start_iso} → {result.main_event.end_iso}")
            else:
                print(f"   ❌ Failed: {', '.join(result.errors)}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()


def demo_complex_tasks():
    """Demo complex task scheduling with LLM decomposition"""
    print("🧠 DEMO: Complex Task Scheduling with LLM Decomposition")
    print("=" * 60)
    
    scheduler = LLMTaskScheduler()
    
    # Complex tasks that need decomposition
    complex_tasks = [
        ("Write a research paper on AI ethics", "2025-11-15T23:59:00"),
        ("Plan company retreat", "2025-12-01T23:59:00"),
        ("Develop mobile app prototype", "2025-11-30T23:59:00"),
        ("Organize wedding ceremony", "2025-10-31T23:59:00")
    ]
    
    for task, deadline in complex_tasks:
        print(f"\n📋 Task: {task}")
        print(f"   Deadline: {deadline}")
        
        try:
            request = SchedulingRequest(task_description=task, deadline=deadline)
            result = scheduler.schedule_task(request)
            
            if result.success:
                print(f"   ✅ Success: Created {result.total_events_created} event(s)")
                
                if result.decomposition:
                    print(f"   🧠 LLM Analysis:")
                    print(f"      Calendar: {result.decomposition.calendar_type}")
                    print(f"      Reasoning: {result.decomposition.reasoning}")
                    
                    if result.decomposition.subtasks:
                        print(f"      Subtasks ({len(result.decomposition.subtasks)}):")
                        for i, subtask in enumerate(result.decomposition.subtasks, 1):
                            print(f"        {i}. {subtask.title} ({subtask.duration_minutes} min)")
                    else:
                        print(f"      Simple task: {result.decomposition.total_duration_minutes} minutes")
                
                if result.scheduled_tasks:
                    print(f"   ⏰ Scheduled Tasks:")
                    for task in result.scheduled_tasks:
                        print(f"      {task.task_id}: {task.title}")
                        print(f"        {task.start_iso} → {task.end_iso} ({task.duration_minutes} min)")
                
                if result.main_event:
                    print(f"   📅 Main Event: {result.main_event.title}")
                    print(f"      ID: {result.main_event.event_id[:8]}...")
                    print(f"      Calendar: {result.main_event.calendar}")
                
                if result.subtask_events:
                    print(f"   📅 Subtask Events ({len(result.subtask_events)}):")
                    for event in result.subtask_events:
                        print(f"      {event.title} (ID: {event.event_id[:8]}...)")
                        print(f"        Parent: {event.parent_id[:8] if event.parent_id else 'None'}...")
                
            else:
                print(f"   ❌ Failed: {', '.join(result.errors)}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()


def demo_free_time_analysis():
    """Demo free time analysis"""
    print("⏰ DEMO: Free Time Analysis")
    print("=" * 40)
    
    scheduler = LLMTaskScheduler()
    
    # Different deadline scenarios
    deadlines = [
        ("+1d", "Next 24 hours"),
        ("+7d", "Next week"),
        ("+30d", "Next month"),
        ("2025-11-01T23:59:00", "Until November 1st")
    ]
    
    for deadline, description in deadlines:
        print(f"\n📊 {description}")
        print(f"   Deadline: {deadline}")
        
        try:
            summary = scheduler.get_free_time_summary(deadline)
            
            print(f"   📈 Summary:")
            print(f"      Total events: {summary['total_events']}")
            print(f"      Free slots: {summary['total_free_slots']}")
            print(f"      Free time: {summary['total_free_minutes']} minutes ({summary['total_free_minutes']/60:.1f} hours)")
            
            if summary['free_slots']:
                print(f"   📅 First few free slots:")
                for i, slot in enumerate(summary['free_slots'][:3], 1):
                    start_dt = datetime.fromisoformat(slot['start'])
                    end_dt = datetime.fromisoformat(slot['end'])
                    print(f"      {i}. {start_dt.strftime('%Y-%m-%d %H:%M')} → {end_dt.strftime('%H:%M')} ({slot['duration_minutes']} min)")
                
                if len(summary['free_slots']) > 3:
                    print(f"      ... and {len(summary['free_slots']) - 3} more slots")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()


def demo_constraints():
    """Demo scheduling with constraints"""
    print("🔒 DEMO: Scheduling with Constraints")
    print("=" * 45)
    
    from task_scheduler import ConstraintAdder
    from datetime import time, date
    
    scheduler = LLMTaskScheduler()
    
    # Create constraints
    constraints = ConstraintAdder()
    constraints.add_weekly_blackout(weekday=0, start_t=time(12,0), end_t=time(13,0))  # Monday lunch
    constraints.add_weekly_blackout(weekday=4, start_t=time(17,0), end_t=time(18,0))  # Friday evening
    constraints.set_min_gap_minutes(30)  # 30 min gap between tasks
    constraints.set_max_tasks_per_day(2)  # Max 2 tasks per day
    
    print("🔒 Constraints applied:")
    print("   - Monday 12:00-13:00 blocked (lunch)")
    print("   - Friday 17:00-18:00 blocked (evening)")
    print("   - 30 minute gap between tasks")
    print("   - Maximum 2 tasks per day")
    print()
    
    # Test task with constraints
    task = "Complete project documentation"
    deadline = "+7d"
    
    print(f"📋 Task: {task}")
    print(f"   Deadline: {deadline}")
    
    try:
        request = SchedulingRequest(
            task_description=task,
            deadline=deadline,
            constraints=constraints
        )
        
        result = scheduler.schedule_task(request)
        
        if result.success:
            print(f"   ✅ Success: Created {result.total_events_created} event(s)")
            
            if result.scheduled_tasks:
                print(f"   ⏰ Scheduled Tasks (respecting constraints):")
                for task in result.scheduled_tasks:
                    print(f"      {task.task_id}: {task.title}")
                    print(f"        {task.start_iso} → {task.end_iso} ({task.duration_minutes} min)")
        else:
            print(f"   ❌ Failed: {', '.join(result.errors)}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")


def main():
    """Run all demos"""
    print("🚀 LLM Task Scheduling System Demo")
    print("=" * 60)
    print("This demo showcases the capabilities of the LLM task scheduling system.")
    print("Make sure Ollama and CalBridge are running before proceeding.")
    print()
    
    try:
        # Run demos
        demo_simple_tasks()
        demo_complex_tasks()
        demo_free_time_analysis()
        demo_constraints()
        
        print("🎉 Demo completed successfully!")
        print("\nTo run individual demos or use the system:")
        print("  python -m LLM_task_scheduling.cli --help")
        print("  python -m LLM_task_scheduling.cli schedule 'Your task' 'deadline'")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("Make sure Ollama and CalBridge are running.")


if __name__ == "__main__":
    main()
