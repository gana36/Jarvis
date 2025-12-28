"""Authentication middleware for Firebase token verification"""
import logging
from fastapi import Request, HTTPException, status
import firebase_admin
from firebase_admin import auth, credentials
import os

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Middleware for Firebase Authentication"""
    
    @staticmethod
    async def verify_token(auth_header: str) -> dict:
        """
        Verify Firebase ID token from Authorization header.
        
        Args:
            auth_header: Authorization header value (Bearer <token>)
            
        Returns:
            Decoded token with user info
            
        Raises:
            HTTPException: If token is invalid or missing
        """
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = auth_header.split('Bearer ')[1]
        
        try:
            # Initialize Firebase Admin if not already done
            if not firebase_admin._apps:
                cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                
                if cred_path:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                else:
                    # Try to use GOOGLE_CREDENTIALS_JSON from environment
                    from app.config import get_settings
                    import json
                    import tempfile
                    
                    settings = get_settings()
                    if settings.google_credentials_json:
                        # Parse JSON and write to temp file for Firebase
                        creds_dict = json.loads(settings.google_credentials_json)
                        
                        # Set project ID env var (Firebase needs this for token verification)
                        if 'project_id' in creds_dict and not os.getenv('GOOGLE_CLOUD_PROJECT'):
                            os.environ['GOOGLE_CLOUD_PROJECT'] = creds_dict['project_id']
                            logger.info(f"Set GOOGLE_CLOUD_PROJECT to {creds_dict['project_id']}")
                        
                        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
                        json.dump(creds_dict, temp_file)
                        temp_file.close()
                        
                        cred = credentials.Certificate(temp_file.name)
                        firebase_admin.initialize_app(cred)
                        logger.info("Firebase initialized with GOOGLE_CREDENTIALS_JSON")
                    else:
                        firebase_admin.initialize_app()
            
            # Verify the token
            decoded_token = auth.verify_id_token(token)
            return decoded_token
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Token verification failed: {error_msg}")
            
            # Extract cleaner message if it's a known Firebase error
            detail = f"Invalid authentication token: {error_msg}"
            if "Token is expired" in error_msg:
                detail = "Your session has expired. Please log out and log back in."
            elif "Firebase ID token has incorrect \"aud\" (audience) claim" in error_msg:
                detail = "Token project mismatch. The frontend and backend are using different Firebase projects."
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=detail
            )


async def get_current_user(request: Request) -> str:
    """
    FastAPI dependency to get current authenticated user ID.
    Supports both Authorization header and 'token' query parameter.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User ID from verified token
        
    Raises:
        HTTPException: If authentication fails
    """
    auth_header = request.headers.get("Authorization")
    
    # Check query params if header is missing (useful for redirects)
    if not auth_header:
        token_param = request.query_params.get("token")
        if token_param:
            auth_header = f"Bearer {token_param}"
    
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header or token query parameter required"
        )
    
    user_info = await AuthMiddleware.verify_token(auth_header)
    user_id = user_info.get("uid")
    
    # Preload user memories ONCE on first auth (not every request)
    if user_id not in _preloaded_users:
        try:
            from app.services.memory_service import preload_user_memories
            memory_count = preload_user_memories(user_id)
            _preloaded_users.add(user_id)
            if memory_count > 0:
                print(f"🚀 PRELOADED {memory_count} memories for user {user_id[:8]}... on login")
        except Exception as e:
            logger.warning(f"Failed to preload memories: {e}")
    
    return user_id


# Track users who have already been preloaded this session
_preloaded_users: set = set()
