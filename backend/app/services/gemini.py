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

    async def classify_and_extract(self, user_message: str) -> dict:
        """
        Classify intent AND extract relevant details in a single LLM call.
        
        Args:
            user_message: User's message
            
        Returns:
            Dict with 'intent', 'confidence', and 'details' (null for simple intents)
            
        Example outputs:
            Calendar: {"intent": "CREATE_CALENDAR_EVENT", "confidence": 0.95, 
                      "details": {"title": "movie", "date": "2025-12-20", "hour": 18, "minute": 0, "duration": 60}}
            Weather: {"intent": "GET_WEATHER", "confidence": 0.95, "details": null}
        """
        try:
            from datetime import datetime
            
            # Get current context
            now = datetime.now()
            current_time = now.strftime("%I:%M %p")
            current_date = now.strftime("%Y-%m-%d")
            day_of_week = now.strftime("%A")
            
            # Unified prompt for classification + extraction
            prompt = f"""Classify intent and extract details if applicable. Return JSON only.

Current time: {current_time}
Current date: {current_date} ({day_of_week})

Input: "{user_message}"

Intents: GET_WEATHER, ADD_TASK, DAILY_SUMMARY, CREATE_CALENDAR_EVENT, UPDATE_CALENDAR_EVENT, DELETE_CALENDAR_EVENT, LEARN, GENERAL_CHAT

For calendar intents, extract:
- title: event name (clean, no articles)
- date: ISO date (YYYY-MM-DD) - understand "today", "tomorrow", "next Monday", etc.
- hour: 24-hour format (0-23)
- minute: (0-59)
- duration: minutes (default 60 if not specified)

For UPDATE, also extract:
- event_name: which event to update
- new_title: new name (null if not changing)
- new_hour, new_minute: new time (null if not changing)

For DELETE, extract:
- event_name: which event to delete

Output format:
{{
  "intent": "INTENT_NAME",
  "confidence": 0.95,
  "details": {{...}} or null
}}

Examples:
"create movie at 6pm tomorrow" → {{"intent": "CREATE_CALENDAR_EVENT", "confidence": 0.95, "details": {{"title": "movie", "date": "2025-12-21", "hour": 18, "minute": 0, "duration": 60}}}}
"what's the weather" → {{"intent": "GET_WEATHER", "confidence": 0.95, "details": null}}
"change movie to 7pm" → {{"intent": "UPDATE_CALENDAR_EVENT", "confidence": 0.95, "details": {{"event_name": "movie", "new_hour": 19, "new_minute": 0}}}}"""

            # Generate with minimal tokens for speed
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.0,  # Deterministic
                    "max_output_tokens": 200,  # Enough for intent + details
                }
            )
            
            # Parse JSON response
            import json
            response_text = response.text.strip()
            
            # Extract JSON if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            logger.info(f"Classified: {result['intent']} (confidence: {result['confidence']}) | Details: {result.get('details')}")
            return result
            
        except Exception as e:
            logger.error(f"Classification + extraction failed: {e}")
            # Fallback to generic chat
            return {"intent": "GENERAL_CHAT", "confidence": 0.5, "details": null}

    async def classify_intent(self, user_message: str) -> dict:
        """
        Classify user intent using minimal prompt for speed.
        
        Args:
            user_message: User's transcribed message
            
        Returns:
            Dict with 'intent' and 'confidence' fields
        """
        try:
            # Ultra-minimal prompt for speed
            prompt = f"""Classify intent. Return JSON only.

Input: "{user_message}"

Intents: GET_WEATHER, ADD_TASK, COMPLETE_TASK, UPDATE_TASK, DELETE_TASK, LIST_TASKS, GET_TASK_REMINDERS, DAILY_SUMMARY, CREATE_CALENDAR_EVENT, UPDATE_CALENDAR_EVENT, DELETE_CALENDAR_EVENT, LEARN, GENERAL_CHAT

Output format:
{{"intent": "INTENT_NAME", "confidence": 0.95}}"""

            # Generate with minimal tokens for speed
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,  # Low temp for consistent classification
                    "max_output_tokens": 50,  # Very small for JSON only
                }
            )
            
            # Parse JSON response
            import json
            response_text = response.text.strip()
            
            # Extract JSON if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            logger.info(f"Intent classified: {result['intent']} (confidence: {result['confidence']})")
            return result
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            # Fallback to generic chat
            return {"intent": "GENERAL_CHAT", "confidence": 0.5}

    async def extract_calendar_event(self, user_message: str) -> dict:
        """
        Extract calendar event details from natural language.
        
        Args:
            user_message: User's request (e.g., "create movie event at 6pm today")
            
        Returns:
            Dict with 'title', 'hour', 'minute', 'am_pm' fields
            Example: {"title": "movie", "hour": 18, "minute": 0, "am_pm": "pm"}
        """
        try:
            from datetime import datetime
            
            # Get current time for context
            now = datetime.now()
            current_time = now.strftime("%I:%M %p")
            current_date = now.strftime("%Y-%m-%d")
            
            # Minimal prompt for fast extraction
            prompt = f"""Extract calendar event details. Return JSON only.

Current time: {current_time}
Current date: {current_date}

Input: "{user_message}"

Extract:
- title: event name (clean, no articles like "a", "the")
- hour: hour in 24-hour format (0-23)
- minute: minute (0-59)

Output format:
{{"title": "event name", "hour": 18, "minute": 0}}"""

            # Generate with minimal tokens for speed
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.0,  # Deterministic extraction
                    "max_output_tokens": 100,  # Small JSON only
                }
            )
            
            # Parse JSON response
            import json
            response_text = response.text.strip()
            
            # Extract JSON if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            logger.info(f"Extracted event: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Event extraction failed: {e}")
            # Fallback to defaults
            return {"title": "New Event", "hour": datetime.now().hour + 1, "minute": 0}

    async def extract_calendar_update(self, user_message: str) -> dict:
        """
        Extract calendar update details from natural language.
        
        Args:
            user_message: User's request (e.g., "change movie to 7pm")
            
        Returns:
            Dict with 'event_name', 'new_title', 'new_hour', 'new_minute'
        """
        try:
            from datetime import datetime
            
            now = datetime.now()
            current_time = now.strftime("%I:%M %p")
            
            # Minimal prompt for fast extraction
            prompt = f"""Extract calendar update details. Return JSON only.

Current time: {current_time}

Input: "{user_message}"

Extract:
- event_name: which event to update (e.g., "movie", "lunch")
- new_title: new event name if changing (null if not changing)
- new_hour: new hour in 24-hour format if changing (null if not changing)
- new_minute: new minute if changing (null if not changing)

Output format:
{{"event_name": "movie", "new_title": null, "new_hour": 19, "new_minute": 0}}"""

            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.0,
                    "max_output_tokens": 100,
                }
            )
            
            import json
            response_text = response.text.strip()
            
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            logger.info(f"Extracted update: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Update extraction failed: {e}")
            return {"event_name": None, "new_title": None, "new_hour": None, "new_minute": None}




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
