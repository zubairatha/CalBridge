"""
Command Line Interface for Smart Task Scheduling
Provides easy-to-use CLI commands for task scheduling operations.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from smart_scheduler import SmartScheduler


def parse_datetime(date_str: str) -> datetime:
    """Parse datetime string in various formats."""
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse datetime: {date_str}")


def schedule_task_command(args):
    """Handle schedule task command."""
    scheduler = SmartScheduler(args.db_path, args.memory_file)
    
    deadline = None
    if args.deadline:
        deadline = parse_datetime(args.deadline)
    
    print(f"Scheduling task: {args.task}")
    if deadline:
        print(f"Deadline: {deadline}")
    
    result = scheduler.schedule_task(
        args.task, 
        deadline, 
        auto_create_events=not args.no_events
    )
    
    if result['success']:
        print(f"\n🎉 TASK SCHEDULING COMPLETED SUCCESSFULLY!")
        print(f"🆔 Task ID: {result['task_id']}")
        print(f"📅 Scheduled subtasks: {result['scheduled_subtasks']}")
        print(f"⚠️  Unscheduled subtasks: {result['unscheduled_subtasks']}")
        print(f"📅 Calendar events created: {len(result['created_events'])}")
        
        if args.verbose:
            print(f"\n📊 DETAILED RESULTS:")
            print(f"Decomposed task:")
            print(json.dumps(result['decomposed_task'], indent=2))
            
            if result['time_allocation']:
                print(f"\nTime allocation:")
                print(json.dumps(result['time_allocation'], indent=2))
    else:
        print(f"\n❌ TASK SCHEDULING FAILED!")
        print(f"Error: {result['error']}")
        return 1
    
    return 0


def list_tasks_command(args):
    """Handle list tasks command."""
    scheduler = SmartScheduler(args.db_path, args.memory_file)
    
    tasks = scheduler.get_scheduled_tasks(args.status)
    
    if not tasks:
        print("No tasks found.")
        return 0
    
    print(f"Found {len(tasks)} tasks:")
    print("-" * 80)
    
    for task in tasks:
        print(f"ID: {task['task_id']}")
        print(f"Title: {task['title']}")
        print(f"Status: {task['status']}")
        print(f"Complexity: {task['task_complexity']}")
        print(f"Estimated hours: {task['estimated_total_hours']}")
        print(f"Subtasks: {len(task['subtasks'])}")
        
        if args.verbose:
            print("Subtasks:")
            for subtask in task['subtasks']:
                print(f"  - {subtask['title']} ({subtask['status']})")
                if subtask['scheduled_start']:
                    print(f"    Scheduled: {subtask['scheduled_start']} - {subtask['scheduled_end']}")
        
        print("-" * 80)
    
    return 0


def show_task_command(args):
    """Handle show task command."""
    scheduler = SmartScheduler(args.db_path, args.memory_file)
    
    task = scheduler.get_task_details(args.task_id)
    
    if not task:
        print(f"Task {args.task_id} not found.")
        return 1
    
    print(f"Task Details:")
    print(f"ID: {task['task_id']}")
    print(f"Title: {task['title']}")
    print(f"Description: {task['description']}")
    print(f"Status: {task['status']}")
    print(f"Calendar: {task['calendar_assignment']}")
    print(f"Complexity: {task['task_complexity']}")
    print(f"Estimated hours: {task['estimated_total_hours']}")
    print(f"Created: {task['created_at']}")
    print(f"Updated: {task['updated_at']}")
    
    print(f"\nSubtasks ({len(task['subtasks'])}):")
    for i, subtask in enumerate(task['subtasks'], 1):
        print(f"{i}. {subtask['title']}")
        print(f"   Status: {subtask['status']}")
        print(f"   Priority: {subtask['priority']}")
        print(f"   Difficulty: {subtask['difficulty']}")
        print(f"   Estimated hours: {subtask['estimated_hours']}")
        
        if subtask['scheduled_start']:
            print(f"   Scheduled: {subtask['scheduled_start']} - {subtask['scheduled_end']}")
        
        if subtask['dependencies']:
            print(f"   Dependencies: {', '.join(subtask['dependencies'])}")
        
        if subtask['calendar_event_id']:
            print(f"   Calendar event: {subtask['calendar_event_id']}")
        
        print()
    
    return 0


def add_memory_command(args):
    """Handle add memory command."""
    scheduler = SmartScheduler(args.db_path, args.memory_file)
    
    success = scheduler.add_user_memory(args.title, args.description, args.tags)
    
    if success:
        print(f"✅ Added memory: '{args.title}'")
    else:
        print(f"❌ Failed to add memory: '{args.title}'")
        return 1
    
    return 0


def show_preferences_command(args):
    """Handle show preferences command."""
    scheduler = SmartScheduler(args.db_path, args.memory_file)
    
    preferences = scheduler.get_user_preferences()
    
    print("User Memories:")
    for memory in preferences['memories']:
        print(f"- {memory['title']}: {memory['description']}")
        print(f"  Tags: {memory['tags']}")
    
    print(f"\nScheduling Constraints:")
    constraints = preferences['constraints']
    for key, value in constraints.items():
        print(f"- {key}: {value}")
    
    return 0


def reschedule_task_command(args):
    """Handle reschedule task command."""
    scheduler = SmartScheduler(args.db_path, args.memory_file)
    
    deadline = None
    if args.deadline:
        deadline = parse_datetime(args.deadline)
    
    print(f"Rescheduling task {args.task_id}...")
    
    result = scheduler.reschedule_task(args.task_id, deadline)
    
    if result['success']:
        print(f"✅ Task rescheduled successfully!")
        print(f"Scheduled subtasks: {result['scheduled_subtasks']}")
        print(f"Calendar events created: {len(result['created_events'])}")
    else:
        print(f"❌ Task rescheduling failed: {result['error']}")
        return 1
    
    return 0


def delete_task_command(args):
    """Handle delete task command."""
    scheduler = SmartScheduler(args.db_path, args.memory_file)
    
    if not args.force:
        confirm = input(f"Are you sure you want to delete task {args.task_id}? (y/N): ")
        if confirm.lower() != 'y':
            print("Deletion cancelled.")
            return 0
    
    success = scheduler.delete_task(args.task_id)
    
    if success:
        print(f"✅ Task {args.task_id} deleted successfully!")
    else:
        print(f"❌ Failed to delete task {args.task_id}")
        return 1
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Smart Task Scheduling System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Schedule a new task
  python -m smart_task_scheduling.cli schedule "Build a mobile app" --deadline "2025-02-15"

  # List all tasks
  python -m smart_task_scheduling.cli list

  # Show task details
  python -m smart_task_scheduling.cli show 1

  # Add user memory
  python -m smart_task_scheduling.cli add-memory "Coffee Break" "Take coffee break at 10:30 AM" "coffee, break, 10:30am"

  # Show all memories and preferences
  python -m smart_task_scheduling.cli preferences
        """
    )
    
    parser.add_argument('--db-path', default='task_scheduler.db',
                       help='Path to SQLite database file')
    parser.add_argument('--memory-file', default='user_memory.json',
                       help='Path to user memory JSON file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Schedule task command
    schedule_parser = subparsers.add_parser('schedule', help='Schedule a new task')
    schedule_parser.add_argument('task', help='Task description')
    schedule_parser.add_argument('--deadline', help='Deadline (YYYY-MM-DD HH:MM)')
    schedule_parser.add_argument('--no-events', action='store_true',
                               help='Do not create calendar events')
    
    # List tasks command
    list_parser = subparsers.add_parser('list', help='List all tasks')
    list_parser.add_argument('--status', help='Filter by status')
    
    # Show task command
    show_parser = subparsers.add_parser('show', help='Show task details')
    show_parser.add_argument('task_id', type=int, help='Task ID to show')
    
    # Add memory command
    add_mem_parser = subparsers.add_parser('add-memory', help='Add a new memory item')
    add_mem_parser.add_argument('title', help='Memory title')
    add_mem_parser.add_argument('description', help='Memory description')
    add_mem_parser.add_argument('tags', help='Comma-separated tags')
    
    # Show preferences command
    subparsers.add_parser('preferences', help='Show all user memories and constraints')
    
    # Reschedule task command
    reschedule_parser = subparsers.add_parser('reschedule', help='Reschedule existing task')
    reschedule_parser.add_argument('task_id', type=int, help='Task ID to reschedule')
    reschedule_parser.add_argument('--deadline', help='New deadline (YYYY-MM-DD HH:MM)')
    
    # Delete task command
    delete_parser = subparsers.add_parser('delete', help='Delete a task')
    delete_parser.add_argument('task_id', type=int, help='Task ID to delete')
    delete_parser.add_argument('--force', action='store_true',
                             help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'schedule':
            return schedule_task_command(args)
        elif args.command == 'list':
            return list_tasks_command(args)
        elif args.command == 'show':
            return show_task_command(args)
        elif args.command == 'add-memory':
            return add_memory_command(args)
        elif args.command == 'preferences':
            return show_preferences_command(args)
        elif args.command == 'reschedule':
            return reschedule_task_command(args)
        elif args.command == 'delete':
            return delete_task_command(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
