"""
System Test Script for LLM Task Scheduling

This script tests the complete system to ensure all components work together.
Run this after setting up the environment to verify everything is working.
"""

import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the path to import task_scheduler
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'task_scheduler'))

def test_imports():
    """Test that all modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from .llm_decomposer import LLMTaskDecomposer, TaskDecomposition, Subtask
        print("  ✅ LLM Decomposer imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import LLM Decomposer: {e}")
        return False
    
    try:
        from .time_allotment import TimeAllotmentAgent, TimeSlot, ScheduledTask
        print("  ✅ Time Allotment Agent imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import Time Allotment Agent: {e}")
        return False
    
    try:
        from .event_creator import EventCreator, EventData, CreatedEvent, EventCreationResult
        print("  ✅ Event Creator imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import Event Creator: {e}")
        return False
    
    try:
        from .main_scheduler import LLMTaskScheduler, SchedulingRequest, SchedulingResult
        print("  ✅ Main Scheduler imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import Main Scheduler: {e}")
        return False
    
    try:
        from .cli import main as cli_main
        print("  ✅ CLI imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import CLI: {e}")
        return False
    
    return True


def test_task_scheduler_import():
    """Test that task_scheduler can be imported"""
    print("🔍 Testing task_scheduler import...")
    
    try:
        from task_scheduler import schedule_ordered_with_constraints, Assignment, ScheduleOptions, ConstraintAdder
        print("  ✅ task_scheduler imported successfully")
        return True
    except ImportError as e:
        print(f"  ❌ Failed to import task_scheduler: {e}")
        print("  💡 Make sure task_scheduler.py is in the parent directory")
        return False


def test_calendar_config():
    """Test calendar configuration loading"""
    print("🔍 Testing calendar configuration...")
    
    try:
        from .llm_decomposer import LLMTaskDecomposer
        decomposer = LLMTaskDecomposer()
        
        # Test getting calendar IDs
        work_id = decomposer.get_calendar_id("Work")
        home_id = decomposer.get_calendar_id("Home")
        
        print(f"  ✅ Calendar config loaded")
        print(f"     Work calendar ID: {work_id}")
        print(f"     Home calendar ID: {home_id}")
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to load calendar config: {e}")
        return False


def test_ollama_connection():
    """Test Ollama API connection"""
    print("🔍 Testing Ollama connection...")
    
    try:
        import requests
        
        # Test Ollama API
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            print(f"  ✅ Ollama connected successfully")
            print(f"     Available models: {', '.join(model_names)}")
            
            if 'llama3' in model_names:
                print("  ✅ llama3 model is available")
                return True
            else:
                print("  ⚠️  llama3 model not found, but Ollama is working")
                return True
        else:
            print(f"  ❌ Ollama API returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("  ❌ Cannot connect to Ollama API")
        print("  💡 Make sure Ollama is running: ollama serve")
        return False
    except Exception as e:
        print(f"  ❌ Error testing Ollama: {e}")
        return False


def test_calbridge_connection():
    """Test CalBridge API connection"""
    print("🔍 Testing CalBridge connection...")
    
    try:
        import requests
        
        # Test CalBridge API
        response = requests.get("http://127.0.0.1:8765/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"  ✅ CalBridge connected successfully")
            print(f"     Authorized: {status.get('authorized', False)}")
            print(f"     Status code: {status.get('status_code', 'Unknown')}")
            return True
        else:
            print(f"  ❌ CalBridge API returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("  ❌ Cannot connect to CalBridge API")
        print("  💡 Make sure CalBridge is running: python helper_app.py")
        return False
    except Exception as e:
        print(f"  ❌ Error testing CalBridge: {e}")
        return False


def test_simple_scheduling():
    """Test simple task scheduling without LLM"""
    print("🔍 Testing simple task scheduling...")
    
    try:
        from .main_scheduler import LLMTaskScheduler
        
        scheduler = LLMTaskScheduler()
        
        # Test simple scheduling
        deadline = (datetime.now().astimezone() + timedelta(days=1)).isoformat()
        result = scheduler.schedule_simple_task(
            task_description="Test simple task",
            deadline=deadline,
            duration_minutes=30,
            calendar_type="Home"
        )
        
        if result.success:
            print(f"  ✅ Simple scheduling successful")
            print(f"     Created {result.total_events_created} event(s)")
            
            # Clean up
            if result.total_events_created > 0:
                deleted = scheduler.cleanup_events(result)
                print(f"     Cleaned up {deleted} event(s)")
            
            return True
        else:
            print(f"  ❌ Simple scheduling failed: {', '.join(result.errors)}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error testing simple scheduling: {e}")
        return False


def main():
    """Run all system tests"""
    print("🧪 LLM Task Scheduling System Test")
    print("=" * 50)
    print("This script tests the complete system to ensure all components work together.")
    print()
    
    tests = [
        ("Module Imports", test_imports),
        ("Task Scheduler Import", test_task_scheduler_import),
        ("Calendar Configuration", test_calendar_config),
        ("Ollama Connection", test_ollama_connection),
        ("CalBridge Connection", test_calbridge_connection),
        ("Simple Scheduling", test_simple_scheduling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready to use.")
        print("\nNext steps:")
        print("  1. Run the demo: python -m LLM_task_scheduling.demo")
        print("  2. Try the CLI: python -m LLM_task_scheduling.cli --help")
        print("  3. Schedule a task: python -m LLM_task_scheduling.cli schedule 'Your task' '+1d'")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("\nCommon issues:")
        print("  - Ollama not running: ollama serve")
        print("  - CalBridge not running: python helper_app.py")
        print("  - Missing dependencies: pip install -r requirements.txt")
        print("  - Missing task_scheduler.py in parent directory")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
