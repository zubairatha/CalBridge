#!/usr/bin/env python3
"""
Test LLM Decomposer Component
"""
import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from llm_decomposer import LLMDecomposer, TaskDecomposition


def test_basic_functionality():
    """Test basic LLM Decomposer functionality"""
    print("🧪 TESTING LLM DECOMPOSER")
    print("=" * 80)
    
    decomposer = LLMDecomposer()
    
    # Test cases from the spec
    test_cases = [
        {
            "name": "Work - Draft project proposal",
            "td_output": {
                "calendar": "work_1",
                "type": "complex",
                "title": "Draft project proposal",
                "duration": None
            },
            "expected_min_subtasks": 2,
            "expected_max_subtasks": 5
        },
        {
            "name": "Home - Plan 5-day Japan trip",
            "td_output": {
                "calendar": "home_1",
                "type": "complex",
                "title": "Plan 5-day Japan trip",
                "duration": None
            },
            "expected_min_subtasks": 2,
            "expected_max_subtasks": 5
        },
        {
            "name": "Work - Prepare onboarding plan",
            "td_output": {
                "calendar": "work_1",
                "type": "complex",
                "title": "Prepare onboarding plan",
                "duration": None
            },
            "expected_min_subtasks": 2,
            "expected_max_subtasks": 5
        },
        {
            "name": "Work - Research and write quarterly report",
            "td_output": {
                "calendar": "work_1",
                "type": "complex",
                "title": "Research and write quarterly report",
                "duration": None
            },
            "expected_min_subtasks": 2,
            "expected_max_subtasks": 5
        },
        {
            "name": "Home - Prepare taxes",
            "td_output": {
                "calendar": "home_1",
                "type": "complex",
                "title": "Prepare taxes",
                "duration": None
            },
            "expected_min_subtasks": 2,
            "expected_max_subtasks": 5
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['name']} ---")
        print(f"Task: '{test_case['td_output']['title']}'")
        print(f"Expected: {test_case['expected_min_subtasks']}-{test_case['expected_max_subtasks']} subtasks")
        print("-" * 60)
        
        try:
            result = decomposer.decompose_safe(test_case['td_output'])
            
            # Validate results
            num_subtasks = len(result.subtasks)
            in_range = test_case['expected_min_subtasks'] <= num_subtasks <= test_case['expected_max_subtasks']
            
            # Validate subtasks
            all_valid = True
            all_capped = True
            for st in result.subtasks:
                # Check duration format
                valid_format = decomposer._validate_iso8601_duration(st.duration)
                if not valid_format:
                    all_valid = False
                    print(f"   ⚠️  Invalid duration format: {st.duration}")
                
                # Check duration cap (≤ PT3H)
                total_minutes = decomposer._parse_duration_to_minutes(st.duration)
                if total_minutes > 180:  # 3 hours = 180 minutes
                    all_capped = False
                    print(f"   ⚠️  Duration exceeds PT3H: {st.duration} ({total_minutes} minutes)")
            
            print(f"✅ Result:")
            print(f"   • Calendar: {result.calendar}")
            print(f"   • Type: {result.type}")
            print(f"   • Title: {result.title}")
            print(f"   • Subtasks: {num_subtasks} {'✓' if in_range else '✗'}")
            print(f"   • All durations valid: {'✓' if all_valid else '✗'}")
            print(f"   • All durations ≤ PT3H: {'✓' if all_capped else '✗'}")
            
            for j, st in enumerate(result.subtasks, 1):
                print(f"      {j}. {st.title} ({st.duration})")
            
            # Check JSON format
            result_dict = result.to_dict()
            print(f"   • JSON format: {json.dumps(result_dict, indent=2)}")
            
            # Validate structure
            assert 'calendar' in result_dict
            assert 'type' in result_dict
            assert 'title' in result_dict
            assert 'subtasks' in result_dict
            assert result_dict['type'] == 'complex'
            assert isinstance(result_dict['subtasks'], list)
            assert len(result_dict['subtasks']) >= 2
            assert len(result_dict['subtasks']) <= 5
            
            success = in_range and all_valid and all_capped
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
            import traceback
            traceback.print_exc()
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


def test_duration_validation():
    """Test ISO-8601 duration validation"""
    print("\n🔍 TESTING DURATION VALIDATION")
    print("=" * 80)
    
    decomposer = LLMDecomposer()
    
    valid_durations = [
        "PT30M",
        "PT1H",
        "PT1H30M",
        "PT2H",
        "PT2H30M",
        "PT3H",
        "PT45M",
        "PT15M"
    ]
    
    invalid_durations = [
        "30M",
        "1H",
        "PT4H",
        "PT3H30M",
        "PT2.5H",
        "2 hours",
        "PT",
        "PT30",
        "30 minutes"
    ]
    
    print("\nValid durations:")
    for duration in valid_durations:
        is_valid = decomposer._validate_iso8601_duration(duration)
        total_minutes = decomposer._parse_duration_to_minutes(duration)
        capped = decomposer._cap_duration_to_pt3h(duration)
        print(f"  {duration:10} → Valid: {is_valid:5} | Minutes: {total_minutes:3} | Capped: {capped}")
    
    print("\nInvalid durations:")
    for duration in invalid_durations:
        is_valid = decomposer._validate_iso8601_duration(duration)
        print(f"  {duration:15} → Valid: {is_valid:5}")


def test_constraints():
    """Test that constraints are enforced"""
    print("\n🔍 TESTING CONSTRAINTS ENFORCEMENT")
    print("=" * 80)
    
    decomposer = LLMDecomposer()
    
    # Test that simple tasks are rejected
    print("\n1. Testing simple task rejection:")
    try:
        simple_task = {
            "calendar": "work_1",
            "type": "simple",
            "title": "Call mom",
            "duration": "PT30M"
        }
        result = decomposer.decompose(simple_task)
        print("   ❌ Should have raised ValueError for simple task")
    except ValueError as e:
        print(f"   ✅ Correctly rejected simple task: {e}")
    
    # Test duration capping
    print("\n2. Testing duration capping:")
    test_durations = ["PT4H", "PT5H", "PT3H30M", "PT10H"]
    for duration in test_durations:
        capped = decomposer._cap_duration_to_pt3h(duration)
        total_minutes = decomposer._parse_duration_to_minutes(capped)
        print(f"   {duration:10} → {capped:10} ({total_minutes} minutes)")
        assert total_minutes <= 180, f"Duration {capped} exceeds 3 hours"


def test_edge_cases():
    """Test edge cases"""
    print("\n🔍 TESTING EDGE CASES")
    print("=" * 80)
    
    decomposer = LLMDecomposer()
    
    edge_cases = [
        {
            "name": "Very short complex task",
            "td_output": {
                "calendar": "work_1",
                "type": "complex",
                "title": "Review document",
                "duration": None
            }
        },
        {
            "name": "Very long complex task",
            "td_output": {
                "calendar": "work_1",
                "type": "complex",
                "title": "Design and implement complete software architecture with testing and documentation",
                "duration": None
            }
        },
        {
            "name": "Task with no calendar",
            "td_output": {
                "calendar": None,
                "type": "complex",
                "title": "Prepare presentation",
                "duration": None
            }
        }
    ]
    
    for edge_case in edge_cases:
        print(f"\n--- {edge_case['name']} ---")
        print(f"Task: '{edge_case['td_output']['title']}'")
        
        try:
            result = decomposer.decompose_safe(edge_case['td_output'])
            print(f"✅ Result: {len(result.subtasks)} subtasks")
            for i, st in enumerate(result.subtasks, 1):
                print(f"   {i}. {st.title} ({st.duration})")
            
            # Validate constraints
            assert 2 <= len(result.subtasks) <= 5, "Subtask count out of range"
            for st in result.subtasks:
                assert decomposer._validate_iso8601_duration(st.duration), f"Invalid duration: {st.duration}"
                total_minutes = decomposer._parse_duration_to_minutes(st.duration)
                assert total_minutes <= 180, f"Duration exceeds PT3H: {st.duration}"
            
        except Exception as e:
            print(f"❌ Error: {e}")


def test_spec_examples():
    """Test with examples from the spec"""
    print("\n🔍 TESTING SPEC EXAMPLES")
    print("=" * 80)
    
    decomposer = LLMDecomposer()
    
    spec_examples = [
        {
            "name": "Spec Example 1: Draft project proposal",
            "td_output": {
                "calendar": "work_1",
                "type": "complex",
                "title": "Draft project proposal",
                "duration": None
            },
            "expected_subtasks": [
                "Research",
                "Outline",
                "Write",
                "Review",
                "Export"
            ]
        },
        {
            "name": "Spec Example 2: Plan 5-day Japan trip",
            "td_output": {
                "calendar": "home_1",
                "type": "complex",
                "title": "Plan 5-day Japan trip",
                "duration": None
            }
        },
        {
            "name": "Spec Example 3: Prepare onboarding plan",
            "td_output": {
                "calendar": "work_1",
                "type": "complex",
                "title": "Prepare onboarding plan",
                "duration": None
            }
        }
    ]
    
    for example in spec_examples:
        print(f"\n--- {example['name']} ---")
        print(f"Task: '{example['td_output']['title']}'")
        print("-" * 60)
        
        try:
            result = decomposer.decompose_safe(example['td_output'])
            
            print(f"✅ Decomposition:")
            print(f"   • Calendar: {result.calendar}")
            print(f"   • Type: {result.type}")
            print(f"   • Title: {result.title}")
            print(f"   • Subtasks: {len(result.subtasks)}")
            
            for i, st in enumerate(result.subtasks, 1):
                print(f"      {i}. {st.title} ({st.duration})")
            
            # Verify constraints
            assert 2 <= len(result.subtasks) <= 5
            for st in result.subtasks:
                assert decomposer._validate_iso8601_duration(st.duration)
                total_minutes = decomposer._parse_duration_to_minutes(st.duration)
                assert total_minutes <= 180
            
            # Check JSON output
            result_dict = result.to_dict()
            print(f"\n   JSON Output:")
            print(json.dumps(result_dict, indent=4))
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


def interactive_mode():
    """Interactive mode for testing custom tasks"""
    print("\n🚀 INTERACTIVE MODE")
    print("=" * 80)
    print("Enter complex tasks to decompose")
    print("Format: task title")
    print("Examples:")
    print("  - Draft project proposal")
    print("  - Plan 5-day Japan trip")
    print("  - Prepare onboarding plan")
    print("=" * 80)
    
    decomposer = LLMDecomposer()
    
    while True:
        try:
            title = input("\n🔍 Enter task title (or 'quit' to exit): ").strip()
            
            if title.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not title:
                print("⚠️  Please enter a task title")
                continue
            
            calendar = input("Enter calendar ID (default: work_1): ").strip()
            if not calendar:
                calendar = "work_1"
            
            td_output = {
                "calendar": calendar,
                "type": "complex",
                "title": title,
                "duration": None
            }
            
            print(f"\nDecomposing: '{title}'")
            
            result = decomposer.decompose_safe(td_output)
            
            print(f"\n✅ Result:")
            print(f"   • Calendar: {result.calendar}")
            print(f"   • Type: {result.type}")
            print(f"   • Title: {result.title}")
            print(f"   • Subtasks: {len(result.subtasks)}")
            
            for i, st in enumerate(result.subtasks, 1):
                print(f"      {i}. {st.title} ({st.duration})")
            
            print(f"\n   JSON: {json.dumps(result.to_dict(), indent=2)}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🧪 LLM DECOMPOSER TEST SUITE")
        print("=" * 80)
        print("Usage:")
        print("  python test_llm_decomposer.py --basic")
        print("  python test_llm_decomposer.py --duration")
        print("  python test_llm_decomposer.py --constraints")
        print("  python test_llm_decomposer.py --edge-cases")
        print("  python test_llm_decomposer.py --spec-examples")
        print("  python test_llm_decomposer.py --interactive")
        print("  python test_llm_decomposer.py --all")
        print("=" * 80)
        return
    
    arg = sys.argv[1]
    
    if arg == "--basic":
        test_basic_functionality()
    elif arg == "--duration":
        test_duration_validation()
    elif arg == "--constraints":
        test_constraints()
    elif arg == "--edge-cases":
        test_edge_cases()
    elif arg == "--spec-examples":
        test_spec_examples()
    elif arg == "--interactive":
        interactive_mode()
    elif arg == "--all":
        test_basic_functionality()
        test_duration_validation()
        test_constraints()
        test_edge_cases()
        test_spec_examples()
    else:
        print(f"Unknown argument: {arg}")
        print("Use --help for usage information")


if __name__ == "__main__":
    main()


