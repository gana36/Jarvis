"""Orchestrator service for intent routing and handler coordination"""
import asyncio
import logging
from functools import lru_cache
from typing import Any, Dict, List, AsyncGenerator, Tuple, Optional
from datetime import datetime, timedelta

from app.services.gemini import get_gemini_service
from app.services.fitbit_tool import get_fitbit_tool
from app.services.gmail_tool import get_gmail_tool
from app.services.memory_service import get_memory_service
from app.services.yelp_tool import get_yelp_tool
from app.api.files import get_file_path, delete_file

logger = logging.getLogger(__name__)


class OrchestratorService:
    """Orchestrates intent classification and routes to appropriate handlers"""

    def __init__(self):
        """Initialize orchestrator service"""
        self.gemini_service = get_gemini_service()
        self.user_profile_cache = {}  # Session-level profile cache
        self.conversation_history = {}  # user_id -> list of {"role": "user/model", "parts": "..."}
        self.yelp_chat_ids = {}  # user_id -> last yelp chat_id for multi-turn
        logger.info("✓ Orchestrator service initialized")

    async def process_transcript(self, transcript: str, user_id: str = "default", file_ids: List[str] = None) -> Dict[str, Any]:
        """
        Process transcript by classifying intent and routing to handler.
        
        Args:
            transcript: User's transcribed message
            user_id: User identifier for profile loading
            
        Returns:
            Dict containing:
                - transcript: Original user input
                - intent: Classified intent
                - confidence: Classification confidence score
                - handler_response: Handler's structured response
        """
        try:
            # Step 1: Load user profile (cached)
            profile = await self._get_user_profile(user_id)
            
            # Step 2: Get conversation history
            history = self._get_conversation_history(user_id)
            
            # Step 2.5: Resolve file_ids to paths
            file_paths = []
            if file_ids:
                for fid in file_ids:
                    path = get_file_path(fid)
                    if path:
                        file_paths.append(path)
                logger.info(f"Resolved {len(file_paths)} file paths from {len(file_ids)} IDs")
            
            # Step 3: Classify Intent using fast Gemini Flash (with history context)
            if file_paths:
                # Priority: if files are present, force document analysis mode
                intent = "DOC_ANALYSIS"
                confidence = 1.0
                logger.info(f"Orchestrator: Analysis Mode Triggered (Files present). Forcing intent={intent}")
            else:
                intent_result = await self.gemini_service.classify_intent(transcript, history=history)
                intent = intent_result["intent"]
                confidence = intent_result["confidence"]
                logger.info(f"Orchestrator: Intent={intent}, Confidence={confidence}")
            
            # Step 4: Route to appropriate handler (extraction happens inside handlers)
            handler_response = await self._route_to_handler(intent, transcript, confidence, profile, history, user_id, file_paths=file_paths)
            
            # Step 5: Update conversation history for all intents
            self._add_to_history(user_id, "user", transcript)
            self._add_to_history(user_id, "model", handler_response["message"])
            
            # Step 6: Extract and update profile (non-blocking)
            asyncio.create_task(self._extract_and_update_profile(transcript, user_id))
            
            return {
                "transcript": transcript,
                "intent": intent,
                "confidence": confidence,
                "handler_response": handler_response,
            }
            
        except Exception as e:
            logger.error(f"Orchestrator processing error: {e}")
            # Fallback to general chat on error
            return {
                "transcript": transcript,
                "intent": "GENERAL_CHAT",
                "confidence": 0.0,
                "handler_response": await self._handle_general_chat(transcript, profile=None, history=None, file_paths=None),
            }
        finally:
            # Step 7: Auto-cleanup: Delete files after processing
            if file_ids:
                for f_id in file_ids:
                    logger.info(f"🗑️ Deleting file {f_id} in process_transcript finally block")
                    delete_file(f_id)

    async def process_transcript_stream(self, transcript: str, user_id: str = "default", file_ids: List[str] = None):
        """
        Process transcript with streaming support for faster responses.
        
        Classifies intent and either:
        - Streams from Gemini for GENERAL_CHAT (conversational responses)
        - Returns immediate handler response for structured intents (weather, tasks, etc.)
        
        Args:
            transcript: User's transcribed message
            user_id: User identifier for profile loading
            
        Yields:
            For GENERAL_CHAT: Text chunks as they stream from Gemini
            For other intents: Single handler message (no streaming needed)
            
        Returns (via header metadata):
            Intent and confidence for client-side handling
        """
        try:
            # Step 1: Load user profile (cached)
            profile = await self._get_user_profile(user_id)
            
            # Step 2: Get conversation history
            history = self._get_conversation_history(user_id)

            # Step 2.5: Resolve file_ids to paths
            file_paths = []
            if file_ids:
                for fid in file_ids:
                    path = get_file_path(fid)
                    if path:
                        file_paths.append(path)
                logger.info(f"Resolved {len(file_paths)} file paths for streaming")
            
            # Step 3: Classify Intent (with history context)
            if file_paths:
                intent = "DOC_ANALYSIS"
                confidence = 1.0
            else:
                intent_result = await self.gemini_service.classify_intent(transcript, history=history)
                intent = intent_result["intent"]
                confidence = intent_result["confidence"]
            
            logger.info(f"Orchestrator Streaming: Intent={intent}, Confidence={confidence}")
            
            # Apply confidence threshold
            confidence_threshold = 0.7
            if confidence < confidence_threshold:
                logger.info(f"Low confidence ({confidence}), fallback to GENERAL_CHAT")
                intent = "GENERAL_CHAT"
            
            # For GENERAL_CHAT: stream from Gemini for natural conversation
            if intent == "GENERAL_CHAT":
                logger.info("Streaming from Gemini for GENERAL_CHAT")
                # Add user message to history
                self._add_to_history(user_id, "user", transcript)
                
                # Collect response for history
                full_response = ""
                
                # Stream with profile and history context (and files)
                async for chunk in self.gemini_service.generate_response_stream(transcript, profile, history, file_paths=file_paths):
                    full_response += chunk
                    yield chunk, intent, confidence
                
                # Add assistant response to history
                self._add_to_history(user_id, "model", full_response)
            elif intent == "DOC_ANALYSIS":
                logger.info("Streaming from Gemini for DOC_ANALYSIS")
                # Add user message to history
                self._add_to_history(user_id, "user", transcript)
                
                # Collect response for history
                full_response = ""
                
                # Prepend focus instruction
                analysis_transcript = f"[SYSTEM: Focus exclusively on the provided document/image. Answer based ONLY on its content.] {transcript}"
                
                # Stream with focus context
                async for chunk in self.gemini_service.generate_response_stream(analysis_transcript, profile, history, file_paths=file_paths):
                    full_response += chunk
                    yield chunk, intent, confidence
                
                # Add assistant response to history
                self._add_to_history(user_id, "model", full_response)
            else:
                # For structured intents: return immediate response
                handler_response = await self._route_to_handler(intent, transcript, confidence, profile, history, user_id, file_paths=file_paths)
                
                # Add to history
                self._add_to_history(user_id, "user", transcript)
                self._add_to_history(user_id, "model", handler_response["message"])
                
                yield handler_response["message"], intent, confidence

        except Exception as e:
            logger.error(f"Orchestrator streaming error: {e}")
            # Fallback to generic response
            yield "I'm sorry, I encountered an error. How else can I help?", "GENERAL_CHAT", 0.0
        finally:
            # Step 4: Auto-cleanup: Delete files after streaming/processing is complete
            if file_ids:
                for f_id in file_ids:
                    logger.info(f"🗑️ Deleting file {f_id} in streaming finally block")
                    delete_file(f_id)
            
            # Extract and update profile (non-blocking) - only if transcript successful
            if transcript:
                asyncio.create_task(self._extract_and_update_profile(transcript, user_id))
            yield "I'm having trouble processing that right now.", "GENERAL_CHAT", 0.0

    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get user profile with session-level caching.
        
        Args:
            user_id: User identifier
            
        Returns:
            User profile dict
        """
        # Check session cache first
        if user_id in self.user_profile_cache:
            logger.debug(f"Profile cache HIT for user: {user_id}")
            return self.user_profile_cache[user_id]
        
        # Load from Firestore
        try:
            from app.services.profile_tool import get_profile_tool
            profile_tool = get_profile_tool()
            profile = profile_tool.get_or_create_profile(user_id)
            
            # Cache for session
            self.user_profile_cache[user_id] = profile
            logger.info(f"📂 Loaded profile for user: {user_id}")
            return profile
        except Exception as e:
            logger.error(f"Failed to load profile: {e}")
            # Return minimal default
            return {
                'user_id': user_id,
                'name': None,
                'timezone': 'America/New_York',
                'dietary_preference': None,
                'learning_level': None,
            }
    
    async def _extract_and_update_profile(self, transcript: str, user_id: str):
        """
        Extract profile information from transcript and update Firestore (non-blocking).
        
        Args:
            transcript: User's message
            user_id: User identifier
        """
        try:
            from app.services.profile_extraction import extract_profile_info, normalize_profile_data
            from app.services.profile_tool import get_profile_tool
            
            # Extract profile info using LLM
            extracted = await extract_profile_info(self.gemini_service.model, transcript)
            
            if extracted:
                # Normalize the data
                normalized = normalize_profile_data(extracted)
                
                # Update in Firestore
                profile_tool = get_profile_tool()
                profile_tool.update_profile_fields(user_id, normalized)
                
                # Update session cache
                if user_id in self.user_profile_cache:
                    self.user_profile_cache[user_id].update(normalized)
                
                logger.info(f"✨ Profile updated from conversation: {list(normalized.keys())}")
        except Exception as e:
            logger.error(f"Profile extraction/update failed: {e}")
    
    def _get_conversation_history(self, user_id: str) -> list:
        """
        Get conversation history for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of conversation messages
        """
        return self.conversation_history.get(user_id, [])
    
    def _add_to_history(self, user_id: str, role: str, content: str):
        """
        Add a message to conversation history.
        
        Args:
            user_id: User identifier
            role: "user" or "model"
            content: Message content
        """
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        self.conversation_history[user_id].append({
            "role": role,
            "parts": content
        })
        
        # Keep only last 10 messages (5 exchanges)
        if len(self.conversation_history[user_id]) > 10:
            self.conversation_history[user_id] = self.conversation_history[user_id][-10:]
        
        logger.debug(f"History updated for {user_id}: {len(self.conversation_history[user_id])} messages")
    
    async def _route_to_handler(
        self, intent: str, transcript: str, confidence: float, profile: Dict[str, Any], history: list = None, user_id: str = "default", file_paths: List[str] = None
    ) -> Dict[str, Any]:
        """
        Route to appropriate handler based on intent.
        
        Args:
            intent: Classified intent
            transcript: User's message
            confidence: Classification confidence
            profile: User profile for context
            history: Conversation history for context
            user_id: User identifier for data isolation
            
        Returns:
            Handler's structured response
        """
        # Fallback to general chat for low confidence
        confidence_threshold = 0.7
        if confidence < confidence_threshold:
            logger.info(f"Low confidence ({confidence}), fallback to GENERAL_CHAT")
            intent = "GENERAL_CHAT"
        
        # Handler mapping
        handlers = {
            "GET_WEATHER": lambda t: self._handle_get_weather(t, profile, history),
            "ADD_TASK": lambda t: self._handle_add_task(t, user_id, history),
            "COMPLETE_TASK": lambda t: self._handle_complete_task(t, user_id, history),
            "UPDATE_TASK": lambda t: self._handle_update_task(t, user_id, history),
            "DELETE_TASK": lambda t: self._handle_delete_task(t, user_id, history),
            "LIST_TASKS": lambda t: self._handle_list_tasks(t, user_id, history),
            "GET_TASK_REMINDERS": lambda t: self._handle_get_task_reminders(t, user_id, history),
            "DAILY_SUMMARY": lambda t: self._handle_daily_summary(t, user_id, history),
            "CREATE_CALENDAR_EVENT": lambda t: self._handle_create_calendar_event(t, user_id, history),
            "UPDATE_CALENDAR_EVENT": lambda t: self._handle_update_calendar_event(t, user_id, history),
            "DELETE_CALENDAR_EVENT": lambda t: self._handle_delete_calendar_event(t, user_id, history),
            "CHECK_EMAIL": lambda t: self._handle_check_email(t, user_id, history),
            "SEARCH_EMAIL": lambda t: self._handle_search_email(t, user_id, history),
            "READ_EMAIL": lambda t: self._handle_read_email(t, user_id, history),
            "ANALYZE_EMAIL": lambda t: self._handle_analyze_email(t, user_id, history),
            "SEARCH_RESTAURANTS": lambda t: self._handle_search_restaurants(t, user_id, profile, history),
            "REMEMBER_THIS": lambda t: self._handle_remember_this(t, user_id, history),
            "RECALL_MEMORY": lambda t: self._handle_recall_memory(t, user_id, history),
            "FORGET_THIS": lambda t: self._handle_forget_this(t, user_id, history),
            "LEARN": lambda t: self._handle_learn(t, history, file_paths=file_paths),
            "GET_NEWS": lambda t: self._handle_news(t, history),
            "DOC_ANALYSIS": lambda t: self._handle_doc_analysis(t, profile, history, user_id, file_paths)
        }
        
        # Handle GENERAL_CHAT specially to pass history and user_id for memory context
        if intent == "GENERAL_CHAT":
            handler_response = await self._handle_general_chat(transcript, profile, history, user_id, file_paths=file_paths)
        else:
            # Get handler or default to general chat
            handler = handlers.get(intent, lambda t: self._handle_general_chat(t, profile, history, user_id, file_paths=file_paths))
            handler_response = await handler(transcript)
        
        # Beautify the message for natural speech (skip for GENERAL_CHAT as it's already natural)
        if "message" in handler_response and intent != "GENERAL_CHAT":
            handler_response["message"] = await self._beautify_response(
                handler_response["message"], 
                intent
            )
        
        return handler_response

    def _parse_date_range(self, transcript: str) -> tuple[Any, Any]:
        """
        Parse natural language date references from transcript.
        
        Supports:
          - "today" -> (today 00:00, today 23:59)
          - "tomorrow" -> (tomorrow 00:00, tomorrow 23:59)
          - "next Monday", "Tuesday", etc. -> (next occurrence 00:00, 23:59)
          - No match -> (today 00:00, 7 days from now 23:59)
        
        Args:
            transcript: User's message
            
        Returns:
            Tuple of (start_datetime, end_datetime) with timezone
        """
        from datetime import timedelta
        import re
        
        # Get current local time with timezone
        now = datetime.now().astimezone()
        transcript_lower = transcript.lower()
        
        # Check for "today"
        if "today" in transcript_lower:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            return (start, end)
        
        # Check for "tomorrow"
        if "tomorrow" in transcript_lower:
            tomorrow = now + timedelta(days=1)
            start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
            return (start, end)
        
        # Check for specific day names (e.g., "Monday", "next Tuesday")
        day_names = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for day_name, day_num in day_names.items():
            if day_name in transcript_lower:
                # Calculate next occurrence of this day
                current_day = now.weekday()
                days_ahead = (day_num - current_day) % 7
                
                # If it's the same day, assume next week
                if days_ahead == 0:
                    days_ahead = 7
                
                target_date = now + timedelta(days=days_ahead)
                start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                return (start, end)
        
        # Default: next 7 days (for update/delete operations)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = (now + timedelta(days=7)).replace(hour=23, minute=59, second=59, microsecond=999999)
        logger.info(f"No specific date found, using default range: next 7 days")
        return (start, end)

    def _find_best_task_match(self, query: str, tasks: list) -> dict | None:
        """
        Find best matching task using fuzzy string matching.
        
        Args:
            query: Task name to search for
            tasks: List of task dictionaries
            
        Returns:
            Best matching task or None
        """
        from difflib import SequenceMatcher
        
        best_match = None
        best_score = 0.0
        
        for task in tasks:
            title = task.get('title', '').lower()
            score = SequenceMatcher(None, query.lower(), title).ratio()
            
            if score > best_score and score > 0.6:  # 60% match threshold
                best_score = score
                best_match = task
        
        logger.info(f"Fuzzy match: '{query}' -> '{best_match['title'] if best_match else 'none'}' (score: {best_score:.2f})")
        return best_match

    # ========== Handler Functions (Mock Data) ==========

    async def _beautify_response(self, raw_message: str, intent: str) -> str:
        """Transform structured response into natural conversational speech.
        
        Optimized for low latency (~100-150ms):
        - Uses Gemini Flash
        - Minimal prompt
        - Short output limit
        """
        try:
            # Skip for very short messages or if already natural
            if len(raw_message) < 30:
                return raw_message
            
            prompt = f"""Make this natural for a voice assistant speaking directly to the user.
Use "you/your" (not "they/their"). Conversational, 2-3 sentences.

Input: {raw_message}

Natural:"""
            
            response = self.gemini_service.model.generate_content(
                prompt,
                generation_config={"temperature": 0.7, "max_output_tokens": 120}
            )
            
            beautified = response.text.strip()
            if beautified.startswith('"'):
                beautified = beautified.strip('"')
            
            return beautified if beautified else raw_message
            
        except Exception as e:
            logger.warning(f"Beautification skipped: {e}")
            return raw_message


    async def _handle_get_weather(self, transcript: str, profile: Dict[str, Any] = None, history: list = None) -> Dict[str, Any]:
        """
        Handle weather requests using Gemini with Google Search grounding.
        Includes 15-minute caching for performance.
        """
        logger.info(f"Handler: GET_WEATHER with profile: {profile.get('location') if profile else 'none'}")
        
        try:
            from app.services.weather_tool import get_weather_tool
            
            # Extract location from transcript (Gemini-based with context awareness)
            location = self._extract_location(transcript, history)
            
            # Get profile location if available
            profile_location = profile.get('location') if profile else None
            
            # Get weather tool
            weather_tool = get_weather_tool()
            
            # Get weather (city priority → profile_location → auto-location)
            weather = await weather_tool.get_weather(city=location, profile_location=profile_location)
            
            # Handle errors
            if weather.get("error"):
                return {
                    "type": "weather",
                    "data": {},
                    "message": f"I couldn't get the weather for {location}. Please try another location."
                }
            
            # Format response message
            message = f"""The weather in {weather['location']} is {weather['temperature_c']}°C 
({weather['temperature_f']}°F). {weather['condition']}."""
            
            # Add optional details if available
            if 'humidity' in weather:
                message += f" Humidity is {weather['humidity']}%."
            if 'wind_speed_kmh' in weather:
                message += f" Wind speed is {weather['wind_speed_kmh']} km/h."
            
            return {
                "type": "weather",
                "data": weather,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Weather handler failed: {e}")
            return {
                "type": "weather",
                "data": {"error": str(e)},
                "message": "I'm having trouble getting the weather right now. Please try again."
            }
    
    def _extract_location(self, transcript: str, history: list = None) -> Optional[str]:
        """Extract location from weather query using Gemini for reliable extraction."""
        try:
            # Build conversation history context
            history_context = ""
            if history and len(history) > 0:
                history_lines = []
                for msg in history[-4:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

            # Use Gemini to extract location from any weather query format
            prompt = f"""{history_context}Extract ONLY the city/location name from this weather query. Return just the city name, nothing else.
If no location is mentioned directly, use the history above to resolve pronouns or implied locations (e.g., "how about there?").
If no location is mentioned or implied, return "null".

Examples:
- "how is dallas weather today?" → "Dallas"
- "what's the weather in new york?" → "New York"
- "tell me tokyo weather" → "Tokyo"
- "weather for san francisco" → "San Francisco"
- "what's the weather today?" → null
- "how's it outside?" → null

Query: "{transcript}"

Location:"""

            response = self.gemini_service.model.generate_content(
                prompt,
                generation_config={"temperature": 0.0, "max_output_tokens": 20}
            )
            
            location = response.text.strip().strip('"\'')
            
            # Handle "null" or empty responses
            if location.lower() == "null" or not location:
                return None
            
            logger.info(f"📍 Extracted location: '{location}' from '{transcript}'")
            return location
            
        except Exception as e:
            logger.warning(f"Location extraction failed: {e}, using fallback")
            # Fallback to simple pattern matching
            text = transcript.lower()
            patterns = [
                "weather in ",
                "weather for ",
                "what's the weather in ",
                "how's the weather in ",
                "tell me the weather in ",
                "what is the weather in "
            ]
            
            for pattern in patterns:
                if pattern in text:
                    location = text.split(pattern, 1)[1].strip()
                    location = location.rstrip('?!.')
                    return location if location else None
            
            return None

    async def _handle_add_task(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """
        Handle task creation requests with priority and due date extraction.
        """
        logger.info("Handler: ADD_TASK")
        
        try:
            from app.services.task_tool import get_task_tool
            from datetime import datetime
            
            # Get current date for context
            now = datetime.now().astimezone()
            current_date = now.strftime("%Y-%m-%d (%A)")
            
            # Build conversation history context
            history_context = ""
            if history and len(history) > 0:
                history_lines = []
                for msg in history[-4:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"
            
            # Use Gemini to extract title, priority, and due date
            prompt = f"""{history_context}Extract task details. Return JSON only.
Use the history to resolve pronouns if the user says something like "add that to my list".

Current date: {current_date}

User: "{transcript}"

Extract:
- title: task description (clean, no words like "add", "create", "task", "todo")
- priority: "high", "medium", "low", or null if not mentioned
- due_date: ISO date string (YYYY-MM-DD) or null if not mentioned
  Parse natural dates: "tomorrow", "Friday", "next Monday", "in 3 days", "by Friday"

Format: {{"title": "...", "priority": null, "due_date": null}}

Examples:
- "Add buy groceries" → {{"title": "buy groceries", "priority": null, "due_date": null}}
- "Add high priority task finish presentation" → {{"title": "finish presentation", "priority": "high", "due_date": null}}
- "Add call dentist by Friday" → {{"title": "call dentist", "priority": null, "due_date": "2025-12-27"}}
- "Add finish report tomorrow" → {{"title": "finish report", "priority": null, "due_date": "2025-12-23"}}
- "Remember to water plants next Monday" → {{"title": "water plants", "priority": null, "due_date": "2025-12-30"}}"""

            response = self.gemini_service.model.generate_content(
                prompt,
                generation_config={"temperature": 0.0, "max_output_tokens": 150}
            )
            
            import json
            text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                if text.startswith('json'):
                    text = text[4:].strip()
            else:
                # No code blocks - extract JSON directly
                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1:
                    text = text[start:end+1]
            
            extracted = json.loads(text)
            title = extracted.get("title", "New task")
            priority = extracted.get("priority")
            due_date_str = extracted.get("due_date")
            
            # Parse due date if provided
            due_date = None
            if due_date_str:
                try:
                    # Parse ISO date and set to end of day
                    due_date = datetime.fromisoformat(due_date_str).replace(
                        hour=23, minute=59, second=59
                    ).astimezone()
                except Exception as e:
                    logger.warning(f"Failed to parse due date '{due_date_str}': {e}")
            
            # Create task in Firestore
            task_tool = get_task_tool(user_id)
            task = task_tool.add_task(
                title=title,
                status="pending",
                priority=priority,
                due_date=due_date
            )
            
            # Build response message
            parts = [f"I've added '{title}'"]
            if priority:
                parts.append(f"with {priority} priority")
            if due_date:
                # Format due date nicely
                due_str = due_date.strftime("%A, %B %d")
                parts.append(f"due {due_str}")
            parts[-1] += " to your task list."
            
            return {
                "type": "task_creation",
                "data": task,
                "message": " ".join(parts)
            }
            
        except Exception as e:
            logger.error(f"Task creation failed: {e}")
            return {
                "type": "task_creation",
                "data": {"error": str(e)},
                "message": "I had trouble adding that task. Please try again.",
            }


    async def _handle_complete_task(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """
        Mark task as completed.
        
        Strategy:
        1. Extract task name from transcript (LLM)
        2. List pending tasks  
        3. Fuzzy match to find task
        4. Mark as complete
        
        Timeline: ~250ms total
        """
        logger.info("Handler: COMPLETE_TASK")
        
        try:
            from app.services.task_tool import get_task_tool
            from app.services.gemini_task_extraction import extract_task_completion
            
            # Step 1: Extract task name (~150ms, context-aware)
            extracted = await extract_task_completion(self.gemini_service.model, transcript, history)
            task_name = extracted.get("task_name", "")
            
            if not task_name:
                return {
                    "type": "task_completion",
                    "data": {"error": "Could not identify task"},
                    "message": "Which task would you like to mark as complete?"
                }
            
            # Step 2: Get pending tasks (~50ms)
            task_tool = get_task_tool(user_id)
            pending_tasks = task_tool.list_tasks(status_filter="pending")
            
            if not pending_tasks:
                return {
                    "type": "task_completion",
                    "data": {},
                    "message": "You don't have any pending tasks."
                }
            
            # Step 3: Fuzzy match
            matching_task = self._find_best_task_match(task_name, pending_tasks)
            
            if not matching_task:
                return {
                    "type": "task_completion",
                    "data": {"searched_for": task_name},
                    "message": f"I couldn't find a task matching '{task_name}'."
                }
            
            # Step 4: Mark complete (~50ms)
            updated = task_tool.mark_complete(matching_task["id"])
            
            return {
                "type": "task_completion",
                "data": updated,
                "message": f"I've marked '{matching_task['title']}' as complete."
            }
            
        except Exception as e:
            logger.error(f"Task completion failed: {e}")
            return {
                "type": "task_completion",
                "data": {"error": str(e)},
                "message": "I had trouble completing that task."
            }
    async def _handle_update_task(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """
        Update task fields (priority, title, status).
        
        Strategy:
        1. Extract task name and updates (LLM, context-aware)
        2. List all tasks
        3. Fuzzy match to find task
        4. Update task
        
        Timeline: ~300ms total
        """
        logger.info("Handler: UPDATE_TASK")
        
        try:
            from app.services.task_tool import get_task_tool
            from app.services.gemini_task_extraction import extract_task_update
            
            # Step 1: Extract details (~200ms, context-aware)
            extracted = await extract_task_update(self.gemini_service.model, transcript, history)
            
            task_name = extracted.get("task_name", "")
            priority = extracted.get("priority")
            new_title = extracted.get("new_title")
            
            if not task_name:
                return {
                    "type": "task_update",
                    "data": {"error": "Could not identify task"},
                    "message": "Which task would you like to update?"
                }
            
            # Step 2: Get all tasks
            task_tool = get_task_tool(user_id)
            all_tasks = task_tool.list_tasks()
            
            if not all_tasks:
                return {
                    "type": "task_update",
                    "data": {},
                    "message": "You don't have any tasks."
                }
            
            # Step 3: Fuzzy match
            matching_task = self._find_best_task_match(task_name, all_tasks)
            
            if not matching_task:
                return {
                    "type": "task_update",
                    "data": {"searched_for": task_name},
                    "message": f"I couldn't find a task matching '{task_name}'."
                }
            
            # Step 4: Build updates and apply
            updates = {}
            if priority:
                updates['priority'] = priority
            if new_title:
                updates['title'] = new_title
            
            if not updates:
                return {
                    "type": "task_update",
                    "data": matching_task,
                    "message": "What would you like to update for this task?"
                }
            
            updated = task_tool.update_task(matching_task["id"], updates)
            
            # Build response message
            changes = []
            if priority:
                changes.append(f"priority to {priority}")
            if new_title:
                changes.append(f"title to '{new_title}'")
            
            changes_str = " and ".join(changes)
            
            return {
                "type": "task_update",
                "data": updated,
                "message": f"I've updated '{matching_task['title']}' - changed {changes_str}."
            }
            
        except Exception as e:
            logger.error(f"Task update failed: {e}")
            return {
                "type": "task_update",
                "data": {"error": str(e)},
                "message": "I had trouble updating that task."
            }
    async def _handle_delete_task(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """
        Delete task permanently.
        
        Strategy:
        1. Extract task name (LLM, context-aware)
        2. List all tasks (pending + completed)
        3. Fuzzy match to find task
        4. Delete task
        
        Timeline: ~250ms total
        """
        logger.info("Handler: DELETE_TASK")
        
        try:
            from app.services.task_tool import get_task_tool
            from app.services.gemini_task_extraction import extract_task_deletion
            
            # Step 1: Extract task name (~150ms, context-aware)
            extracted = await extract_task_deletion(self.gemini_service.model, transcript, history)
            task_name = extracted.get("task_name", "")
            
            if not task_name:
                return {
                    "type": "task_deletion",
                    "data": {"error": "Could not identify task"},
                    "message": "Which task would you like to delete?"
                }
            
            # Step 2: Get all tasks (including completed)
            task_tool = get_task_tool(user_id)
            all_tasks = task_tool.list_tasks()
            
            if not all_tasks:
                return {
                    "type": "task_deletion",
                    "data": {},
                    "message": "You don't have any tasks to delete."
                }
            
            # Step 3: Fuzzy match
            matching_task = self._find_best_task_match(task_name, all_tasks)
            
            if not matching_task:
                return {
                    "type": "task_deletion",
                    "data": {"searched_for": task_name},
                    "message": f"I couldn't find a task matching '{task_name}'."
                }
            
            # Step 4: Delete task (~50ms)
            task_title = matching_task['title']
            success = task_tool.delete_task(matching_task["id"])
            
            if success:
                return {
                    "type": "task_deletion",
                    "data": {"deleted_task": matching_task},
                    "message": f"I've deleted '{task_title}' from your tasks."
                }
            else:
                return {
                    "type": "task_deletion",
                    "data": {"error": "Deletion failed"},
                    "message": "I had trouble deleting that task."
                }
            
        except Exception as e:
            logger.error(f"Task deletion failed: {e}")
            return {
                "type": "task_deletion",
                "data": {"error": str(e)},
                "message": "I had trouble deleting that task."
            }

    async def _handle_list_tasks(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """List all pending tasks with optional priority filtering."""
        logger.info("Handler: LIST_TASKS")
        
        try:
            from app.services.task_tool import get_task_tool
            
            # Simple keyword-based filter detection (no LLM needed)
            transcript_lower = transcript.lower()
            priority_filter = None
            
            if "high priority" in transcript_lower or "high-priority" in transcript_lower:
                priority_filter = "high"
            elif "medium priority" in transcript_lower or "medium-priority" in transcript_lower:
                priority_filter = "medium"
            elif "low priority" in transcript_lower or "low-priority" in transcript_lower:
                priority_filter = "low"
            
            # Get all pending tasks (simple, no LLM extraction)
            task_tool = get_task_tool(user_id)
            all_tasks = task_tool.list_tasks(status_filter="pending")
            
            # Apply priority filter if detected
            if priority_filter:
                all_tasks = [t for t in all_tasks if t.get('priority') == priority_filter]
                logger.info(f"Filtered for {priority_filter} priority: {len(all_tasks)} tasks")
            
            if not all_tasks:
                if priority_filter:
                    return {
                        "type": "task_list",
                        "data": {"tasks": [], "filter": priority_filter},
                        "message": f"You don't have any {priority_filter} priority tasks."
                    }
                return {
                    "type": "task_list",
                    "data": {"tasks": []},
                    "message": "You don't have any pending tasks."
                }
            
            # Group by priority for better voice output
            priority_order = ['high', 'medium', 'low', None]
            tasks_by_priority = {p: [] for p in priority_order}
            for task in all_tasks:
                tasks_by_priority[task.get('priority')].append(task)
            
            # Build message
            if priority_filter:
                parts = [f"You have {len(all_tasks)} {priority_filter} priority task{'s' if len(all_tasks) != 1 else ''}:"]
            else:
                parts = [f"You have {len(all_tasks)} pending task{'s' if len(all_tasks) != 1 else ''}:"]
            
            for priority in priority_order:
                tasks = tasks_by_priority[priority]
                if not tasks:
                    continue
                for task in tasks:
                    # Only show priority prefix if not filtering by priority
                    prefix = f"{priority.upper()}: " if priority and not priority_filter else ""
                    parts.append(f"- {prefix}{task['title']}")
            
            return {
                "type": "task_list",
                "data": {"tasks": all_tasks, "count": len(all_tasks), "filter": priority_filter},
                "message": "\n".join(parts)
            }
            
        except Exception as e:
            logger.error(f"List tasks failed: {e}")
            return {
                "type": "task_list",
                "data": {"error": str(e)},
                "message": "I had trouble listing your tasks."
            }


    async def _handle_get_task_reminders(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """Compile and prioritize task reminders."""
        logger.info("Handler: GET_TASK_REMINDERS")
        
        try:
            from app.services.task_tool import get_task_tool
            from datetime import datetime, timedelta
            
            now = datetime.now().astimezone()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = now.replace(hour=23, minute=59, second=59)
            soon_end = (now + timedelta(days=3)).replace(hour=23, minute=59, second=59)
            
            # Get all pending tasks
            task_tool = get_task_tool(user_id)
            tasks = task_tool.list_tasks(status_filter="pending")
            
            # Categorize
            overdue = []
            due_today = []
            due_soon = []
            no_due_date = []
            
            for task in tasks:
                if not task.get('due_date'):
                    no_due_date.append(task)
                    continue
                
                due_date = datetime.fromisoformat(task['due_date'])
                
                if due_date < today_start:
                    overdue.append(task)
                elif today_start <= due_date <= today_end:
                    due_today.append(task)
                elif due_date <= soon_end:
                    due_soon.append(task)
            
            # Sort by priority
            priority_order = {'high': 0, 'medium': 1, 'low': 2, None: 3}
            overdue.sort(key=lambda x: priority_order.get(x.get('priority'), 3))
            due_today.sort(key=lambda x: priority_order.get(x.get('priority'), 3))
            due_soon.sort(key=lambda x: (x.get('due_date'), priority_order.get(x.get('priority'), 3)))
            
            # Build response
            parts = []
            
            if overdue:
                parts.append(f"\n⚠️ Overdue ({len(overdue)} task{'s' if len(overdue) != 1 else ''}):")
                for task in overdue:
                    due = datetime.fromisoformat(task['due_date'])
                    days_overdue = (now - due).days
                    priority_str = f"{task.get('priority', '').upper()}: " if task.get('priority') else ""
                    parts.append(f"- {priority_str}{task['title']} ({days_overdue} day{'s' if days_overdue != 1 else ''} overdue)")
            
            if due_today:
                parts.append(f"\n✅ Due Today ({len(due_today)} task{'s' if len(due_today) != 1 else ''}):")
                for task in due_today:
                    priority_str = f"{task.get('priority', '').upper()}: " if task.get('priority') else ""
                    parts.append(f"- {priority_str}{task['title']}")
            
            if due_soon:
                parts.append(f"\n📅 Due Soon ({len(due_soon)} task{'s' if len(due_soon) != 1 else ''}):")
                for task in due_soon:
                    due = datetime.fromisoformat(task['due_date'])
                    due_str = due.strftime("%A")
                    priority_str = f"{task.get('priority', '').upper()}: " if task.get('priority') else ""
                    parts.append(f"- {priority_str}{task['title']} (due{due_str})")
            
            if not parts:
                if no_due_date:
                    return {
                        "type": "task_reminders",
                        "data": {"no_due_date": no_due_date},
                        "message": f"You have {len(no_due_date)} pending task{'s' if len(no_due_date) != 1 else ''} with no due dates."
                    }
                else:
                    return {
                        "type": "task_reminders",
                        "data": {},
                        "message": "You're all caught up! No tasks with upcoming due dates."
                    }
            
            message = "Here's what you need to do:" + "".join(parts)
            
            return {
                "type": "task_reminders",
                "data": {
                    "overdue": overdue,
                    "due_today": due_today,
                    "due_soon": due_soon
                },
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Get reminders failed: {e}")
            return {
                "type": "task_reminders",
                "data": {"error": str(e)},
                "message": "I had trouble getting your reminders."
            }

    async def _handle_daily_summary(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """
        Handle daily summary requests with real calendar data.
        Supports date references like "today", "tomorrow", "next Monday".
        
        Args:
            transcript: User's summary request
            user_id: User identifier for data isolation
            
        Returns:
            Daily summary with calendar events
        """
        logger.info(f"Handler: DAILY_SUMMARY for user {user_id}")
        
        try:
            # Try to get real calendar events
            from app.services.calendar_tool import get_calendar_tool
            
            calendar_tool = get_calendar_tool(user_id=user_id)
            
            # Parse date range from transcript (context-aware)
            resolved_transcript = transcript
            date_keywords = ["today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "yesterday", "next", "last"]
            
            if history and not any(kw in transcript.lower() for kw in date_keywords):
                history_context = ""
                history_lines = []
                for msg in history[-4:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"
                
                resolution_prompt = f"""{history_context}Resolve the date or time reference in this request.
If the user says "tell me more" or "what about then?", use history to find the date they were just talking about.
Original Request: "{transcript}"
Resolved Request (include the date mentioned in history):"""
                try:
                    resp = self.gemini_service.model.generate_content(resolution_prompt)
                    resolved_transcript = resp.text.strip().strip('"')
                    logger.info(f"📅 Resolved summary date: '{transcript}' -> '{resolved_transcript}'")
                except Exception as ex:
                    logger.warning(f"Failed to resolve summary date: {ex}")

            start_date, end_date = self._parse_date_range(resolved_transcript)
            
            # Check if authorized first
            if not calendar_tool.service:
                logger.info(f"User {user_id} requested summary but calendar is not authorized")
                return {
                    "type": "summary",
                    "data": {"error": "not_authorized"},
                    "message": "I don't have access to your calendar yet. You can connect it in the Profile settings!",
                }

            # Fetch events for the specified date range
            events = calendar_tool.get_events_in_range(start_date, end_date)
            
            # Get tasks for comprehensive summary
            from app.services.task_tool import get_task_tool
            task_tool = get_task_tool(user_id)
            all_tasks = task_tool.list_tasks(status_filter="pending")
            
            # Categorize tasks by due date
            overdue_tasks = []
            due_today_tasks = []
            
            for task in all_tasks:
                if not task.get('due_date'):
                    continue
                due_date = datetime.fromisoformat(task['due_date'])
                if due_date < start_date:
                    overdue_tasks.append(task)
                elif start_date <= due_date <= end_date:
                    due_today_tasks.append(task)
            
            # Sort by priority
            priority_order = {'high': 0, 'medium': 1, 'low': 2, None: 3}
            overdue_tasks.sort(key=lambda x: priority_order.get(x.get('priority'), 3))
            due_today_tasks.sort(key=lambda x: priority_order.get(x.get('priority'), 3))

            # Fetch Fitbit health data
            fitbit_tool = get_fitbit_tool()
            health_summary = fitbit_tool.get_daily_summary(start_date)

            if events:
                # Use real calendar data
                summary_message_parts = [calendar_tool.summarize_events(events)]

                # Add health data if available
                if health_summary:
                    summary_message_parts.append(f"\n\n💪 Health Summary:\n{health_summary}")

                # Add overdue tasks
                if overdue_tasks:
                    summary_message_parts.append(f"\n\n⚠️ Overdue ({len(overdue_tasks)} task{'s' if len(overdue_tasks) != 1 else ''}):")
                    for task in overdue_tasks:
                        priority = f"[{task.get('priority', '').upper()}] " if task.get('priority') else ""
                        summary_message_parts.append(f"  • {priority}{task['title']}")
                
                # Add tasks due today
                if due_today_tasks:
                    summary_message_parts.append(f"\n\n✅ Tasks Due Today ({len(due_today_tasks)}):")
                    for task in due_today_tasks:
                        priority = f"[{task.get('priority', '').upper()}] " if task.get('priority') else ""
                        summary_message_parts.append(f"  • {priority}{task['title']}")
                
                summary_message = "\n".join(summary_message_parts)
                
                # Determine date context for response
                now = datetime.now().astimezone()
                is_today = start_date.date() == now.date()
                is_tomorrow = start_date.date() == (now + timedelta(days=1)).date()
                
                # Update message to reflect the date
                if not is_today:
                    if is_tomorrow:
                        date_str = "tomorrow"
                    else:
                        date_str = f"on {start_date.strftime('%A, %B %d')}"
                    
                    # Replace "today" with appropriate date reference
                    summary_message = summary_message.replace("today", date_str)
                
                return {
                    "type": "summary",
                    "data": {
                        "date": start_date.strftime("%Y-%m-%d"),
                        "events": events,
                        "event_count": len(events),
                        "source": "google_calendar"
                    },
                    "message": summary_message,
                }
            else:
                # No events found
                logger.info("No calendar events found for specified date range")

                # Determine date context
                now = datetime.now().astimezone()
                is_today = start_date.date() == now.date()
                is_tomorrow = start_date.date() == (now + timedelta(days=1)).date()

                if is_today:
                    date_msg = "today"
                elif is_tomorrow:
                    date_msg = "tomorrow"
                else:
                    date_msg = f"on {start_date.strftime('%A, %B %d')}"

                # Build message with health data if available
                if health_summary:
                    message = f"You have no events scheduled {date_msg}.\n\n💪 Health Summary:\n{health_summary}"
                else:
                    message = f"You have no events scheduled {date_msg}."

                return {
                    "type": "summary",
                    "data": {
                        "date": start_date.strftime("%Y-%m-%d"),
                        "events": [],
                        "event_count": 0,
                        "source": "google_calendar"
                    },
                    "message": message,
                }
                
        except Exception as e:
            # Fallback to mock data on any error
            logger.warning(f"Calendar integration failed, using mock data: {e}")
            return self._get_mock_daily_summary()
    
    def _get_mock_daily_summary(self) -> Dict[str, Any]:
        """Return mock daily summary data"""
        from datetime import datetime
        return {
            "type": "summary",
            "data": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "tasks_completed": 5,
                "tasks_pending": 3,
                "meetings_attended": 2,
                "highlights": [
                    "Completed project proposal",
                    "Team standup at 10 AM",
                    "Code review session",
                ],
                "source": "mock_data"
            },
            "message": "Today you completed 5 tasks and attended 2 meetings. Great progress!",
        }

    async def _handle_create_calendar_event(self, transcript: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Handle calendar event creation requests.
        
        Args:
            transcript: User's create request
            user_id: User identifier for data isolation
            
        Returns:
            Creation confirmation or error
        """
        logger.info(f"Handler: CREATE_CALENDAR_EVENT for user {user_id}")
        
        try:
            from app.services.calendar_tool import get_calendar_tool
            from datetime import datetime, timedelta
            
            calendar_tool = get_calendar_tool(user_id=user_id)
            
            # Step 2: Extract event details using dedicated method
            logger.info(f"Extracting event details from: {transcript}")
            details = await self.gemini_service.extract_calendar_event(transcript)
            
            summary = details.get('title', 'New Event')
            hour = details.get('hour', datetime.now().hour + 1)
            minute = details.get('minute', 0)
            duration_minutes = details.get('duration', 60)  # Default 1 hour
            
            # Parse date (supports "today", "tomorrow", "2025-12-21", etc.)
            event_date_str = details.get('date')
            now = datetime.now()
            
            if event_date_str:
                try:
                    # Parse ISO date format
                    event_date = datetime.fromisoformat(event_date_str)
                    start_time = event_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                except:
                    # Fallback to today
                    logger.warning(f"Could not parse date '{event_date_str}', using today")
                    start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                # No date specified, use today
                start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time is in the past (and no explicit date), assume next day
            if start_time < now and not event_date_str:
                start_time += timedelta(days=1)
            
            # Set end time based on duration
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Format for Google Calendar API (ISO format with timezone)
            # Use timezone-aware datetime
            from datetime import timezone, timedelta as td
            
            # Get local timezone offset
            local_tz_offset = datetime.now().astimezone().strftime('%z')
            # Format: -0500 -> -05:00
            tz_formatted = f"{local_tz_offset[:3]}:{local_tz_offset[3:]}"
            
            start_iso = start_time.strftime(f"%Y-%m-%dT%H:%M:%S{tz_formatted}")
            end_iso = end_time.strftime(f"%Y-%m-%dT%H:%M:%S{tz_formatted}")
            
            # Create the event
            result = calendar_tool.create_event(
                summary=summary,
                start_time=start_iso,
                end_time=end_iso
            )
            
            if "error" in result:
                return {
                    "type": "calendar_create",
                    "data": result,
                    "message": f"Failed to create event: {result['error']}"
                }
            
            # Format time for response
            time_str = start_time.strftime("%I:%M %p").lstrip('0')
            
            return {
                "type": "calendar_create",
                "data": result,
                "message": f"I've created '{summary}' in your calendar at {time_str} today."
            }
            
        except Exception as e:
            logger.error(f"Calendar creation failed: {e}")
            return {
                "type": "calendar_create",
                "data": {"error": str(e)},
                "message": "I had trouble creating that calendar event. Please try again."
            }

    async def _handle_update_calendar_event(self, transcript: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Handle calendar event update requests.
        
        Args:
            transcript: User's update request
            user_id: User identifier for data isolation
            
        Returns:
            Update confirmation or error
        """
        logger.info(f"Handler: UPDATE_CALENDAR_EVENT for user {user_id}")
        
        try:
            from app.services.calendar_tool import get_calendar_tool
            from datetime import datetime, timedelta
            
            calendar_tool = get_calendar_tool(user_id=user_id)
            
            # Step 2: Extract update details
            logger.info(f"Extracting update details from: {transcript}")
            details = await self.gemini_service.extract_calendar_update(transcript)
            
            event_name = details.get('event_name')
            if not event_name:
                return {
                    "type": "calendar_update",
                    "data": {"error": "Could not identify which event to update"},
                    "message": "I couldn't tell which event you want to update. Please specify the event name."
                }
            
            # Parse date range from transcript (default: next 7 days)
            start_date, end_date = self._parse_date_range(transcript)
            
            # Fetch events in the date range
            events = calendar_tool.get_events_in_range(start_date, end_date)
            
            # Find the event (flexible matching)
            matching_event = None
            
            for event in events:
                event_summary = event.get('summary', '').lower()
                event_name_lower = event_name.lower()
                
                # Match if event_name is in summary OR summary is in event_name
                # e.g., "study" matches "study event" or "study event" matches "study"
                if event_summary and (event_name_lower in event_summary or event_summary in event_name_lower):
                    matching_event = event
                    break
            
            if not matching_event:
                event_names = [e.get('summary') for e in events]
                return {
                    "type": "calendar_update",
                    "data": {"available_events": event_names},
                    "message": f"I couldn't find '{event_name}'. Available events: {', '.join(event_names)}."
                }
            
            # Build update params
            new_title = details.get('new_title')
            new_hour = details.get('new_hour')
            new_minute = details.get('new_minute')
            
            # Format new time if provided
            new_start_time = None
            new_end_time = None
            
            if new_hour is not None:
                now = datetime.now()
                new_start = now.replace(hour=new_hour, minute=new_minute or 0, second=0, microsecond=0)
                
                if new_start < now:
                    new_start += timedelta(days=1)
                
                # Format with timezone
                local_tz_offset = datetime.now().astimezone().strftime('%z')
                tz_formatted = f"{local_tz_offset[:3]}:{local_tz_offset[3:]}"
                
                new_start_time = new_start.strftime(f"%Y-%m-%dT%H:%M:%S{tz_formatted}")
                new_end = new_start + timedelta(hours=1)
                new_end_time = new_end.strftime(f"%Y-%m-%dT%H:%M:%S{tz_formatted}")
            
            # Update the event
            result = calendar_tool.update_event(
                event_id=matching_event['id'],
                summary=new_title,
                start_time=new_start_time,
                end_time=new_end_time
            )
            
            if "error" in result:
                return {
                    "type": "calendar_update",
                    "data": result,
                    "message": f"Failed to update event: {result['error']}"
                }
            
            # Build response message
            changes = []
            if new_title:
                changes.append(f"name to '{new_title}'")
            if new_hour is not None:
                time_str = new_start.strftime("%I:%M %p").lstrip('0')
                changes.append(f"time to {time_str}")
            
            change_desc = " and ".join(changes) if changes else "the event"
            
            return {
                "type": "calendar_update",
                "data": result,
                "message": f"I've updated '{matching_event['summary']}' - changed {change_desc}."
            }
            
        except Exception as e:
            logger.error(f"Calendar update failed: {e}")
            return {
                "type": "calendar_update",
                "data": {"error": str(e)},
                "message": "I had trouble updating that calendar event. Please try again."
            }

    async def _handle_delete_calendar_event(self, transcript: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Handle calendar event deletion requests.
        
        Args:
            transcript: User's delete request
            user_id: User identifier for data isolation
            
        Returns:
            Deletion confirmation or error
        """
        logger.info(f"Handler: DELETE_CALENDAR_EVENT for user {user_id}")
        
        try:
            from app.services.calendar_tool import get_calendar_tool
            
            calendar_tool = get_calendar_tool(user_id=user_id)
            
            # Step 2: Extract event name from transcript
            # Use simple extraction - just pull event name from natural language
            # e.g., "delete the haircut" -> "haircut"
            import re
            
            # Try to extract event name (words after "delete", "remove", etc.)
            delete_keywords = r'(?:delete|remove|cancel)\s+(?:the\s+)?([\w\s]+?)(?:\s+event|\s+appointment|\s+from|\s+at|$)'
            match = re.search(delete_keywords, transcript.lower())
            
            if match:
                event_name = match.group(1).strip()
            else:
                # Fallback: just take the last few words as event name
                words = transcript.split()
                event_name = ' '.join(words[-3:]) if len(words) >= 3 else ' '.join(words)
            
            logger.info(f"Extracted event name for deletion: '{event_name}'")
            
            # Parse date range from transcript (default: next 7 days)
            start_date, end_date = self._parse_date_range(transcript)
            
            # Fetch events in the date range
            events = calendar_tool.get_events_in_range(start_date, end_date)
            
            if not events:
                return {
                    "type": "calendar_delete",
                    "data": {"error": "No events found"},
                    "message": "You don't have any events today to delete."
                }
            
            # Find matching event by name from details (flexible matching)
            matching_event = None
            event_name_lower = event_name.lower()
            
            for event in events:
                event_summary = event.get('summary', '').lower()
                # Match if event_name is in summary OR summary is in event_name
                if event_summary and (event_name_lower in event_summary or event_summary in event_name_lower):
                    matching_event = event
                    break
            
            if not matching_event:
                event_names = [e.get('summary') for e in events]
                return {
                    "type": "calendar_delete",
                    "data": {"available_events": event_names},
                    "message": f"I couldn't find '{event_name}'. You have: {', '.join(event_names)}."
                }
            
            # Delete the event
            result = calendar_tool.delete_event(matching_event['id'])
            
            if "error" in result:
                return {
                    "type": "calendar_delete",
                    "data": result,
                    "message": f"Failed to delete: {result['error']}"
                }
            
            return {
                "type": "calendar_delete",
                "data": {"deleted_event": matching_event['summary']},
                "message": f"I've deleted '{matching_event['summary']}' from your calendar."
            }
            
        except Exception as e:
            logger.error(f"Calendar deletion failed: {e}")
            return {
                "type": "calendar_delete",
                "data": {"error": str(e)},
                "message": "I had trouble deleting that event. Please try again."
            }

    async def _handle_learn(self, transcript: str, history: list = None, file_paths: List[str] = None) -> Dict[str, Any]:
        """
        Handle educational queries using Google Search grounding.
        
        Args:
            transcript: User's learning question
            
        Returns:
            Educational response with citations
        """
        logger.info("Handler: LEARN")
        
        try:
            from app.services.learning_tool import get_learning_tool
            
            # Get learning tool
            learning_tool = get_learning_tool()
            
            # Get user's learning level from profile if available (future enhancement)
            learning_level = None
            
            # Answer question with search grounding (context-aware) and files
            result = await learning_tool.answer_question(transcript, learning_level, history, file_paths=file_paths)
            
            # Handle errors
            if "error" in result:
                return {
                    "type": "educational",
                    "data": {"error": result["error"]},
                    "message": result["answer"]
                }
            
            # Format response - keep answer and citations separate
            answer = result["answer"]
            citations = result.get("citations", [])
            
            # Message contains only the answer (UI will display citations separately)
            message = answer
            
            return {
                "type": "educational",
                "data": {
                    "answer": answer,
                    "citations": citations,
                    "confidence": result.get("confidence", "medium")
                },
                "message": message,
            }
            
        except Exception as e:
            logger.error(f"Learn handler failed: {e}")
            return {
                "type": "educational",
                "data": {"error": str(e)},
                "message": "I'm having trouble finding information on that right now.",
            }
    async def _handle_news(self, transcript: str, history: list = None) -> Dict[str, Any]:
        """
        Handle news requests using NewsAPI.org.
        """
        logger.info("Handler: GET_NEWS")
        
        try:
            from app.services.news_tool import get_news_tool
            
            # Extract news topic using Gemini (context-aware)
            history_context = ""
            if history and len(history) > 0:
                history_lines = []
                for msg in history[-4:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

            prompt = f"""{history_context}Extract the news topic or search query from this text. 
Return ONLY the topic. If it's a general request like "latest news", return "top headlines".
If the user says "more news" or "anything else?", use the history to find the previous topic.
Use history to resolve pronouns like "that" or "them".

Request: "{transcript}"

Topic:"""

            response = self.gemini_service.model.generate_content(
                prompt,
                generation_config={"temperature": 0.0, "max_output_tokens": 20}
            )
            
            topic = response.text.strip().strip('"\'')
            if not topic:
                topic = "top headlines"
            
            logger.info(f"📰 News topic: '{topic}'")
            
            # Get news tool
            news_tool = get_news_tool()
            
            # Get news briefing
            result = await news_tool.get_news_briefing(topic)
            
            return {
                "type": "news",
                "data": result.get("data", {}),
                "message": result.get("message", f"Here are the latest updates on {topic}.")
            }
            
        except Exception as e:
            logger.error(f"News handler failed: {e}")
            return {
                "type": "news",
                "data": {"error": str(e)},
                "message": "I'm having trouble getting the news right now."
            }

    async def _handle_check_email(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """
        Handle email check requests - get unread count and recent emails.
        Extracts parameters from user request like "last 5 emails", "unread emails", etc.
        
        Args:
            transcript: User's request (e.g., "show me my last 5 emails")
            user_id: User identifier for data isolation
            
        Returns:
            Email summary with requested emails
        """
        logger.info(f"Handler: CHECK_EMAIL for user {user_id}")
        
        try:
            gmail_tool = get_gmail_tool(user_id=user_id)
            
            # Check if authorized
            if not gmail_tool.service:
                logger.info(f"User {user_id} requested email check but Gmail is not authorized")
                return {
                    "type": "email",
                    "data": {"error": "not_authorized"},
                    "message": "I don't have access to your Gmail yet. You can connect it in the Profile settings!"
                }
            
            # Extract email parameters from user's request using Gemini (context-aware)
            import json
            history_context = ""
            if history and len(history) > 0:
                history_lines = []
                for msg in history[-4:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

            prompt = f"""{history_context}Extract email query parameters from this request. Return JSON only.
Use the conversation history to resolve pronouns like "those" or "them" (e.g., "summarize them").

Request: "{transcript}"

Extract:
- count: number of emails requested (default 5 if not specified)
- filter: "unread", "all", or "today" (default "unread" for checking emails)
- summarize: true if user wants a summary, false for just listing

Examples:
"show me my last 5 emails" -> {{"count": 5, "filter": "all", "summarize": false}}
"do I have any new emails" -> {{"count": 3, "filter": "unread", "summarize": false}}
"summarize my last 10 emails" -> {{"count": 10, "filter": "all", "summarize": true}}
"check my inbox" -> {{"count": 5, "filter": "unread", "summarize": false}}

JSON:"""

            try:
                response = self.gemini_service.model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.0, "max_output_tokens": 100}
                )
                response_text = response.text.strip()
                
                # Extract JSON
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                params = json.loads(response_text)
                email_count = min(params.get("count", 5), 20)  # Cap at 20
                email_filter = params.get("filter", "unread")
                summarize = params.get("summarize", False)
                
                logger.info(f"📧 Email params: count={email_count}, filter={email_filter}, summarize={summarize}")
            except Exception as e:
                logger.warning(f"Failed to parse email params, using defaults: {e}")
                email_count = 5
                email_filter = "unread"
                summarize = False
            
            # Build query based on filter - always include category:primary
            base_filter = "category:primary"
            if email_filter == "unread":
                query = f"{base_filter} is:unread"
            elif email_filter == "today":
                from datetime import datetime
                today = datetime.now().strftime("%Y/%m/%d")
                query = f"{base_filter} after:{today}"
            else:
                # "all" = just primary inbox
                query = base_filter
            
            # Get unread count for context
            unread_count = gmail_tool.get_unread_count()
            
            # Get emails based on extracted parameters
            emails = gmail_tool.get_recent_emails(max_results=email_count, query=query)
            
            # Build response
            if not emails:
                if email_filter == "unread":
                    message = "You have no unread emails. Your inbox is all caught up!"
                else:
                    message = f"I couldn't find any emails matching your request."
            else:
                # Summary response
                if summarize:
                    message = gmail_tool.summarize_emails(emails)
                else:
                    # List response
                    if email_filter == "unread":
                        message = f"You have {unread_count} unread email{'s' if unread_count != 1 else ''}."
                        if unread_count > 0:
                            message += f" Here are the latest {min(len(emails), email_count)}:\n"
                    else:
                        message = f"Here are your last {len(emails)} email{'s' if len(emails) != 1 else ''}:\n"
                    
                    for i, email in enumerate(emails, 1):
                        sender = email.get('from', 'Unknown')
                        if '<' in sender:
                            sender = sender.split('<')[0].strip()
                        subject = email.get('subject', '(No Subject)')
                        if len(subject) > 50:
                            subject = subject[:47] + "..."
                        unread_icon = "📬" if email.get('is_unread') else "📭"
                        message += f"\n{i}. {unread_icon} '{subject}' from {sender}"
            
            return {
                "type": "email",
                "data": {
                    "unread_count": unread_count,
                    "emails": emails,
                    "count_requested": email_count,
                    "filter": email_filter,
                    "source": "gmail"
                },
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Check email handler failed: {e}")
            return {
                "type": "email",
                "data": {"error": str(e)},
                "message": "I'm having trouble checking your emails right now."
            }

    async def _handle_search_email(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """
        Handle email search requests - find specific emails.
        
        Args:
            transcript: User's request (e.g., "find emails from John")
            user_id: User identifier for data isolation
            
        Returns:
            Search results with matching emails
        """
        logger.info(f"Handler: SEARCH_EMAIL for user {user_id}")
        
        try:
            gmail_tool = get_gmail_tool(user_id=user_id)
            
            # Check if authorized
            if not gmail_tool.service:
                logger.info(f"User {user_id} requested email search but Gmail is not authorized")
                return {
                    "type": "email_search",
                    "data": {"error": "not_authorized"},
                    "message": "I don't have access to your Gmail yet. You can connect it in the Profile settings!"
                }
            
            # Extract search query using Gemini (context-aware)
            history_context = ""
            if history and len(history) > 0:
                history_lines = []
                for msg in history[-4:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

            prompt = f"""{history_context}Extract the Gmail search query from this request. 
Return ONLY the Gmail search syntax. Use Gmail operators: from:, subject:, to:, is:unread, newer_than:, older_than:

Use history to resolve pronouns like "from him" or "about that".

IMPORTANT: 
- For "from" queries, use the exact name: "from John" → "from:John"
- Keep queries simple and precise
- Do NOT include "category:primary" - I'll add that

Examples:
- "find emails from John" → "from:John"
- "find emails from John Smith" → "from:John Smith"
- "emails about meeting" → "subject:meeting OR meeting"
- "messages from boss last week" → "from:boss newer_than:7d"
- "unread emails from sarah" → "from:sarah is:unread"
- "emails from amazon" → "from:amazon"

Request: "{transcript}"

Gmail query:"""

            response = self.gemini_service.model.generate_content(
                prompt,
                generation_config={"temperature": 0.0, "max_output_tokens": 50}
            )
            
            query = response.text.strip().strip('"\'')
            if not query:
                query = transcript  # Fallback to raw transcript
            
            # Always add category:primary to filter out Promotions/Social/Updates
            if "category:" not in query.lower():
                query = f"category:primary {query}"
            
            logger.info(f"📧 Gmail search query: '{query}'")
            
            # Search emails
            results = gmail_tool.search_emails(query=query, max_results=5)
            
            if not results:
                return {
                    "type": "email_search",
                    "data": {"query": query, "results": []},
                    "message": f"I couldn't find any emails matching '{query}'."
                }
            
            # Build response
            message = f"I found {len(results)} email{'s' if len(results) != 1 else ''} matching your search:\n"
            
            for i, email in enumerate(results[:3], 1):
                sender = email.get('from', 'Unknown')
                if '<' in sender:
                    sender = sender.split('<')[0].strip()
                subject = email.get('subject', '(No Subject)')
                if len(subject) > 40:
                    subject = subject[:37] + "..."
                unread = "📬" if email.get('is_unread') else "📭"
                message += f"\n{i}. {unread} '{subject}' from {sender}"
            
            if len(results) > 3:
                message += f"\n\n...and {len(results) - 3} more."
            
            return {
                "type": "email_search",
                "data": {
                    "query": query,
                    "results": results,
                    "source": "gmail"
                },
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Search email handler failed: {e}")
            return {
                "type": "email_search",
                "data": {"error": str(e)},
                "message": "I'm having trouble searching your emails right now."
            }

    async def _handle_analyze_email(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """
        Handle email content analysis requests - read bodies and analyze with LLM.
        
        Args:
            transcript: User's request (e.g., "do any of my emails have deadlines?")
            user_id: User identifier for data isolation
            
        Returns:
            Analysis results from reading email content
        """
        logger.info(f"Handler: ANALYZE_EMAIL for user {user_id}")
        
        try:
            gmail_tool = get_gmail_tool(user_id=user_id)
            
            # Check if authorized
            if not gmail_tool.service:
                logger.info(f"User {user_id} requested email analysis but Gmail is not authorized")
                return {
                    "type": "email_analysis",
                    "data": {"error": "not_authorized"},
                    "message": "I don't have access to your Gmail yet. You can connect it in the Profile settings!"
                }
            
            # Extract how many emails to analyze (default 5, max 10)
            import re
            count_match = re.search(r'\b(\d+)\s*emails?\b', transcript.lower())
            email_count = min(int(count_match.group(1)), 10) if count_match else 5
            
            # Fetch recent emails from Primary inbox
            emails = gmail_tool.get_recent_emails(max_results=email_count, query="category:primary")
            
            if not emails:
                return {
                    "type": "email_analysis",
                    "data": {"emails_analyzed": 0},
                    "message": "You don't have any recent emails in your Primary inbox to analyze."
                }
            
            # Fetch full body for each email
            email_contents = []
            for email in emails:
                body = gmail_tool.get_email_body(email.get('id', ''))
                # Truncate long bodies to avoid token limits
                if len(body) > 1500:
                    body = body[:1500] + "...[truncated]"
                
                email_contents.append({
                    'from': email.get('from', 'Unknown'),
                    'subject': email.get('subject', '(No Subject)'),
                    'date': email.get('date', ''),
                    'body': body or email.get('snippet', '')
                })
            
            # Build email digest for LLM
            email_digest = ""
            for i, e in enumerate(email_contents, 1):
                email_digest += f"\n--- Email {i} ---\n"
                email_digest += f"From: {e['from']}\n"
                email_digest += f"Subject: {e['subject']}\n"
                email_digest += f"Date: {e['date']}\n"
                email_digest += f"Content: {e['body']}\n"
            
            # Send to LLM for analysis (context-aware analysis)
            history_context = ""
            if history and len(history) > 0:
                history_lines = []
                for msg in history[-4:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

            prompt = f"""{history_context}You are Manas, analyzing the user's emails to answer their question.
Use history if the user's question refers to previous turns.

User's question: "{transcript}"

Here are their last {len(email_contents)} emails:
{email_digest}

Based on these emails, answer the user's question directly and conversationally.
Be specific - mention email subjects/senders when relevant.
Keep response under 3 sentences unless they asked for a detailed summary."""

            response = self.gemini_service.model.generate_content(
                prompt,
                generation_config={"temperature": 0.7, "max_output_tokens": 300}
            )
            
            analysis = response.text.strip()
            
            return {
                "type": "email_analysis",
                "data": {
                    "emails_analyzed": len(email_contents),
                    "question": transcript
                },
                "message": analysis
            }
            
        except Exception as e:
            logger.error(f"Analyze email handler failed: {e}")
            return {
                "type": "email_analysis",
                "data": {"error": str(e)},
                "message": "I'm having trouble analyzing your emails right now."
            }

    async def _handle_read_email(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """
        Handle requests to read a specific email thread.
        """
        logger.info(f"Handler: READ_EMAIL for user {user_id}")
        
        try:
            gmail_tool = get_gmail_tool(user_id=user_id)
            if not gmail_tool.service:
                return {
                    "type": "email_thread",
                    "data": {"error": "not_authorized"},
                    "message": "I don't have access to your Gmail yet."
                }

            # Use Gemini to resolve WHICH email to read based on transcript and history
            history_context = ""
            if history:
                history_lines = []
                for msg in history[-6:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

            prompt = f"""{history_context}The user wants to read a specific email. 
Identify the target email from the conversation history. 
Look for things like "the first one", "the one from Sarah", "that flight email".

Extract:
- thread_id: the thread ID of the target email (if available in history)
- message_id: the message ID (if available)
- sender_name: name of the sender mentioned
- subject_hint: some words from the subject

Return ONLY JSON.
{{ "thread_id": "...", "message_id": "...", "sender_hint": "...", "subject_hint": "..." }}

Request: "{transcript}"
JSON:"""

            response = self.gemini_service.model.generate_content(
                prompt,
                generation_config={"temperature": 0.0, "max_output_tokens": 150}
            )
            
            import json
            res_text = response.text.strip()
            if "```json" in res_text:
                res_text = res_text.split("```json")[1].split("```")[0].strip()
            
            resolve_data = json.loads(res_text)
            thread_id = resolve_data.get("thread_id")
            message_id = resolve_data.get("message_id")
            
            # If we don't have a direct ID, search for it
            if not thread_id and not message_id:
                search_query = ""
                if resolve_data.get("sender_hint"):
                    search_query += f"from:{resolve_data['sender_hint']} "
                if resolve_data.get("subject_hint"):
                    search_query += f"subject:{resolve_data['subject_hint']} "
                
                if not search_query:
                    search_query = transcript
                
                logger.info(f"🔍 READ_EMAIL: Searching for target email with query: '{search_query}'")
                search_results = gmail_tool.search_emails(f"category:primary {search_query}", max_results=1)
                
                if search_results:
                    message_id = search_results[0]['id']
                    # We'll fetch the full details below to get threadId
            
            if not message_id and not thread_id:
                return {
                    "type": "email_thread",
                    "data": {"error": "not_found"},
                    "message": "I couldn't figure out which email you'd like me to read. Could you be more specific?"
                }

            # Fetch thread details
            if not thread_id and message_id:
                details = gmail_tool.get_email_details(message_id)
                thread_id = details.get("threadId")

            if thread_id:
                messages = gmail_tool.get_thread_messages(thread_id)
                if messages:
                    # Get shared subject from last message headers if needed
                    first_msg = gmail_tool.get_email_details(messages[0]['id'])
                    subject = first_msg.get('subject', 'No Subject')
                    
                    return {
                        "type": "email_thread",
                        "data": {
                            "thread_id": thread_id,
                            "subject": subject,
                            "messages": messages,
                            "count": len(messages)
                        },
                        "message": f"I've opened the thread '{subject}'. It has {len(messages)} message{'s' if len(messages) != 1 else ''}."
                    }
            
            # Fallback to single message
            if message_id:
                details = gmail_tool.get_email_details(message_id)
                return {
                    "type": "email_thread",
                    "data": {
                        "thread_id": details.get("threadId"),
                        "subject": details.get('subject'),
                        "messages": [{
                            "id": message_id,
                            "from": details.get('from'),
                            "date": details.get('date'),
                            "body": details.get('body'),
                            "snippet": details.get('snippet')
                        }],
                        "count": 1
                    },
                    "message": f"Here is the email from {details.get('from')}."
                }

            return {
                "type": "email_thread",
                "data": {"error": "failed_retrieval"},
                "message": "I had trouble loading that email. Please try again."
            }

        except Exception as e:
            logger.error(f"Read email handler failed: {e}")
            return {
                "type": "email_thread",
                "data": {"error": str(e)},
                "message": "I'm having trouble opening that email right now."
            }

    async def _handle_search_restaurants(
        self, 
        transcript: str, 
        user_id: str = "default",
        profile: Dict[str, Any] = None,
        history: list = None
    ) -> Dict[str, Any]:
        """
        Handle restaurant search requests using Yelp AI API.
        
        Args:
            transcript: User's request (e.g., "find Italian restaurants near me")
            user_id: User identifier
            profile: User profile with location info
            
        Returns:
            Search results with restaurants and AI-generated summary
        """
        logger.info(f"Handler: SEARCH_RESTAURANTS for user {user_id}")
        
        try:
            yelp_tool = get_yelp_tool()
            memory_service = get_memory_service()
            
            # Check if Yelp API is configured
            if not yelp_tool.is_available:
                logger.warning("Yelp API not configured")
                return {
                    "type": "restaurants",
                    "data": {"error": "not_configured"},
                    "message": "Restaurant search isn't configured yet. Please add YELP_API_KEY to your environment."
                }
            
            # Extract location from profile if available
            latitude = None
            longitude = None
            location_context = ""
            
            if profile:
                location = profile.get("location", "")
                if location:
                    location_context = location
                # Try to get coordinates from profile (if stored)
                if profile.get("latitude") and profile.get("longitude"):
                    latitude = profile.get("latitude")
                    longitude = profile.get("longitude")
            
            # Check memories for location and food preferences
            food_preference = ""
            if user_id:
                try:
                    memories = memory_service.get_all_memories(user_id)
                    for mem in memories:
                        if isinstance(mem, dict):
                            text = mem.get("memory", mem.get("text", "")).lower()
                        else:
                            text = str(mem).lower()
                        # Look for location keywords
                        if any(kw in text for kw in ["live in", "lives in", "living in", "i'm from", "located in", "i'm in", "i am in", "i stay in"]):
                            location_context = text
                            logger.info(f"📍 Found location in memory: {text}")
                        # Look for food preferences
                        if any(kw in text for kw in ["vegetarian", "vegan", "gluten-free", "halal", "kosher", "allergic", "don't eat", "prefer"]):
                            food_preference = text
                            logger.info(f"🥗 Found food preference in memory: {text}")
                except Exception as e:
                    logger.warning(f"Could not get memories: {e}")
            
            # Resolve transcript if it has pronouns and history is available
            resolved_transcript = transcript
            if history and any(kw in transcript.lower() for kw in ["there", "it", "that", "those", "here"]):
                history_context = ""
                history_lines = []
                for msg in history[-4:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"
                
                resolution_prompt = f"""{history_context}Resolve the location or cuisine in this restaurant search request.
Use history to resolve pronouns like "there", "it", "that".
Original Request: "{transcript}"
Resolved Request (short and factual):"""
                try:
                    resp = self.gemini_service.model.generate_content(resolution_prompt)
                    resolved_transcript = resp.text.strip().strip('"')
                    logger.info(f"🍽️ Resolved restaurant query: '{transcript}' -> '{resolved_transcript}'")
                except Exception as ex:
                    logger.warning(f"Failed to resolve restaurant query: {ex}")

            # Enhance query with location and preferences
            query = resolved_transcript
            needs_location = any(kw in transcript.lower() for kw in ["near me", "nearest", "nearby", "around me", "close to me"])
            
            # If no location from profile/memory and needs location, try IP geolocation
            if not location_context and needs_location and latitude is None:
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        response = await client.get("http://ip-api.com/json")
                        ip_data = response.json()
                        if ip_data.get('status') == 'success':
                            latitude = ip_data.get('lat')
                            longitude = ip_data.get('lon')
                            location_context = f"{ip_data.get('city')}, {ip_data.get('regionName')}"
                            logger.info(f"📍 Auto-detected location for Yelp: {location_context} ({latitude}, {longitude})")
                except Exception as e:
                    logger.warning(f"IP-based location detection failed for Yelp: {e}")
            if location_context and needs_location:
                # Append location context to query
                query = f"{transcript} in {location_context}"
                logger.info(f"🍽️ Enhanced query with location: {query}")
            
            if food_preference and not any(kw in transcript.lower() for kw in ["vegetarian", "vegan", "gluten", "halal", "kosher"]):
                # Add food preference if not already specified
                query = f"{query} ({food_preference})"
                logger.info(f"🍽️ Enhanced query with preference: {query}")
            
            # Search using Yelp AI
            chat_id = self.yelp_chat_ids.get(user_id)
            response = await yelp_tool.search_restaurants(
                query=query,
                latitude=latitude,
                longitude=longitude,
                chat_id=chat_id
            )
            
            # Store chat_id for multi-turn conversational support
            if response.chat_id:
                self.yelp_chat_ids[user_id] = response.chat_id
            
            # Format businesses for response
            businesses_data = []
            for biz in response.businesses[:5]:  # Limit to 5 results
                businesses_data.append({
                    "id": biz.id,
                    "name": biz.name,
                    "rating": biz.rating,
                    "review_count": biz.review_count,
                    "price": biz.price,
                    "distance": biz.distance,
                    "image_url": biz.image_url,
                    "tags": biz.tags,
                    "url": biz.url,
                    "phone": biz.phone,
                    "address": ", ".join(biz.location.get("display_address", [])) if biz.location else None,
                    "categories": biz.categories
                })
            
            # Build user-friendly message
            if response.response_text:
                message = response.response_text
            elif businesses_data:
                message = f"I found {len(businesses_data)} restaurants for you:\n"
                for i, biz in enumerate(businesses_data[:3], 1):
                    rating = f"⭐ {biz['rating']}" if biz.get('rating') else ""
                    price = biz.get('price', '')
                    message += f"\n{i}. {biz['name']} {rating} {price}"
            else:
                message = "I couldn't find any restaurants matching your request. Try being more specific about the cuisine or location."
            
            return {
                "type": "restaurants",
                "data": {
                    "businesses": businesses_data,
                    "count": len(businesses_data),
                    "chat_id": response.chat_id
                },
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Search restaurants handler failed: {e}")
            return {
                "type": "restaurants",
                "data": {"error": str(e)},
                "message": "I'm having trouble searching for restaurants right now. Please try again."
            }

    async def _handle_remember_this(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """
        Handle requests to remember facts/preferences.
        """
        logger.info(f"Handler: REMEMBER_THIS for user {user_id}")
        
        try:
            memory_service = get_memory_service()
            
            # Resolve history context
            history_context = ""
            if history:
                history_lines = []
                for msg in history[-4:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"

            # Extract what to remember using Gemini
            prompt = f"""{history_context}Extract the fact or information the user wants to remember.
If the user says "remember this" or "save that", use the history to find the important information they just mentioned.
Return ONLY the fact as a clear, concise statement from the user's perspective.

Examples:
"Remember I have a second wife named Sarah" -> "Second wife's name is Sarah"

User request: "{transcript}"

Fact to remember:"""

            response = self.gemini_service.model.generate_content(
                prompt,
                generation_config={"temperature": 0.0, "max_output_tokens": 100}
            )
            
            fact = response.text.strip().strip('"\'')
            
            if not fact:
                return {
                    "type": "memory",
                    "data": {"error": "could not extract"},
                    "message": "I couldn't understand what you'd like me to remember. Could you rephrase that?"
                }
            
            # Fire-and-forget: Store memory in background for instant response
            async def save_memory_async():
                try:
                    result = memory_service.add_memory(user_id, fact, metadata={"source": "explicit"})
                    if result.get("success"):
                        logger.info(f"✓ Background: Stored memory for {user_id}: {fact}")
                    else:
                        logger.warning(f"Background: Failed to store memory: {result.get('error')}")
                except Exception as e:
                    logger.error(f"Background: Memory save failed: {e}")
            
            # Don't await - fire and forget!
            asyncio.create_task(save_memory_async())
            
            logger.info(f"Responding immediately, memory save in background for {user_id}")
            return {
                "type": "memory",
                "data": {"action": "stored", "memory": fact},
                "message": f"Got it! I'll remember that."
            }
                
        except Exception as e:
            logger.error(f"Remember handler failed: {e}")
            return {
                "type": "memory",
                "data": {"error": str(e)},
                "message": "I'm having trouble with my memory right now."
            }

    async def _handle_recall_memory(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """
        Handle requests to recall stored memories.
        
        Args:
            transcript: User's request (e.g., "what do you know about my family?")
            user_id: User identifier for data isolation
            
        Returns:
            List of relevant memories
        """
        logger.info(f"Handler: RECALL_MEMORY for user {user_id}")
        
        try:
            memory_service = get_memory_service()
            
            # Check if asking for everything or specific topic
            is_general = any(phrase in transcript.lower() for phrase in [
                "what do you know about me",
                "what do you remember",
                "everything you know",
                "all my info",
                "what have i told you"
            ])
            
            if is_general:
                # Get all memories
                memories = memory_service.get_all_memories(user_id)
            else:
                # Search for relevant memories (Gemini-based parameter extraction recommended in future)
                search_query = transcript
                
                # If transcript is very short and we have history, try to resolve pronouns
                if len(transcript.split()) < 4 and history:
                    # Quick prompt to resolve pronoun for memory search
                    # (This is an inline extraction for now)
                    history_context = ""
                    history_lines = []
                    for msg in history[-4:]:
                        role = "User" if msg.get("role") == "user" else "Manas"
                        content = msg.get("parts", "")
                        history_lines.append(f"{role}: {content}")
                    history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"
                    
                    prompt = f"""{history_context}Resolve the subject of this memory query. 
Use the history to resolve pronouns like "that", "it", or "him".
Query: "{transcript}"
Resolved Subject (short):"""
                    try:
                        resp = self.gemini_service.model.generate_content(prompt)
                        search_query = resp.text.strip()
                        logger.info(f"🧠 Resolved memory search: '{transcript}' -> '{search_query}'")
                    except:
                        pass

                memories = memory_service.search_memories(user_id, search_query, limit=10)
            
            if not memories:
                return {
                    "type": "memory",
                    "data": {"action": "recall", "memories": []},
                    "message": "I don't have any memories stored for you yet. Tell me something to remember!"
                }
            
            # Format memories - handle both dict and string formats
            memory_list = []
            for mem in memories:
                if isinstance(mem, str):
                    # Mem0 returned raw strings
                    memory_text = mem
                elif isinstance(mem, dict):
                    # Mem0 returned dicts
                    memory_text = mem.get("memory", mem.get("text", str(mem)))
                else:
                    memory_text = str(mem)
                
                if memory_text:
                    memory_list.append(memory_text)
            
            if not memory_list:
                return {
                    "type": "memory",
                    "data": {"action": "recall", "memories": []},
                    "message": "I don't have any relevant memories about that."
                }
            
            # Build response
            if is_general:
                message = f"Here's what I remember about you:\n"
            else:
                message = f"Here's what I remember about that:\n"
            
            for i, mem in enumerate(memory_list[:10], 1):
                message += f"\n{i}. {mem}"
            
            if len(memory_list) > 10:
                message += f"\n\n...and {len(memory_list) - 10} more things."
            
            return {
                "type": "memory",
                "data": {"action": "recall", "memories": memory_list, "count": len(memory_list)},
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Recall memory handler failed: {e}")
            return {
                "type": "memory",
                "data": {"error": str(e)},
                "message": "I'm having trouble accessing my memory right now."
            }

    async def _handle_forget_this(self, transcript: str, user_id: str = "default", history: list = None) -> Dict[str, Any]:
        """
        Handle requests to delete specific memories.
        
        Args:
            transcript: User's request (e.g., "forget what I told you about my job")
            user_id: User identifier for data isolation
            
        Returns:
            Confirmation of deleted memory
        """
        logger.info(f"Handler: FORGET_THIS for user {user_id}")
        
        try:
            memory_service = get_memory_service()
            
            # Check if user wants to forget everything
            forget_all = any(phrase in transcript.lower() for phrase in [
                "forget everything",
                "clear all memories",
                "delete all",
                "forget all"
            ])
            
            if forget_all:
                success = memory_service.delete_all_memories(user_id)
                if success:
                    return {
                        "type": "memory",
                        "data": {"action": "deleted_all"},
                        "message": "I've forgotten everything about you. We're starting fresh!"
                    }
                else:
                    return {
                        "type": "memory",
                        "data": {"error": "delete_failed"},
                        "message": "I had trouble clearing my memories."
                    }
            
            # Find matching memories to delete
            memories = memory_service.search_memories(user_id, transcript, limit=5)
            
            if not memories:
                return {
                    "type": "memory",
                    "data": {"action": "not_found"},
                    "message": "I couldn't find any memories matching that. What would you like me to forget?"
                }
            
            # Delete the top matching memory
            top_memory = memories[0]
            
            # Handle both dict and string formats
            if isinstance(top_memory, str):
                memory_id = None  # Can't delete by ID if just a string
                memory_text = top_memory
            elif isinstance(top_memory, dict):
                memory_id = top_memory.get("id")
                memory_text = top_memory.get("memory", top_memory.get("text", str(top_memory)))
            else:
                memory_id = None
                memory_text = str(top_memory)
            
            if memory_id:
                success = memory_service.delete_memory(memory_id, user_id=user_id)
                if success:
                    return {
                        "type": "memory",
                        "data": {"action": "deleted", "memory": memory_text},
                        "message": f"Done! I've forgotten that: {memory_text}"
                    }
            
            return {
                "type": "memory",
                "data": {"error": "delete_failed"},
                "message": f"I found '{memory_text}' but couldn't delete it. The memory format may not support deletion."
            }
            
        except Exception as e:
            logger.error(f"Forget handler failed: {e}")
            return {
                "type": "memory",
                "data": {"error": str(e)},
                "message": "I'm having trouble with my memory right now."
            }

    async def _handle_general_chat(self, transcript: str, profile: Dict[str, Any] = None, history: list = None, user_id: str = None, file_paths: List[str] = None) -> Dict[str, Any]:
        """
        Handle general conversation using Gemini AI with memory context.
        
        Args:
            transcript: User's conversational message
            profile: Optional user profile for personalization
            history: Optional conversation history for context
            user_id: Optional user ID for memory context injection
            
        Returns:
            Conversational response from Gemini
        """
        logger.info("Handler: GENERAL_CHAT")
        
        try:
            # Inject user memories as context if available
            memory_context = ""
            if user_id:
                try:
                    memory_service = get_memory_service()
                    memories = memory_service.get_all_memories(user_id)
                    if memories:
                        memory_parts = []
                        for mem in memories:
                            if isinstance(mem, dict):
                                text = mem.get("memory", mem.get("text", ""))
                            else:
                                text = str(mem)
                            if text:
                                memory_parts.append(f"- {text}")
                        if memory_parts:
                            memory_context = "Facts the user told me about themselves (these describe the user's life, NOT the user's name - use 'your' when referencing):\n" + "\n".join(memory_parts)
                            print(f"💭 Injecting {len(memory_parts)} memories into chat context")
                except Exception as e:
                    logger.warning(f"Failed to get memories for context: {e}")
            
            # Generate conversational response with profile, history, memory context, and files
            response = await self.gemini_service.generate_response(
                transcript, 
                profile, 
                history,
                memory_context=memory_context,
                file_paths=file_paths
            )
            
            return {
                "type": "conversation",
                "data": {
                    "response_type": "casual",
                    "context": "general_chat",
                    "memory_used": bool(memory_context),
                },
                "message": response,
            }
        except Exception as e:
            logger.error(f"General chat failed: {e}")
            return {
                "type": "conversation",
                "data": {"error": str(e)},
                "message": "I'm having trouble thinking right now. Can you try again?",
            }

    async def _handle_doc_analysis(self, transcript: str, profile: Dict[str, Any] = None, history: list = None, user_id: str = None, file_paths: List[str] = None) -> Dict[str, Any]:
        """Specific handler for document/image analysis to ensure focus."""
        logger.info("Handler: DOC_ANALYSIS")
        
        # Prepend instruction for focus
        focused_transcript = f"[SYSTEM: Analyze the provided document/image. Answer the user based ONLY on the content of the file(s).] {transcript}"
        
        return await self._handle_general_chat(focused_transcript, profile, history, user_id, file_paths)

@lru_cache
def get_orchestrator() -> OrchestratorService:
    """
    Get cached orchestrator service instance.
    
    Returns:
        Configured OrchestratorService instance
    """
    return OrchestratorService()
