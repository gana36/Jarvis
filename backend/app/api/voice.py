"""Voice API endpoints for audio ingestion"""
import logging

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.stt import get_stt_service
from app.services.gemini import get_gemini_service
from app.services.tts import get_tts_service

logger = logging.getLogger(__name__)
router = APIRouter()


class IngestResponse(BaseModel):
    """Response for audio ingest endpoint"""

    success: bool
    message: str
    audio_size_bytes: int
    transcript: str
    ai_response: str
    audio_base64: str | None = None  # Base64-encoded audio from TTS


@router.post("/ingest", response_model=IngestResponse)
async def ingest_audio(
    audio: UploadFile = File(...),
    voice_id: str | None = Form(None),
):
    """
    Ingest audio from frontend and transcribe using Google Cloud Speech-to-Text.
    
    Args:
        audio: Audio file (webm format expected)
        voice_id: Optional ElevenLabs voice ID for TTS
        
    Returns:
        Success status, audio metadata, transcript, AI response, and TTS audio
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
        audio_base64 = None
        
        if transcript:
            try:
                gemini_service = get_gemini_service()
                ai_response = await gemini_service.generate_response(transcript)
                
                # Convert AI response to speech
                try:
                    tts_service = get_tts_service()
                    audio_base64 = tts_service.text_to_speech_base64(
                        ai_response,
                        voice_id=voice_id
                    )
                except ValueError as e:
                    logger.warning(f"TTS not configured: {e}")
                except Exception as e:
                    logger.error(f"TTS generation failed: {e}")
                    
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
            audio_base64=audio_base64,
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


@router.post("/ingest-stream")
async def ingest_audio_stream(
    audio: UploadFile = File(...),
    voice_id: str | None = Form(None),
):
    """
    Ingest audio and stream the TTS response for lower latency.
    
    Args:
        audio: Audio file (webm format expected)
        voice_id: Optional ElevenLabs voice ID for TTS
        
    Returns:
        Streaming audio/mpeg response
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

    logger.info(f"Streaming mode: Received audio, size: {audio_size} bytes")

    # Transcribe audio
    try:
        stt_service = get_stt_service()
        transcript = await stt_service.transcribe_audio(audio_data)
        
        if not transcript:
            logger.warning("No speech detected in audio")
            raise HTTPException(status_code=400, detail="No speech detected")
        
        logger.info(f"Streaming: Transcription complete: '{transcript}'")
        
        # Stream audio generator
        async def generate_audio():
            try:
                # Get services
                gemini_service = get_gemini_service()
                tts_service = get_tts_service()
                
                # Stream text from Gemini
                text_stream = gemini_service.generate_response_stream(transcript)
                
                # Stream audio from TTS
                audio_stream = tts_service.text_to_speech_stream(text_stream, voice_id=voice_id)
                
                # Yield audio chunks
                for audio_chunk in audio_stream:
                    yield audio_chunk
                    
            except Exception as e:
                logger.error(f"Streaming generation failed: {e}")
                # Can't really return error in stream, just end it
                return
        
        return StreamingResponse(
            generate_audio(),
            media_type="audio/mpeg",
            headers={
                "X-Transcript": transcript,  # Send transcript in header
                "Cache-Control": "no-cache",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Streaming processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Streaming failed: {str(e)}"
        )
