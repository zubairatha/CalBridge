#!/usr/bin/env python3
"""
Full Pipeline Test: User Query → Slot Extractor → Absolute Resolver → Time Standardizer
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


def test_full_pipeline_with_ts(query: str, timezone: str = "America/New_York"):
    """Test the full pipeline from user query to time standardization"""
    print("🚀 FULL PIPELINE TEST WITH TIME STANDARDIZER")
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
        
        # Summary
        print("📊 FULL PIPELINE SUMMARY")
        print("=" * 80)
        print(f"Original Query: '{query}'")
        print(f"Extracted Slots: {slots.to_dict()}")
        print(f"Absolute Resolution: {resolution.to_dict()}")
        print(f"Time Standardization: {standardization.to_dict()}")
        
        return {
            'user_query': user_query,
            'slots': slots,
            'resolution': resolution,
            'standardization': standardization,
            'success': True
        }
        
    except Exception as e:
        print(f"❌ Pipeline Error: {e}")
        return {
            'query': query,
            'error': str(e),
            'success': False
        }


def test_multiple_queries_with_ts():
    """Test multiple queries through the full pipeline with Time Standardizer"""
    print("🔍 TESTING MULTIPLE QUERIES WITH TIME STANDARDIZER")
    print("=" * 80)
    
    test_queries = [
        "Complete Math HW by 14 Nov",
        "Call Mom tomorrow for 30 minutes",
        "Plan John's Bday by 21st November",
        "Work on project from 9am to 5pm",
        "Study for 2 hours tonight",
        "Meeting at 3pm for 1 hour",
        "Deadline is Friday",
        "Start next week, finish by EOM",
        "Buy groceries at the store",
        "Review documents this afternoon for 45 minutes before 5pm",
        "Take a 1.5 hour break this evening",
        "Finish report by end of month",
        "Schedule meeting for next Monday morning",
        "Work on presentation for 2h30m tomorrow"
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test {i}: '{query}' ---")
        result = test_full_pipeline_with_ts(query)
        results.append(result)
        
        if result['success']:
            print("✅ Pipeline completed successfully")
        else:
            print("❌ Pipeline failed")
        
        print("\n" + "="*80)
    
    # Summary
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"\n📊 FINAL SUMMARY")
    print(f"Total queries: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success rate: {successful/total*100:.1f}%")
    
    return results


def interactive_mode_with_ts():
    """Interactive mode for testing custom queries with Time Standardizer"""
    print("🚀 INTERACTIVE PIPELINE TEST WITH TIME STANDARDIZER")
    print("=" * 80)
    print("Enter queries to test through the full pipeline")
    print("Examples:")
    print("  - 'Complete Math HW by 14 Nov'")
    print("  - 'Call Mom tomorrow for 30 minutes'")
    print("  - 'Work on project from 9am to 5pm'")
    print("  - 'Buy groceries at the store'")
    print("  - 'Take a 1.5 hour break this evening'")
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
            
            test_full_pipeline_with_ts(query, timezone)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def test_specific_scenarios():
    """Test specific scenarios that are important for Time Standardizer"""
    print("🎯 TESTING SPECIFIC SCENARIOS")
    print("=" * 80)
    
    scenarios = [
        {
            "name": "EOD semantics test",
            "query": "Finish report by end of day",
            "description": "Should result in 11:59:59 seconds"
        },
        {
            "name": "Duration normalization test",
            "query": "Take a 1.5 hour break",
            "description": "Should normalize 1.5h to PT1H30M"
        },
        {
            "name": "Cross-midnight test",
            "query": "Work from 11pm to 2am",
            "description": "Should handle cross-midnight correctly"
        },
        {
            "name": "No time information test",
            "query": "Buy groceries",
            "description": "Should handle no time info gracefully"
        },
        {
            "name": "Complex duration test",
            "query": "Study for 2h30m tomorrow",
            "description": "Should handle compound duration"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Scenario {i}: {scenario['name']} ---")
        print(f"Description: {scenario['description']}")
        print(f"Query: '{scenario['query']}'")
        print("-" * 40)
        
        result = test_full_pipeline_with_ts(scenario['query'])
        
        if result['success']:
            print("✅ Scenario completed successfully")
        else:
            print("❌ Scenario failed")
        
        print("\n" + "="*80)


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🚀 FULL PIPELINE TEST WITH TIME STANDARDIZER")
        print("=" * 80)
        print("Usage:")
        print("  python test_full_pipeline_with_ts.py 'your query here'")
        print("  python test_full_pipeline_with_ts.py --multiple")
        print("  python test_full_pipeline_with_ts.py --interactive")
        print("  python test_full_pipeline_with_ts.py --scenarios")
        print("=" * 80)
        print("Examples:")
        print("  python test_full_pipeline_with_ts.py 'Complete Math HW by 14 Nov'")
        print("  python test_full_pipeline_with_ts.py 'Call Mom tomorrow for 30 minutes'")
        print("  python test_full_pipeline_with_ts.py 'Work on project from 9am to 5pm'")
        print("  python test_full_pipeline_with_ts.py 'Take a 1.5 hour break this evening'")
        print("=" * 80)
        return
    
    arg = sys.argv[1]
    
    if arg == "--multiple":
        test_multiple_queries_with_ts()
    elif arg == "--interactive":
        interactive_mode_with_ts()
    elif arg == "--scenarios":
        test_specific_scenarios()
    else:
        # Single query test
        test_full_pipeline_with_ts(arg)


if __name__ == "__main__":
    main()
