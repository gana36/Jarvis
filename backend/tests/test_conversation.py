"""Tests for orchestrator conversation enhancements"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.orchestrator import OrchestratorService


@pytest.mark.asyncio
async def test_general_chat_uses_real_gemini():
    """Test that GENERAL_CHAT handler uses real Gemini responses, not mocks"""
    
    # Create orchestrator
    orchestrator = OrchestratorService()
    
    # Mock Gemini service to return specific response
    mock_response = "Hello! How can I help you today?"
    orchestrator.gemini_service.generate_response = AsyncMock(return_value=mock_response)
    
    # Call handler directly
    result = await orchestrator._handle_general_chat("Hello", profile=None, history=None)
    
    # Verify response is from Gemini, not the mock message
    assert result["message"] == mock_response
    assert result["message"] != "I'm here to help! This is a mock conversational response. How can I assist you today?"
    assert result["type"] == "conversation"
    assert orchestrator.gemini_service.generate_response.called


@pytest.mark.asyncio
async def test_conversation_history_storage():
    """Test that conversation history is stored and limited correctly"""
    
    orchestrator = OrchestratorService()
    user_id = "test_user"
    
    # Add some messages
    orchestrator._add_to_history(user_id, "user", "First message")
    orchestrator._add_to_history(user_id, "model", "First response")
    orchestrator._add_to_history(user_id, "user", "Second message")
    orchestrator._add_to_history(user_id, "model", "Second response")
    
    # Get history
    history = orchestrator._get_conversation_history(user_id)
    
    # Verify history structure
    assert len(history) == 4
    assert history[0]["role"] == "user"
    assert history[0]["parts"] == "First message"
    assert history[1]["role"] == "model"
    assert history[1]["parts"] == "First response"
    
    # Test limit: add more than 10 messages
    for i in range(20):
        orchestrator._add_to_history(user_id, "user", f"Message {i}")
        orchestrator._add_to_history(user_id, "model", f"Response {i}")
    
    # Verify only last 10 are kept
    history = orchestrator._get_conversation_history(user_id)
    assert len(history) == 10
    assert history[-1]["parts"] == "Response 19"  # Last message


@pytest.mark.asyncio
async def test_conversation_history_passed_to_gemini():
    """Test that conversation history is passed to Gemini for context"""
    
    orchestrator = OrchestratorService()
    
    # Mock Gemini service
    orchestrator.gemini_service.generate_response = AsyncMock(return_value="Using history!")
    
    # Create fake history
    history = [
        {"role": "user", "parts": "My name is John"},
        {"role": "model", "parts": "Nice to meet you, John!"}
    ]
    
    # Call handler with history
    result = await orchestrator._handle_general_chat("What's my name?", profile=None, history=history)
    
    # Verify Gemini was called with history
    orchestrator.gemini_service.generate_response.assert_called_once()
    call_args = orchestrator.gemini_service.generate_response.call_args
    
    # Check that history was passed (3rd argument)
    assert call_args[0][2] == history or call_args[1].get('history') == history


@pytest.mark.asyncio  
async def test_profile_context_passed_to_gemini():
    """Test that user profile is passed to Gemini for personalization"""
    
    orchestrator = OrchestratorService()
    
    # Mock Gemini service
    orchestrator.gemini_service.generate_response = AsyncMock(return_value="Hello John!")
    
    # Create fake profile
    profile = {
        "name": "John",
        "timezone": "America/New_York",
        "dietary_preference": "vegetarian"
    }
    
    # Call handler with profile
    result = await orchestrator._handle_general_chat("Hi", profile=profile, history=None)
    
    # Verify Gemini was called with profile
    orchestrator.gemini_service.generate_response.assert_called_once()
    call_args = orchestrator.gemini_service.generate_response.call_args
    
    # Check that profile was passed (2nd argument)
    assert call_args[0][1] == profile or call_args[1].get('profile') == profile


@pytest.mark.asyncio
async def test_process_transcript_updates_history():
    """Test that process_transcript updates conversation history for GENERAL_CHAT"""
    
    orchestrator = OrchestratorService()
    user_id = "test_user"
    
    # Mock dependencies
    orchestrator.gemini_service.classify_intent = AsyncMock(
        return_value={"intent": "GENERAL_CHAT", "confidence": 0.9}
    )
    orchestrator.gemini_service.generate_response = AsyncMock(
        return_value="Hello! How are you?"
    )
    orchestrator._get_user_profile = AsyncMock(return_value={})
    
    # Process transcript
    await orchestrator.process_transcript("Hi Jarvis", user_id=user_id)
    
    # Verify history was updated
    history = orchestrator._get_conversation_history(user_id)
    assert len(history) == 2  # User message + assistant response
    assert history[0]["role"] == "user"
    assert history[0]["parts"] == "Hi Jarvis"
    assert history[1]["role"] == "model"
    assert history[1]["parts"] == "Hello! How are you?"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
