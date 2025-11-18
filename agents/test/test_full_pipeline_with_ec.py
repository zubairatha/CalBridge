"""
Full pipeline integration test with Event Creator Agent

Tests the complete flow: UQ → SE → AR → TS → TD → LD → TA → EC
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from user_query import UserQueryHandler
from slot_extractor import SlotExtractor
from absolute_resolver import AbsoluteResolver
from time_standardizer import TimeStandardizer
from task_difficulty_analyzer import TaskDifficultyAnalyzer
from llm_decomposer import LLMDecomposer
from time_allotment_agent import TimeAllotmentAgent
from event_creator_agent import EventCreatorAgent


def run_full_pipeline_with_ec(query: str, verbose: bool = True, db_path: str = None):
    """
    Run the full pipeline from user query to calendar events
    
    Returns:
        dict with all intermediate outputs and final event creation result
    """
    if verbose:
        print("\n" + "=" * 80)
        print(f"FULL PIPELINE TEST WITH EC: {query}")
        print("=" * 80)
    
    results = {}
    
    # Step 1: User Query Handler
    if verbose:
        print("\n[Step 1] User Query Handler (UQ)")
    uq = UserQueryHandler(default_timezone="America/New_York")
    uq_result = uq.process_query(query)
    results["uq"] = {
        "query": uq_result.query,
        "timezone": uq_result.timezone
    }
    if verbose:
        print(f"   Query: {uq_result.query}")
        print(f"   Timezone: {uq_result.timezone}")
    
    # Step 2: Slot Extractor
    if verbose:
        print("\n[Step 2] Slot Extractor (SE)")
    se = SlotExtractor()
    se_result = se.extract_slots_safe(uq_result.query, uq_result.timezone)
    results["se"] = {
        "start_text": se_result.start_text if se_result else None,
        "end_text": se_result.end_text if se_result else None,
        "duration": se_result.duration if se_result else None
    }
    if verbose:
        print(f"   Start text: {se_result.start_text if se_result else None}")
        print(f"   End text: {se_result.end_text if se_result else None}")
        print(f"   Duration: {se_result.duration if se_result else None}")
    
    # Step 3: Absolute Resolver
    if verbose:
        print("\n[Step 3] Absolute Resolver (AR)")
    from context_provider import ContextProvider
    context_provider = ContextProvider(timezone=uq_result.timezone)
    context = context_provider.get_context()
    ar = AbsoluteResolver()
    se_dict = se_result.to_dict() if se_result else None
    ar_result = ar.resolve_absolute_safe(se_dict, context) if se_result else None
    results["ar"] = {
        "start_text": ar_result.start_text if ar_result else None,
        "end_text": ar_result.end_text if ar_result else None,
        "duration": ar_result.duration if ar_result else None
    }
    if verbose:
        print(f"   Start: {ar_result.start_text if ar_result else None}")
        print(f"   End: {ar_result.end_text if ar_result else None}")
        print(f"   Duration: {ar_result.duration if ar_result else None}")
    
    # Step 4: Time Standardizer
    if verbose:
        print("\n[Step 4] Time Standardizer (TS)")
    ts = TimeStandardizer()
    ar_dict = ar_result.to_dict() if ar_result else None
    ts_result = ts.standardize_safe(ar_dict, uq_result.timezone) if ar_result else None
    results["ts"] = {
        "start": ts_result.start if ts_result else None,
        "end": ts_result.end if ts_result else None,
        "duration": ts_result.duration if ts_result else None
    }
    if verbose:
        print(f"   Start (ISO): {ts_result.start if ts_result else None}")
        print(f"   End (ISO): {ts_result.end if ts_result else None}")
        print(f"   Duration: {ts_result.duration if ts_result else None}")
    
    # Step 5: Task Difficulty Analyzer
    if verbose:
        print("\n[Step 5] Task Difficulty Analyzer (TD)")
    td = TaskDifficultyAnalyzer()
    ts_dict = ts_result.to_dict() if ts_result else None
    td_result = td.analyze_safe(uq_result.query, ts_dict.get("duration") if ts_dict else None) if ts_result else None
    results["td"] = td_result.to_dict() if td_result else None
    if verbose:
        if td_result:
            print(f"   Type: {td_result.type}")
            print(f"   Calendar: {td_result.calendar}")
            print(f"   Title: {td_result.title}")
            print(f"   Duration: {td_result.duration}")
        else:
            print("   ⚠️  TD analysis failed")
    
    # Step 6: LLM Decomposer (only for complex tasks)
    if verbose:
        print("\n[Step 6] LLM Decomposer (LD)")
    ld_result = None
    if td_result and td_result.type == "complex":
        ld = LLMDecomposer()
        td_dict = td_result.to_dict()  # Convert Pydantic object to dict
        ld_result = ld.decompose_safe(td_dict)
        results["ld"] = ld_result.to_dict() if ld_result else None
        if verbose:
            if ld_result:
                print(f"   Type: {ld_result.type}")
                print(f"   Subtasks: {len(ld_result.subtasks)}")
                for i, subtask in enumerate(ld_result.subtasks, 1):
                    print(f"      {i}. {subtask.title} ({subtask.duration})")
            else:
                print("   ⚠️  Decomposition failed")
    else:
        if verbose:
            print("   Skipped (simple task)")
    
    # Step 7: Time Allotment Agent
    if verbose:
        print("\n[Step 7] Time Allotment Agent (TA)")
    ta = TimeAllotmentAgent()
    ta_result = None
    
    try:
        if td_result and td_result.type == "simple":
            # Simple task path
            td_dict = td_result.to_dict()
            ts_dict = {
                "start": ts_result.start,
                "end": ts_result.end,
                "duration": ts_result.duration
            }
            ta_result = ta.schedule_simple_task(td_dict, ts_dict)
            results["ta"] = ta_result.to_dict()
            if verbose:
                print(f"   ✅ Scheduled simple task")
                print(f"   ID: {ta_result.id}")
                print(f"   Slot: {ta_result.slot[0]} → {ta_result.slot[1]}")
        
        elif ld_result and ld_result.type == "complex":
            # Complex task path
            ld_dict = ld_result.to_dict()
            ts_dict = {
                "start": ts_result.start,
                "end": ts_result.end,
                "duration": ts_result.duration
            }
            ta_result = ta.schedule_complex_task(ld_dict, ts_dict)
            results["ta"] = ta_result.to_dict()
            if verbose:
                print(f"   ✅ Scheduled complex task with {len(ta_result.subtasks)} subtasks")
                print(f"   Parent ID: {ta_result.id}")
                for i, subtask in enumerate(ta_result.subtasks, 1):
                    print(f"   Subtask {i}: {subtask.slot[0]} → {subtask.slot[1]}")
        else:
            if verbose:
                print("   ⚠️  Cannot schedule: missing TD or LD output")
    
    except Exception as e:
        if verbose:
            print(f"   ❌ Scheduling failed: {e}")
        results["ta_error"] = str(e)
    
    # Step 8: Event Creator Agent
    if verbose:
        print("\n[Step 8] Event Creator Agent (EC)")
    ec = EventCreatorAgent(db_path=db_path)
    ec_result = None
    
    try:
        if ta_result:
            ta_dict = ta_result.to_dict()
            
            if ta_dict.get("type") == "simple":
                # Create simple task event
                create_result = ec.create_simple_task(ta_dict)
                if create_result.success:
                    ec_result = {
                        "success": True,
                        "type": "simple",
                        "task_id": create_result.task_id,
                        "calendar_event_id": create_result.calendar_event_id
                    }
                    if verbose:
                        print(f"   ✅ Created simple task event")
                        print(f"   Task ID: {create_result.task_id}")
                        print(f"   Calendar Event ID: {create_result.calendar_event_id}")
                else:
                    ec_result = {
                        "success": False,
                        "error": create_result.error
                    }
                    if verbose:
                        print(f"   ❌ Failed to create event: {create_result.error}")
            
            elif ta_dict.get("type") == "complex":
                # Create complex task events (subtasks only)
                create_result = ec.create_complex_task(ta_dict)
                ec_result = {
                    "success": create_result["success"],
                    "type": "complex",
                    "created": create_result.get("created", []),
                    "failed": create_result.get("failed", [])
                }
                if verbose:
                    if create_result["success"]:
                        print(f"   ✅ Created {len(create_result['created'])} subtask events")
                        for item in create_result["created"]:
                            print(f"      - Task {item['task_id']}: Event {item['calendar_event_id']}")
                    else:
                        print(f"   ⚠️  Partial failure: {len(create_result.get('failed', []))} failed")
        else:
            if verbose:
                print("   ⚠️  Cannot create events: missing TA output")
    
    except Exception as e:
        if verbose:
            print(f"   ❌ Event creation failed: {e}")
        results["ec_error"] = str(e)
    
    results["ec"] = ec_result
    
    return results


def test_simple_task_full_pipeline():
    """Test full pipeline with simple task"""
    print("\n" + "=" * 80)
    print("TEST: Simple Task Full Pipeline with EC")
    print("=" * 80)
    
    query = "Call mom tomorrow at 2pm for 30 minutes"
    db_path = "test_full_pipeline_ec_simple.db"
    
    results = run_full_pipeline_with_ec(query, verbose=True, db_path=db_path)
    
    # Validate final output
    ec_result = results.get("ec")
    if ec_result and ec_result.get("success"):
        assert ec_result["type"] == "simple", "Should be simple task"
        assert "calendar_event_id" in ec_result, "Should have calendar event ID"
        print("\n✅ Simple task pipeline with EC completed successfully!")
        
        # Cleanup
        import os
        if os.path.exists(db_path):
            os.remove(db_path)
        return True
    else:
        print("\n❌ Simple task pipeline with EC failed")
        if "ec_error" in results:
            print(f"   Error: {results['ec_error']}")
        return False


def test_complex_task_full_pipeline():
    """Test full pipeline with complex task"""
    print("\n" + "=" * 80)
    print("TEST: Complex Task Full Pipeline with EC")
    print("=" * 80)
    
    query = "Plan a 5-day Japan trip by Nov 15"
    db_path = "test_full_pipeline_ec_complex.db"
    
    results = run_full_pipeline_with_ec(query, verbose=True, db_path=db_path)
    
    # Validate final output
    ec_result = results.get("ec")
    if ec_result and ec_result.get("success"):
        assert ec_result["type"] == "complex", "Should be complex task"
        assert len(ec_result.get("created", [])) > 0, "Should have created events"
        print("\n✅ Complex task pipeline with EC completed successfully!")
        
        # Cleanup
        import os
        if os.path.exists(db_path):
            os.remove(db_path)
        return True
    else:
        print("\n❌ Complex task pipeline with EC failed")
        if "ec_error" in results:
            print(f"   Error: {results['ec_error']}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Event Creator Agent with full pipeline")
    parser.add_argument("--test", choices=["simple", "complex", "all"],
                       default="all", help="Which test to run")
    parser.add_argument("--query", type=str, help="Custom query to test")
    
    args = parser.parse_args()
    
    if args.query:
        print("\n" + "=" * 80)
        print("CUSTOM QUERY TEST WITH EC")
        print("=" * 80)
        db_path = "test_custom_query_ec.db"
        result = run_full_pipeline_with_ec(args.query, verbose=True, db_path=db_path)
        
        ec_result = result.get("ec")
        if ec_result and ec_result.get("success"):
            print("\n" + "=" * 80)
            print("✅ Custom query completed successfully!")
            print("=" * 80)
            print("\n📋 EC Agent Output:")
            print(json.dumps(ec_result, indent=2))
            print("\n" + "=" * 80)
            sys.exit(0)
        else:
            print("\n❌ Custom query failed")
            sys.exit(1)
    
    success = True
    
    if args.test == "simple":
        success = test_simple_task_full_pipeline()
    elif args.test == "complex":
        success = test_complex_task_full_pipeline()
    else:
        success = test_simple_task_full_pipeline() and test_complex_task_full_pipeline()
    
    sys.exit(0 if success else 1)

