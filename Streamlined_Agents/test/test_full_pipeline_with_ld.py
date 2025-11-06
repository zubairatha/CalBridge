#!/usr/bin/env python3
"""
Full Pipeline Test: User Query → Slot Extractor → Absolute Resolver → Time Standardizer → Task Difficulty Analyzer → LLM Decomposer
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
from llm_decomposer import LLMDecomposer


def test_full_pipeline_with_ld(query: str, timezone: str = "America/New_York"):
    """Test the full pipeline from user query to task decomposition (if complex)"""
    print("🚀 FULL PIPELINE TEST WITH LLM DECOMPOSER")
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
        
        # Step 6: LLM Decomposer (only for complex tasks)
        decomposition = None
        if analysis.type == "complex":
            print("🔨 STEP 6: LLM Decomposer (Complex Task)")
            decomposer = LLMDecomposer()
            decomposition = decomposer.decompose_safe(analysis.to_dict())
            print(f"✅ Task Decomposition: {len(decomposition.subtasks)} subtasks")
            for i, st in enumerate(decomposition.subtasks, 1):
                print(f"   {i}. {st.title} ({st.duration})")
            print()
        else:
            print("⏭️  STEP 6: LLM Decomposer (Skipped - Simple Task)")
            print("   Simple tasks don't need decomposition")
            print()
        
        # Final Summary
        print("📊 FULL PIPELINE SUMMARY")
        print("=" * 80)
        print(f"Original Query: '{query}'")
        print(f"\n1. Extracted Slots: {json.dumps(slots.to_dict(), indent=2)}")
        print(f"\n2. Absolute Resolution: {json.dumps(resolution.to_dict(), indent=2)}")
        print(f"\n3. Time Standardization: {json.dumps(standardization.to_dict(), indent=2)}")
        print(f"\n4. Task Difficulty Analysis: {json.dumps(analysis.to_dict(), indent=2)}")
        
        if decomposition:
            print(f"\n5. Task Decomposition: {json.dumps(decomposition.to_dict(), indent=2)}")
        
        # Final Output (ready for calendar creation)
        print("\n" + "=" * 80)
        print("🎯 FINAL OUTPUT (Ready for CalBridge)")
        print("=" * 80)
        
        if decomposition:
            # Complex task - output with subtasks
            final_output = {
                "calendar_id": decomposition.calendar,
                "type": decomposition.type,
                "title": decomposition.title,
                "subtasks": [
                    {
                        "title": st.title,
                        "duration": st.duration,
                        "start_iso": standardization.start,  # Will be scheduled separately for each subtask
                        "end_iso": standardization.end
                    }
                    for st in decomposition.subtasks
                ]
            }
        else:
            # Simple task - output without subtasks
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
            'decomposition': decomposition,
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


def test_multiple_queries_with_ld():
    """Test multiple queries through the full pipeline with LLM Decomposer"""
    print("🔍 TESTING MULTIPLE QUERIES WITH LLM DECOMPOSER")
    print("=" * 80)
    
    test_queries = [
        # Simple tasks (should skip decomposition)
        "Call Mom tomorrow for 30 minutes",
        "Send the signed NDA to the client",
        "Buy groceries and fruits",
        
        # Complex tasks (should be decomposed)
        "Finish project proposal by Nov 15",
        "Prepare onboarding plan for new hire",
        "Research and write quarterly report",
        "Plan 5-day Japan trip",
        "Organize team meeting with stakeholders"
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"--- Test {i}/{len(test_queries)}: '{query}' ---")
        print(f"{'='*80}\n")
        result = test_full_pipeline_with_ld(query)
        results.append(result)
        
        if result['success']:
            task_type = result.get('analysis', {}).type
            has_decomposition = result.get('decomposition') is not None
            
            if task_type == 'complex' and has_decomposition:
                print("\n✅ Pipeline completed successfully (Complex → Decomposed)")
            elif task_type == 'simple' and not has_decomposition:
                print("\n✅ Pipeline completed successfully (Simple → No Decomposition)")
            else:
                print("\n⚠️  Pipeline completed but decomposition logic may be incorrect")
        else:
            print("\n❌ Pipeline failed")
        
        print("\n" + "="*80)
    
    # Summary
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    simple_count = sum(1 for r in results if r.get('success') and r.get('analysis', {}).type == 'simple')
    complex_count = sum(1 for r in results if r.get('success') and r.get('analysis', {}).type == 'complex')
    decomposed_count = sum(1 for r in results if r.get('success') and r.get('decomposition') is not None)
    
    print(f"\n📊 FINAL SUMMARY")
    print("=" * 80)
    print(f"Total queries: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success rate: {successful/total*100:.1f}%")
    print(f"\nTask Classification:")
    print(f"  Simple: {simple_count}")
    print(f"  Complex: {complex_count}")
    print(f"  Decomposed: {decomposed_count}")
    
    return results


def test_simple_vs_complex():
    """Test that simple tasks skip decomposition and complex tasks get decomposed"""
    print("\n🔍 TESTING SIMPLE VS COMPLEX TASK HANDLING")
    print("=" * 80)
    
    test_cases = [
        {
            "name": "Simple Task",
            "query": "Call mom tomorrow for 20 minutes",
            "expected_type": "simple",
            "should_decompose": False
        },
        {
            "name": "Complex Task",
            "query": "Finish project proposal by Nov 15",
            "expected_type": "complex",
            "should_decompose": True
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']}: '{test_case['query']}' ---")
        print(f"Expected: type={test_case['expected_type']}, decompose={test_case['should_decompose']}")
        print("-" * 60)
        
        result = test_full_pipeline_with_ld(test_case['query'])
        
        if result['success']:
            actual_type = result.get('analysis', {}).type
            has_decomposition = result.get('decomposition') is not None
            
            type_match = actual_type == test_case['expected_type']
            decompose_match = has_decomposition == test_case['should_decompose']
            
            print(f"\nResults:")
            print(f"  Type: {actual_type} {'✓' if type_match else '✗'}")
            print(f"  Decomposed: {has_decomposition} {'✓' if decompose_match else '✗'}")
            
            if type_match and decompose_match:
                print("  ✅ Test PASSED")
            else:
                print("  ⚠️  Test PARTIAL")
        else:
            print(f"  ❌ Test FAILED: {result.get('error')}")
        
        print("\n" + "="*80)


def interactive_mode_with_ld():
    """Interactive mode for testing custom queries with LLM Decomposer"""
    print("🚀 INTERACTIVE PIPELINE TEST WITH LLM DECOMPOSER")
    print("=" * 80)
    print("Enter queries to test through the full pipeline")
    print("Examples:")
    print("  - 'Call Mom tomorrow for 30 minutes' (Simple)")
    print("  - 'Finish project proposal by Nov 15' (Complex)")
    print("  - 'Plan 5-day Japan trip' (Complex)")
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
            
            test_full_pipeline_with_ld(query, timezone)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🚀 FULL PIPELINE TEST WITH LLM DECOMPOSER")
        print("=" * 80)
        print("Usage:")
        print("  python test_full_pipeline_with_ld.py 'your query here'")
        print("  python test_full_pipeline_with_ld.py --multiple")
        print("  python test_full_pipeline_with_ld.py --simple-vs-complex")
        print("  python test_full_pipeline_with_ld.py --interactive")
        print("=" * 80)
        print("Examples:")
        print("  python test_full_pipeline_with_ld.py 'Call Mom tomorrow for 30 minutes'")
        print("  python test_full_pipeline_with_ld.py 'Finish project proposal by Nov 15'")
        print("  python test_full_pipeline_with_ld.py 'Plan 5-day Japan trip'")
        print("=" * 80)
        return
    
    arg = sys.argv[1]
    
    if arg == "--multiple":
        test_multiple_queries_with_ld()
    elif arg == "--simple-vs-complex":
        test_simple_vs_complex()
    elif arg == "--interactive":
        interactive_mode_with_ld()
    else:
        # Single query test
        test_full_pipeline_with_ld(arg)


if __name__ == "__main__":
    main()


