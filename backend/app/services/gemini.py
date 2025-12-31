import logging
import mimetypes
from functools import lru_cache
from typing import List, Optional, Dict, Any

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
        
        # Configure model for speed - use Gemini 2.0 Flash (stable, higher limits)
        self.model = genai.GenerativeModel(
            model_name="models/gemini-2.0-flash",
            # Minimal safety settings for speed
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            },
        )
        logger.info("✓ Gemini Flash service initialized")

    async def generate_response(self, user_message: str, profile: dict = None, history: list = None, memory_context: str = None, file_paths: List[str] = None, visual: bool = False) -> str:
        """
        Generate a conversational response to user input.
        
        Args:
            user_message: User's transcribed message
            profile: Optional user profile for personalization
            history: Optional conversation history for context
            memory_context: Optional long-term memory context about the user
            file_paths: Optional list of paths to images or documents
            
        Returns:
            Conversational response
        """
        try:
            # Build profile context if available
            profile_context = ""
            if profile:
                name = profile.get('name')
                dietary = profile.get('dietary_preference')
                level = profile.get('learning_level')
                timezone = profile.get('timezone')
                
                context_parts = []
                if name:
                    context_parts.append(f"User's name: {name}")
                if dietary:
                    context_parts.append(f"Dietary: {dietary}")
                if level:
                    context_parts.append(f"Learning level: {level}")
                if timezone:
                    context_parts.append(f"Timezone: {timezone}")
                
                if context_parts:
                    profile_context = f"Context: {', '.join(context_parts)}\n\n"
            
            # Build conversation history if available
            history_context = ""
            if history and len(history) > 0:
                history_lines = []
                for msg in history[-6:]:  # Last 6 messages (3 exchanges)
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "\n".join(history_lines) + "\n\n"
            
            # Build memory context if available
            memory_section = ""
            if memory_context:
                memory_section = f"{memory_context}\n\n"
            
            # Construct prompt with personality, context, and memories
            brief_instruction = " Keep responses brief (1-2 sentences)." if not visual else " Provide a detailed, technical response with code blocks if requested. Use markdown for structure."
            
            prompt = f"""You are Manas, a helpful and friendly personal AI assistant. You are concise, warm, and conversational. Respond naturally as if chatting with a friend.{brief_instruction}

IMPORTANT: When referencing the user's personal information below, use "your" (e.g., "your favorite color is blue"), never "my".

{memory_section}Your capabilities: weather queries, task management (add/complete/update/delete tasks), calendar events (create/update/delete), daily summaries, task reminders, and general conversation.
{profile_context}{history_context}User: {user_message}
Manas:"""

            # Prepare parts for multimodal content
            prompt_parts = [prompt]
            
            # Add files if provided
            if file_paths:
                for path in file_paths:
                    try:
                        mime_type, _ = mimetypes.guess_type(path)
                        # Default to octet-stream if unknown
                        mime_type = mime_type or "application/octet-stream"
                        
                        with open(path, "rb") as f:
                            data = f.read()
                        
                        prompt_parts.append({
                            "mime_type": mime_type,
                            "data": data
                        })
                        logger.info(f"Added file to Gemini prompt: {path} ({mime_type})")
                    except Exception as e:
                        logger.error(f"Failed to load file for Gemini: {path}, error: {e}")

            # Generate response with parts
            response = self.model.generate_content(
                prompt_parts,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 1024 if visual else 150,  # Larger for visual
                }
            )
            
            ai_response = response.text.strip()
            logger.info(f"Gemini response: '{ai_response}'")
            return ai_response
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            # Return friendly fallback response
            return "I'm having trouble thinking right now. Can you try again?"

    async def generate_response_stream(self, user_message: str, profile: dict = None, history: list = None, file_paths: List[str] = None, visual: bool = False):
        """
        Generate a conversational response with streaming, with optional profile context and history.
        
        Args:
            user_message: User's transcribed message
            profile: Optional user profile for personalization
            history: Optional conversation history for context
            file_paths: Optional list of paths to images or documents
            
        Yields:
            Text chunks as they're generated
        """
        try:
            # Build profile context if available
            profile_context = ""
            if profile:
                name = profile.get('name')
                dietary = profile.get('dietary_preference')
                level = profile.get('learning_level')
                timezone = profile.get('timezone')
                
                context_parts = []
                if name:
                    context_parts.append(f"User's name: {name}")
                if dietary:
                    context_parts.append(f"Dietary: {dietary}")
                if level:
                    context_parts.append(f"Learning level: {level}")
                if timezone:
                    context_parts.append(f"Timezone: {timezone}")
                
                if context_parts:
                    profile_context = f"Context: {', '.join(context_parts)}\n\n"
            
            # Build conversation history if available
            history_context = ""
            if history and len(history) > 0:
                history_lines = []
                for msg in history[-6:]:  # Last 6 messages (3 exchanges)
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "\n".join(history_lines) + "\n\n"
            
            # Construct prompt with personality and context
            brief_instruction = " Keep responses brief (1-2 sentences)." if not visual else " Provide a detailed, technical response with code blocks if requested. Use markdown for structure."
            
            prompt = f"""You are Manas, a helpful and friendly personal AI assistant. You are concise, warm, and conversational. Respond naturally as if chatting with a friend.{brief_instruction}


Your capabilities: weather queries, task management (add/complete/update/delete tasks), calendar events (create/update/delete), daily summaries, task reminders, and general conversation.
{profile_context}{history_context}User: {user_message}
Manas:"""

            # Prepare parts for multimodal content
            prompt_parts = [prompt]
            
            # Add files if provided
            if file_paths:
                for path in file_paths:
                    try:
                        mime_type, _ = mimetypes.guess_type(path)
                        mime_type = mime_type or "application/octet-stream"
                        
                        with open(path, "rb") as f:
                            data = f.read()
                        
                        prompt_parts.append({
                            "mime_type": mime_type,
                            "data": data
                        })
                        logger.info(f"Added file to Gemini stream prompt: {path} ({mime_type})")
                    except Exception as e:
                        logger.error(f"Failed to load file for Gemini stream: {path}, error: {e}")

            # Generate response with streaming enabled
            response = self.model.generate_content(
                prompt_parts,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 1024 if visual else 150,  # Larger for visual
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

    async def classify_and_extract(self, user_message: str, history: list = None, timezone: str = None) -> dict:
        """
        Classify intent AND extract relevant details in a single LLM call.
        
        Args:
            user_message: User's message
            history: Optional conversation history for context
            timezone: Optional user timezone for date/time parsing (e.g., 'America/New_York')

            
        Returns:
            Dict with 'intent', 'confidence', and 'details' (null for simple intents)
            
        Example outputs:
            Calendar: {"intent": "CREATE_CALENDAR_EVENT", "confidence": 0.95, 
                      "details": {"title": "movie", "date": "2025-12-20", "hour": 18, "minute": 0, "duration": 60}}
            Weather: {"intent": "GET_WEATHER", "confidence": 0.95, "details": null}
        """
        try:
            from datetime import datetime
            import pytz
            
            # Get current context in user's timezone (Cloud Run uses UTC by default)
            # Use timezone from profile, fallback to America/New_York if not set
            tz_name = timezone or 'America/New_York'
            try:
                user_tz = pytz.timezone(tz_name)
            except pytz.UnknownTimeZoneError:
                user_tz = pytz.timezone('America/New_York')
            
            now = datetime.now(user_tz)
            current_time = now.strftime("%I:%M %p")
            current_date = now.strftime("%Y-%m-%d")
            day_of_week = now.strftime("%A")
            
            # Build conversation history if available
            history_context = ""
            if history and len(history) > 0:
                history_lines = []
                for msg in history[-4:]:  # Last 4 messages for classification context
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

            # Unified prompt for classification + extraction
            prompt = f"""{history_context}Classify intent and extract details if applicable. Return JSON only.
Use the conversation history above to resolve pronouns like "that", "those", or "the one" if the current input is a follow-up.

Current time: {current_time}
Current date: {current_date} ({day_of_week})

Input: "{user_message}"

Intents: GET_WEATHER, ADD_TASK, COMPLETE_TASK, UPDATE_TASK, DELETE_TASK, LIST_TASKS, GET_TASK_REMINDERS, DAILY_SUMMARY, CREATE_CALENDAR_EVENT, UPDATE_CALENDAR_EVENT, DELETE_CALENDAR_EVENT, CHECK_EMAIL, SEARCH_EMAIL, READ_EMAIL, ANALYZE_EMAIL, SEARCH_RESTAURANTS, REMEMBER_THIS, RECALL_MEMORY, FORGET_THIS, LEARN, GET_NEWS, VISUAL_RENDER, GENERAL_CHAT

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

    async def classify_intent(self, user_message: str, history: list = None) -> dict:
        """
        Classify user intent using minimal prompt for speed.
        
        Args:
            user_message: User's transcribed message
            history: Optional conversation history for context
            
        Returns:
            Dict with 'intent' and 'confidence' fields
        """
        try:
            # Build conversation history if available
            history_context = ""
            if history and len(history) > 0:
                history_lines = []
                for msg in history[-4:]:  # Last 4 messages for classification context
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

            # Ultra-minimal prompt for speed
            prompt = f"""{history_context}Classify intent. Return JSON only.
If the input is a follow-up (e.g., "more casual", "closest one", "how about that?"), use the history to determine the intent.

Input: "{user_message}"

Intents:
- LEARN: factual questions, educational queries, "who is", "what is", current events, explanations
- GET_WEATHER: weather queries
- ADD_TASK, COMPLETE_TASK, UPDATE_TASK, DELETE_TASK, LIST_TASKS, GET_TASK_REMINDERS: task management  
- DAILY_SUMMARY, CREATE_CALENDAR_EVENT, UPDATE_CALENDAR_EVENT, DELETE_CALENDAR_EVENT: calendar/scheduling
- CHECK_EMAIL: list emails, show inbox, "my last 5 emails", "any new emails?", "show me my emails", unread count
- SEARCH_EMAIL: find emails with specific criteria like from/subject/date, "emails from Bob", "find emails about invoices"
- ANALYZE_EMAIL: analyze/summarize email content, "do any emails have deadlines?", "summarize my emails", "what are my emails about?", "any urgent emails?"
- SEARCH_RESTAURANTS: restaurant/food recommendations, "find restaurants near me", "best Italian place", "where to eat", "recommend a sushi place", "coffee shops nearby"
- REMEMBER_THIS: user wants you to remember something, "remember that", "don't forget", store fact
- RECALL_MEMORY: user asks what you remember, "what do you know about me", "what did I tell you"
- FORGET_THIS: user wants to delete a memory, "forget that", "delete memory"
- GET_NEWS: latest news, breaking updates, "what's the news", news about [topic], daily briefing
- VISUAL_RENDER: technical output, code generation, markdown creation, step-by-step documentation, "write code", "generate a script", "show me markdown", "render a document", "create a config"
- GENERAL_CHAT: greetings, casual conversation, opinions

Examples:
- "who is the president" → LEARN
- "what are the latest news" → GET_NEWS
- "any news about apple?" → GET_NEWS
- "how's the weather" → GET_WEATHER
- "add task" → ADD_TASK
- "do I have any new emails?" → CHECK_EMAIL
- "show me my last 5 emails" → CHECK_EMAIL
- "what are my recent emails" → CHECK_EMAIL
- "find emails from John" → SEARCH_EMAIL
- "emails about meeting" → SEARCH_EMAIL
- "summarize my last 5 emails" → ANALYZE_EMAIL
- "do any of my emails have deadlines?" → ANALYZE_EMAIL
- "what are my emails about?" → ANALYZE_EMAIL
- "any urgent emails I should read?" → ANALYZE_EMAIL
- "find restaurants near me" → SEARCH_RESTAURANTS
- "best Italian restaurant" → SEARCH_RESTAURANTS
- "recommend a sushi place nearby" → SEARCH_RESTAURANTS
- "where can I get coffee?" → SEARCH_RESTAURANTS
- "remember that my wife's birthday is March 15" → REMEMBER_THIS
- "what do you know about my family?" → RECALL_MEMORY
- "forget what I told you about my job" → FORGET_THIS
- "write a python script" → VISUAL_RENDER
- "write merge sort in c++" → VISUAL_RENDER
- "generate a markdown document" → VISUAL_RENDER
- "show me the steps for this" → VISUAL_RENDER
- "hello" → GENERAL_CHAT

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

    async def extract_calendar_event(self, user_message: str, history: list = None, timezone: str = None) -> dict:
        """
        Extract calendar event details from natural language.
        
        Args:
            user_message: User's request (e.g., "create movie event at 6pm today")
            history: Optional conversation history for context
            timezone: Optional user timezone for date/time parsing
            
        Returns:
            Dict with 'title', 'hour', 'minute', 'am_pm' fields
            Example: {"title": "movie", "hour": 18, "minute": 0, "am_pm": "pm"}
        """
        try:
            from datetime import datetime
            import pytz
            
            # Get current time in user's timezone
            tz_name = timezone or 'America/New_York'
            try:
                user_tz = pytz.timezone(tz_name)
            except pytz.UnknownTimeZoneError:
                user_tz = pytz.timezone('America/New_York')
            
            now = datetime.now(user_tz)
            current_time = now.strftime("%I:%M %p")
            current_date = now.strftime("%Y-%m-%d")
            
            # Build conversation history if available
            history_context = ""
            if history and len(history) > 0:
                history_lines = []
                for msg in history[-4:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

            # Minimal prompt for fast extraction
            prompt = f"""{history_context}Extract calendar event details. Return JSON only.
Use the history above to resolve pronouns or dates (e.g., "at that same time tomorrow").

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

    async def extract_calendar_update(self, user_message: str, history: list = None) -> dict:
        """
        Extract calendar update details from natural language.
        
        Args:
            user_message: User's request (e.g., "change movie to 7pm")
            history: Optional conversation history for context
            
        Returns:
            Dict with 'event_name', 'new_title', 'new_hour', 'new_minute'
        """
        try:
            from datetime import datetime
            
            now = datetime.now()
            current_time = now.strftime("%I:%M %p")
            
            # Build conversation history if available
            history_context = ""
            if history and len(history) > 0:
                history_lines = []
                for msg in history[-4:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

            # Minimal prompt for fast extraction
            prompt = f"""{history_context}Extract calendar update details. Return JSON only.
Use the history to identify which event the user is referring to if using pronouns.

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
