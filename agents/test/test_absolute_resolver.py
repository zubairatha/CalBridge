#!/usr/bin/env python3
"""
Test script for Absolute Resolver component
"""
import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from absolute_resolver import AbsoluteResolver
from context_provider import ContextProvider


def test_absolute_resolver():
    """Test the Absolute Resolver with various scenarios"""
    print("🔍 TESTING ABSOLUTE RESOLVER")
    print("=" * 80)
    
    # Initialize components
    resolver = AbsoluteResolver()
    context_provider = ContextProvider(timezone="America/New_York")
    
    # Get test context (October 18, 2025 3:00 PM - Saturday)
    context = context_provider.get_context_for_testing(2025, 10, 18, 15, 0)
    
    print("📅 Test Context:")
    for key, value in context.items():
        print(f"   {key}: {value}")
    print()
    
    # Test cases from the specification
    test_cases = [
        {
            "name": "Deadline only",
            "slots": {"start_text": None, "end_text": "Nov 15", "duration": "2h"},
            "expected_pattern": "start=NOW, end=Nov 15 11:59pm"
        },
        {
            "name": "Start-only (vague)",
            "slots": {"start_text": "tomorrow", "end_text": None, "duration": None},
            "expected_pattern": "start=tomorrow 9am, end=tomorrow 11:59pm"
        },
        {
            "name": "Explicit times on weekday (range)",
            "slots": {"start_text": "Friday 2pm", "end_text": "Friday 4pm", "duration": "30m"},
            "expected_pattern": "start=Oct 24 2pm, end=Oct 24 4pm"
        },
        {
            "name": "Bare time that already passed",
            "slots": {"start_text": "11am", "end_text": None, "duration": None},
            "expected_pattern": "start=tomorrow 11am, end=tomorrow 11:59pm"
        },
        {
            "name": "Start + deadline",
            "slots": {"start_text": "next week", "end_text": "EOM", "duration": None},
            "expected_pattern": "start=Oct 20 9am, end=Oct 31 11:59pm"
        },
        {
            "name": "Duration only",
            "slots": {"start_text": None, "end_text": None, "duration": "45m"},
            "expected_pattern": "start=NOW, end=END_OF_TODAY"
        },
        {
            "name": "No time information",
            "slots": {"start_text": None, "end_text": None, "duration": None},
            "expected_pattern": "start=NOW, end=END_OF_TODAY"
        },
        {
            "name": "Cross-midnight case",
            "slots": {"start_text": "Friday 8pm", "end_text": "Friday 6pm", "duration": None},
            "expected_pattern": "start=Oct 24 8pm, end=Oct 25 6pm"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"--- Test {i}: {test_case['name']} ---")
        print(f"Slots: {test_case['slots']}")
        print(f"Expected: {test_case['expected_pattern']}")
        
        try:
            resolution = resolver.resolve_absolute_safe(test_case['slots'], context)
            print(f"✅ Result: {resolution}")
            
            # Validate format
            start_text = resolution.start_text
            end_text = resolution.end_text
            duration = resolution.duration
            
            # Check if format matches expected pattern
            format_valid = True
            if start_text and not ("," in start_text and "am" in start_text.lower() or "pm" in start_text.lower()):
                format_valid = False
                print("   ⚠️  Start format might be incorrect")
            
            if end_text and not ("," in end_text and "am" in end_text.lower() or "pm" in end_text.lower()):
                format_valid = False
                print("   ⚠️  End format might be incorrect")
            
            if format_valid:
                print("   ✅ Format looks correct")
            
            # Check duration preservation
            if test_case['slots'].get('duration') != duration:
                print(f"   ⚠️  Duration not preserved: expected {test_case['slots'].get('duration')}, got {duration}")
            else:
                print("   ✅ Duration preserved correctly")
            
            results.append({
                'name': test_case['name'],
                'slots': test_case['slots'],
                'resolution': resolution,
                'success': True
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'name': test_case['name'],
                'slots': test_case['slots'],
                'error': str(e),
                'success': False
            })
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_tests = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total_tests - successful
    
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {successful/total_tests*100:.1f}%")
    
    return results


def test_custom_scenarios():
    """Test custom scenarios"""
    print("\n" + "=" * 80)
    print("CUSTOM SCENARIOS TEST")
    print("=" * 80)
    
    resolver = AbsoluteResolver()
    context_provider = ContextProvider()
    
    # Get current context
    context = context_provider.get_context()
    
    custom_scenarios = [
        "Meeting tomorrow at 3pm for 1 hour",
        "Deadline is Friday",
        "Work from 9am to 5pm",
        "Study for 2 hours tonight",
        "Call mom",
        "Finish project by end of month",
        "Start next week, finish by EOM"
    ]
    
    print("Testing custom scenarios with current context:")
    print(f"Current time: {context['NOW_ISO']}")
    print(f"Today: {context['TODAY_HUMAN']}")
    print()
    
    for scenario in custom_scenarios:
        print(f"📝 Scenario: '{scenario}'")
        print("-" * 50)
        
        # This would normally come from the Slot Extractor
        # For testing, we'll create mock slots
        if "tomorrow" in scenario and "3pm" in scenario:
            mock_slots = {"start_text": "tomorrow 3pm", "end_text": None, "duration": "1 hour"}
        elif "deadline" in scenario.lower() and "friday" in scenario.lower():
            mock_slots = {"start_text": None, "end_text": "Friday", "duration": None}
        elif "from" in scenario and "to" in scenario:
            mock_slots = {"start_text": "9am", "end_text": "5pm", "duration": None}
        elif "tonight" in scenario and "2 hours" in scenario:
            mock_slots = {"start_text": "tonight", "end_text": None, "duration": "2 hours"}
        elif "call mom" in scenario.lower():
            mock_slots = {"start_text": None, "end_text": None, "duration": None}
        elif "end of month" in scenario.lower():
            mock_slots = {"start_text": None, "end_text": "end of month", "duration": None}
        elif "next week" in scenario and "EOM" in scenario:
            mock_slots = {"start_text": "next week", "end_text": "EOM", "duration": None}
        else:
            mock_slots = {"start_text": None, "end_text": None, "duration": None}
        
        print(f"Mock slots: {mock_slots}")
        
        try:
            resolution = resolver.resolve_absolute_safe(mock_slots, context)
            print(f"✅ Resolution: {resolution}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()


def interactive_mode():
    """Interactive mode for testing"""
    print("\n" + "=" * 80)
    print("INTERACTIVE ABSOLUTE RESOLVER TEST")
    print("=" * 80)
    print("Enter slot information to resolve (type 'quit' to exit)")
    print("Format: start_text, end_text, duration")
    print("Examples:")
    print("  - tomorrow, null, null")
    print("  - null, Friday, 2h")
    print("  - 3pm, 5pm, 30m")
    print("=" * 80)
    
    resolver = AbsoluteResolver()
    context_provider = ContextProvider()
    context = context_provider.get_context()
    
    while True:
        try:
            user_input = input("\n🔍 Enter slots (start, end, duration): ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                print("⚠️  Please enter slot information")
                continue
            
            # Parse input
            parts = [part.strip() for part in user_input.split(',')]
            if len(parts) != 3:
                print("⚠️  Please enter exactly 3 values separated by commas")
                continue
            
            start_text = parts[0] if parts[0].lower() != 'null' else None
            end_text = parts[1] if parts[1].lower() != 'null' else None
            duration = parts[2] if parts[2].lower() != 'null' else None
            
            slots = {
                "start_text": start_text,
                "end_text": end_text,
                "duration": duration
            }
            
            print(f"📊 Resolving: {slots}")
            
            resolution = resolver.resolve_absolute_safe(slots, context)
            print(f"✅ Result: {resolution}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🚀 ABSOLUTE RESOLVER TEST TOOL")
        print("=" * 80)
        print("Usage:")
        print("  python test_absolute_resolver.py --test")
        print("  python test_absolute_resolver.py --custom")
        print("  python test_absolute_resolver.py --interactive")
        print("=" * 80)
        return
    
    arg = sys.argv[1]
    
    if arg == "--test":
        test_absolute_resolver()
    elif arg == "--custom":
        test_custom_scenarios()
    elif arg == "--interactive":
        interactive_mode()
    else:
        print("Invalid argument. Use --test, --custom, or --interactive")


if __name__ == "__main__":
    main()
