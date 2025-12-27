"""Application configuration and environment variables"""
import json
import os
from functools import lru_cache
from tempfile import NamedTemporaryFile

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Google Cloud credentials as JSON string
    google_credentials_json: str | None = None
    
    # Google Cloud project ID (supports both GOOGLE_PROJECT_ID and GOOGLE_CLOUD_PROJECT)
    google_project_id: str | None = None
    google_cloud_project: str | None = None  # Alternative name used by some services
    
    # Gemini API key for conversational AI
    gemini_api_key: str | None = None
    gcp_weather_api_key: str | None = None  # Google Cloud Weather API key
    
    # ElevenLabs configuration for Text-to-Speech
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Default: Rachel voice
    
    # Google Calendar configuration
    google_calendar_id: str = "primary"  # Default to primary calendar
    
    # Google OAuth configuration for Calendar
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Fitbit OAuth configuration for health data
    fitbit_client_id: str | None = None
    fitbit_client_secret: str | None = None
    fitbit_redirect_uri: str = "http://localhost:8000/auth/fitbit/callback"

    # Vertex AI for LEARN intent (web search grounding)
    vertex_ai_project_id: str | None = None
    vertex_ai_location: str = "us-central1"
    vertex_ai_credentials_path: str | None = None
    vertex_ai_credentials: str | None = None  # Alternative: JSON string
    
    # You.com Search API for LEARN intent
    youcom_api_key: str | None = None
    
    # NewsAPI.org key for NEWS intent
    news_api_key: str | None = None
    
    # Qdrant Cloud for long-term memory vector storage
    qdrant_url: str | None = None  # e.g., https://xxx.cloud.qdrant.io:6333
    qdrant_api_key: str | None = None
    
    # Yelp AI API for restaurant search
    yelp_api_key: str | None = None
    yelp_api_base_url: str = "https://api.yelp.com"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra env vars without causing errors


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


def setup_google_credentials():
    """
    Set up Google Cloud credentials from environment.
    
    If GOOGLE_CREDENTIALS_JSON is set, write it to a temp file
    and set GOOGLE_APPLICATION_CREDENTIALS to point to it.
    """
    settings = get_settings()
    
    if settings.google_credentials_json:
        # Parse JSON to validate it
        try:
            creds_dict = json.loads(settings.google_credentials_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid GOOGLE_CREDENTIALS_JSON: {e}")
        
        # Write to temporary file
        # Note: This file persists for the lifetime of the process
        temp_file = NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(creds_dict, temp_file)
        temp_file.close()
        
        # Set environment variable for Google Cloud SDK
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file.name
        print(f"Google Cloud credentials loaded from environment")
    elif os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print(f"Using GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    else:
        print("Warning: No Google Cloud credentials configured")
