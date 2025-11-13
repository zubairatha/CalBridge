#!/usr/bin/env python3
"""
Streamlined Agents - Full Pipeline Application

A complete CLI application that processes natural language queries through
the entire 8-stage pipeline and creates calendar events.
"""
import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from user_query import UserQueryHandler
from slot_extractor import SlotExtractor
from absolute_resolver import AbsoluteResolver
from time_standardizer import TimeStandardizer
from task_difficulty_analyzer import TaskDifficultyAnalyzer
from llm_decomposer import LLMDecomposer
from time_allotment_agent import TimeAllotmentAgent
from event_creator_agent import EventCreatorAgent
from context_provider import ContextProvider


class PipelineOrchestrator:
    """Orchestrates the full 8-stage pipeline with detailed tracking"""
    
    def __init__(self, verbose: bool = True, db_path: Optional[str] = None):
        self.verbose = verbose
        self.db_path = db_path
        self.results = {}
        self.errors = []
        
    def _print_step_header(self, step_num: int, step_name: str, step_abbr: str):
        """Print formatted step header"""
        print("\n" + "=" * 80)
        print(f"STEP {step_num}: {step_name} ({step_abbr})")
        print("=" * 80)
    
    def _print_success(self, message: str):
        """Print success message"""
        print(f"✅ {message}")
    
    def _print_error(self, message: str):
        """Print error message"""
        print(f"❌ {message}")
        self.errors.append(message)
    
    def _print_info(self, message: str):
        """Print info message"""
        print(f"ℹ️  {message}")
    
    def _print_warning(self, message: str):
        """Print warning message"""
        print(f"⚠️  {message}")
    
    def _print_data(self, label: str, data: Any, indent: int = 2):
        """Print formatted data"""
        spaces = " " * indent
        if isinstance(data, dict):
            print(f"{spaces}{label}:")
            for key, value in data.items():
                if value is not None:
                    print(f"{spaces}  • {key}: {value}")
        elif isinstance(data, list):
            print(f"{spaces}{label}:")
            for i, item in enumerate(data, 1):
                print(f"{spaces}  {i}. {item}")
        else:
            print(f"{spaces}{label}: {data}")
    
    def run_pipeline(self, query: str, timezone: str = "America/New_York") -> Dict[str, Any]:
        """
        Run the complete 8-stage pipeline
        
        Args:
            query: User's natural language query
            timezone: Timezone for processing
            
        Returns:
            Dictionary with all results and final status
        """
        print("\n" + "=" * 80)
        print("🚀 STREAMLINED AGENTS - FULL PIPELINE")
        print("=" * 80)
        print(f"📝 Query: {query}")
        print(f"🌍 Timezone: {timezone}")
        print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: User Query Handler
        self._print_step_header(1, "User Query Handler", "UQ")
        try:
            uq = UserQueryHandler(default_timezone=timezone)
            uq_result = uq.process_query(query)
            self.results["uq"] = {
                "query": uq_result.query,
                "timezone": uq_result.timezone
            }
            self._print_success("Query validated")
            self._print_data("Result", self.results["uq"])
        except Exception as e:
            self._print_error(f"UQ failed: {e}")
            return {"success": False, "error": f"UQ failed: {e}", "results": self.results}
        
        # Step 2: Slot Extractor
        self._print_step_header(2, "Slot Extractor", "SE")
        try:
            se = SlotExtractor()
            se_result = se.extract_slots_safe(uq_result.query, uq_result.timezone)
            if se_result:
                self.results["se"] = {
                    "start_text": se_result.start_text,
                    "end_text": se_result.end_text,
                    "duration": se_result.duration
                }
                self._print_success("Time slots extracted")
                self._print_data("Result", self.results["se"])
            else:
                self._print_warning("SE returned None - using defaults")
                self.results["se"] = {"start_text": None, "end_text": None, "duration": None}
        except Exception as e:
            self._print_error(f"SE failed: {e}")
            return {"success": False, "error": f"SE failed: {e}", "results": self.results}
        
        # Step 3: Absolute Resolver
        self._print_step_header(3, "Absolute Resolver", "AR")
        try:
            context_provider = ContextProvider(timezone=uq_result.timezone)
            context = context_provider.get_context()
            ar = AbsoluteResolver()
            se_dict = se_result.to_dict() if se_result else None
            ar_result = ar.resolve_absolute_safe(se_dict, context) if se_result else None
            
            if ar_result:
                self.results["ar"] = {
                    "start_text": ar_result.start_text,
                    "end_text": ar_result.end_text,
                    "duration": ar_result.duration
                }
                self._print_success("Absolute times resolved")
                self._print_data("Result", self.results["ar"])
            else:
                self._print_warning("AR returned None")
                self.results["ar"] = {"start_text": None, "end_text": None, "duration": None}
        except Exception as e:
            self._print_error(f"AR failed: {e}")
            return {"success": False, "error": f"AR failed: {e}", "results": self.results}
        
        # Step 4: Time Standardizer
        self._print_step_header(4, "Time Standardizer", "TS")
        try:
            ts = TimeStandardizer()
            ar_dict = ar_result.to_dict() if ar_result else None
            ts_result = ts.standardize_safe(ar_dict, uq_result.timezone) if ar_result else None
            
            if ts_result:
                self.results["ts"] = {
                    "start": ts_result.start,
                    "end": ts_result.end,
                    "duration": ts_result.duration
                }
                self._print_success("Times standardized to ISO format")
                self._print_data("Result", self.results["ts"])
            else:
                self._print_warning("TS returned None")
                self.results["ts"] = {"start": None, "end": None, "duration": None}
        except Exception as e:
            self._print_error(f"TS failed: {e}")
            return {"success": False, "error": f"TS failed: {e}", "results": self.results}
        
        # Step 5: Task Difficulty Analyzer
        self._print_step_header(5, "Task Difficulty Analyzer", "TD")
        try:
            td = TaskDifficultyAnalyzer()
            ts_dict = ts_result.to_dict() if ts_result else None
            td_result = td.analyze_safe(uq_result.query, ts_dict.get("duration") if ts_dict else None) if ts_result else None
            
            if td_result:
                self.results["td"] = td_result.to_dict()
                self._print_success("Task classified")
                self._print_data("Result", self.results["td"])
                print(f"  📊 Task Type: {td_result.type.upper()}")
                print(f"  📅 Calendar: {td_result.calendar or 'N/A'}")
                print(f"  📝 Title: {td_result.title}")
            else:
                self._print_warning("TD returned None")
                self.results["td"] = None
        except Exception as e:
            self._print_error(f"TD failed: {e}")
            return {"success": False, "error": f"TD failed: {e}", "results": self.results}
        
        # Step 6: LLM Decomposer (only for complex tasks)
        self._print_step_header(6, "LLM Decomposer", "LD")
        ld_result = None
        if td_result and td_result.type == "complex":
            try:
                ld = LLMDecomposer()
                td_dict = td_result.to_dict()
                ld_result = ld.decompose_safe(td_dict)
                
                if ld_result:
                    self.results["ld"] = ld_result.to_dict()
                    self._print_success(f"Task decomposed into {len(ld_result.subtasks)} subtasks")
                    print(f"  📋 Subtasks:")
                    for i, subtask in enumerate(ld_result.subtasks, 1):
                        print(f"     {i}. {subtask.title} ({subtask.duration})")
                else:
                    self._print_warning("LD returned None")
                    self.results["ld"] = None
            except Exception as e:
                self._print_error(f"LD failed: {e}")
                self.results["ld"] = None
        else:
            self._print_info("Skipped (simple task)")
            self.results["ld"] = None
        
        # Step 7: Time Allotment Agent
        self._print_step_header(7, "Time Allotment Agent", "TA")
        ta_result = None
        try:
            ta = TimeAllotmentAgent()
            
            if td_result and td_result.type == "simple":
                td_dict = td_result.to_dict()
                ts_dict = {
                    "start": ts_result.start,
                    "end": ts_result.end,
                    "duration": ts_result.duration
                }
                ta_result = ta.schedule_simple_task(td_dict, ts_dict)
                self.results["ta"] = ta_result.to_dict()
                self._print_success("Simple task scheduled")
                print(f"  🆔 Task ID: {ta_result.id}")
                print(f"  ⏰ Slot: {ta_result.slot[0]} → {ta_result.slot[1]}")
                
            elif ld_result and ld_result.type == "complex":
                ld_dict = ld_result.to_dict()
                ts_dict = {
                    "start": ts_result.start,
                    "end": ts_result.end,
                    "duration": ts_result.duration
                }
                ta_result = ta.schedule_complex_task(ld_dict, ts_dict)
                self.results["ta"] = ta_result.to_dict()
                self._print_success(f"Complex task scheduled with {len(ta_result.subtasks)} subtasks")
                print(f"  🆔 Parent ID: {ta_result.id}")
                print(f"  📋 Subtasks:")
                for i, subtask in enumerate(ta_result.subtasks, 1):
                    print(f"     {i}. {subtask.title}")
                    print(f"        Slot: {subtask.slot[0]} → {subtask.slot[1]}")
                    print(f"        ID: {subtask.id}")
            else:
                self._print_warning("Cannot schedule: missing TD or LD output")
                self.results["ta"] = None
                
        except Exception as e:
            self._print_error(f"TA failed: {e}")
            self.results["ta"] = None
        
        # Step 8: Event Creator Agent
        self._print_step_header(8, "Event Creator Agent", "EC")
        ec_result = None
        try:
            ec = EventCreatorAgent(db_path=self.db_path)
            
            if ta_result:
                ta_dict = ta_result.to_dict()
                
                if ta_dict.get("type") == "simple":
                    create_result = ec.create_simple_task(ta_dict)
                    if create_result.success:
                        ec_result = {
                            "success": True,
                            "type": "simple",
                            "task_id": create_result.task_id,
                            "calendar_event_id": create_result.calendar_event_id
                        }
                        self._print_success("Simple task event created")
                        print(f"  🆔 Task ID: {create_result.task_id}")
                        print(f"  📅 Calendar Event ID: {create_result.calendar_event_id}")
                    else:
                        ec_result = {"success": False, "error": create_result.error}
                        self._print_error(f"Event creation failed: {create_result.error}")
                
                elif ta_dict.get("type") == "complex":
                    create_result = ec.create_complex_task(ta_dict)
                    ec_result = {
                        "success": create_result["success"],
                        "type": "complex",
                        "created": create_result.get("created", []),
                        "failed": create_result.get("failed", [])
                    }
                    if create_result["success"]:
                        self._print_success(f"Created {len(create_result['created'])} subtask events")
                        for item in create_result["created"]:
                            print(f"  📅 Task {item['task_id']}: Event {item['calendar_event_id']}")
                    else:
                        self._print_warning(f"Partial failure: {len(create_result.get('failed', []))} failed")
                        for item in create_result.get("failed", []):
                            print(f"  ❌ Task {item['task_id']}: {item.get('error', 'Unknown error')}")
            else:
                self._print_warning("Cannot create events: missing TA output")
                ec_result = None
                
        except Exception as e:
            self._print_error(f"EC failed: {e}")
            ec_result = None
        
        self.results["ec"] = ec_result
        
        # Final Summary
        self._print_summary()
        
        return {
            "success": ec_result is not None and (ec_result.get("success") if isinstance(ec_result, dict) else False),
            "results": self.results,
            "errors": self.errors
        }
    
    def _print_summary(self):
        """Print final summary"""
        print("\n" + "=" * 80)
        print("📊 PIPELINE SUMMARY")
        print("=" * 80)
        
        # Check each step
        steps = [
            ("UQ", "User Query Handler", self.results.get("uq")),
            ("SE", "Slot Extractor", self.results.get("se")),
            ("AR", "Absolute Resolver", self.results.get("ar")),
            ("TS", "Time Standardizer", self.results.get("ts")),
            ("TD", "Task Difficulty Analyzer", self.results.get("td")),
            ("LD", "LLM Decomposer", self.results.get("ld")),
            ("TA", "Time Allotment Agent", self.results.get("ta")),
            ("EC", "Event Creator Agent", self.results.get("ec")),
        ]
        
        for abbr, name, result in steps:
            if result is not None:
                print(f"✅ {abbr}: {name}")
            else:
                print(f"⚠️  {abbr}: {name} (skipped or failed)")
        
        # Final result
        ec_result = self.results.get("ec")
        if ec_result and isinstance(ec_result, dict) and ec_result.get("success"):
            print("\n" + "🎉 SUCCESS: Calendar events created!")
            if ec_result.get("type") == "simple":
                print(f"   📅 Event ID: {ec_result.get('calendar_event_id')}")
            else:
                print(f"   📅 Created {len(ec_result.get('created', []))} events")
        else:
            print("\n" + "❌ FAILED: Could not create calendar events")
            if self.errors:
                print("   Errors:")
                for error in self.errors:
                    print(f"     • {error}")
        
        print("=" * 80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Streamlined Agents - Process natural language queries and create calendar events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Call mom tomorrow at 2pm for 30 minutes"
  %(prog)s "Plan a 5-day Japan trip by Nov 15"
  %(prog)s --interactive
  %(prog)s --query "Review project proposal next Monday for 1 hour" --timezone "America/Los_Angeles"
        """
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="Natural language query to process"
    )
    
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode (prompt for queries)"
    )
    
    parser.add_argument(
        "--timezone",
        "-t",
        default="America/New_York",
        help="Timezone for processing (default: America/New_York)"
    )
    
    parser.add_argument(
        "--db-path",
        "-d",
        help="Path to Event Creator database (default: event_creator.db in Streamlined_Agents/)"
    )
    
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output final result as JSON"
    )
    
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all events in the database"
    )
    
    parser.add_argument(
        "--delete",
        "-D",
        metavar="TASK_ID",
        help="Delete a task by ID (cascade if parent)"
    )
    
    parser.add_argument(
        "--delete-parent",
        metavar="PARENT_ID",
        help="Delete all children of a parent task by parent ID"
    )
    
    parser.add_argument(
        "--delete-all",
        action="store_true",
        help="Delete all events from both the database and calendar (WARNING: This cannot be undone!)"
    )
    
    args = parser.parse_args()
    
    # List events mode
    if args.list:
        from event_creator_agent import EventCreatorAgent
        agent = EventCreatorAgent(db_path=args.db_path)
        events = agent.list_events()
        
        if not events:
            print("📭 No events found in the database")
            return
        
        print("\n" + "=" * 80)
        print("📋 EVENTS IN DATABASE")
        print("=" * 80)
        print(f"Total: {len(events)} event(s)\n")
        
        # Group by parent tasks
        parent_tasks = [e for e in events if e["type"] == "parent"]
        simple_tasks = [e for e in events if e["type"] == "simple"]
        subtasks = [e for e in events if e["type"] == "subtask"]
        
        # Print parent tasks with their children
        for parent in parent_tasks:
            print(f"📁 PARENT: {parent['title']}")
            print(f"   ID: {parent['task_id']}")
            print(f"   Children: {parent['child_count']}")
            print(f"   Has Event: {'No' if not parent['has_event'] else 'Yes (parent tasks have no calendar events)'}")
            print()
            
            # Print children
            children = [e for e in subtasks if e['parent_id'] == parent['task_id']]
            for i, child in enumerate(children, 1):
                print(f"   └─ {i}. {child['title']}")
                print(f"      ID: {child['task_id']}")
                if child['has_event']:
                    print(f"      Calendar Event ID: {child['calendar_event_id']}")
                    print(f"      Calendar ID: {child['calendar_id']}")
                else:
                    print(f"      Calendar Event: None")
                print()
        
        # Print simple tasks
        for task in simple_tasks:
            print(f"📝 SIMPLE: {task['title']}")
            print(f"   ID: {task['task_id']}")
            if task['has_event']:
                print(f"   Calendar Event ID: {task['calendar_event_id']}")
                print(f"   Calendar ID: {task['calendar_id']}")
            else:
                print(f"   Calendar Event: None")
            print()
        
        # Print orphaned subtasks (if any)
        orphaned = [e for e in subtasks if e['parent_id'] not in [p['task_id'] for p in parent_tasks]]
        if orphaned:
            print("⚠️  ORPHANED SUBTASKS (parent not found):")
            for task in orphaned:
                print(f"   • {task['title']} (ID: {task['task_id']}, Parent: {task['parent_id']})")
            print()
        
        if args.json:
            print("\n" + "=" * 80)
            print("📄 JSON OUTPUT")
            print("=" * 80)
            print(json.dumps(events, indent=2, default=str))
        
        return
    
    # Delete by ID mode
    if args.delete:
        from event_creator_agent import EventCreatorAgent
        agent = EventCreatorAgent(db_path=args.db_path)
        
        print("\n" + "=" * 80)
        print(f"🗑️  DELETING TASK: {args.delete}")
        print("=" * 80)
        
        result = agent.delete_by_id(args.delete)
        
        if result.deleted:
            print(f"✅ Successfully deleted {len(result.deleted)} task(s):")
            for item in result.deleted:
                print(f"   • Task ID: {item['task_id']}")
                if item.get('calendar_event_id'):
                    print(f"     Calendar Event ID: {item['calendar_event_id']}")
        
        if result.skipped:
            print(f"⚠️  Skipped {len(result.skipped)} task(s):")
            for item in result.skipped:
                print(f"   • Task ID: {item['task_id']}")
                print(f"     Reason: {item.get('reason', 'Unknown')}")
        
        if result.errors:
            print(f"❌ Errors deleting {len(result.errors)} task(s):")
            for item in result.errors:
                print(f"   • Task ID: {item['task_id']}")
                print(f"     Error: {item.get('reason', 'Unknown error')}")
        
        if not result.deleted and not result.skipped and not result.errors:
            print("⚠️  No tasks found to delete")
        
        if args.json:
            print("\n" + "=" * 80)
            print("📄 JSON OUTPUT")
            print("=" * 80)
            print(json.dumps(result.to_dict(), indent=2, default=str))
        
        return
    
    # Delete by parent ID mode
    if args.delete_parent:
        from event_creator_agent import EventCreatorAgent
        agent = EventCreatorAgent(db_path=args.db_path)
        
        print("\n" + "=" * 80)
        print(f"🗑️  DELETING CHILDREN OF PARENT: {args.delete_parent}")
        print("=" * 80)
        
        result = agent.delete_by_parent_id(args.delete_parent)
        
        if result.deleted:
            print(f"✅ Successfully deleted {len(result.deleted)} subtask(s):")
            for item in result.deleted:
                print(f"   • Task ID: {item['task_id']}")
                if item.get('calendar_event_id'):
                    print(f"     Calendar Event ID: {item['calendar_event_id']}")
            print(f"   Parent task also deleted")
        
        if result.skipped:
            print(f"⚠️  Skipped {len(result.skipped)} task(s):")
            for item in result.skipped:
                print(f"   • Task ID: {item['task_id']}")
                print(f"     Reason: {item.get('reason', 'Unknown')}")
        
        if result.errors:
            print(f"❌ Errors deleting {len(result.errors)} task(s):")
            for item in result.errors:
                print(f"   • Task ID: {item['task_id']}")
                print(f"     Error: {item.get('reason', 'Unknown error')}")
        
        if not result.deleted and not result.skipped and not result.errors:
            print("⚠️  No tasks found to delete")
        
        if args.json:
            print("\n" + "=" * 80)
            print("📄 JSON OUTPUT")
            print("=" * 80)
            print(json.dumps(result.to_dict(), indent=2, default=str))
        
        return
    
    # Delete all events mode
    if args.delete_all:
        from event_creator_agent import EventCreatorAgent
        agent = EventCreatorAgent(db_path=args.db_path)
        
        # Get confirmation
        print("\n" + "=" * 80)
        print("⚠️  WARNING: DELETE ALL EVENTS")
        print("=" * 80)
        print("This will delete ALL events from:")
        print("  1. The calendar (via CalBridge API)")
        print("  2. The database (tasks and event_map tables)")
        print("\nThis action CANNOT be undone!")
        print("=" * 80)
        
        # List current events
        events = agent.list_events()
        if events:
            print(f"\n📋 Current events in database: {len(events)}")
            print("\nEvents to be deleted:")
            for event in events:
                if event["has_event"]:
                    print(f"   • {event['title']} (ID: {event['task_id']}, Event: {event['calendar_event_id']})")
                else:
                    print(f"   • {event['title']} (ID: {event['task_id']}, No calendar event)")
        else:
            print("\n📭 No events found in database")
            return
        
        # Ask for confirmation
        confirm = input("\nAre you sure you want to delete ALL events? (type 'yes' to confirm): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Operation cancelled")
            return
        
        print("\n" + "=" * 80)
        print("🗑️  DELETING ALL EVENTS")
        print("=" * 80)
        
        result = agent.delete_all_events()
        
        if result.deleted:
            print(f"\n✅ Successfully deleted {len(result.deleted)} calendar event(s):")
            for item in result.deleted:
                print(f"   • Task ID: {item['task_id']}")
                if item.get('calendar_event_id'):
                    print(f"     Calendar Event ID: {item['calendar_event_id']}")
        
        if result.skipped:
            print(f"\n⚠️  Skipped {len(result.skipped)} event(s) (already deleted):")
            for item in result.skipped:
                print(f"   • Task ID: {item['task_id']}")
        
        if result.errors:
            print(f"\n❌ Errors deleting {len(result.errors)} event(s):")
            for item in result.errors:
                print(f"   • Task ID: {item.get('task_id', 'Unknown')}")
                print(f"     Error: {item.get('reason', 'Unknown error')}")
        
        print("\n✅ All database entries have been deleted")
        print("=" * 80)
        
        # Verify database is empty
        remaining_events = agent.list_events()
        if remaining_events:
            print(f"\n⚠️  Warning: {len(remaining_events)} event(s) still remain in database")
        else:
            print("\n✅ Database is now empty")
        
        if args.json:
            print("\n" + "=" * 80)
            print("📄 JSON OUTPUT")
            print("=" * 80)
            print(json.dumps(result.to_dict(), indent=2, default=str))
        
        return
    
    # Interactive mode
    if args.interactive:
        print("🚀 Streamlined Agents - Interactive Mode")
        print("Enter queries (or 'quit' to exit):\n")
        
        orchestrator = PipelineOrchestrator(db_path=args.db_path)
        
        while True:
            try:
                query = input("📝 Query: ").strip()
                if not query or query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                orchestrator.run_pipeline(query, args.timezone)
                print("\n" + "-" * 80 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
        
        return
    
    # Single query mode
    if not args.query and not args.list and not args.delete and not args.delete_parent and not args.delete_all:
        parser.print_help()
        sys.exit(1)
    
    if not args.query:
        # If no query but other flags were provided, they should have been handled above
        # This is a fallback
        sys.exit(0)
    
    orchestrator = PipelineOrchestrator(db_path=args.db_path)
    result = orchestrator.run_pipeline(args.query, args.timezone)
    
    if args.json:
        print("\n" + "=" * 80)
        print("📄 JSON OUTPUT")
        print("=" * 80)
        print(json.dumps(result, indent=2, default=str))
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()

