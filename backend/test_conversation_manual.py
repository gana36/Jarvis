"""Manual test script for conversation enhancements"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.orchestrator import OrchestratorService


async def test_general_chat():
    """Test GENERAL_CHAT with real Gemini responses"""
    
    print("=" * 60)
    print("TEST 1: GENERAL_CHAT uses real Gemini (not mock)")
    print("=" * 60)
    
    orchestrator = OrchestratorService()
    
    # Test 1: Basic conversation
    print("\n📝 Test: 'Hello Jarvis, how are you?'")
    result = await orchestrator.process_transcript("Hello Jarvis, how are you?")
    
    print(f"Intent: {result['intent']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Response: {result['handler_response']['message']}")
    
    # Check it's NOT the mock response
    is_mock = "mock conversational response" in result['handler_response']['message'].lower()
    
    if is_mock:
        print("❌ FAILED: Still using mock response!")
        return False
    else:
        print("✅ PASSED: Using real Gemini response!")
    
    return True


async def test_conversation_memory():
    """Test conversation memory works"""
    
    print("\n" + "=" * 60)
    print("TEST 2: Conversation Memory")
    print("=" * 60)
    
    orchestrator = OrchestratorService()
    user_id = "test_user_123"
    
    # First message: tell Jarvis your name
    print("\n📝 Message 1: 'My name is Alice'")
    result1 = await orchestrator.process_transcript("My name is Alice", user_id=user_id)
    print(f"Response: {result1['handler_response']['message']}")
    
    # Check history
    history = orchestrator._get_conversation_history(user_id)
    print(f"\n📊 History after message 1: {len(history)} messages")
    
    if len(history) != 2:
        print(f"❌ FAILED: Expected 2 messages in history, got {len(history)}")
        return False
    
    # Second message: ask Jarvis to remember
    print("\n📝 Message 2: 'What's my name?'")
    result2 = await orchestrator.process_transcript("What's my name?", user_id=user_id)
    print(f"Response: {result2['handler_response']['message']}")
    
    # Check if response contains "Alice" (should remember from history)
    contains_name = "alice" in result2['handler_response']['message'].lower()
    
    history = orchestrator._get_conversation_history(user_id)
    print(f"\n📊 History after message 2: {len(history)} messages")
    
    if len(history) != 4:
        print(f"❌ FAILED: Expected 4 messages in history, got {len(history)}")
        return False
    
    if contains_name:
        print("✅ PASSED: Jarvis remembered the name from history!")
    else:
        print("⚠️  WARNING: Response may not include name, but history is being tracked")
    
    return True


async def test_history_limit():
    """Test that history is limited to 10 messages"""
    
    print("\n" + "=" * 60)
    print("TEST 3: History Limit (10 messages)")
    print("=" * 60)
    
    orchestrator = OrchestratorService()
    user_id = "test_limit_user"
    
    # Add 20 messages (10 exchanges)
    print("\n📝 Adding 20 messages (10 exchanges)...")
    for i in range(10):
        orchestrator._add_to_history(user_id, "user", f"Message {i}")
        orchestrator._add_to_history(user_id, "model", f"Response {i}")
    
    history = orchestrator._get_conversation_history(user_id)
    
    print(f"📊 History length: {len(history)}")
    print(f"📊 Oldest message: {history[0]['parts']}")
    print(f"📊 Newest message: {history[-1]['parts']}")
    
    if len(history) == 10:
        print("✅ PASSED: History correctly limited to 10 messages!")
        return True
    else:
        print(f"❌ FAILED: Expected 10 messages, got {len(history)}")
        return False


async def test_streaming_with_history():
    """Test streaming mode uses history"""
    
    print("\n" + "=" * 60)
    print("TEST 4: Streaming with History")
    print("=" * 60)
    
    orchestrator = OrchestratorService()
    user_id = "test_stream_user"
    
    # First message via streaming
    print("\n📝 Streaming Message 1: 'I love pizza'")
    full_response = ""
    
    async for chunk, intent, confidence in orchestrator.process_transcript_stream("I love pizza", user_id=user_id):
        full_response += chunk
    
    print(f"Response: {full_response}")
    
    # Check history
    history = orchestrator._get_conversation_history(user_id)
    print(f"\n📊 History after streaming: {len(history)} messages")
    
    if len(history) == 2:
        print("✅ PASSED: Streaming updates history correctly!")
        return True
    else:
        print(f"❌ FAILED: Expected 2 messages in history, got {len(history)}")
        return False


async def main():
    """Run all tests"""
    
    print("\n" + "🧪" * 30)
    print("JARVIS CONVERSATION ENHANCEMENT TESTS")
    print("🧪" * 30)
    
    try:
        results = []
        
        # Run tests
        results.append(await test_general_chat())
        results.append(await test_conversation_memory())
        results.append(await test_history_limit())
        results.append(await test_streaming_with_history())
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(results)
        total = len(results)
        
        print(f"\n✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if passed == total:
            print("\n🎉 All tests PASSED!")
        else:
            print("\n⚠️  Some tests failed, please review above")
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
