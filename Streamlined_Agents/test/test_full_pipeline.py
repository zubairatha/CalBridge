#!/usr/bin/env python3
"""
Full Pipeline Test: User Query → Slot Extractor → Absolute Resolver
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


def test_full_pipeline(query: str, timezone: str = "America/New_York"):
    """Test the full pipeline from user query to absolute resolution"""
    print("🚀 FULL PIPELINE TEST")
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
        
        # Summary
        print("📊 PIPELINE SUMMARY")
        print("=" * 80)
        print(f"Original Query: '{query}'")
        print(f"Extracted Slots: {slots.to_dict()}")
        print(f"Absolute Resolution: {resolution.to_dict()}")
        
        return {
            'user_query': user_query,
            'slots': slots,
            'resolution': resolution,
            'success': True
        }
        
    except Exception as e:
        print(f"❌ Pipeline Error: {e}")
        return {
            'query': query,
            'error': str(e),
            'success': False
        }


def test_multiple_queries():
    """Test multiple queries through the full pipeline"""
    print("🔍 TESTING MULTIPLE QUERIES")
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
        "Review documents this afternoon for 45 minutes before 5pm"
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test {i}: '{query}' ---")
        result = test_full_pipeline(query)
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


def interactive_mode():
    """Interactive mode for testing custom queries"""
    print("🚀 INTERACTIVE PIPELINE TEST")
    print("=" * 80)
    print("Enter queries to test through the full pipeline")
    print("Examples:")
    print("  - 'Complete Math HW by 14 Nov'")
    print("  - 'Call Mom tomorrow for 30 minutes'")
    print("  - 'Work on project from 9am to 5pm'")
    print("  - 'Buy groceries at the store'")
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
            
            test_full_pipeline(query)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🚀 FULL PIPELINE TEST TOOL")
        print("=" * 80)
        print("Usage:")
        print("  python test_full_pipeline.py 'your query here'")
        print("  python test_full_pipeline.py --multiple")
        print("  python test_full_pipeline.py --interactive")
        print("=" * 80)
        print("Examples:")
        print("  python test_full_pipeline.py 'Complete Math HW by 14 Nov'")
        print("  python test_full_pipeline.py 'Call Mom tomorrow for 30 minutes'")
        print("  python test_full_pipeline.py 'Work on project from 9am to 5pm'")
        print("=" * 80)
        return
    
    arg = sys.argv[1]
    
    if arg == "--multiple":
        test_multiple_queries()
    elif arg == "--interactive":
        interactive_mode()
    else:
        # Single query test
        test_full_pipeline(arg)


if __name__ == "__main__":
    main()
