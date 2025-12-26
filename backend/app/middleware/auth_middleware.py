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
                    firebase_admin.initialize_app()
            
            # Verify the token
            decoded_token = auth.verify_id_token(token)
            return decoded_token
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(e)}"
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
    return user_info.get("uid")
