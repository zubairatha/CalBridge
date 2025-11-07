"""
Comprehensive tests for Event Creator Agent

Tests create and delete operations for simple and complex tasks
"""
import sys
import os
import json
import requests
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from event_creator_agent import EventCreatorAgent, CreateResult, DeleteResult


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


def is_calbridge_available():
    """Check if CalBridge is available"""
    try:
        response = requests.get("http://127.0.0.1:8765/status", timeout=2)
        return response.status_code == 200
    except:
        return False


def test_database_setup():
    """Test database initialization"""
    print("\n" + "=" * 60)
    print("TEST: Database Setup")
    print("=" * 60)
    
    db_path = "test_ec_db_setup.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    agent = EventCreatorAgent(db_path=db_path)
    
    # Check tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    assert "tasks" in tables, "tasks table should exist"
    assert "event_map" in tables, "event_map table should exist"
    
    print("✅ Database tables created correctly")
    
    os.remove(db_path)
    return True


def test_simple_task_validation():
    """Test simple task validation"""
    print("\n" + "=" * 60)
    print("TEST: Simple Task Validation")
    print("=" * 60)
    
    db_path = "test_ec_validation.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    agent = EventCreatorAgent(db_path=db_path)
    
    # Test invalid cases
    invalid_cases = [
        ({"type": "complex"}, "Wrong type"),
        ({"type": "simple"}, "Missing fields"),
        ({"type": "simple", "calendar": "test", "title": "Test", "slot": ["2025-11-07T14:00:00-05:00", "2025-11-07T14:00:00-05:00"], "id": "test", "parent_id": None}, "Invalid slot (start >= end)"),
        ({"type": "simple", "calendar": "test", "title": "Test", "slot": ["2025-11-07T14:00:00-05:00", "2025-11-07T14:30:00-05:00"], "id": "test", "parent_id": "not-null"}, "parent_id should be null"),
    ]
    
    all_passed = True
    for invalid_input, description in invalid_cases:
        result = agent.create_simple_task(invalid_input)
        if not result.success:
            print(f"✅ Correctly rejected: {description}")
        else:
            print(f"❌ Should have rejected: {description}")
            all_passed = False
    
    os.remove(db_path)
    return all_passed


def test_simple_task_creation():
    """Test simple task creation"""
    print("\n" + "=" * 60)
    print("TEST: Simple Task Creation")
    print("=" * 60)
    
    if not is_calbridge_available():
        print("⚠️  Skipping: CalBridge not available")
        return False
    
    calendar_id = get_test_calendar()
    if not calendar_id:
        print("⚠️  Skipping: No calendar available")
        return False
    
    db_path = "test_ec_simple.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    agent = EventCreatorAgent(db_path=db_path)
    
    now = datetime.now().astimezone()
    slot_start = (now + timedelta(days=1, hours=2)).isoformat()
    slot_end = (now + timedelta(days=1, hours=2, minutes=30)).isoformat()
    
    ta_output = {
        "calendar": calendar_id,
        "type": "simple",
        "title": "Test Simple Task",
        "slot": [slot_start, slot_end],
        "id": "test-simple-create",
        "parent_id": None
    }
    
    result = agent.create_simple_task(ta_output)
    
    if not result.success:
        print(f"❌ Failed to create: {result.error}")
        os.remove(db_path)
        return False
    
    print(f"✅ Simple task created")
    print(f"   Task ID: {result.task_id}")
    print(f"   Event ID: {result.calendar_event_id}")
    
    # Verify database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (result.task_id,))
    task = cursor.fetchone()
    assert task is not None, "Task should be in database"
    assert task[0] == result.task_id, "Task ID should match"
    assert task[1] == ta_output["title"], "Title should match"
    assert task[2] is None, "parent_id should be null"
    
    cursor.execute("SELECT * FROM event_map WHERE task_id = ?", (result.task_id,))
    event_map = cursor.fetchone()
    assert event_map is not None, "Event map should exist"
    assert event_map[0] == result.task_id, "Task ID should match"
    assert event_map[1] == calendar_id, "Calendar ID should match"
    assert event_map[2] == result.calendar_event_id, "Event ID should match"
    
    conn.close()
    print("✅ Database entries verified")
    
    os.remove(db_path)
    return True


def test_complex_task_creation():
    """Test complex task creation"""
    print("\n" + "=" * 60)
    print("TEST: Complex Task Creation")
    print("=" * 60)
    
    if not is_calbridge_available():
        print("⚠️  Skipping: CalBridge not available")
        return False
    
    calendar_id = get_test_calendar()
    if not calendar_id:
        print("⚠️  Skipping: No calendar available")
        return False
    
    db_path = "test_ec_complex.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    agent = EventCreatorAgent(db_path=db_path)
    
    now = datetime.now().astimezone()
    parent_id = "test-complex-parent"
    
    ta_output = {
        "calendar": calendar_id,
        "type": "complex",
        "title": "Test Complex Task",
        "id": parent_id,
        "parent_id": None,
        "subtasks": [
            {
                "title": "Subtask 1",
                "slot": [(now + timedelta(days=2, hours=10)).isoformat(), 
                        (now + timedelta(days=2, hours=11)).isoformat()],
                "id": "test-subtask-1",
                "parent_id": parent_id
            },
            {
                "title": "Subtask 2",
                "slot": [(now + timedelta(days=3, hours=10)).isoformat(), 
                        (now + timedelta(days=3, hours=11)).isoformat()],
                "id": "test-subtask-2",
                "parent_id": parent_id
            }
        ]
    }
    
    result = agent.create_complex_task(ta_output)
    
    if not result["success"]:
        print(f"❌ Failed to create: {result.get('error')}")
        os.remove(db_path)
        return False
    
    print(f"✅ Complex task created")
    print(f"   Created: {len(result['created'])} events")
    print(f"   Failed: {len(result['failed'])} events")
    
    assert len(result["created"]) == 2, "Should create 2 subtask events"
    assert len(result["failed"]) == 0, "Should not have failures"
    
    # Verify database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check parent (should exist, but no event_map)
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (parent_id,))
    parent = cursor.fetchone()
    assert parent is not None, "Parent task should be in database"
    assert parent[2] is None, "Parent parent_id should be null"
    
    cursor.execute("SELECT * FROM event_map WHERE task_id = ?", (parent_id,))
    parent_event_map = cursor.fetchone()
    assert parent_event_map is None, "Parent should not have event_map"
    
    # Check subtasks
    cursor.execute("SELECT * FROM tasks WHERE parent_id = ?", (parent_id,))
    subtasks = cursor.fetchall()
    assert len(subtasks) == 2, "Should have 2 subtasks in database"
    
    cursor.execute("SELECT COUNT(*) FROM event_map")
    event_map_count = cursor.fetchone()[0]
    assert event_map_count == 2, "Should have 2 event_map entries (for subtasks only)"
    
    conn.close()
    print("✅ Database entries verified")
    
    os.remove(db_path)
    return True


def test_delete_by_id():
    """Test delete by ID"""
    print("\n" + "=" * 60)
    print("TEST: Delete by ID")
    print("=" * 60)
    
    if not is_calbridge_available():
        print("⚠️  Skipping: CalBridge not available")
        return False
    
    calendar_id = get_test_calendar()
    if not calendar_id:
        print("⚠️  Skipping: No calendar available")
        return False
    
    db_path = "test_ec_delete.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    agent = EventCreatorAgent(db_path=db_path)
    
    # Create a simple task first
    now = datetime.now().astimezone()
    ta_output = {
        "calendar": calendar_id,
        "type": "simple",
        "title": "Test Delete Task",
        "slot": [(now + timedelta(days=4, hours=10)).isoformat(), 
                (now + timedelta(days=4, hours=10, minutes=30)).isoformat()],
        "id": "test-delete-id",
        "parent_id": None
    }
    
    create_result = agent.create_simple_task(ta_output)
    if not create_result.success:
        print(f"❌ Failed to create task for deletion test")
        os.remove(db_path)
        return False
    
    # Delete by ID
    delete_result = agent.delete_by_id("test-delete-id")
    
    assert len(delete_result.deleted) == 1, "Should delete 1 task"
    assert len(delete_result.skipped) == 0, "Should not skip"
    assert len(delete_result.errors) == 0, "Should not have errors"
    
    print(f"✅ Delete by ID successful")
    print(f"   Deleted: {len(delete_result.deleted)}")
    
    # Verify database is clean
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks")
    task_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM event_map")
    event_map_count = cursor.fetchone()[0]
    conn.close()
    
    assert task_count == 0, "Database should be clean"
    assert event_map_count == 0, "Event map should be clean"
    
    print("✅ Database cleaned correctly")
    
    os.remove(db_path)
    return True


def test_delete_by_parent_id():
    """Test delete by parent_id (cascade)"""
    print("\n" + "=" * 60)
    print("TEST: Delete by Parent ID")
    print("=" * 60)
    
    if not is_calbridge_available():
        print("⚠️  Skipping: CalBridge not available")
        return False
    
    calendar_id = get_test_calendar()
    if not calendar_id:
        print("⚠️  Skipping: No calendar available")
        return False
    
    db_path = "test_ec_delete_parent.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    agent = EventCreatorAgent(db_path=db_path)
    
    # Create a complex task
    now = datetime.now().astimezone()
    parent_id = "test-delete-parent"
    
    ta_output = {
        "calendar": calendar_id,
        "type": "complex",
        "title": "Test Delete Parent",
        "id": parent_id,
        "parent_id": None,
        "subtasks": [
            {
                "title": "Subtask for Delete",
                "slot": [(now + timedelta(days=5, hours=10)).isoformat(), 
                        (now + timedelta(days=5, hours=11)).isoformat()],
                "id": "test-delete-subtask",
                "parent_id": parent_id
            }
        ]
    }
    
    create_result = agent.create_complex_task(ta_output)
    if not create_result["success"]:
        print(f"❌ Failed to create task for deletion test")
        os.remove(db_path)
        return False
    
    # Delete by parent_id
    delete_result = agent.delete_by_parent_id(parent_id)
    
    assert len(delete_result.deleted) == 1, "Should delete 1 subtask"
    assert len(delete_result.skipped) == 0, "Should not skip"
    assert len(delete_result.errors) == 0, "Should not have errors"
    
    print(f"✅ Delete by parent_id successful")
    print(f"   Deleted: {len(delete_result.deleted)}")
    
    # Verify database is clean
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks")
    task_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM event_map")
    event_map_count = cursor.fetchone()[0]
    conn.close()
    
    assert task_count == 0, "Database should be clean"
    assert event_map_count == 0, "Event map should be clean"
    
    print("✅ Database cleaned correctly")
    
    os.remove(db_path)
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("EVENT CREATOR AGENT - COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    results = []
    
    results.append(("Database Setup", test_database_setup()))
    results.append(("Simple Task Validation", test_simple_task_validation()))
    results.append(("Simple Task Creation", test_simple_task_creation()))
    results.append(("Complex Task Creation", test_complex_task_creation()))
    results.append(("Delete by ID", test_delete_by_id()))
    results.append(("Delete by Parent ID", test_delete_by_parent_id()))
    
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
    
    parser = argparse.ArgumentParser(description="Test Event Creator Agent")
    parser.add_argument("--test", choices=["db", "validation", "simple", "complex", "delete-id", "delete-parent", "all"],
                       default="all", help="Which test to run")
    
    args = parser.parse_args()
    
    if args.test == "db":
        test_database_setup()
    elif args.test == "validation":
        test_simple_task_validation()
    elif args.test == "simple":
        test_simple_task_creation()
    elif args.test == "complex":
        test_complex_task_creation()
    elif args.test == "delete-id":
        test_delete_by_id()
    elif args.test == "delete-parent":
        test_delete_by_parent_id()
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)

