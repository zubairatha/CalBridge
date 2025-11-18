"""
Full pipeline integration test with Time Allotment Agent

Tests the complete flow: UQ → SE → AR → TS → TD → LD → TA
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from user_query import UserQueryHandler
from slot_extractor import SlotExtractor
from absolute_resolver import AbsoluteResolver
from time_standardizer import TimeStandardizer
from task_difficulty_analyzer import TaskDifficultyAnalyzer
from llm_decomposer import LLMDecomposer
from time_allotment_agent import TimeAllotmentAgent


def run_full_pipeline(query: str, verbose: bool = True):
    """
    Run the full pipeline from user query to scheduled tasks
    
    Returns:
        dict with all intermediate outputs and final scheduled result
    """
    if verbose:
        print("\n" + "=" * 80)
        print(f"FULL PIPELINE TEST: {query}")
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
            # Simple task path - need to convert to dict format
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
            # Complex task path - need to convert to dict format
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
    
    return results


def test_simple_task_pipeline():
    """Test full pipeline with a simple task"""
    print("\n" + "=" * 80)
    print("TEST: Simple Task Full Pipeline")
    print("=" * 80)
    
    query = "Call mom tomorrow at 2pm for 30 minutes"
    results = run_full_pipeline(query, verbose=True)
    
    # Validate final output
    ta_result = results.get("ta")
    if ta_result:
        assert ta_result["type"] == "simple", "Should be simple task"
        assert ta_result["parent_id"] is None, "Parent ID should be null"
        assert "slot" in ta_result, "Should have slot"
        assert len(ta_result["slot"]) == 2, "Slot should have [start, end]"
        print("\n✅ Simple task pipeline completed successfully!")
        return True
    else:
        print("\n❌ Simple task pipeline failed")
        return False


def test_complex_task_pipeline():
    """Test full pipeline with a complex task"""
    print("\n" + "=" * 80)
    print("TEST: Complex Task Full Pipeline")
    print("=" * 80)
    
    query = "Plan a 5-day Japan trip by Nov 15"
    results = run_full_pipeline(query, verbose=True)
    
    # Validate final output
    ta_result = results.get("ta")
    if ta_result:
        assert ta_result["type"] == "complex", "Should be complex task"
        assert ta_result["parent_id"] is None, "Parent ID should be null"
        assert "subtasks" in ta_result, "Should have subtasks"
        assert len(ta_result["subtasks"]) >= 2, "Should have at least 2 subtasks"
        
        # Validate subtask parent_id relationships
        parent_id = ta_result["id"]
        for subtask in ta_result["subtasks"]:
            assert subtask["parent_id"] == parent_id, "Subtask parent_id should match parent"
            assert "slot" in subtask, "Subtask should have slot"
        
        print("\n✅ Complex task pipeline completed successfully!")
        return True
    else:
        print("\n❌ Complex task pipeline failed")
        if "ta_error" in results:
            print(f"   Error: {results['ta_error']}")
        return False


def test_multiple_queries():
    """Test multiple queries"""
    print("\n" + "=" * 80)
    print("TEST: Multiple Queries")
    print("=" * 80)
    
    queries = [
        "Call mom tomorrow at 2pm for 30 minutes",
        "Plan a 5-day Japan trip next week",
        "Review project proposal next Monday for 1 hour",
    ]
    
    results = []
    for query in queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print('='*80)
        result = run_full_pipeline(query, verbose=False)
        results.append((query, result.get("ta") is not None))
        
        if result.get("ta"):
            ta_result = result["ta"]
            print(f"   ✅ Scheduled: {ta_result['type']} task")
            if ta_result["type"] == "complex":
                print(f"      {len(ta_result['subtasks'])} subtasks")
        else:
            print(f"   ❌ Failed to schedule")
    
    passed = sum(1 for _, success in results if success)
    print(f"\n✅ {passed}/{len(queries)} queries scheduled successfully")
    
    return passed == len(queries)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Time Allotment Agent with full pipeline")
    parser.add_argument("--test", choices=["simple", "complex", "multiple", "all"],
                       default="all", help="Which test to run")
    parser.add_argument("--query", type=str, help="Custom query to test (overrides --test)")
    
    args = parser.parse_args()
    
    # If custom query provided, run it directly
    if args.query:
        print("\n" + "=" * 80)
        print("CUSTOM QUERY TEST")
        print("=" * 80)
        result = run_full_pipeline(args.query, verbose=True)
        
        ta_result = result.get("ta")
        if ta_result:
            print("\n" + "=" * 80)
            print("✅ Custom query scheduled successfully!")
            print("=" * 80)
            print("\n📋 TA Agent Output (JSON):")
            print(json.dumps(ta_result, indent=2))
            print("\n" + "=" * 80)
            sys.exit(0)
        else:
            print("\n❌ Custom query failed to schedule")
            if "ta_error" in result:
                print(f"   Error: {result['ta_error']}")
            sys.exit(1)
    
    # Otherwise run standard tests
    success = True
    
    if args.test == "simple":
        success = test_simple_task_pipeline()
    elif args.test == "complex":
        success = test_complex_task_pipeline()
    elif args.test == "multiple":
        success = test_multiple_queries()
    else:
        success = test_simple_task_pipeline() and test_complex_task_pipeline()
    
    sys.exit(0 if success else 1)

