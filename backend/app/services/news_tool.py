"""
News Tool - Live News Briefing with NewsAPI.org
"""

import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class NewsTool:
    """News retrieval and briefing service."""
    
    def __init__(self, gemini_model=None):
        """Initialize with config and optional Gemini model for summarization."""
        from app.config import get_settings
        settings = get_settings()
        self.news_api_key = settings.news_api_key
        self.gemini = gemini_model
        
        if not self.news_api_key:
            logger.warning("NEWS_API_KEY not set - news retrieval disabled")

    async def get_news_briefing(self, query: str) -> Dict[str, Any]:
        """
        Fetch news articles and format them for a professional briefing.
        
        Args:
            query: The news topic or search query.
            
        Returns:
            Dict containing articles and optional AI summary.
        """
        if not self.news_api_key:
            return {
                "error": "missing_api_key",
                "message": "News service not configured.",
                "articles": []
            }

        try:
            # Use top-headlines for general queries, everything for specific topics
            if query.lower() in ["top headlines", "latest news", "general"]:
                url = "https://newsapi.org/v2/top-headlines"
                params = {
                    "language": "en",
                    "pageSize": 10,
                    "apiKey": self.news_api_key
                }
            else:
                url = "https://newsapi.org/v2/everything"
                params = {
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                    "apiKey": self.news_api_key
                }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            raw_articles = data.get('articles', [])
            articles = []
            
            for item in raw_articles:
                # Basic cleaning/validation
                if item.get("title") and item.get("url") and "[Removed]" not in item.get("title"):
                    articles.append({
                        "title": item.get("title"),
                        "description": item.get("description"),
                        "url": item.get("url"),
                        "thumbnail": item.get("urlToImage"),
                        "source": item.get("source", {}).get("name") or "News Source",
                        "timestamp": item.get("publishedAt")
                    })
            
            # Limit to top 5 valid articles
            articles = articles[:5]
            
            if not articles:
                return {
                    "message": f"I couldn't find any recent news stories regarding '{query}'.",
                    "articles": []
                }

            # Generate a brief conversational summary if Gemini is available
            ai_summary = ""
            if self.gemini and articles:
                ai_summary = await self._summarize_news(query, articles)

            return {
                "message": ai_summary or f"Here are the top news stories for {query}.",
                "data": {
                    "articles": articles,
                    "query": query
                }
            }
            
        except Exception as e:
            logger.error(f"News tool error: {e}")
            return {
                "error": "retrieval_failed",
                "message": "I'm having trouble accessing the latest news right now.",
                "articles": []
            }

    async def _summarize_news(self, query: str, articles: List[Dict[str, Any]]) -> str:
        """Create a professional conversational intro for the news briefing."""
        headlines = "\n".join([f"- {a['title']}" for a in articles])
        
        prompt = f"""You are Jarvis, a professional AI assistant. 
Briefly summarize the state of news regarding '{query}' based on these headlines.
Keep it to 1-2 professional sentences that act as an intro to the list I'm showing.
Do not use emojis. Be direct and sophisticated.

Headlines:
{headlines}

Intro:"""
        
        try:
            response = self.gemini.generate_content(
                prompt,
                generation_config={"temperature": 0.4}
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Failed to generate news summary: {e}")
            return f"I've found {len(articles)} relevant news stories for {query}."

def get_news_tool():
    """Factory function for news tool."""
    from app.services.gemini import get_gemini_service
    gemini_service = get_gemini_service()
    return NewsTool(gemini_service.model)
