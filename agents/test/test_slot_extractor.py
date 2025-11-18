#!/usr/bin/env python3
"""
Interactive test script for testing custom queries with the Slot Extractor
Usage: python test_query.py "your query here"
"""
import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from user_query import UserQueryHandler
from slot_extractor import SlotExtractor


def test_single_query(query: str, timezone: str = "America/New_York"):
    """Test a single query and show detailed results"""
    print("🔍 TESTING QUERY")
    print("=" * 60)
    print(f"Query: '{query}'")
    print(f"Timezone: {timezone}")
    print("-" * 60)
    
    try:
        # Initialize components
        query_handler = UserQueryHandler(default_timezone=timezone)
        slot_extractor = SlotExtractor()
        
        # Step 1: Process User Query
        user_query = query_handler.process_query(query)
        print(f"✅ User Query: {user_query}")
        
        # Step 2: Extract Slots
        slots = slot_extractor.extract_slots_safe(user_query.query, user_query.timezone)
        print(f"🎯 Slots Extracted:")
        print(f"   • Start: {slots.start_text or 'None'}")
        print(f"   • End: {slots.end_text or 'None'}")
        print(f"   • Duration: {slots.duration or 'None'}")
        
        # Step 3: JSON Output
        json_output = slots.to_dict()
        print(f"📄 JSON: {json_output}")
        
        # Step 4: Analysis
        print(f"\n📊 Analysis:")
        has_start = slots.start_text is not None
        has_end = slots.end_text is not None
        has_duration = slots.duration is not None
        has_any = has_start or has_end or has_duration
        
        if has_any:
            print(f"   ✅ Time information detected")
            if has_start:
                print(f"   📅 Start time: '{slots.start_text}'")
            if has_end:
                print(f"   ⏰ End time: '{slots.end_text}'")
            if has_duration:
                print(f"   ⏱️  Duration: '{slots.duration}'")
        else:
            print(f"   ℹ️  No time information detected (all nulls)")
        
        return slots
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_multiple_queries(queries: list, timezone: str = "America/New_York"):
    """Test multiple queries"""
    print("🔍 TESTING MULTIPLE QUERIES")
    print("=" * 60)
    
    query_handler = UserQueryHandler(default_timezone=timezone)
    slot_extractor = SlotExtractor()
    
    results = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n{i}. Query: '{query}'")
        print("-" * 40)
        
        try:
            user_query = query_handler.process_query(query)
            slots = slot_extractor.extract_slots_safe(user_query.query, user_query.timezone)
            
            print(f"✅ Extracted: {slots}")
            
            # Quick analysis
            has_any = slots.start_text or slots.end_text or slots.duration
            status = "⏰ Has time info" if has_any else "ℹ️  No time info"
            print(f"   {status}")
            
            results.append({
                'query': query,
                'slots': slots,
                'has_time_info': bool(has_any)
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'query': query,
                'error': str(e),
                'has_time_info': False
            })
    
    # Summary
    print(f"\n📊 SUMMARY")
    print("=" * 60)
    total = len(results)
    successful = sum(1 for r in results if 'slots' in r)
    with_time = sum(1 for r in results if r.get('has_time_info', False))
    
    print(f"Total queries: {total}")
    print(f"Successful extractions: {successful}")
    print(f"With time information: {with_time}")
    print(f"Without time information: {total - with_time}")
    
    return results


def interactive_mode():
    """Interactive mode for testing queries"""
    print("🚀 INTERACTIVE SLOT EXTRACTOR TEST")
    print("=" * 60)
    print("Enter queries to test (type 'quit' to exit)")
    print("Examples:")
    print("  - 'Complete Math HW by 14 Nov'")
    print("  - 'Call Mom tomorrow for 30 minutes'")
    print("  - 'Buy groceries at the store'")
    print("  - 'Work on project from 9am to 5pm'")
    print("=" * 60)
    
    query_handler = UserQueryHandler()
    slot_extractor = SlotExtractor()
    
    while True:
        try:
            query = input("\n🔍 Enter query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not query:
                print("⚠️  Please enter a query")
                continue
            
            # Test the query
            user_query = query_handler.process_query(query)
            slots = slot_extractor.extract_slots_safe(user_query.query, user_query.timezone)
            
            print(f"🎯 Result: {slots}")
            
            # Quick analysis
            has_any = slots.start_text or slots.end_text or slots.duration
            if has_any:
                print("✅ Time information detected")
            else:
                print("ℹ️  No time information detected")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🚀 SLOT EXTRACTOR TEST TOOL")
        print("=" * 60)
        print("Usage:")
        print("  python test_query.py 'your query here'")
        print("  python test_query.py --interactive")
        print("  python test_query.py --examples")
        print("=" * 60)
        return
    
    arg = sys.argv[1]
    
    if arg == "--interactive":
        interactive_mode()
    elif arg == "--examples":
        example_queries = [
            "Complete Math HW by 14 Nov",
            "Call Mom tomorrow for 30 minutes",
            "Buy groceries at the store",
            "Work on project from 9am to 5pm",
            "Study for 2 hours tonight",
            "Meeting at 3pm for 1 hour",
            "Deadline is Friday",
            "Start next week, finish by EOM",
            "Review documents this afternoon for 45 minutes before 5pm",
            "ping Alex about the doc"
        ]
        test_multiple_queries(example_queries)
    else:
        # Single query test
        test_single_query(arg)


if __name__ == "__main__":
    main()
