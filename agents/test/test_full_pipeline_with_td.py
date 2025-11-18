#!/usr/bin/env python3
"""
Full Pipeline Test: User Query → Slot Extractor → Absolute Resolver → Time Standardizer → Task Difficulty Analyzer
"""
import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from user_query import UserQueryHandler
from slot_extractor import SlotExtractor
from absolute_resolver import AbsoluteResolver
from context_provider import ContextProvider
from time_standardizer import TimeStandardizer
from task_difficulty_analyzer import TaskDifficultyAnalyzer


def test_full_pipeline_with_td(query: str, timezone: str = "America/New_York"):
    """Test the full pipeline from user query to task difficulty analysis"""
    print("🚀 FULL PIPELINE TEST WITH TASK DIFFICULTY ANALYZER")
    print("=" * 80)
    print(f"Query: '{query}'")
    print(f"Timezone: {timezone}")
    print("-" * 80)
    
    try:
        # Step 1: User Query Handler
        print("📝 STEP 1: User Query Handler")
        query_handler = UserQueryHandler(default_timezone=timezone)
        user_query = query_handler.process_query(query)
        print(f"✅ User Query: {user_query}")
        print()
        
        # Step 2: Slot Extractor
        print("🎯 STEP 2: Slot Extractor")
        slot_extractor = SlotExtractor()
        slots = slot_extractor.extract_slots_safe(user_query.query, user_query.timezone)
        print(f"✅ Slots Extracted: {slots}")
        print(f"   • Start: {slots.start_text or 'None'}")
        print(f"   • End: {slots.end_text or 'None'}")
        print(f"   • Duration: {slots.duration or 'None'}")
        print()
        
        # Step 3: Absolute Resolver
        print("⏰ STEP 3: Absolute Resolver")
        context_provider = ContextProvider(timezone=timezone)
        context = context_provider.get_context()
        
        print("📅 Context Information:")
        print(f"   • Current Time: {context['NOW_ISO']}")
        print(f"   • Today: {context['TODAY_HUMAN']}")
        print(f"   • End of Today: {context['END_OF_TODAY']}")
        print()
        
        absolute_resolver = AbsoluteResolver()
        resolution = absolute_resolver.resolve_absolute_safe(slots.to_dict(), context)
        print(f"✅ Absolute Resolution: {resolution}")
        print(f"   • Start: {resolution.start_text}")
        print(f"   • End: {resolution.end_text}")
        print(f"   • Duration: {resolution.duration or 'None'}")
        print()
        
        # Step 4: Time Standardizer
        print("🔧 STEP 4: Time Standardizer")
        time_standardizer = TimeStandardizer()
        standardization = time_standardizer.standardize_safe(resolution.to_dict(), timezone)
        print(f"✅ Time Standardization: {standardization}")
        print(f"   • Start ISO: {standardization.start}")
        print(f"   • End ISO: {standardization.end}")
        print(f"   • Duration ISO: {standardization.duration or 'None'}")
        print()
        
        # Step 5: Task Difficulty Analyzer
        print("📊 STEP 5: Task Difficulty Analyzer")
        task_analyzer = TaskDifficultyAnalyzer()
        analysis = task_analyzer.analyze_safe(user_query.query, standardization.duration)
        print(f"✅ Task Analysis: {analysis}")
        print(f"   • Calendar: {analysis.calendar or 'None'}")
        print(f"   • Type: {analysis.type}")
        print(f"   • Title: {analysis.title}")
        print(f"   • Duration: {analysis.duration or 'None'}")
        print()
        
        # Final Summary
        print("📊 FULL PIPELINE SUMMARY")
        print("=" * 80)
        print(f"Original Query: '{query}'")
        print(f"\n1. Extracted Slots: {json.dumps(slots.to_dict(), indent=2)}")
        print(f"\n2. Absolute Resolution: {json.dumps(resolution.to_dict(), indent=2)}")
        print(f"\n3. Time Standardization: {json.dumps(standardization.to_dict(), indent=2)}")
        print(f"\n4. Task Difficulty Analysis: {json.dumps(analysis.to_dict(), indent=2)}")
        
        # Final Output (ready for calendar creation)
        print("\n" + "=" * 80)
        print("🎯 FINAL OUTPUT (Ready for CalBridge)")
        print("=" * 80)
        final_output = {
            "title": analysis.title,
            "start_iso": standardization.start,
            "end_iso": standardization.end,
            "calendar_id": analysis.calendar,
            "type": analysis.type,
            "duration": analysis.duration
        }
        print(json.dumps(final_output, indent=2))
        
        return {
            'user_query': user_query,
            'slots': slots,
            'resolution': resolution,
            'standardization': standardization,
            'analysis': analysis,
            'final_output': final_output,
            'success': True
        }
        
    except Exception as e:
        import traceback
        print(f"❌ Pipeline Error: {e}")
        traceback.print_exc()
        return {
            'query': query,
            'error': str(e),
            'success': False
        }


def test_multiple_queries_with_td():
    """Test multiple queries through the full pipeline with Task Difficulty Analyzer"""
    print("🔍 TESTING MULTIPLE QUERIES WITH TASK DIFFICULTY ANALYZER")
    print("=" * 80)
    
    test_queries = [
        "Call Mom tomorrow for 30 minutes",
        "Finish project proposal by Nov 15",
        "Send the signed NDA to the client",
        "Buy groceries and fruits",
        "Prepare onboarding plan for new hire",
        "Meeting with team for 1 hour",
        "Work on project from 9am to 5pm",
        "Study for 2 hours tonight",
        "Pick up package from post office",
        "Research and write quarterly report"
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"--- Test {i}/{len(test_queries)}: '{query}' ---")
        print(f"{'='*80}\n")
        result = test_full_pipeline_with_td(query)
        results.append(result)
        
        if result['success']:
            print("\n✅ Pipeline completed successfully")
        else:
            print("\n❌ Pipeline failed")
        
        print("\n" + "="*80)
    
    # Summary
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"\n📊 FINAL SUMMARY")
    print("=" * 80)
    print(f"Total queries: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success rate: {successful/total*100:.1f}%")
    
    # Breakdown by type
    if successful > 0:
        simple_count = sum(1 for r in results if r.get('success') and r.get('analysis', {}).type == 'simple')
        complex_count = sum(1 for r in results if r.get('success') and r.get('analysis', {}).type == 'complex')
        print(f"\nTask Classification:")
        print(f"  Simple: {simple_count}")
        print(f"  Complex: {complex_count}")
    
    return results


def test_user_examples():
    """Test with user-provided examples"""
    print("\n🔍 TESTING USER PROVIDED EXAMPLES")
    print("=" * 80)
    
    user_examples = [
        {
            "query": "Meeting with team",
            "duration_expectation": "PT30M",  # Expected to extract duration
            "start": "2025-11-05T00:00:00-05:00",
            "end": "2025-11-05T23:59:59-05:00"
        },
        {
            "query": "Call mom",
            "duration_expectation": None,
            "start": "2025-11-05T00:00:00-05:00",
            "end": "2025-11-05T23:59:59-05:00"
        },
        {
            "query": "Prepare project proposal",
            "duration_expectation": None,  # Might extract duration, but if not, should be complex
            "start": "2025-11-05T00:00:00-05:00",
            "end": "2025-11-05T23:59:59-05:00"
        }
    ]
    
    for i, example in enumerate(user_examples, 1):
        print(f"\n--- User Example {i} ---")
        print(f"Query: '{example['query']}'")
        print(f"Expected duration: {example['duration_expectation']}")
        print("-" * 60)
        
        result = test_full_pipeline_with_td(example['query'])
        
        if result['success']:
            print("\n✅ Analysis completed successfully")
        else:
            print("\n❌ Analysis failed")
        
        print("\n" + "="*80)


def interactive_mode_with_td():
    """Interactive mode for testing custom queries with Task Difficulty Analyzer"""
    print("🚀 INTERACTIVE PIPELINE TEST WITH TASK DIFFICULTY ANALYZER")
    print("=" * 80)
    print("Enter queries to test through the full pipeline")
    print("Examples:")
    print("  - 'Call Mom tomorrow for 30 minutes'")
    print("  - 'Finish project proposal by Nov 15'")
    print("  - 'Buy groceries and fruits'")
    print("  - 'Meeting with team'")
    print("=" * 80)
    
    while True:
        try:
            query = input("\n🔍 Enter query (or 'quit' to exit): ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not query:
                print("⚠️  Please enter a query")
                continue
            
            timezone = input("Enter timezone (default: America/New_York): ").strip()
            if not timezone:
                timezone = "America/New_York"
            
            test_full_pipeline_with_td(query, timezone)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def test_specific_scenarios():
    """Test specific scenarios important for the full pipeline"""
    print("🎯 TESTING SPECIFIC SCENARIOS")
    print("=" * 80)
    
    scenarios = [
        {
            "name": "Simple task with duration",
            "query": "Call mom tomorrow for 20 minutes",
            "description": "Should classify as simple, assign Home calendar"
        },
        {
            "name": "Complex work task",
            "query": "Finish project proposal by Nov 15",
            "description": "Should classify as complex, assign Work calendar"
        },
        {
            "name": "Simple work action",
            "query": "Send the signed NDA to the client",
            "description": "Should classify as simple, assign Work calendar"
        },
        {
            "name": "Personal simple task",
            "query": "Buy groceries and fruits",
            "description": "Should classify as simple, assign Home calendar"
        },
        {
            "name": "Complex multi-step task",
            "query": "Prepare onboarding plan for new hire",
            "description": "Should classify as complex, assign Work calendar"
        },
        {
            "name": "No time information",
            "query": "Buy groceries",
            "description": "Should handle gracefully with default times"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Scenario {i}: {scenario['name']} ---")
        print(f"Description: {scenario['description']}")
        print(f"Query: '{scenario['query']}'")
        print("-" * 60)
        
        result = test_full_pipeline_with_td(scenario['query'])
        
        if result['success']:
            print("\n✅ Scenario completed successfully")
        else:
            print("\n❌ Scenario failed")
        
        print("\n" + "="*80)


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🚀 FULL PIPELINE TEST WITH TASK DIFFICULTY ANALYZER")
        print("=" * 80)
        print("Usage:")
        print("  python test_full_pipeline_with_td.py 'your query here'")
        print("  python test_full_pipeline_with_td.py --multiple")
        print("  python test_full_pipeline_with_td.py --interactive")
        print("  python test_full_pipeline_with_td.py --scenarios")
        print("  python test_full_pipeline_with_td.py --user-examples")
        print("=" * 80)
        print("Examples:")
        print("  python test_full_pipeline_with_td.py 'Call Mom tomorrow for 30 minutes'")
        print("  python test_full_pipeline_with_td.py 'Finish project proposal by Nov 15'")
        print("  python test_full_pipeline_with_td.py 'Buy groceries and fruits'")
        print("=" * 80)
        return
    
    arg = sys.argv[1]
    
    if arg == "--multiple":
        test_multiple_queries_with_td()
    elif arg == "--interactive":
        interactive_mode_with_td()
    elif arg == "--scenarios":
        test_specific_scenarios()
    elif arg == "--user-examples":
        test_user_examples()
    else:
        # Single query test
        test_full_pipeline_with_td(arg)


if __name__ == "__main__":
    main()

