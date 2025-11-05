#!/usr/bin/env python3
"""
Absolute Resolver Performance Test with Qwen2.5
"""
import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from datetime import datetime
from absolute_resolver import AbsoluteResolver
from context_provider import ContextProvider


def test_absolute_resolver_performance():
    """Test Absolute Resolver performance with various scenarios"""
    print("🧪 ABSOLUTE RESOLVER PERFORMANCE TEST (Qwen2.5)")
    print("=" * 80)
    
    resolver = AbsoluteResolver()
    context_provider = ContextProvider(timezone="America/New_York")
    context = context_provider.get_context()
    
    print("📅 Current Context:")
    print(f"   • Current Time: {context['NOW_ISO']}")
    print(f"   • Today: {context['TODAY_HUMAN']}")
    print(f"   • End of Today: {context['END_OF_TODAY']}")
    print()
    
    # Test scenarios covering different edge cases
    test_scenarios = [
        {
            "name": "Deadline only",
            "slots": {"start_text": None, "end_text": "Nov 15", "duration": "2h"},
            "expected_behavior": "Should set start to NOW, end to Nov 15 11:59pm"
        },
        {
            "name": "Start only (tomorrow)",
            "slots": {"start_text": "tomorrow", "end_text": None, "duration": "30m"},
            "expected_behavior": "Should set start to tomorrow 12am, end to tomorrow 11:59pm"
        },
        {
            "name": "Start only (specific time)",
            "slots": {"start_text": "3pm", "end_text": None, "duration": "1h"},
            "expected_behavior": "Should set start to today 3pm (or tomorrow if past), end to 11:59pm"
        },
        {
            "name": "Range with times",
            "slots": {"start_text": "9am", "end_text": "5pm", "duration": None},
            "expected_behavior": "Should set both to same day, handle past times"
        },
        {
            "name": "Weekday reference",
            "slots": {"start_text": "Friday 2pm", "end_text": "Friday 4pm", "duration": "30m"},
            "expected_behavior": "Should resolve to next Friday"
        },
        {
            "name": "Vague periods",
            "slots": {"start_text": "this evening", "end_text": None, "duration": "2h"},
            "expected_behavior": "Should set start to evening time (6pm), end to 11:59pm"
        },
        {
            "name": "Next week reference",
            "slots": {"start_text": "next week", "end_text": None, "duration": "1h"},
            "expected_behavior": "Should set start to next Monday 9am, end to 11:59pm"
        },
        {
            "name": "EOM deadline",
            "slots": {"start_text": None, "end_text": "EOM", "duration": "2h"},
            "expected_behavior": "Should set start to NOW, end to end of month 11:59pm"
        },
        {
            "name": "Cross-midnight range",
            "slots": {"start_text": "11pm", "end_text": "2am", "duration": None},
            "expected_behavior": "Should handle cross-midnight correctly"
        },
        {
            "name": "Duration only",
            "slots": {"start_text": None, "end_text": None, "duration": "1.5h"},
            "expected_behavior": "Should set start to NOW, end to END_OF_TODAY"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n--- Test {i}: {scenario['name']} ---")
        print(f"Expected: {scenario['expected_behavior']}")
        print(f"Input slots: {scenario['slots']}")
        
        try:
            resolution = resolver.resolve_absolute_safe(scenario['slots'], context)
            print(f"✅ Resolution: {resolution}")
            
            # Analyze the resolution quality
            quality_score = analyze_resolution_quality(scenario, resolution, context)
            print(f"📊 Quality Score: {quality_score}/10")
            
            results.append({
                'name': scenario['name'],
                'success': True,
                'resolution': resolution,
                'quality_score': quality_score
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'name': scenario['name'],
                'success': False,
                'error': str(e),
                'quality_score': 0
            })
        
        print("-" * 40)
    
    # Summary
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    avg_quality = sum(r['quality_score'] for r in results) / total if total > 0 else 0
    
    print(f"\n📊 PERFORMANCE SUMMARY")
    print(f"Total tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success rate: {successful/total*100:.1f}%")
    print(f"Average quality score: {avg_quality:.1f}/10")
    
    # Detailed quality breakdown
    print(f"\n📈 QUALITY BREAKDOWN")
    for result in results:
        if result['success']:
            print(f"  {result['name']}: {result['quality_score']}/10")
        else:
            print(f"  {result['name']}: FAILED")
    
    return results


def analyze_resolution_quality(scenario, resolution, context):
    """Analyze the quality of the resolution (0-10 scale)"""
    score = 0
    
    # Check if resolution is valid
    if not resolution.start_text or not resolution.end_text:
        return 0
    
    try:
        # Parse the resolution times
        from time_standardizer import TimeStandardizer
        standardizer = TimeStandardizer()
        
        # Convert to dict for standardizer
        resolution_dict = {
            'start_text': resolution.start_text,
            'end_text': resolution.end_text,
            'duration': resolution.duration
        }
        
        # Try to standardize (this will validate the format)
        standardization = standardizer.standardize_safe(resolution_dict, "America/New_York")
        
        # Basic format validation (2 points)
        if standardization.start and standardization.end:
            score += 2
        
        # Time logic validation (3 points)
        start_dt = datetime.fromisoformat(standardization.start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(standardization.end.replace('Z', '+00:00'))
        
        if start_dt <= end_dt:
            score += 3
        else:
            score += 1  # Partial credit for at least producing times
        
        # Context appropriateness (3 points)
        scenario_name = scenario['name'].lower()
        
        if 'deadline' in scenario_name:
            # For deadlines, start should be reasonable (not too far in past)
            now = datetime.now()
            if start_dt >= now.replace(hour=0, minute=0, second=0, microsecond=0):
                score += 3
            else:
                score += 1
        elif 'start only' in scenario_name:
            # For start-only, end should be end of day
            if end_dt.hour == 23 and end_dt.minute == 59:
                score += 3
            else:
                score += 1
        elif 'range' in scenario_name:
            # For ranges, should be same day or logical progression
            if start_dt.date() == end_dt.date() or (end_dt - start_dt).days <= 1:
                score += 3
            else:
                score += 1
        else:
            # General case
            score += 2
        
        # Duration handling (2 points)
        if resolution.duration:
            if resolution.duration == scenario['slots'].get('duration'):
                score += 2
            else:
                score += 1
        else:
            if not scenario['slots'].get('duration'):
                score += 2
            else:
                score += 0
        
    except Exception as e:
        # If we can't analyze, give partial credit for having a response
        score = 1
    
    return min(score, 10)  # Cap at 10


def test_specific_edge_cases():
    """Test specific edge cases that commonly cause issues"""
    print("\n🔍 EDGE CASE TESTING")
    print("=" * 80)
    
    resolver = AbsoluteResolver()
    context_provider = ContextProvider(timezone="America/New_York")
    context = context_provider.get_context()
    
    edge_cases = [
        {
            "name": "Ambiguous time (2pm)",
            "slots": {"start_text": "2pm", "end_text": None, "duration": None},
            "issue": "Should handle if 2pm is past today"
        },
        {
            "name": "Weekend reference",
            "slots": {"start_text": "Saturday", "end_text": None, "duration": None},
            "issue": "Should resolve to next Saturday"
        },
        {
            "name": "This vs Next week",
            "slots": {"start_text": "this Friday", "end_text": None, "duration": None},
            "issue": "Should distinguish this vs next Friday"
        },
        {
            "name": "Time without date",
            "slots": {"start_text": "6pm", "end_text": "8pm", "duration": None},
            "issue": "Should handle same-day assumption"
        },
        {
            "name": "Relative time",
            "slots": {"start_text": "in 2 hours", "end_text": None, "duration": None},
            "issue": "Should calculate from current time"
        }
    ]
    
    for i, case in enumerate(edge_cases, 1):
        print(f"\n--- Edge Case {i}: {case['name']} ---")
        print(f"Issue: {case['issue']}")
        print(f"Input: {case['slots']}")
        
        try:
            resolution = resolver.resolve_absolute_safe(case['slots'], context)
            print(f"✅ Resolution: {resolution}")
            
            # Check for common issues
            issues_found = []
            if not resolution.start_text or not resolution.end_text:
                issues_found.append("Missing start/end")
            if resolution.start_text and resolution.end_text:
                if resolution.start_text == resolution.end_text:
                    issues_found.append("Start equals end")
            
            if issues_found:
                print(f"⚠️  Issues: {', '.join(issues_found)}")
            else:
                print("✅ No obvious issues")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 40)


def interactive_performance_test():
    """Interactive mode for testing custom scenarios"""
    print("\n🚀 INTERACTIVE PERFORMANCE TEST")
    print("=" * 80)
    print("Enter slot combinations to test Absolute Resolver performance")
    print("Format: JSON with start_text, end_text, duration")
    print("Examples:")
    print('  {"start_text": "tomorrow", "end_text": null, "duration": "1h"}')
    print('  {"start_text": null, "end_text": "Friday", "duration": "2h"}')
    print("=" * 80)
    
    resolver = AbsoluteResolver()
    context_provider = ContextProvider(timezone="America/New_York")
    context = context_provider.get_context()
    
    while True:
        try:
            print("\n🔍 Enter slots JSON (or 'quit' to exit):")
            user_input = input().strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                print("⚠️  Please enter slots JSON")
                continue
            
            try:
                slots = json.loads(user_input)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON: {e}")
                continue
            
            print(f"\n🔄 Testing with Qwen2.5...")
            resolution = resolver.resolve_absolute_safe(slots, context)
            print(f"✅ Resolution: {resolution}")
            
            # Quick quality check
            quality = analyze_resolution_quality({'name': 'custom', 'slots': slots}, resolution, context)
            print(f"📊 Quality Score: {quality}/10")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🧪 ABSOLUTE RESOLVER PERFORMANCE TEST")
        print("=" * 80)
        print("Usage:")
        print("  python test_absolute_resolver_performance.py --test")
        print("  python test_absolute_resolver_performance.py --edge")
        print("  python test_absolute_resolver_performance.py --interactive")
        print("=" * 80)
        return
    
    arg = sys.argv[1]
    
    if arg == "--test":
        test_absolute_resolver_performance()
    elif arg == "--edge":
        test_specific_edge_cases()
    elif arg == "--interactive":
        interactive_performance_test()
    else:
        print(f"Unknown argument: {arg}")


if __name__ == "__main__":
    main()
