#!/usr/bin/env python3
"""
Test Task Difficulty Analyzer Component
"""
import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from task_difficulty_analyzer import TaskDifficultyAnalyzer


def test_basic_functionality():
    """Test basic TD functionality with various scenarios"""
    print("🧪 TESTING TASK DIFFICULTY ANALYZER")
    print("=" * 80)
    
    analyzer = TaskDifficultyAnalyzer()
    
    # Test cases from the spec and user requirements
    test_cases = [
        {
            "name": "Simple via duration; Home",
            "query": "call mom tomorrow for 20 minutes",
            "duration": "PT20M",
            "expected_type": "simple",
            "expected_calendar": "home"
        },
        {
            "name": "Complex work deliverable",
            "query": "finish project proposal by Nov 15",
            "duration": None,
            "expected_type": "complex",
            "expected_calendar": "work"
        },
        {
            "name": "Simple atomic work action",
            "query": "send the signed NDA to the client",
            "duration": None,
            "expected_type": "simple",
            "expected_calendar": "work"
        },
        {
            "name": "Personal simple",
            "query": "buy groceries and fruits",
            "duration": None,
            "expected_type": "simple",
            "expected_calendar": "home"
        },
        {
            "name": "Ambiguous phrasing → complex",
            "query": "prepare onboarding plan for new hire",
            "duration": None,
            "expected_type": "complex",
            "expected_calendar": "work"
        },
        {
            "name": "User example: duration provided",
            "query": "Study for 2 hours",
            "duration": "PT2H",
            "expected_type": "simple",
            "expected_calendar": None  # Could be work or home
        },
        {
            "name": "User example: duration provided (30 min)",
            "query": "Call dentist to schedule appointment",
            "duration": "PT30M",
            "expected_type": "simple",
            "expected_calendar": "home"
        },
        {
            "name": "Complex multi-step work",
            "query": "research and write quarterly report",
            "duration": None,
            "expected_type": "complex",
            "expected_calendar": "work"
        },
        {
            "name": "Simple personal errand",
            "query": "pick up package from post office",
            "duration": None,
            "expected_type": "simple",
            "expected_calendar": "home"
        },
        {
            "name": "Complex coordination task",
            "query": "organize team meeting with stakeholders",
            "duration": None,
            "expected_type": "complex",
            "expected_calendar": "work"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['name']} ---")
        print(f"Query: '{test_case['query']}'")
        print(f"Duration: {test_case['duration']}")
        print(f"Expected: type={test_case['expected_type']}, calendar={test_case['expected_calendar']}")
        print("-" * 60)
        
        try:
            result = analyzer.analyze_safe(test_case['query'], test_case['duration'])
            
            # Validate results
            type_correct = result.type == test_case['expected_type']
            calendar_correct = (
                test_case['expected_calendar'] is None or 
                (test_case['expected_calendar'] == 'work' and 'work' in (result.calendar or '').lower()) or
                (test_case['expected_calendar'] == 'home' and 'home' in (result.calendar or '').lower())
            )
            duration_preserved = result.duration == test_case['duration']
            
            print(f"✅ Result:")
            print(f"   • Calendar: {result.calendar}")
            print(f"   • Type: {result.type} {'✓' if type_correct else '✗ (expected: ' + test_case['expected_type'] + ')'}")
            print(f"   • Title: {result.title}")
            print(f"   • Duration: {result.duration} {'✓' if duration_preserved else '✗ (duration not preserved!)'}")
            
            # Check JSON format
            result_dict = result.to_dict()
            print(f"   • JSON format: {json.dumps(result_dict, indent=2)}")
            
            # Validate JSON structure
            assert 'calendar' in result_dict
            assert 'type' in result_dict
            assert 'title' in result_dict
            assert 'duration' in result_dict
            assert result_dict['type'] in ['simple', 'complex']
            assert result.duration == test_case['duration'], "Duration must be preserved exactly!"
            
            success = type_correct and duration_preserved
            results.append({
                'name': test_case['name'],
                'success': success,
                'result': result
            })
            
            if success:
                print("   ✅ Test PASSED")
            else:
                print("   ⚠️  Test PARTIAL (some expectations not met)")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'name': test_case['name'],
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    successful = sum(1 for r in results if r.get('success', False))
    total = len(results)
    print(f"Total tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success rate: {successful/total*100:.1f}%")
    
    return results


def test_duration_preservation():
    """Test that duration is always preserved exactly"""
    print("\n🔍 TESTING DURATION PRESERVATION")
    print("=" * 80)
    
    analyzer = TaskDifficultyAnalyzer()
    
    duration_cases = [
        "PT30M",
        "PT2H",
        "PT1H30M",
        None
    ]
    
    query = "Test task"
    
    for duration in duration_cases:
        print(f"\nTesting with duration: {duration}")
        try:
            result = analyzer.analyze_safe(query, duration)
            assert result.duration == duration, f"Duration not preserved! Input: {duration}, Output: {result.duration}"
            print(f"✅ Duration preserved: {result.duration}")
        except Exception as e:
            print(f"❌ Error: {e}")


def test_calendar_selection():
    """Test calendar selection logic"""
    print("\n🔍 TESTING CALENDAR SELECTION")
    print("=" * 80)
    
    analyzer = TaskDifficultyAnalyzer()
    
    # Test Work vs Home selection
    work_queries = [
        "Send invoice to client",
        "Prepare deck for meeting",
        "Merge approved PR",
        "Submit expense report"
    ]
    
    home_queries = [
        "Call mom",
        "Buy groceries",
        "Go to gym",
        "Schedule dentist appointment"
    ]
    
    print("\nWork queries:")
    for query in work_queries:
        try:
            result = analyzer.analyze_safe(query, None)
            calendar_lower = (result.calendar or '').lower()
            is_work = 'work' in calendar_lower if result.calendar else False
            print(f"  '{query}' → Calendar: {result.calendar} {'✓' if is_work else '⚠️'}")
        except Exception as e:
            print(f"  '{query}' → Error: {e}")
    
    print("\nHome queries:")
    for query in home_queries:
        try:
            result = analyzer.analyze_safe(query, None)
            calendar_lower = (result.calendar or '').lower()
            is_home = 'home' in calendar_lower if result.calendar else False
            print(f"  '{query}' → Calendar: {result.calendar} {'✓' if is_home else '⚠️'}")
        except Exception as e:
            print(f"  '{query}' → Error: {e}")


def test_user_examples():
    """Test with user-provided examples"""
    print("\n🔍 TESTING USER PROVIDED EXAMPLES")
    print("=" * 80)
    
    analyzer = TaskDifficultyAnalyzer()
    
    # User example from requirements
    user_examples = [
        {
            "query": "Meeting with team",
            "duration": "PT30M",
            "start": "2025-11-05T00:00:00-05:00",
            "end": "2025-11-05T23:59:59-05:00"
        },
        {
            "query": "Call mom",
            "duration": None,
            "start": "2025-11-05T00:00:00-05:00",
            "end": "2025-11-05T23:59:59-05:00"
        },
        {
            "query": "Prepare project proposal",
            "duration": "PT2H",
            "start": "2025-11-05T00:00:00-05:00",
            "end": "2025-11-05T23:59:59-05:00"
        }
    ]
    
    for i, example in enumerate(user_examples, 1):
        print(f"\n--- User Example {i} ---")
        print(f"Query: '{example['query']}'")
        print(f"Duration: {example['duration']}")
        print(f"Time range: {example['start']} to {example['end']}")
        print("-" * 60)
        
        try:
            result = analyzer.analyze_safe(example['query'], example['duration'])
            
            print(f"✅ Analysis:")
            print(f"   • Calendar: {result.calendar}")
            print(f"   • Type: {result.type}")
            print(f"   • Title: {result.title}")
            print(f"   • Duration: {result.duration}")
            
            # Verify duration preservation
            assert result.duration == example['duration'], "Duration must be preserved!"
            
            # Verify JSON structure
            result_dict = result.to_dict()
            print(f"   • JSON: {json.dumps(result_dict)}")
            
        except Exception as e:
            print(f"❌ Error: {e}")


def test_edge_cases():
    """Test edge cases"""
    print("\n🔍 TESTING EDGE CASES")
    print("=" * 80)
    
    analyzer = TaskDifficultyAnalyzer()
    
    edge_cases = [
        {
            "name": "Empty duration string",
            "query": "Test task",
            "duration": ""
        },
        {
            "name": "Very long query",
            "query": "This is a very long query that describes a complex multi-step task that requires coordination with multiple team members and involves research, drafting, review, and approval processes",
            "duration": None
        },
        {
            "name": "Query with special characters",
            "query": "Send email to client@example.com re: NDA #123",
            "duration": None
        },
        {
            "name": "Ambiguous query (could be work or home)",
            "query": "Prepare taxes",
            "duration": None
        }
    ]
    
    for edge_case in edge_cases:
        print(f"\n--- {edge_case['name']} ---")
        print(f"Query: '{edge_case['query']}'")
        print(f"Duration: {edge_case['duration']}")
        
        try:
            result = analyzer.analyze_safe(edge_case['query'], edge_case['duration'])
            print(f"✅ Result: {result}")
            print(f"   JSON: {json.dumps(result.to_dict())}")
        except Exception as e:
            print(f"❌ Error: {e}")


def interactive_mode():
    """Interactive mode for testing custom queries"""
    print("\n🚀 INTERACTIVE MODE")
    print("=" * 80)
    print("Enter queries to test Task Difficulty Analyzer")
    print("Format: query | duration (or 'null' for no duration)")
    print("Examples:")
    print("  call mom tomorrow for 20 minutes | PT20M")
    print("  finish project proposal | null")
    print("=" * 80)
    
    analyzer = TaskDifficultyAnalyzer()
    
    while True:
        try:
            user_input = input("\n🔍 Enter query and duration (or 'quit' to exit): ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                print("⚠️  Please enter a query")
                continue
            
            # Parse input (format: query | duration)
            parts = user_input.split('|')
            query = parts[0].strip()
            duration_str = parts[1].strip() if len(parts) > 1 else "null"
            
            duration = None if duration_str.lower() == 'null' else duration_str
            
            print(f"\nAnalyzing: '{query}'")
            print(f"Duration: {duration}")
            
            result = analyzer.analyze_safe(query, duration)
            
            print(f"\n✅ Result:")
            print(f"   • Calendar: {result.calendar}")
            print(f"   • Type: {result.type}")
            print(f"   • Title: {result.title}")
            print(f"   • Duration: {result.duration}")
            print(f"   • JSON: {json.dumps(result.to_dict(), indent=2)}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🧪 TASK DIFFICULTY ANALYZER TEST SUITE")
        print("=" * 80)
        print("Usage:")
        print("  python test_task_difficulty_analyzer.py --basic")
        print("  python test_task_difficulty_analyzer.py --duration")
        print("  python test_task_difficulty_analyzer.py --calendars")
        print("  python test_task_difficulty_analyzer.py --user-examples")
        print("  python test_task_difficulty_analyzer.py --edge-cases")
        print("  python test_task_difficulty_analyzer.py --interactive")
        print("  python test_task_difficulty_analyzer.py --all")
        print("=" * 80)
        return
    
    arg = sys.argv[1]
    
    if arg == "--basic":
        test_basic_functionality()
    elif arg == "--duration":
        test_duration_preservation()
    elif arg == "--calendars":
        test_calendar_selection()
    elif arg == "--user-examples":
        test_user_examples()
    elif arg == "--edge-cases":
        test_edge_cases()
    elif arg == "--interactive":
        interactive_mode()
    elif arg == "--all":
        test_basic_functionality()
        test_duration_preservation()
        test_calendar_selection()
        test_user_examples()
        test_edge_cases()
    else:
        print(f"Unknown argument: {arg}")
        print("Use --help for usage information")


if __name__ == "__main__":
    main()

