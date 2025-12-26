"""Profile API endpoints for user profile management"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.profile_tool import get_profile_tool
from app.middleware import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


class ProfileResponse(BaseModel):
    """User profile response model"""
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    timezone: str
    location: Optional[str] = None
    dietary_preference: Optional[str] = None
    learning_level: Optional[str] = None
    preferred_voice: Optional[str] = None
    interests: list[str] = []
    created_at: str
    updated_at: str


class ProfileUpdate(BaseModel):
    """Profile update request model"""
    name: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    dietary_preference: Optional[str] = None
    learning_level: Optional[str] = None
    preferred_voice: Optional[str] = None
    interests: Optional[list[str]] = None
    timezone: Optional[str] = None


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(user_id: str = Depends(get_current_user)):
    """
    Get user profile by ID.
    
    Args:
        user_id: Authenticated user identifier
        
    Returns:
        User profile data
    """
    try:
        profile_tool = get_profile_tool()
        profile = profile_tool.get_or_create_profile(user_id)
        
        return ProfileResponse(**profile)
        
    except Exception as e:
        logger.error(f"Failed to get profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve profile: {str(e)}"
        )


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    updates: ProfileUpdate,
    user_id: str = Depends(get_current_user)
):
    """
    Update user profile fields.
    
    Args:
        updates: Profile fields to update
        user_id: Authenticated user identifier
        
    Returns:
        Updated profile data
    """
    try:
        profile_tool = get_profile_tool()
        
        # Convert to dict and remove None values
        update_dict = updates.model_dump(exclude_none=True)
        
        if not update_dict:
            raise HTTPException(
                status_code=400,
                detail="No fields provided to update"
            )
        
        # Update profile
        updated_profile = profile_tool.update_profile_fields(user_id, update_dict)
        
        return ProfileResponse(**updated_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update profile: {str(e)}"
        )



class ProfileExtractRequest(BaseModel):
    """Request model for profile extraction"""
    transcript: str


@router.post("/profile/extract")
async def extract_profile(
    request: ProfileExtractRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Extract profile information from user transcript.
    
    Args:
        request: Request containing transcript
        user_id: Authenticated user identifier
        
    Returns:
        Extracted profile data or confirmation of update
    """
    logger.info(f"Extracting profile for user {user_id} from transcript: {request.transcript[:50]}...")
    
    try:
        from app.services.orchestrator import get_orchestrator
        orchestrator = get_orchestrator()
        
        # We can reuse the internal orchestrator method
        # It's an internal method but we need its logic here for a manual trigger
        await orchestrator._extract_and_update_profile(request.transcript, user_id)
        
        # Return updated profile to confirm
        profile_tool = get_profile_tool()
        updated_profile = profile_tool.get_or_create_profile(user_id)
        
        return {
            "success": True,
            "message": "Manual profile extraction triggered",
            "profile": ProfileResponse(**updated_profile)
        }
            
    except Exception as e:
        logger.error(f"Profile extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Profile extraction failed: {str(e)}"
        )


@router.delete("/profile/field/{field_name}")
async def clear_profile_field(
    field_name: str,
    user_id: str = Depends(get_current_user)
):
    """
    Clear a specific profile field.
    
    Args:
        field_name: Name of field to clear
        user_id: Authenticated user identifier
        
    Returns:
        Success message
    """
    # Validate field name
    allowed_fields = [
        'name', 'email', 'location', 'dietary_preference',
        'learning_level', 'preferred_voice', 'interests'
    ]
    
    if field_name not in allowed_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot clear field '{field_name}'. Allowed fields: {allowed_fields}"
        )
    
    try:
        profile_tool = get_profile_tool()
        success = profile_tool.clear_profile_field(user_id, field_name)
        
        if success:
            return {
                "success": True,
                "message": f"Field '{field_name}' cleared successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to clear field '{field_name}'"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear field: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear field: {str(e)}"
        )


@router.get("/profile/voices")
async def get_available_voices():
    """
    Get list of available ElevenLabs voices.
    
    Returns:
        List of voice options with IDs and names
    """
    # Common ElevenLabs voices (these are actual voice IDs from ElevenLabs)
    voices = [
        {
            "id": "21m00Tcm4TlvDq8ikWAM",
            "name": "Rachel",
            "description": "Calm, professional female voice"
        },
        {
            "id": "AZnzlk1XvdvUeBnXmlld",
            "name": "Domi",
            "description": "Energetic, youthful female voice"
        },
        {
            "id": "EXAVITQu4vr4xnSDxMaL",
            "name": "Bella",
            "description": "Soft, warm female voice"
        },
        {
            "id": "ErXwobaYiN019PkySvjV",
            "name": "Antoni",
            "description": "Friendly, professional male voice"
        },
        {
            "id": "VR6AewLTigWG4xSOukaG",
            "name": "Arnold",
            "description": "Deep, authoritative male voice"
        },
        {
            "id": "pNInz6obpgDQGcFmaJgB",
            "name": "Adam",
            "description": "Clear, articulate male voice"
        },
    ]
    
    return {
        "voices": voices,
        "default": "21m00Tcm4TlvDq8ikWAM"  # Rachel
    }
