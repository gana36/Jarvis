"""Long-term memory service using Mem0 for persistent fact storage"""
import logging
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from mem0 import Memory

from app.config import get_settings

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Long-term memory service for storing and retrieving user facts/preferences.
    Uses Mem0 for intelligent memory management with vector search.
    """

    def __init__(self):
        """Initialize the memory service with Mem0"""
        settings = get_settings()
        
        # Configure vector store - use Qdrant Cloud if configured, else local
        if settings.qdrant_url and settings.qdrant_api_key:
            # Qdrant Cloud configuration (production)
            vector_store_config = {
                "provider": "qdrant",
                "config": {
                    "collection_name": "jarvis_memories",
                    "embedding_model_dims": 768,
                    "url": settings.qdrant_url,
                    "api_key": settings.qdrant_api_key,
                }
            }
            logger.info("Using Qdrant Cloud for memory storage")
        else:
            # Local Qdrant configuration (development)
            vector_store_config = {
                "provider": "qdrant",
                "config": {
                    "collection_name": "jarvis_memories",
                    "embedding_model_dims": 768,
                    "path": "./qdrant_data",
                }
            }
            logger.info("Using local Qdrant for memory storage")
        
        # Configure LLM and embedder - prefer OpenAI if available (more stable with Mem0)
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if openai_key:
            # OpenAI configuration (most stable)
            llm_config = {
                "provider": "openai",
                "config": {
                    "model": "gpt-4o-mini",
                }
            }
            embedder_config = {
                "provider": "openai",
                "config": {
                    "model": "text-embedding-3-small",
                }
            }
            logger.info("Using OpenAI for Mem0 LLM/embedder")
        else:
            # Gemini configuration (fallback)
            llm_config = {
                "provider": "gemini",
                "config": {
                    "api_key": settings.gemini_api_key,
                    "model": "gemini-2.0-flash",
                }
            }
            embedder_config = {
                "provider": "gemini", 
                "config": {
                    "api_key": settings.gemini_api_key,
                    "model": "models/text-embedding-004",
                }
            }
            logger.info("Using Gemini for Mem0 LLM/embedder")
        
        # Build full config
        config = {
            "llm": llm_config,
            "embedder": embedder_config,
            "vector_store": vector_store_config,
            "version": "v1.1"
        }
        
        try:
            self.memory = Memory.from_config(config)
            logger.info("✓ Memory service initialized with Mem0")
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            self.memory = None

    def add_memory(self, user_id: str, text: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Store a new memory for a user.
        
        Args:
            user_id: User identifier
            text: The fact/preference to remember
            metadata: Optional metadata (source, category, etc.)
            
        Returns:
            Result with memory ID and status
        """
        if not self.memory:
            return {"success": False, "error": "Memory service not initialized"}
        
        try:
            result = self.memory.add(
                text,
                user_id=user_id,
                metadata=metadata or {"source": "explicit"}
            )
            logger.info(f"✓ Added memory for user {user_id}: {text[:50]}...")
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return {"success": False, "error": str(e)}

    def search_memories(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant memories using semantic search.
        
        Args:
            user_id: User identifier
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of relevant memories
        """
        if not self.memory:
            return []
        
        try:
            results = self.memory.search(
                query,
                user_id=user_id,
                limit=limit
            )
            # Mem0 may return {'results': [...]} or just a list
            if isinstance(results, dict) and 'results' in results:
                results = results['results']
            logger.info(f"Found {len(results)} memories for query: {query[:30]}...")
            return results
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    def get_all_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of all memories
        """
        if not self.memory:
            return []
        
        try:
            results = self.memory.get_all(user_id=user_id)
            # Mem0 may return {'results': [...]} or just a list
            if isinstance(results, dict) and 'results' in results:
                results = results['results']
            logger.info(f"Retrieved {len(results)} total memories for user {user_id}")
            return results
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory by ID.
        
        Args:
            memory_id: The memory ID to delete
            
        Returns:
            True if deleted successfully
        """
        if not self.memory:
            return False
        
        try:
            self.memory.delete(memory_id=memory_id)
            logger.info(f"✓ Deleted memory {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False

    def delete_all_memories(self, user_id: str) -> bool:
        """
        Delete all memories for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if deleted successfully
        """
        if not self.memory:
            return False
        
        try:
            self.memory.delete_all(user_id=user_id)
            logger.info(f"✓ Deleted all memories for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete all memories: {e}")
            return False

    def get_relevant_context(self, user_id: str, query: str, limit: int = 3) -> str:
        """
        Get relevant memories as context string for AI responses.
        
        Args:
            user_id: User identifier
            query: The current conversation/query
            limit: Max memories to include
            
        Returns:
            Formatted context string
        """
        memories = self.search_memories(user_id, query, limit=limit)
        
        if not memories:
            return ""
        
        context_parts = ["Relevant things I remember about you:"]
        for mem in memories:
            memory_text = mem.get("memory", mem.get("text", ""))
            if memory_text:
                context_parts.append(f"- {memory_text}")
        
        return "\n".join(context_parts)


# Singleton instance
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """Get or create the memory service singleton"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
