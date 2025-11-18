#!/usr/bin/env python3
"""
Time Standardizer Test Suite
"""
import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from time_standardizer import TimeStandardizer


def test_time_standardizer():
    """Test the Time Standardizer with various inputs"""
    print("🧪 TIME STANDARDIZER TEST SUITE")
    print("=" * 80)
    
    standardizer = TimeStandardizer()
    
    # Test cases from the spec
    test_cases = [
        {
            "name": "Deadline only case",
            "ar_output": {
                "start_text": "October 18, 2025 03:00 pm",
                "end_text": "November 15, 2025 11:59 pm",
                "duration": "2h"
            },
            "timezone": "America/New_York",
            "expected_duration": "PT2H"
        },
        {
            "name": "Range on same day",
            "ar_output": {
                "start_text": "October 24, 2025 02:00 pm",
                "end_text": "October 24, 2025 04:00 pm",
                "duration": "30m"
            },
            "timezone": "America/New_York",
            "expected_duration": "PT30M"
        },
        {
            "name": "Start-only case",
            "ar_output": {
                "start_text": "October 19, 2025 09:00 am",
                "end_text": "October 19, 2025 11:59 pm",
                "duration": None
            },
            "timezone": "America/New_York",
            "expected_duration": None
        },
        {
            "name": "Bad ordering (should be repaired)",
            "ar_output": {
                "start_text": "October 24, 2025 08:00 pm",
                "end_text": "October 24, 2025 06:00 pm",
                "duration": None
            },
            "timezone": "America/New_York",
            "expected_duration": None
        },
        {
            "name": "Decimal hours",
            "ar_output": {
                "start_text": "October 20, 2025 09:00 am",
                "end_text": "October 20, 2025 11:59 pm",
                "duration": "1.5h"
            },
            "timezone": "America/New_York",
            "expected_duration": "PT1H30M"
        },
        {
            "name": "Duration normalization - minutes",
            "ar_output": {
                "start_text": "October 21, 2025 10:00 am",
                "end_text": "October 21, 2025 11:59 pm",
                "duration": "45 min"
            },
            "timezone": "America/New_York",
            "expected_duration": "PT45M"
        },
        {
            "name": "Duration normalization - hours",
            "ar_output": {
                "start_text": "October 22, 2025 09:00 am",
                "end_text": "October 22, 2025 11:59 pm",
                "duration": "3 hours"
            },
            "timezone": "America/New_York",
            "expected_duration": "PT3H"
        },
        {
            "name": "Duration normalization - compound",
            "ar_output": {
                "start_text": "October 23, 2025 09:00 am",
                "end_text": "October 23, 2025 11:59 pm",
                "duration": "2h30m"
            },
            "timezone": "America/New_York",
            "expected_duration": "PT2H30M"
        },
        {
            "name": "Duration normalization - half hour",
            "ar_output": {
                "start_text": "October 24, 2025 09:00 am",
                "end_text": "October 24, 2025 11:59 pm",
                "duration": "half an hour"
            },
            "timezone": "America/New_York",
            "expected_duration": "PT30M"
        },
        {
            "name": "Invalid duration (should return null)",
            "ar_output": {
                "start_text": "October 25, 2025 09:00 am",
                "end_text": "October 25, 2025 11:59 pm",
                "duration": "some random text"
            },
            "timezone": "America/New_York",
            "expected_duration": None
        },
        {
            "name": "Past time adjustment - only start < now",
            "ar_output": {
                "start_text": "October 22, 2025 10:00 am",  # Past time
                "end_text": "October 22, 2025 05:00 pm",   # Future time
                "duration": "2h"
            },
            "timezone": "America/New_York",
            "expected_duration": "PT2H"
        },
        {
            "name": "Past time adjustment - both start and end < now",
            "ar_output": {
                "start_text": "October 22, 2025 10:00 am",  # Past time
                "end_text": "October 22, 2025 12:00 pm",   # Past time
                "duration": "1h"
            },
            "timezone": "America/New_York",
            "expected_duration": "PT1H"
        },
        {
            "name": "Past time adjustment - only end < now",
            "ar_output": {
                "start_text": "October 22, 2025 11:00 pm",  # Future time
                "end_text": "October 22, 2025 10:00 am",   # Past time
                "duration": "30m"
            },
            "timezone": "America/New_York",
            "expected_duration": "PT30M"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['name']} ---")
        print(f"Input: {test_case['ar_output']}")
        print(f"Timezone: {test_case['timezone']}")
        
        try:
            result = standardizer.standardize(test_case['ar_output'], test_case['timezone'])
            print(f"✅ Result: {result}")
            
            # Validate duration if expected
            if test_case['expected_duration'] is not None:
                if result.duration == test_case['expected_duration']:
                    print(f"✅ Duration correct: {result.duration}")
                else:
                    print(f"❌ Duration mismatch: expected {test_case['expected_duration']}, got {result.duration}")
            else:
                if result.duration is None:
                    print(f"✅ Duration correctly null")
                else:
                    print(f"❌ Duration should be null, got {result.duration}")
            
            results.append({
                'name': test_case['name'],
                'success': True,
                'result': result
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'name': test_case['name'],
                'success': False,
                'error': str(e)
            })
        
        print("-" * 40)
    
    # Summary
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"\n📊 TEST SUMMARY")
    print(f"Total tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success rate: {successful/total*100:.1f}%")
    
    return results


def test_edge_cases():
    """Test edge cases and error conditions"""
    print("\n🔍 EDGE CASES TEST")
    print("=" * 80)
    
    standardizer = TimeStandardizer()
    
    edge_cases = [
        {
            "name": "Empty AR output",
            "ar_output": {},
            "timezone": "America/New_York",
            "should_fail": True
        },
        {
            "name": "Missing start_text",
            "ar_output": {
                "end_text": "October 25, 2025 11:59 pm",
                "duration": "1h"
            },
            "timezone": "America/New_York",
            "should_fail": True
        },
        {
            "name": "Invalid canonical format",
            "ar_output": {
                "start_text": "Invalid format",
                "end_text": "October 25, 2025 11:59 pm",
                "duration": "1h"
            },
            "timezone": "America/New_York",
            "should_fail": True
        },
        {
            "name": "ISO format fallback",
            "ar_output": {
                "start_text": "2025-10-25T09:00:00-04:00",
                "end_text": "2025-10-25T17:00:00-04:00",
                "duration": "1h"
            },
            "timezone": "America/New_York",
            "should_fail": False
        },
        {
            "name": "Invalid timezone",
            "ar_output": {
                "start_text": "October 25, 2025 09:00 am",
                "end_text": "October 25, 2025 11:59 pm",
                "duration": "1h"
            },
            "timezone": "Invalid/Timezone",
            "should_fail": True
        }
    ]
    
    for i, test_case in enumerate(edge_cases, 1):
        print(f"\n--- Edge Case {i}: {test_case['name']} ---")
        print(f"Input: {test_case['ar_output']}")
        print(f"Timezone: {test_case['timezone']}")
        
        try:
            result = standardizer.standardize(test_case['ar_output'], test_case['timezone'])
            if test_case['should_fail']:
                print(f"❌ Expected failure but got success: {result}")
            else:
                print(f"✅ Success: {result}")
        except Exception as e:
            if test_case['should_fail']:
                print(f"✅ Expected failure: {e}")
            else:
                print(f"❌ Unexpected failure: {e}")
        
        print("-" * 40)


def interactive_test():
    """Interactive test mode for custom inputs"""
    print("\n🚀 INTERACTIVE TIME STANDARDIZER TEST")
    print("=" * 80)
    print("Enter AR output to test through Time Standardizer")
    print("Format: JSON with start_text, end_text, duration")
    print("Examples:")
    print('  {"start_text": "October 25, 2025 09:00 am", "end_text": "October 25, 2025 11:59 pm", "duration": "1h"}')
    print('  {"start_text": "November 15, 2025 11:59 pm", "end_text": "November 15, 2025 11:59 pm", "duration": "2h"}')
    print("=" * 80)
    
    standardizer = TimeStandardizer()
    
    while True:
        try:
            print("\n🔍 Enter AR output JSON (or 'quit' to exit):")
            user_input = input().strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                print("⚠️  Please enter AR output JSON")
                continue
            
            try:
                ar_output = json.loads(user_input)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON: {e}")
                continue
            
            timezone = input("Enter timezone (default: America/New_York): ").strip()
            if not timezone:
                timezone = "America/New_York"
            
            print(f"\n🔄 Processing with timezone: {timezone}")
            result = standardizer.standardize(ar_output, timezone)
            print(f"✅ Result: {result}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🧪 TIME STANDARDIZER TEST TOOL")
        print("=" * 80)
        print("Usage:")
        print("  python test_time_standardizer.py --test")
        print("  python test_time_standardizer.py --edge")
        print("  python test_time_standardizer.py --interactive")
        print("=" * 80)
        return
    
    arg = sys.argv[1]
    
    if arg == "--test":
        test_time_standardizer()
    elif arg == "--edge":
        test_edge_cases()
    elif arg == "--interactive":
        interactive_test()
    else:
        print(f"Unknown argument: {arg}")


if __name__ == "__main__":
    main()
