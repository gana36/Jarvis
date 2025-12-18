"""Gemini AI service for conversational responses"""
import logging
from functools import lru_cache

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.config import get_settings

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Gemini Flash API"""

    def __init__(self, api_key: str):
        """
        Initialize Gemini service with API key.
        
        Args:
            api_key: Google Gemini API key
        """
        genai.configure(api_key=api_key)
        
        # Configure model for speed - use Gemini 2.5 Flash (latest stable)
        self.model = genai.GenerativeModel(
            model_name="models/gemini-2.0-flash-exp",
            # Minimal safety settings for speed
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            },
        )
        logger.info("✓ Gemini Flash service initialized")

    async def generate_response(self, user_message: str) -> str:
        """
        Generate a conversational response to user input.
        
        Args:
            user_message: User's transcribed message
            
        Returns:
            One-sentence conversational response
        """
        try:
            # Construct prompt with instruction for brevity
            prompt = f"""Respond conversationally in ONE short sentence.

User: {user_message}
Assistant:"""

            # Generate response with minimal configuration for speed
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 100,  # Keep response short
                }
            )
            
            ai_response = response.text.strip()
            logger.info(f"Gemini response: '{ai_response}'")
            return ai_response
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            # Return friendly fallback response
            return "I'm having trouble thinking right now. Can you try again?"

    async def generate_response_stream(self, user_message: str):
        """
        Generate a conversational response with streaming.
        
        Args:
            user_message: User's transcribed message
            
        Yields:
            Text chunks as they're generated
        """
        try:
            # Construct prompt with instruction for brevity
            prompt = f"""Respond conversationally in ONE short sentence.

User: {user_message}
Assistant:"""

            # Generate response with streaming enabled
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 100,  # Keep response short
                },
                stream=True,  # Enable streaming
            )
            
            # Yield chunks as they arrive
            for chunk in response:
                if chunk.text:
                    logger.debug(f"Gemini chunk: '{chunk.text}'")
                    yield chunk.text
            
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            yield "I'm having trouble thinking right now."


@lru_cache
def get_gemini_service() -> GeminiService:
    """
    Get cached Gemini service instance.
    
    Returns:
        Configured GeminiService instance
        
    Raises:
        ValueError: If GEMINI_API_KEY is not configured
    """
    settings = get_settings()
    
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY not configured. "
            "Please add it to your .env file."
        )
    
    return GeminiService(api_key=settings.gemini_api_key)
