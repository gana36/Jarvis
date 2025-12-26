"""
Simple Weather Tool - Auto Location + LLM Correction

Flow:
1. No location specified → Use Tallahassee, FL (user's location)
2. Location specified → Use Gemini to correct spelling → Geocode → Weather
"""

import logging
import os
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class WeatherTool:
    """Simple weather tool with auto-location and LLM spell correction."""
    
    def __init__(self, gemini_model=None):
        """Initialize with GCP API key and optional Gemini model."""
        from app.config import get_settings
        settings = get_settings()
        self.api_key = settings.gcp_weather_api_key
        
        if not self.api_key:
            logger.error("GCP_WEATHER_API_KEY not found in .env file!")
            raise ValueError("GCP_WEATHER_API_KEY must be set in .env file")
        self.weather_url = "https://weather.googleapis.com/v1/currentConditions:lookup"
        self.geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        self.gemini = gemini_model
        self.cache = {}
        self.cache_ttl = 900  # 15 minutes
    
    async def correct_city_name(self, city_input: str) -> str:
        """Use Gemini to correct misspellings in city names."""
        if not self.gemini:
            return city_input
        
        try:
            prompt = f"""Correct this city name spelling. Return ONLY the corrected city name, nothing else.

Input: "{city_input}"

Examples:
- "sanfransico" → "San Francisco"
- "tokio" → "Tokyo"  
- "new yourk" → "New York"

Corrected:"""

            response = self.gemini.generate_content(
                prompt,
                generation_config={"temperature": 0.0, "max_output_tokens": 20}
            )
            
            corrected = response.text.strip().strip('"\'')
            logger.info(f"📝 Corrected '{city_input}' → '{corrected}'")
            return corrected
            
        except Exception as e:
            logger.warning(f"City correction failed: {e}, using original")
            return city_input
    
    async def geocode_city(self, city: str) -> Optional[Tuple[float, float, str]]:
        """Convert city name to coordinates. Returns (lat, lng, formatted_name)."""
        try:
            params = {'address': city, 'key': self.api_key}
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.geocode_url, params=params)
                data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                formatted_name = data['results'][0]['formatted_address']
                return (location['lat'], location['lng'], formatted_name)
            
            logger.warning(f"Geocoding failed for '{city}': {data.get('status')}")
            return None
            
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None
            
    async def _get_auto_location(self) -> Optional[Tuple[float, float, str]]:
        """Attempt to get location via IP-based geolocation."""
        try:
            logger.info("Attempting auto-location detection via IP...")
            async with httpx.AsyncClient(timeout=3.0) as client:
                # Use ip-api.com (free, no key needed for low volume)
                response = await client.get("http://ip-api.com/json")
                data = response.json()
                if data.get('status') == 'success':
                    lat, lon = data.get('lat'), data.get('lon')
                    city, region = data.get('city'), data.get('regionName')
                    location_name = f"{city}, {region}"
                    logger.info(f"✓ Auto-detected location: {location_name} ({lat}, {lon})")
                    return (lat, lon, location_name)
        except Exception as e:
            logger.warning(f"IP-based location detection failed: {e}")
        return None
    
    async def get_weather(
        self,
        city: Optional[str] = None,
        profile_location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get weather. Priority: city → profile_location → coords → default location.
        
        Args:
            city: Explicit city name from transcript
            profile_location: User's profile location
            latitude: Manual coordinates
            longitude: Manual coordinates
        """
        location_name = None
        
        # Priority 1: Explicit city name (with spelling correction)
        if city:
            # Correct spelling with LLM
            corrected_city = await self.correct_city_name(city)
            
            # Geocode to get coordinates
            geocode_result = await self.geocode_city(corrected_city)
            if geocode_result:
                latitude, longitude, location_name = geocode_result
            else:
                return {
                    "error": "location_not_found",
                    "message": f"Couldn't find location: {city}"
                }
        
        # Priority 2: Profile location
        elif profile_location:
            # Geocode the profile location
            geocode_result = await self.geocode_city(profile_location)
            if geocode_result:
                latitude, longitude, location_name = geocode_result
            else:
                logger.warning(f"Failed to geocode profile location: {profile_location}. Falling back to default.")
        
        # Priority 3: Use provided coordinates
        if (latitude is None or longitude is None) and not location_name:
            # Priority 4: Dynamic Auto-location (IP-based)
            auto_loc = await self._get_auto_location()
            if auto_loc:
                latitude, longitude, location_name = auto_loc
            else:
                # Absolute fallback if everything fails (approximate center of US or just return error)
                logger.warning("All location detection failed. Using last-resort fallback.")
                latitude, longitude = 37.0902, -95.7129
                location_name = "United States"
        
        # Check cache
        cache_key = f"{latitude:.2f},{longitude:.2f}"
        if cache_key in self.cache:
            age = (datetime.now() - self.cache[cache_key]['timestamp']).total_seconds()
            if age < self.cache_ttl:
                logger.info(f"💾 Cache HIT for {cache_key}")
                return self.cache[cache_key]['data']
        
        # Fetch weather from GCP
        try:
            params = {
                'key': self.api_key,
                'location.latitude': latitude,
                'location.longitude': longitude,
                'unitsSystem': 'IMPERIAL'  # Request Fahrenheit directly
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.weather_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Parse GCP Weather API response
            temp_f = data.get('temperature', {}).get('degrees', 70)
            temp_c = round((temp_f - 32) * 5/9)
            condition = data.get('weatherCondition', {}).get('description', {}).get('text', 'Clear')
            humidity = data.get('relativeHumidity', 50)
            wind_mph = data.get('wind', {}).get('speed', {}).get('value', 0)
            wind_kmh = round(wind_mph * 1.60934)  # mph to km/h
            
            weather_data = {
                'location': location_name or f"{latitude:.2f}, {longitude:.2f}",
                'latitude': latitude,
                'longitude': longitude,
                'temperature_c': temp_c,
                'temperature_f': round(temp_f),
                'condition': condition,
                'humidity': humidity,
                'wind_speed_kmh': wind_kmh
            }
            
            # Cache it
            self.cache[cache_key] = {
                'data': weather_data,
                'timestamp': datetime.now()
            }
            
            logger.info(f"✅ Weather: {weather_data['location']} - {temp_c}°C")
            return weather_data
            
        except Exception as e:
            logger.error(f"Weather fetch failed: {e}")
            return {
                "error": "fetch_error",
                "message": f"Couldn't get weather: {str(e)}"
            }


_weather_tool_instance = None

def get_weather_tool():
    """Get or create weather tool singleton."""
    global _weather_tool_instance
    
    if _weather_tool_instance is None:
        from app.services.gemini import get_gemini_service
        gemini_service = get_gemini_service()
        _weather_tool_instance = WeatherTool(gemini_service.model)
    
    return _weather_tool_instance
