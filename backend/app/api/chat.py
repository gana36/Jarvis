"""Text chat API endpoints"""
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.tts import get_tts_service
from app.middleware import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    """Request for text chat endpoint"""
    message: str
    voice_id: str | None = None


class ChatResponse(BaseModel):
    """Response for text chat endpoint"""
    success: bool
    user_message: str
    ai_response: str
    audio_base64: str | None = None
    intent: str | None = None
    confidence: float | None = None
    data: dict | None = None


@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Process text message and generate AI response.
    
    Args:
        request: ChatRequest with user message and optional voice_id
        user_id: Authenticated user ID
        
    Returns:
        AI response with optional TTS audio
    """
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )
    
    user_message = request.message.strip()
    logger.info(f"Processing text message from user {user_id}: '{user_message}'")
    
    try:
        # Use orchestrator for intent classification and routing
        from app.services.orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        orchestrator_result = await orchestrator.process_transcript(user_message, user_id)
        
        # Extract intent info
        intent = orchestrator_result["intent"]
        confidence = orchestrator_result["confidence"]
        
        # Get AI response
        ai_response = orchestrator_result["handler_response"]["message"]
        orchestrator_data = orchestrator_result["handler_response"].get("data")
        
        logger.info(f"AI Response: {ai_response}")
        
        # Convert AI response to speech if voice_id provided
        audio_base64 = None
        if request.voice_id:
            try:
                tts_service = get_tts_service()
                audio_base64 = tts_service.text_to_speech_base64(
                    ai_response,
                    voice_id=request.voice_id
                )
            except ValueError as e:
                logger.warning(f"TTS not configured: {e}")
            except Exception as e:
                logger.error(f"TTS generation failed: {e}")
        
        return ChatResponse(
            success=True,
            user_message=user_message,
            ai_response=ai_response,
            audio_base64=audio_base64,
            intent=intent,
            confidence=confidence,
            data=orchestrator_data,
        )
        
    except ValueError as e:
        # API key not configured
        logger.warning(f"Orchestrator/Gemini not configured: {e}")
        return ChatResponse(
            success=False,
            user_message=user_message,
            ai_response="AI responses not configured.",
            audio_base64=None,
            intent=None,
            confidence=None,
        )
    except Exception as e:
        logger.error(f"Message processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Message processing failed: {str(e)}"
        )
