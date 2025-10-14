#!/usr/bin/env python3
"""
Demo Script for Smart Task Scheduling System
Shows how to use the system programmatically.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from smart_task_scheduling.smart_scheduler import SmartScheduler


def main():
    """Run a demonstration of the smart task scheduling system."""
    print("🚀 Smart Task Scheduling System Demo")
    print("=" * 50)
    
    try:
        # Initialize the scheduler
        print("1. Initializing Smart Scheduler...")
        scheduler = SmartScheduler()
        print("   ✅ Scheduler initialized successfully")
        
        # Show current user memories
        print("\n2. Current User Memories:")
        preferences = scheduler.get_user_preferences()
        for memory in preferences['memories'][:3]:  # Show first 3
            print(f"   - {memory['title']}: {memory['description']}")
        if len(preferences['memories']) > 3:
            print(f"   ... and {len(preferences['memories']) - 3} more memories")
        
        print(f"\n   Scheduling constraints:")
        print(f"   Wake up: {preferences['constraints']['wake_up_time']}")
        print(f"   Sleep: {preferences['constraints']['sleep_time']}")
        
        # Example 1: Schedule a simple task
        print("\n3. Scheduling Example Task 1: 'Prepare presentation for client meeting'")
        task1 = "Prepare presentation for client meeting"
        deadline1 = datetime.now() + timedelta(days=3)
        
        result1 = scheduler.schedule_task(task1, deadline1, auto_create_events=False)
        
        if result1['success']:
            print(f"   ✅ Task scheduled successfully!")
            print(f"   Task ID: {result1['task_id']}")
            print(f"   Subtasks: {result1['scheduled_subtasks']} scheduled")
            print(f"   Available slots: {result1['available_slots_count']}")
        else:
            print(f"   ❌ Failed to schedule task: {result1['error']}")
        
        # Example 2: Schedule a complex task
        print("\n4. Scheduling Example Task 2: 'Build a mobile app for tracking fitness goals'")
        task2 = "Build a mobile app for tracking fitness goals"
        deadline2 = datetime.now() + timedelta(days=14)
        
        result2 = scheduler.schedule_task(task2, deadline2, auto_create_events=False)
        
        if result2['success']:
            print(f"   ✅ Complex task scheduled successfully!")
            print(f"   Task ID: {result2['task_id']}")
            print(f"   Subtasks: {result2['scheduled_subtasks']} scheduled")
            
            # Show task details
            task_details = scheduler.get_task_details(result2['task_id'])
            if task_details:
                print(f"   Task: {task_details['title']}")
                print(f"   Complexity: {task_details['task_complexity']}")
                print(f"   Calendar: {task_details['calendar_assignment']}")
                print("   Subtasks:")
                for i, subtask in enumerate(task_details['subtasks'][:3], 1):  # Show first 3
                    print(f"     {i}. {subtask['title']} ({subtask['difficulty']})")
                if len(task_details['subtasks']) > 3:
                    print(f"     ... and {len(task_details['subtasks']) - 3} more")
        else:
            print(f"   ❌ Failed to schedule complex task: {result2['error']}")
        
        # Example 3: List all tasks
        print("\n5. Listing All Scheduled Tasks:")
        all_tasks = scheduler.get_scheduled_tasks()
        
        if all_tasks:
            print(f"   Found {len(all_tasks)} tasks:")
            for task in all_tasks:
                print(f"   - ID {task['task_id']}: {task['title']} ({task['status']})")
        else:
            print("   No tasks found")
        
        # Example 4: Add user memory
        print("\n6. Adding User Memory:")
        print("   Adding coffee break memory...")
        success = scheduler.add_user_memory(
            "Coffee Break", 
            "Take coffee break at 10:30 AM", 
            "coffee, break, 10:30am, daily"
        )
        if success:
            print("   ✅ Memory added successfully")
        else:
            print("   ❌ Failed to add memory")
        
        # Example 5: Show system capabilities
        print("\n7. System Capabilities Summary:")
        print("   ✅ User memory system with JSON preferences")
        print("   ✅ LLM-powered task decomposition (llama3)")
        print("   ✅ Intelligent time slot allocation")
        print("   ✅ SQL database for task tracking")
        print("   ✅ CalBridge integration for calendar events")
        print("   ✅ Command-line interface")
        print("   ✅ Comprehensive test suite")
        
        print("\n🎉 Demo completed successfully!")
        print("\nNext steps:")
        print("1. Run: python -m smart_task_scheduling.cli schedule 'Your task here'")
        print("2. Run: python -m smart_task_scheduling.cli add-memory 'Title' 'Description' 'tags'")
        print("3. Run: python -m smart_task_scheduling.cli list")
        print("4. Run: python -m smart_task_scheduling.test_components")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure CalBridge is running on http://127.0.0.1:8765")
        print("2. Ensure Ollama is running with llama3 model")
        print("3. Run: python scripts/cache_calendars.py")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
