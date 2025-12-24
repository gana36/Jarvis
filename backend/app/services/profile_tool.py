"""User Profile Tool for managing user preferences in Firestore"""
import logging
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Optional

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)


class ProfileTool:
    """Service for managing user profiles in Google Firestore"""

    def __init__(self):
        """
        Initialize Profile Tool with Firestore.
        Uses existing Firebase Admin instance from task_tool.
        """
        # Firebase Admin should already be initialized by task_tool
        if not firebase_admin._apps:
            logger.warning("Firebase Admin not initialized, initializing now...")
            import os
            cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            
            if cred_path:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info(f"✓ Firebase Admin initialized with credentials from {cred_path}")
            else:
                firebase_admin.initialize_app()
                logger.info("✓ Firebase Admin initialized with default credentials")
        
        # Get Firestore client
        self.db = firestore.client()
        self.collection = self.db.collection('user_profiles')
        logger.info("✓ Profile Tool initialized with Firestore")

    def get_or_create_profile(self, user_id: str = "default") -> Dict[str, Any]:
        """
        Get user profile or create a default one if it doesn't exist.
        
        Args:
            user_id: User identifier (email or generated ID)
            
        Returns:
            User profile data
        """
        try:
            doc_ref = self.collection.document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                profile = doc.to_dict()
                profile['user_id'] = user_id
                
                # Convert timestamps to ISO strings for JSON serialization
                if profile.get('created_at'):
                    profile['created_at'] = profile['created_at'].isoformat()
                if profile.get('updated_at'):
                    profile['updated_at'] = profile['updated_at'].isoformat()
                
                logger.info(f"✓ Retrieved profile for user: {user_id}")
                return profile
            else:
                # Create default profile
                logger.info(f"Profile not found for {user_id}, creating default profile")
                return self._create_default_profile(user_id)
                
        except Exception as e:
            logger.error(f"Failed to get profile for {user_id}: {e}")
            # Return minimal default profile on error
            return self._minimal_default_profile(user_id)

    def _create_default_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Create a default profile in Firestore.
        
        Args:
            user_id: User identifier
            
        Returns:
            Created profile data
        """
        try:
            now = datetime.now()
            
            default_profile = {
                'name': None,
                'email': None,
                'timezone': 'America/New_York',  # Default US Eastern
                'location': None,
                'dietary_preference': None,
                'learning_level': None,
                'preferred_voice': None,
                'interests': [],
                'created_at': now,
                'updated_at': now,
            }
            
            # Save to Firestore
            self.collection.document(user_id).set(default_profile)
            
            logger.info(f"✓ Created default profile for user: {user_id}")
            
            # Return serialized version
            return {
                'user_id': user_id,
                'name': None,
                'email': None,
                'timezone': 'America/New_York',
                'location': None,
                'dietary_preference': None,
                'learning_level': None,
                'preferred_voice': None,
                'interests': [],
                'created_at': now.isoformat(),
                'updated_at': now.isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to create default profile: {e}")
            return self._minimal_default_profile(user_id)

    def _minimal_default_profile(self, user_id: str) -> Dict[str, Any]:
        """Return minimal in-memory default profile when Firestore fails"""
        now = datetime.now()
        return {
            'user_id': user_id,
            'name': None,
            'email': None,
            'timezone': 'America/New_York',
            'location': None,
            'dietary_preference': None,
            'learning_level': None,
            'preferred_voice': None,
            'interests': [],
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
        }

    def update_profile_fields(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update specific profile fields (incremental updates).
        
        Args:
            user_id: User identifier
            updates: Dictionary of fields to update
            
        Returns:
            Updated profile data
        """
        try:
            doc_ref = self.collection.document(user_id)
            doc = doc_ref.get()
            
            # Ensure profile exists
            if not doc.exists:
                logger.info(f"Profile doesn't exist for {user_id}, creating first")
                self._create_default_profile(user_id)
            
            # Add updated timestamp
            updates['updated_at'] = datetime.now()
            
            # Handle interests append (don't overwrite, merge)
            if 'interests' in updates and isinstance(updates['interests'], list):
                existing_profile = doc.to_dict() if doc.exists else {}
                existing_interests = existing_profile.get('interests', [])
                
                # Merge interests (unique values only)
                new_interests = list(set(existing_interests + updates['interests']))
                updates['interests'] = new_interests
            
            # Update in Firestore
            doc_ref.update(updates)
            
            # Get updated document
            updated_doc = doc_ref.get()
            profile = updated_doc.to_dict()
            profile['user_id'] = user_id
            
            # Convert timestamps
            if profile.get('created_at'):
                profile['created_at'] = profile['created_at'].isoformat()
            if profile.get('updated_at'):
                profile['updated_at'] = profile['updated_at'].isoformat()
            
            logger.info(f"✓ Updated profile for {user_id}: {list(updates.keys())}")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to update profile for {user_id}: {e}")
            # Return current profile without updates
            return self.get_or_create_profile(user_id)

    def clear_profile_field(self, user_id: str, field_name: str) -> bool:
        """
        Clear a specific profile field (set to None or empty list).
        
        Args:
            user_id: User identifier
            field_name: Field to clear
            
        Returns:
            True if successful, False otherwise
        """
        try:
            doc_ref = self.collection.document(user_id)
            
            # Determine appropriate empty value
            empty_value = [] if field_name == 'interests' else None
            
            doc_ref.update({
                field_name: empty_value,
                'updated_at': datetime.now()
            })
            
            logger.info(f"✓ Cleared field '{field_name}' for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear field {field_name} for {user_id}: {e}")
            return False


# Singleton instance with caching
_profile_tool_instance = None


@lru_cache
def get_profile_tool() -> ProfileTool:
    """
    Get cached Profile Tool instance.
    
    Returns:
        Configured ProfileTool instance with Firestore
    """
    global _profile_tool_instance
    
    if _profile_tool_instance is None:
        _profile_tool_instance = ProfileTool()
    
    return _profile_tool_instance
