#!/usr/bin/env python3
"""Test script for intent classification"""
import sys
sys.path.insert(0, '/Users/karthik/Desktop/jarvis/backend')

from app.config import get_settings
from app.services.gemini import get_gemini_service
import asyncio

test_cases = [
    "What's the weather like today?",
    "Add buy milk to my todo list",
    "Give me a summary of my day",
    "How does photosynthesis work?",
    "Hello, how are you?",
    "What temperature will it be tomorrow?",
    "Remind me to call mom",
    "What did I do today?",
    "Teach me about black holes",
    "Tell me a joke",
]

async def test_intent_classification():
    """Test intent classification with various inputs"""
    gemini_service = get_gemini_service()
    
    print("Testing Intent Classification")
    print("=" * 60)
    
    for test_input in test_cases:
        result = await gemini_service.classify_intent(test_input)
        print(f"\nInput: {test_input}")
        print(f"Intent: {result['intent']}")
        print(f"Confidence: {result['confidence']:.2f}")

if __name__ == "__main__":
    asyncio.run(test_intent_classification())
