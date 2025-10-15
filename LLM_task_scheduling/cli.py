"""
Command Line Interface for LLM Task Scheduling

This module provides a CLI interface for the LLM task scheduling system,
allowing users to schedule tasks from the command line.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Optional

from .main_scheduler import LLMTaskScheduler, SchedulingRequest
from .llm_decomposer import LLMTaskDecomposer
from .time_allotment import TimeAllotmentAgent
from .event_creator import EventCreator


def parse_deadline(deadline_str: str) -> str:
    """
    Parse deadline string and return ISO format
    
    Args:
        deadline_str: Deadline in various formats
        
    Returns:
        ISO format deadline string
    """
    try:
        # Try parsing as ISO format first
        if 'T' in deadline_str:
            datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
            return deadline_str
        
        # Try parsing as date only
        if len(deadline_str) == 10 and deadline_str.count('-') == 2:
            # YYYY-MM-DD format
            date_obj = datetime.strptime(deadline_str, '%Y-%m-%d')
            return date_obj.replace(hour=23, minute=59, second=0).isoformat()
        
        # Try parsing as relative days
        if deadline_str.startswith('+') and deadline_str.endswith('d'):
            days = int(deadline_str[1:-1])
            deadline = datetime.now().astimezone() + timedelta(days=days)
            return deadline.replace(hour=23, minute=59, second=0).isoformat()
        
        # Try parsing as relative hours
        if deadline_str.endswith('h'):
            hours = int(deadline_str[:-1])
            deadline = datetime.now().astimezone() + timedelta(hours=hours)
            return deadline.isoformat()
        
        raise ValueError(f"Unable to parse deadline: {deadline_str}")
        
    except Exception as e:
        raise ValueError(f"Invalid deadline format '{deadline_str}': {e}")


def schedule_task_command(args):
    """Handle the schedule task command"""
    try:
        # Parse deadline
        deadline = parse_deadline(args.deadline)
        
        # Create scheduler
        scheduler = LLMTaskScheduler(
            ollama_base=args.ollama_base,
            calbridge_base=args.calbridge_base,
            model=args.model,
            work_start_hour=args.work_start_hour,
            work_end_hour=args.work_end_hour
        )
        
        # Create scheduling request
        request = SchedulingRequest(
            task_description=args.task,
            deadline=deadline,
            constraints=args.constraints
        )
        
        print(f"Scheduling task: {args.task}")
        print(f"Deadline: {deadline}")
        print(f"Using model: {args.model}")
        print()
        
        # Schedule the task
        result = scheduler.schedule_task(request)
        
        # Print results
        scheduler.print_result(result)
        
        # Clean up if requested
        if args.cleanup and result.total_events_created > 0:
            print(f"\n🧹 Cleaning up {result.total_events_created} events...")
            deleted = scheduler.cleanup_events(result)
            print(f"Deleted {deleted} events")
        
        return 0 if result.success else 1
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def simple_schedule_command(args):
    """Handle the simple schedule command"""
    try:
        # Parse deadline
        deadline = parse_deadline(args.deadline)
        
        # Create scheduler
        scheduler = LLMTaskScheduler(
            ollama_base=args.ollama_base,
            calbridge_base=args.calbridge_base,
            model=args.model
        )
        
        print(f"Scheduling simple task: {args.task}")
        print(f"Deadline: {deadline}")
        print(f"Duration: {args.duration} minutes")
        print(f"Calendar: {args.calendar}")
        print()
        
        # Schedule the simple task
        result = scheduler.schedule_simple_task(
            task_description=args.task,
            deadline=deadline,
            duration_minutes=args.duration,
            calendar_type=args.calendar
        )
        
        # Print results
        scheduler.print_result(result)
        
        # Clean up if requested
        if args.cleanup and result.total_events_created > 0:
            print(f"\n🧹 Cleaning up {result.total_events_created} events...")
            deleted = scheduler.cleanup_events(result)
            print(f"Deleted {deleted} events")
        
        return 0 if result.success else 1
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def free_time_command(args):
    """Handle the free time command"""
    try:
        # Parse deadline
        deadline = parse_deadline(args.deadline)
        
        # Create time agent
        agent = TimeAllotmentAgent(
            calbridge_base=args.calbridge_base,
            work_start_hour=args.work_start_hour,
            work_end_hour=args.work_end_hour
        )
        
        print(f"Free time summary until: {deadline}")
        print()
        
        # Get free time summary
        summary = agent.get_free_slots_summary(deadline)
        
        print(f"📊 SUMMARY:")
        print(f"  Total events: {summary['total_events']}")
        print(f"  Total free slots: {summary['total_free_slots']}")
        print(f"  Total free minutes: {summary['total_free_minutes']}")
        print(f"  Total free hours: {summary['total_free_minutes'] / 60:.1f}")
        
        if args.show_slots and summary['free_slots']:
            print(f"\n📅 FREE SLOTS:")
            for i, slot in enumerate(summary['free_slots'][:args.max_slots], 1):
                start_dt = datetime.fromisoformat(slot['start'])
                end_dt = datetime.fromisoformat(slot['end'])
                print(f"  {i:2d}. {start_dt.strftime('%Y-%m-%d %H:%M')} → {end_dt.strftime('%H:%M')} ({slot['duration_minutes']:3d} min)")
            
            if len(summary['free_slots']) > args.max_slots:
                print(f"     ... and {len(summary['free_slots']) - args.max_slots} more slots")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def test_command(args):
    """Handle the test command"""
    try:
        print("Running LLM Task Scheduling Tests")
        print("=" * 50)
        
        # Import and run tests
        from .test_components import run_tests
        
        success = run_tests()
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="LLM Task Scheduling System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Schedule a complex task with LLM decomposition
  python -m LLM_task_scheduling.cli schedule "Write a research paper" "2025-11-15T23:59:00"
  
  # Schedule a simple task without decomposition
  python -m LLM_task_scheduling.cli simple "Call mom" "+1d" --duration 15 --calendar Home
  
  # Check free time until deadline
  python -m LLM_task_scheduling.cli free-time "2025-11-01T23:59:00" --show-slots
  
  # Run tests
  python -m LLM_task_scheduling.cli test

Deadline formats:
  - ISO format: "2025-11-15T23:59:00"
  - Date only: "2025-11-15" (defaults to 23:59)
  - Relative days: "+7d" (7 days from now)
  - Relative hours: "+2h" (2 hours from now)
        """
    )
    
    # Global options
    parser.add_argument('--ollama-base', default='http://127.0.0.1:11434',
                       help='Ollama API base URL')
    parser.add_argument('--calbridge-base', default='http://127.0.0.1:8765',
                       help='CalBridge API base URL')
    parser.add_argument('--model', default='llama3',
                       help='LLM model to use')
    parser.add_argument('--work-start-hour', type=int, default=6,
                       help='Work day start hour (24-hour format)')
    parser.add_argument('--work-end-hour', type=int, default=23,
                       help='Work day end hour (24-hour format)')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up created events after scheduling')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Schedule command
    schedule_parser = subparsers.add_parser('schedule', help='Schedule a task with LLM decomposition')
    schedule_parser.add_argument('task', help='Task description')
    schedule_parser.add_argument('deadline', help='Deadline (see examples for formats)')
    schedule_parser.add_argument('--constraints', type=json.loads, default=None,
                               help='JSON constraints for scheduling')
    
    # Simple schedule command
    simple_parser = subparsers.add_parser('simple', help='Schedule a simple task without decomposition')
    simple_parser.add_argument('task', help='Task description')
    simple_parser.add_argument('deadline', help='Deadline (see examples for formats)')
    simple_parser.add_argument('--duration', type=int, default=30,
                              help='Duration in minutes')
    simple_parser.add_argument('--calendar', choices=['Work', 'Home'], default='Home',
                              help='Calendar type')
    
    # Free time command
    free_parser = subparsers.add_parser('free-time', help='Show free time until deadline')
    free_parser.add_argument('deadline', help='Deadline (see examples for formats)')
    free_parser.add_argument('--show-slots', action='store_true',
                            help='Show individual free time slots')
    free_parser.add_argument('--max-slots', type=int, default=10,
                            help='Maximum number of slots to show')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run component tests')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Route to appropriate command handler
    if args.command == 'schedule':
        return schedule_task_command(args)
    elif args.command == 'simple':
        return simple_schedule_command(args)
    elif args.command == 'free-time':
        return free_time_command(args)
    elif args.command == 'test':
        return test_command(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
