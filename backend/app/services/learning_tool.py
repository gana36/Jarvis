"""
Learning Tool - Educational Questions with Brave Search

Uses Gemini + Brave Search API to answer educational questions
with accurate, web-sourced citations.
"""

import logging
import os
import httpx
import mimetypes
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class LearningTool:
    """Educational question answering with Brave Search integration."""
    
    def __init__(self, gemini_model=None):
        """
        Initialize learning tool with Gemini model and Brave Search.
        
        Args:
            gemini_model: Gemini model instance for answer generation
        """
        self.gemini = gemini_model
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour cache
        
        # Get You.com API key from config settings
        from app.config import get_settings
        settings = get_settings()
        self.youcom_api_key = settings.youcom_api_key
        
        if not self.youcom_api_key:
            logger.warning("YOUCOM_API_KEY not set - web search disabled")
        
        if not self.gemini:
            logger.warning("Learning tool initialized without Gemini model")
    
    async def answer_question(
        self, 
        question: str, 
        learning_level: Optional[str] = None,
        history: list = None,
        file_paths: List[str] = None
    ) -> Dict[str, Any]:
        """
        Answer educational question using web search + Gemini.
        
        Args:
            question: The educational question to answer
            learning_level: Optional learning level (beginner/intermediate/advanced)
            
        Returns:
            Dict with answer, citations, and confidence
        """
        # Check cache
        cache_key = f"{question}:{learning_level or 'default'}"
        if cache_key in self.cache:
            age = (datetime.now() - self.cache[cache_key]['timestamp']).total_seconds()
            if age < self.cache_ttl:
                logger.info(f"📚 Cache HIT for learning question")
                return self.cache[cache_key]['data']
        
        if not self.gemini:
            return {
                "error": "model_not_configured",
                "answer": "Educational service not configured.",
                "citations": []
            }
        
        try:
            # Resolve question if short and history present (pronoun resolution)
            resolved_question = question
            if history and len(question.split()) <= 10:
                history_context = ""
                history_lines = []
                for msg in history[-4:]:
                    role = "User" if msg.get("role") == "user" else "Manas"
                    content = msg.get("parts", "")
                    history_lines.append(f"{role}: {content}")
                history_context = "Conversation History:\n" + "\n".join(history_lines) + "\n\n"
                
                resolution_prompt = f"""{history_context}Resolve the subject of this question.
Use history to resolve pronouns like "him", "her", "it", "that".
Question: "{question}"
Resolved Question (short and factual):"""
                try:
                    resp = self.gemini.generate_content(resolution_prompt)
                    resolved_question = resp.text.strip().strip('"')
                    logger.info(f"📚 Resolved learning query: '{question}' -> '{resolved_question}'")
                except Exception as ex:
                    logger.warning(f"Failed to resolve question: {ex}")

            # Search the web if You.com API key available
            search_results = ""
            citations = []
            
            if self.youcom_api_key:
                search_data = await self._search_web(resolved_question)
                if search_data:
                    search_results = search_data['context']
                    citations = search_data['citations']
            
            # Generate answer using Gemini with search context (and files if any)
            answer = await self._generate_answer(resolved_question, search_results, learning_level, file_paths=file_paths)
            
            result = {
                "answer": answer,
                "citations": citations,
                "confidence": "high" if citations else "medium"
            }
            
            # Cache it
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }
            
            logger.info(f"✅ Learning: Answered with {len(citations)} citations")
            return result
            
        except Exception as e:
            logger.error(f"Learning tool error: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "error": "generation_failed",
                "answer": "I'm having trouble finding information on that right now.",
                "citations": []
            }
    
    async def _search_web(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search the web using You.com RAG API.
        
        Returns:
            Dict with context and citations, or None if search fails
        """
        try:
            url = "https://ydc-index.io/v1/search"
            headers = {
                "X-API-Key": self.youcom_api_key
            }
            params = {
                "query": query,
                "count": 5
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Extract web results from response
            web_results = data.get('results', {}).get('web', [])
            if not web_results:
                return None
            
            # Build context from top results
            context_parts = []
            citations = []
            
            for i, result in enumerate(web_results[:3], 1):  # Top 3 results
                title = result.get('title', '')
                description = result.get('description', '')
                url_link = result.get('url', '')
                thumbnail = result.get('thumbnail_url') or result.get('favicon_url')
                
                if title and description:
                    context_parts.append(f"Source {i}: {title}\n{description}")
                    # Return rich citation data with thumbnail
                    citations.append({
                        'url': url_link,
                        'title': title,
                        'thumbnail': thumbnail
                    })
            
            context = "\n\n".join(context_parts)
            
            return {
                'context': context,
                'citations': citations
            }
            
        except Exception as e:
            logger.warning(f"You.com Search failed: {e}")
            return None
    
    async def _generate_answer(
        self, 
        question: str, 
        search_context: str, 
        learning_level: Optional[str],
        file_paths: List[str] = None
    ) -> str:
        """Generate answer using Gemini with search context."""
        
        # Adjust prompt based on learning level
        level_instruction = ""
        if learning_level:
            level_map = {
                "beginner": "Explain in simple terms suitable for someone without prior knowledge.",
                "intermediate": "Provide a balanced explanation with some technical details.",
                "advanced": "Give a detailed, technical explanation."
            }
            level_instruction = level_map.get(learning_level.lower(), "")
        
        # Build prompt with search context if available
        if search_context:
            prompt = f"""Answer this question directly and confidently using the search results below.

Question: {question}

Search results:
{search_context}

Instructions:
- Give a direct factual answer in 1-2 sentences
- Do NOT use phrases like: "the search results say", "according to sources", "I'm seeing", "sources indicate", "appears to be"
- State facts confidently as if you know them
- Do not comment on the sources or their reliability
- Just answer the question directly

Answer:"""
        else:
            # Fallback to Gemini's knowledge
            prompt = f"""{level_instruction}

Question: {question}

Provide a clear, accurate answer in 2-3 sentences. If you don't have reliable information, say so honestly."""
        
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
                    logger.info(f"📚 Added file to learning tool prompt: {path}")
                except Exception as e:
                    logger.error(f"Failed to load file for learning tool: {path}, error: {e}")

        response = self.gemini.generate_content(
            prompt_parts,
            generation_config={"temperature": 0.3}
        )
        
        return response.text.strip() if response.text else "I couldn't find information on that topic."


_learning_tool_instance = None


def get_learning_tool():
    """Get or create learning tool singleton."""
    global _learning_tool_instance
    
    # Always recreate to ensure fresh config/API key loading
    # This is important for development when .env changes
    from app.services.gemini import get_gemini_service
    gemini_service = get_gemini_service()
    _learning_tool_instance = LearningTool(gemini_service.model)
    
    return _learning_tool_instance
