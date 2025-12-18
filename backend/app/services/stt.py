"""Speech-to-Text service using Google Cloud Speech API"""
import logging
from typing import AsyncIterator

from google.cloud import speech

logger = logging.getLogger(__name__)


class SpeechToTextService:
    """Service for converting audio to text using Google Cloud Speech API"""

    def __init__(self):
        """Initialize Google Cloud Speech client"""
        self.client = speech.SpeechClient()

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio using streaming recognition with partial results.

        Args:
            audio_bytes: Audio data in webm/opus format

        Returns:
            Final transcript text

        Raises:
            Exception: If transcription fails
        """
        # Configure recognition
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,  # Standard for webm opus
            language_code="en-US",
            enable_automatic_punctuation=True,
        )

        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            single_utterance=True,  # Return quickly after speech ends
            interim_results=True,  # Get partial transcripts
        )

        # Create streaming request generator
        def request_generator():
            # Subsequent requests contain audio chunks
            # For optimization, send in chunks rather than all at once
            chunk_size = 8192
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i : i + chunk_size]
                yield speech.StreamingRecognizeRequest(audio_content=chunk)

        # Perform streaming recognition with config and requests
        responses = self.client.streaming_recognize(
            config=streaming_config,
            requests=request_generator()
        )

        final_transcript = ""
        
        try:
            for response in responses:
                # Check if there are any results
                if not response.results:
                    continue

                result = response.results[0]
                
                if not result.alternatives:
                    continue

                transcript = result.alternatives[0].transcript

                # Log partial results
                if not result.is_final:
                    logger.info(f"Partial transcript: {transcript}")
                else:
                    # Store final result
                    logger.info(f"Final transcript: {transcript}")
                    final_transcript = transcript
                    break  # Stop after first final result

        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            raise

        return final_transcript


# Singleton instance
_stt_service: SpeechToTextService | None = None


def get_stt_service() -> SpeechToTextService:
    """Get or create the STT service instance"""
    global _stt_service
    if _stt_service is None:
        _stt_service = SpeechToTextService()
    return _stt_service
