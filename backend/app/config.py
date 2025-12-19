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
    
    # Google Cloud project ID
    google_project_id: str | None = None
    
    # Gemini API key for conversational AI
    gemini_api_key: str | None = None
    
    # ElevenLabs configuration for Text-to-Speech
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Default: Rachel voice

    class Config:
        env_file = ".env"
        case_sensitive = False


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
        print(f"✓ Google Cloud credentials loaded from environment")
    elif os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print(f"✓ Using GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    else:
        print("⚠ Warning: No Google Cloud credentials configured")
