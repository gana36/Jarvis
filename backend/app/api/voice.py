"""Voice API endpoints for audio ingestion"""
import logging

from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel

from app.services.stt import get_stt_service
from app.services.gemini import get_gemini_service

logger = logging.getLogger(__name__)
router = APIRouter()


class IngestResponse(BaseModel):
    """Response for audio ingest endpoint"""

    success: bool
    message: str
    audio_size_bytes: int
    transcript: str
    ai_response: str


@router.post("/ingest", response_model=IngestResponse)
async def ingest_audio(audio: UploadFile = File(...)):
    """
    Ingest audio from frontend and transcribe using Google Cloud Speech-to-Text.
    
    Args:
        audio: Audio file (webm format expected)
        
    Returns:
        Success status, audio metadata, and transcript
    """
    # Validate file type
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=400, detail=f"Invalid file type: {audio.content_type}"
        )

    # Read audio data
    audio_data = await audio.read()
    audio_size = len(audio_data)

    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    if audio_size > max_size:
        raise HTTPException(
            status_code=400, detail=f"File too large: {audio_size} bytes (max {max_size})"
        )

    # Log audio receipt
    logger.info(f"Received audio: {audio.filename}, size: {audio_size} bytes")

    # Transcribe audio using Google Cloud Speech-to-Text
    try:
        stt_service = get_stt_service()
        transcript = await stt_service.transcribe_audio(audio_data)
        
        if not transcript:
            logger.warning("No speech detected in audio")
            transcript = ""
        
        logger.info(f"Transcription complete: '{transcript}'")
        
        # Generate AI response using Gemini Flash
        ai_response = ""
        if transcript:
            try:
                gemini_service = get_gemini_service()
                ai_response = await gemini_service.generate_response(transcript)
            except ValueError as e:
                # API key not configured
                logger.warning(f"Gemini not configured: {e}")
                ai_response = "AI responses not configured."
            except Exception as e:
                logger.error(f"Gemini generation failed: {e}")
                ai_response = "I'm having trouble thinking right now."
        else:
            ai_response = "I didn't catch that. Could you repeat?"
        
        return IngestResponse(
            success=True,
            message="Audio processed successfully",
            audio_size_bytes=audio_size,
            transcript=transcript,
            ai_response=ai_response,
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Audio processing failed: {str(e)}"
        )

