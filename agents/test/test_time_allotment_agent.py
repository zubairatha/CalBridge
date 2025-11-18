"""
Comprehensive tests for Time Allotment Agent

Tests both simple and complex task scheduling paths
"""
import sys
import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from time_allotment_agent import TimeAllotmentAgent, ScheduledSimpleTask, ScheduledComplexTask


def get_test_calendar():
    """Get a test calendar ID from CalBridge"""
    try:
        response = requests.get("http://127.0.0.1:8765/calendars", timeout=10)
        response.raise_for_status()
        calendars = response.json()
        if calendars:
            return calendars[0]["id"]
    except Exception as e:
        print(f"⚠️  Could not fetch calendar: {e}")
    return None


def test_iso8601_conversion():
    """Test ISO-8601 duration to minutes conversion"""
    print("\n" + "=" * 60)
    print("TEST: ISO-8601 Duration Conversion")
    print("=" * 60)
    
    agent = TimeAllotmentAgent()
    
    test_cases = [
        ("PT30M", 30),
        ("PT1H", 60),
        ("PT1H30M", 90),
        ("PT2H", 120),
        ("PT2H30M", 150),
        ("PT3H", 180),
    ]
    
    all_passed = True
    for duration, expected_minutes in test_cases:
        result = agent._iso8601_to_minutes(duration)
        if result == expected_minutes:
            print(f"✅ {duration:10} → {result:3} minutes (expected {expected_minutes})")
        else:
            print(f"❌ {duration:10} → {result:3} minutes (expected {expected_minutes})")
            all_passed = False
    
    return all_passed


def test_simple_task_scheduling():
    """Test simple task scheduling"""
    print("\n" + "=" * 60)
    print("TEST: Simple Task Scheduling")
    print("=" * 60)
    
    calendar_id = get_test_calendar()
    if not calendar_id:
        print("⚠️  Skipping: No calendar available")
        return False
    
    agent = TimeAllotmentAgent()
    
    # Create test window (1 hour from now, 2 days span)
    now = datetime.now().astimezone()
    window_start = (now + timedelta(hours=1)).isoformat()
    window_end = (now + timedelta(days=2)).isoformat()
    
    td_output = {
        "calendar": calendar_id,
        "type": "simple",
        "title": "Call mom",
        "duration": "PT30M"
    }
    
    ts_output = {
        "start": window_start,
        "end": window_end,
        "duration": "PT30M"
    }
    
    try:
        result = agent.schedule_simple_task(td_output, ts_output)
        
        # Validate output structure
        assert result.type == "simple", "Type should be 'simple'"
        assert result.calendar == calendar_id, "Calendar ID should match"
        assert result.title == "Call mom", "Title should match"
        assert result.parent_id is None, "Parent ID should be null for simple tasks"
        assert result.id is not None, "ID should be generated"
        assert len(result.slot) == 2, "Slot should have [start, end]"
        
        # Validate slot times
        slot_start = datetime.fromisoformat(result.slot[0].replace('Z', '+00:00'))
        slot_end = datetime.fromisoformat(result.slot[1].replace('Z', '+00:00'))
        window_start_dt = datetime.fromisoformat(window_start.replace('Z', '+00:00'))
        window_end_dt = datetime.fromisoformat(window_end.replace('Z', '+00:00'))
        
        assert slot_start >= window_start_dt, "Slot should start within window"
        assert slot_end <= window_end_dt, "Slot should end within window"
        
        duration_min = int((slot_end - slot_start).total_seconds() / 60)
        assert duration_min == 30, f"Duration should be 30 minutes, got {duration_min}"
        
        print("✅ Simple task scheduled successfully")
        print(f"   ID: {result.id}")
        print(f"   Slot: {result.slot[0]} → {result.slot[1]}")
        print(f"   Duration: {duration_min} minutes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_task_default_duration():
    """Test simple task with default duration (when TS.duration is null)"""
    print("\n" + "=" * 60)
    print("TEST: Simple Task with Default Duration")
    print("=" * 60)
    
    calendar_id = get_test_calendar()
    if not calendar_id:
        print("⚠️  Skipping: No calendar available")
        return False
    
    agent = TimeAllotmentAgent()
    
    now = datetime.now().astimezone()
    window_start = (now + timedelta(hours=1)).isoformat()
    window_end = (now + timedelta(days=2)).isoformat()
    
    td_output = {
        "calendar": calendar_id,
        "type": "simple",
        "title": "Quick check-in",
        "duration": None  # No duration specified
    }
    
    ts_output = {
        "start": window_start,
        "end": window_end,
        "duration": None  # No duration specified
    }
    
    try:
        result = agent.schedule_simple_task(td_output, ts_output)
        
        slot_start = datetime.fromisoformat(result.slot[0].replace('Z', '+00:00'))
        slot_end = datetime.fromisoformat(result.slot[1].replace('Z', '+00:00'))
        duration_min = int((slot_end - slot_start).total_seconds() / 60)
        
        assert duration_min == 30, f"Should use default duration (30 min), got {duration_min}"
        
        print("✅ Default duration (PT30M) applied correctly")
        print(f"   Duration: {duration_min} minutes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_complex_task_scheduling():
    """Test complex task scheduling with subtasks"""
    print("\n" + "=" * 60)
    print("TEST: Complex Task Scheduling")
    print("=" * 60)
    
    calendar_id = get_test_calendar()
    if not calendar_id:
        print("⚠️  Skipping: No calendar available")
        return False
    
    agent = TimeAllotmentAgent()
    
    now = datetime.now().astimezone()
    window_start = (now + timedelta(hours=1)).isoformat()
    window_end = (now + timedelta(days=3)).isoformat()
    
    ld_output = {
        "calendar": calendar_id,
        "type": "complex",
        "title": "Plan 5-day Japan trip",
        "subtasks": [
            {"title": "List must-see cities and dates (Japan trip)", "duration": "PT1H"},
            {"title": "Compare flights and book (Japan trip)", "duration": "PT1H30M"},
            {"title": "Book hotels for each city (Japan trip)", "duration": "PT2H"}
        ]
    }
    
    ts_output = {
        "start": window_start,
        "end": window_end,
        "duration": None
    }
    
    try:
        result = agent.schedule_complex_task(ld_output, ts_output)
        
        # Validate output structure
        assert result.type == "complex", "Type should be 'complex'"
        assert result.calendar == calendar_id, "Calendar ID should match"
        assert result.title == "Plan 5-day Japan trip", "Title should match"
        assert result.parent_id is None, "Parent ID should be null for parent task"
        assert result.id is not None, "Parent ID should be generated"
        assert len(result.subtasks) == 3, "Should have 3 subtasks"
        
        # Validate subtasks
        for i, subtask in enumerate(result.subtasks):
            assert subtask.parent_id == result.id, f"Subtask {i+1} parent_id should match parent ID"
            assert subtask.id is not None, f"Subtask {i+1} should have an ID"
            assert len(subtask.slot) == 2, f"Subtask {i+1} should have [start, end]"
            
            # Validate slot times
            slot_start = datetime.fromisoformat(subtask.slot[0].replace('Z', '+00:00'))
            slot_end = datetime.fromisoformat(subtask.slot[1].replace('Z', '+00:00'))
            window_start_dt = datetime.fromisoformat(window_start.replace('Z', '+00:00'))
            window_end_dt = datetime.fromisoformat(window_end.replace('Z', '+00:00'))
            
            assert slot_start >= window_start_dt, f"Subtask {i+1} should start within window"
            assert slot_end <= window_end_dt, f"Subtask {i+1} should end within window"
        
        # Validate order (precedence)
        for i in range(1, len(result.subtasks)):
            prev_end = datetime.fromisoformat(result.subtasks[i-1].slot[1].replace('Z', '+00:00'))
            curr_start = datetime.fromisoformat(result.subtasks[i].slot[0].replace('Z', '+00:00'))
            assert curr_start >= prev_end, f"Subtask {i+1} should start after subtask {i} ends"
        
        print("✅ Complex task scheduled successfully")
        print(f"   Parent ID: {result.id}")
        print(f"   Number of subtasks: {len(result.subtasks)}")
        for i, subtask in enumerate(result.subtasks):
            print(f"   Subtask {i+1}: {subtask.slot[0]} → {subtask.slot[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation_errors():
    """Test validation error handling"""
    print("\n" + "=" * 60)
    print("TEST: Validation Error Handling")
    print("=" * 60)
    
    agent = TimeAllotmentAgent()
    
    # Test invalid type
    try:
        td_invalid = {
            "calendar": "test_cal",
            "type": "complex",  # Wrong type for simple task
            "title": "Test",
            "duration": "PT30M"
        }
        ts_output = {
            "start": (datetime.now() + timedelta(hours=1)).isoformat(),
            "end": (datetime.now() + timedelta(days=1)).isoformat(),
            "duration": "PT30M"
        }
        agent.schedule_simple_task(td_invalid, ts_output)
        print("❌ Should have raised ValueError for invalid type")
        return False
    except ValueError:
        print("✅ Correctly rejected invalid type")
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return False
    
    # Test missing calendar
    try:
        td_no_calendar = {
            "calendar": None,
            "type": "simple",
            "title": "Test",
            "duration": "PT30M"
        }
        ts_output = {
            "start": (datetime.now() + timedelta(hours=1)).isoformat(),
            "end": (datetime.now() + timedelta(days=1)).isoformat(),
            "duration": "PT30M"
        }
        agent.schedule_simple_task(td_no_calendar, ts_output)
        print("❌ Should have raised ValueError for missing calendar")
        return False
    except ValueError:
        print("✅ Correctly rejected missing calendar")
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return False
    
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TIME ALLOTMENT AGENT - COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    results = []
    
    results.append(("ISO-8601 Conversion", test_iso8601_conversion()))
    results.append(("Simple Task Scheduling", test_simple_task_scheduling()))
    results.append(("Simple Task Default Duration", test_simple_task_default_duration()))
    results.append(("Complex Task Scheduling", test_complex_task_scheduling()))
    results.append(("Validation Errors", test_validation_errors()))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Time Allotment Agent")
    parser.add_argument("--test", choices=["iso", "simple", "simple-default", "complex", "validation", "all"],
                       default="all", help="Which test to run")
    
    args = parser.parse_args()
    
    if args.test == "iso":
        test_iso8601_conversion()
    elif args.test == "simple":
        test_simple_task_scheduling()
    elif args.test == "simple-default":
        test_simple_task_default_duration()
    elif args.test == "complex":
        test_complex_task_scheduling()
    elif args.test == "validation":
        test_validation_errors()
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)

