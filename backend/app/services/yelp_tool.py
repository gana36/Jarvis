"""Yelp AI Tool for restaurant and business search"""
import httpx
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Business:
    """Business entity from Yelp API response"""
    id: str
    name: str
    rating: Optional[float] = None
    review_count: int = 0
    price: Optional[str] = None
    distance: Optional[str] = None
    image_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    location: Optional[Dict[str, Any]] = None
    coordinates: Optional[Dict[str, float]] = None
    phone: Optional[str] = None
    url: Optional[str] = None
    menu_url: Optional[str] = None
    categories: Optional[List[Dict[str, str]]] = None


@dataclass 
class ChatResponse:
    """Response from Yelp AI Chat API"""
    response_text: str
    chat_id: Optional[str] = None
    businesses: List[Business] = field(default_factory=list)
    types: Optional[List[str]] = None
    raw_response: Optional[Dict[str, Any]] = None


class YelpTool:
    """Service for interacting with Yelp AI Chat API"""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.yelp_api_key
        self.base_url = settings.yelp_api_base_url
        self.endpoint = f"{self.base_url}/ai/chat/v2"
        
        if not self.api_key:
            logger.warning("YELP_API_KEY not configured - Yelp features disabled")

    @property
    def is_available(self) -> bool:
        """Check if Yelp API is configured"""
        return bool(self.api_key)

    async def chat(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        locale: str = "en_US",
        chat_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Send a chat query to Yelp AI API

        Args:
            query: Natural language query (e.g., "best Italian restaurant nearby")
            latitude: User's latitude coordinate
            longitude: User's longitude coordinate
            locale: User's locale (default: en_US)
            chat_id: Optional conversation ID for multi-turn conversations

        Returns:
            ChatResponse with AI response and extracted businesses
        """
        if not self.api_key:
            raise Exception("Yelp API not configured")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload: Dict[str, Any] = {
            "query": query
        }

        # Add user context if location is provided
        if latitude is not None and longitude is not None:
            payload["user_context"] = {
                "locale": locale,
                "latitude": latitude,
                "longitude": longitude
            }
        elif locale:
            payload["user_context"] = {
                "locale": locale
            }

        # Add chat_id for conversation continuity
        if chat_id:
            payload["chat_id"] = chat_id

        logger.info(f"🍽️ Yelp API request: {query}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.endpoint,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Yelp API response status: {response.status_code}")

                # Extract response text
                response_text = data.get("response", {}).get("text", "")

                # Extract chat_id for conversation continuity
                chat_id = data.get("chat_id")

                # Extract businesses from entities
                businesses = self._extract_businesses(data)

                # Extract response types
                types = data.get("types", [])

                return ChatResponse(
                    response_text=response_text,
                    chat_id=chat_id,
                    businesses=businesses,
                    types=types,
                    raw_response=data
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Yelp API: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Yelp API error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            raise Exception(f"Failed to connect to Yelp API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

    def _extract_businesses(self, data: Dict[str, Any]) -> List[Business]:
        """Extract business entities from Yelp AI API response"""
        businesses = []
        entities = data.get("entities", [])

        # Handle list format (new Yelp API response structure)
        if isinstance(entities, list):
            for entity in entities:
                if isinstance(entity, dict) and "businesses" in entity:
                    for business_data in entity.get("businesses", []):
                        businesses.extend(self._parse_business(business_data))
                elif isinstance(entity, dict) and "name" in entity:
                    businesses.extend(self._parse_business(entity))
            return businesses

        # Handle dict format (legacy)
        if isinstance(entities, dict):
            for entity_id, entity_data in entities.items():
                if isinstance(entity_data, dict) and "name" in entity_data:
                    businesses.extend(self._parse_business(entity_data))
            return businesses

        return businesses

    def _parse_business(self, entity_data: Dict[str, Any]) -> List[Business]:
        """Parse a single business entity into a Business object"""
        try:
            if "name" not in entity_data:
                return []

            # Extract categories and create tags
            tags = []
            if "categories" in entity_data and entity_data["categories"]:
                tags = [cat.get("title", "") for cat in entity_data["categories"] if cat.get("title")]

            # Get image URL
            image_url = entity_data.get("image_url")
            if not image_url and "contextual_info" in entity_data:
                contextual_info = entity_data["contextual_info"]
                if isinstance(contextual_info, dict) and "photos" in contextual_info:
                    photos = contextual_info["photos"]
                    if isinstance(photos, list) and len(photos) > 0:
                        if isinstance(photos[0], dict):
                            image_url = photos[0].get("original_url")
                        else:
                            image_url = photos[0]

            # Extract coordinates
            coordinates = None
            coords_data = entity_data.get("coordinates")
            if coords_data and isinstance(coords_data, dict):
                if "latitude" in coords_data and "longitude" in coords_data:
                    coordinates = {
                        "latitude": coords_data["latitude"],
                        "longitude": coords_data["longitude"]
                    }

            # Calculate distance if available
            distance = None
            if "distance" in entity_data:
                dist_meters = entity_data["distance"]
                if dist_meters:
                    distance = f"{(dist_meters * 0.000621371):.1f} mi"

            # Extract menu URL
            menu_url = None
            attributes = entity_data.get("attributes", {})
            if isinstance(attributes, dict):
                menu_url = attributes.get("MenuUrl")
            if not menu_url:
                menu_url = entity_data.get("menu_url")

            business = Business(
                id=entity_data.get("id", entity_data.get("alias", str(hash(entity_data.get("name"))))),
                name=entity_data.get("name", ""),
                rating=entity_data.get("rating"),
                review_count=entity_data.get("review_count", 0),
                price=entity_data.get("price"),
                distance=distance,
                image_url=image_url,
                tags=tags,
                location=entity_data.get("location"),
                coordinates=coordinates,
                phone=entity_data.get("phone"),
                url=entity_data.get("url"),
                menu_url=menu_url,
                categories=entity_data.get("categories")
            )
            return [business]

        except Exception as e:
            logger.warning(f"Failed to parse business entity: {str(e)}")
            return []

    async def search_restaurants(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        locale: str = "en_US"
    ) -> ChatResponse:
        """
        Search for restaurants using natural language

        Args:
            query: Search query (e.g., "best pizza near me")
            latitude: User's latitude
            longitude: User's longitude
            locale: User's locale

        Returns:
            ChatResponse with restaurants and AI-generated summary
        """
        return await self.chat(
            query=query,
            latitude=latitude,
            longitude=longitude,
            locale=locale
        )


@lru_cache
def get_yelp_tool() -> YelpTool:
    """Get cached Yelp Tool instance"""
    return YelpTool()
