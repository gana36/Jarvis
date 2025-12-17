"""Voice API endpoints for audio ingestion"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel

router = APIRouter()


class IngestResponse(BaseModel):
    """Response for audio ingest endpoint"""

    success: bool
    message: str
    audio_size_bytes: int


@router.post("/ingest", response_model=IngestResponse)
async def ingest_audio(audio: UploadFile = File(...)):
    """
    Ingest audio from frontend for processing.
    
    Args:
        audio: Audio file (webm format expected)
        
    Returns:
        Success status and audio metadata
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
    print(f"Received audio: {audio.filename}, size: {audio_size} bytes")

    # TODO: Process audio (speech-to-text, etc.)
    # For now, just acknowledge receipt

    return IngestResponse(
        success=True, message="Audio received successfully", audio_size_bytes=audio_size
    )
