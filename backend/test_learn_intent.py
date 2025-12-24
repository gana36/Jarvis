"""Test LEARN intent with Google Search grounding"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.orchestrator import OrchestratorService


async def test_learn_intent():
    """Test LEARN intent with various educational questions"""
    
    print("=" * 70)
    print("TESTING LEARN INTENT WITH GOOGLE SEARCH GROUNDING")
    print("=" * 70)
    
    orchestrator = OrchestratorService()
    
    # Test questions covering different types
    test_questions = [
        {
            "category": "Factual",
            "question": "Who invented the telephone?"
        },
        {
            "category": "Explanation",
            "question": "How does photosynthesis work?"
        },
        {
            "category": "Current Events",
            "question": "What are the latest developments in AI?"
        },
        {
            "category": "Simple Fact",
            "question": "When did World War II end?"
        }
    ]
    
    results = []
    
    for test in test_questions:
        print(f"\n{'=' * 70}")
        print(f"📚 Category: {test['category']}")
        print(f"❓ Question: \"{test['question']}\"")
        print("-" * 70)
        
        try:
            result = await orchestrator.process_transcript(test['question'])
            
            # Check if routed to LEARN
            intent = result['intent']
            handler_response = result['handler_response']
            
            print(f"✓ Intent: {intent}")
            print(f"✓ Confidence: {result['confidence']}")
            
            # Extract data
            answer = handler_response['data'].get('answer', 'N/A')
            citations = handler_response['data'].get('citations', [])
            message = handler_response['message']
            
            print(f"\n📖 Answer:")
            print(f"   {answer}")
            
            if citations:
                print(f"\n🔗 Citations ({len(citations)}):")
                for i, cite in enumerate(citations, 1):
                    print(f"   {i}. {cite}")
            else:
                print(f"\n⚠️  No citations found")
            
            print(f"\n🗣️  Voice Response:")
            print(f"   {message}")
            
            # Evaluate result
            has_citations = len(citations) > 0
            is_learn_intent = intent == "LEARN"
            has_answer = len(answer) > 20
            
            test_passed = has_answer  # Minimum requirement
            
            results.append({
                'question': test['question'],
                'passed': test_passed,
                'citations': len(citations),
                'intent_correct': is_learn_intent
            })
            
            if test_passed:
                print(f"\n✅ PASSED")
            else:
                print(f"\n❌ FAILED (Answer too short or missing)")
                
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'question': test['question'],
                'passed': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\n{'=' * 70}")
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    
    print(f"\n✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    # Citation stats
    total_citations = sum(r.get('citations', 0) for r in results)
    avg_citations = total_citations / total if total > 0 else 0
    
    print(f"\n📊 Average citations per question: {avg_citations:.1f}")
    
    if passed == total:
        print(f"\n🎉 All tests PASSED!")
    else:
        print(f"\n⚠️  Some tests failed")
    
    return results


async def main():
    """Run tests"""
    try:
        await test_learn_intent()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
