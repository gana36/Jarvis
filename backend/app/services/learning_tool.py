"""
Learning Tool - Educational Questions with Brave Search

Uses Gemini + Brave Search API to answer educational questions
with accurate, web-sourced citations.
"""

import logging
import os
import httpx
from typing import Dict, Any, Optional
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
        learning_level: Optional[str] = None
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
            # Search the web if You.com API key available
            search_results = ""
            citations = []
            
            if self.youcom_api_key:
                search_data = await self._search_web(question)
                if search_data:
                    search_results = search_data['context']
                    citations = search_data['citations']
            
            # Generate answer using Gemini with search context
            answer = await self._generate_answer(question, search_results, learning_level)
            
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
                
                if title and description:
                    context_parts.append(f"Source {i}: {title}\n{description}")
                    # Extract domain for citation
                    domain = url_link.split('//')[1].split('/')[0] if '//' in url_link else url_link
                    citations.append(domain)
            
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
        learning_level: Optional[str]
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
        
        response = self.gemini.generate_content(
            prompt,
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
