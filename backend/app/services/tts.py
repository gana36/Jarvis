"""ElevenLabs Text-to-Speech service for voice responses"""
import base64
import logging
from functools import lru_cache

from elevenlabs import ElevenLabs

from app.config import get_settings

logger = logging.getLogger(__name__)


class TTSService:
    """Service for converting text to speech using ElevenLabs"""

    def __init__(self, api_key: str, voice_id: str):
        """
        Initialize TTS service with API key.
        
        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID to use for speech synthesis
        """
        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = voice_id
        logger.info(f"✓ ElevenLabs TTS service initialized with voice: {voice_id}")

    def text_to_speech(self, text: str, voice_id: str | None = None) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID (uses instance default if not provided)
            
        Returns:
            Audio bytes (MP3 format)
        """
        try:
            # Use provided voice or fall back to instance default
            voice = voice_id or self.voice_id
            
            # Generate audio using streaming API (collects all chunks)
            audio_generator = self.client.text_to_speech.convert(
                voice_id=voice,
                text=text,
                model_id="eleven_turbo_v2",  # Standard turbo (not v2_5 which is too fast)
                output_format="mp3_44100_128",  # Good quality, reasonable size
                voice_settings={
                    "stability": 0.5,  # Balance between consistency and expressiveness
                    "similarity_boost": 0.75,  # Closer to original voice
                    "style": 0.0,  # No style exaggeration
                    "use_speaker_boost": True,  # Better clarity
                }
            )
            
            # Collect all audio chunks
            audio_bytes = b"".join(audio_generator)
            
            logger.info(f"✓ Generated {len(audio_bytes)} bytes of audio for text: '{text[:50]}...' with voice: {voice}")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            raise

    def text_to_speech_base64(self, text: str, voice_id: str | None = None) -> str:
        """
        Convert text to speech and encode as base64.
        
        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID (uses instance default if not provided)
            
        Returns:
            Base64-encoded audio string
        """
        audio_bytes = self.text_to_speech(text, voice_id=voice_id)
        return base64.b64encode(audio_bytes).decode('utf-8')

    def text_to_speech_stream(self, text_stream, voice_id: str | None = None):
        """
        Convert streaming text to streaming audio.
        
        Args:
            text_stream: Async generator yielding text chunks
            voice_id: Optional voice ID (uses instance default if not provided)
            
        Yields:
            Audio bytes chunks
        """
        try:
            # Use provided voice or fall back to instance default
            voice = voice_id or self.voice_id
            
            # Convert async generator to regular generator for ElevenLabs
            def text_iterator():
                """Collect all text chunks before sending to TTS"""
                full_text = ""
                for chunk in text_stream:
                    full_text += chunk
                    yield chunk
                logger.info(f"✓ Streaming TTS for: '{full_text[:50]}...' with voice: {voice}")
            
            # Stream audio using ElevenLabs streaming API
            audio_stream = self.client.text_to_speech.convert(
                voice_id=voice,
                text=text_iterator(),
                model_id="eleven_turbo_v2",  # Standard turbo for natural pacing
                output_format="mp3_44100_128",
                voice_settings={
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True,
                },
                optimize_streaming_latency=3,  # Optimize but not maximum
            )
            
            # Yield audio chunks as they're generated
            for audio_chunk in audio_stream:
                yield audio_chunk
                
        except Exception as e:
            logger.error(f"Streaming TTS failed: {e}")
            raise


@lru_cache
def get_tts_service() -> TTSService:
    """
    Get cached TTS service instance.
    
    Returns:
        Configured TTSService instance
        
    Raises:
        ValueError: If ELEVENLABS_API_KEY is not configured
    """
    settings = get_settings()
    
    if not settings.elevenlabs_api_key:
        raise ValueError(
            "ELEVENLABS_API_KEY not configured. "
            "Please add it to your .env file."
        )
    
    return TTSService(
        api_key=settings.elevenlabs_api_key,
        voice_id=settings.elevenlabs_voice_id
    )
