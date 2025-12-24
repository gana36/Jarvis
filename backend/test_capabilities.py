"""Quick test to verify capabilities are listed correctly"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.orchestrator import OrchestratorService


async def test_capabilities():
    """Test that Jarvis lists capabilities when asked"""
    
    print("=" * 60)
    print("Testing: 'What can you do?' / 'What are you capable of?'")
    print("=" * 60)
    
    orchestrator = OrchestratorService()
    
    # Test various ways of asking
    questions = [
        "What can you do?",
        "What are you capable of doing?",
        "What are your capabilities?",
    ]
    
    for question in questions:
        print(f"\n📝 Question: '{question}'")
        result = await orchestrator.process_transcript(question)
        response = result['handler_response']['message']
        print(f"Response: {response}\n")
        
        # Check if response mentions key capabilities
        response_lower = response.lower()
        
        mentioned = []
        if "weather" in response_lower:
            mentioned.append("✅ weather")
        if "task" in response_lower:
            mentioned.append("✅ tasks")
        if "calendar" in response_lower:
            mentioned.append("✅ calendar")
        if "summar" in response_lower:
            mentioned.append("✅ summaries")
        if "remind" in response_lower:
            mentioned.append("✅ reminders")
        
        if mentioned:
            print(f"Capabilities mentioned: {', '.join(mentioned)}")
        else:
            print("⚠️  Note: Response may be more general")


if __name__ == "__main__":
    asyncio.run(test_capabilities())
