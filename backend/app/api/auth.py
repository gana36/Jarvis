"""OAuth authentication endpoints for Google Calendar"""
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from google_auth_oauthlib.flow import Flow
from pydantic import BaseModel

from app.config import get_settings
from app.middleware import get_current_user
from app.services.calendar_tool import get_calendar_tool

logger = logging.getLogger(__name__)
router = APIRouter()

# Token storage path
TOKEN_FILE = Path("calendar_token.json")

# Calendar scopes - includes write access and basic profile info
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'openid',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email'
]


class AuthStatus(BaseModel):
    """Authorization status response"""
    authorized: bool
    calendar_connected: bool


@router.get("/google/calendar")
async def google_calendar_auth(user_id: str = Depends(get_current_user)):
    """
    Initiate Google OAuth flow for Calendar access.
    
    Redirects user to Google OAuth consent screen.
    """
    settings = get_settings()
    
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(
            status_code=500,
            detail="OAuth not configured. Add GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET to .env"
        )
    
    # Create OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_oauth_redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.google_oauth_redirect_uri
    )
    
    # Generate authorization URL
    # We pass user_id in the state parameter to associate the token with the correct user on callback
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=user_id
    )
    
    logger.info(f"Redirecting user {user_id} to Google OAuth: {authorization_url}")
    return RedirectResponse(url=authorization_url)


@router.get("/google/callback")
async def google_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    """
    Handle OAuth callback from Google.
    
    Args:
        code: Authorization code from Google
        state: The user_id we passed in
        error: Error message if authorization failed
    """
    if error:
        logger.error(f"OAuth authorization failed: {error}")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Authorization Failed</title></head>
                <body>
                    <h1>❌ Authorization Failed</h1>
                    <p>Error: {error}</p>
                    <p><a href="/">Return to app</a></p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")
    
    if not state:
        logger.error("No state (user_id) provided in callback")
        raise HTTPException(status_code=400, detail="No user identification provided")
    
    user_id = state
    settings = get_settings()
    
    # Create OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_oauth_redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.google_oauth_redirect_uri
    )
    
    try:
        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Save tokens using CalendarTool which handles Firestore
        calendar_tool = get_calendar_tool(user_id=user_id)
        calendar_tool._save_credentials(credentials)
        
        logger.info(f"✓ OAuth tokens saved successfully for user {user_id}")
        
        return HTMLResponse(
            content="""
            <html>
                <head>
                    <title>Authorization Successful</title>
                    <style>
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        }
                        .container {
                            background: white;
                            padding: 3rem;
                            border-radius: 12px;
                            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                            text-align: center;
                            max-width: 500px;
                        }
                        h1 { color: #2d3748; margin-bottom: 1rem; }
                        p { color: #718096; line-height: 1.6; }
                        .success-icon { font-size: 4rem; margin-bottom: 1rem; }
                        .close-btn {
                            margin-top: 2rem;
                            padding: 0.75rem 2rem;
                            background: #667eea;
                            color: white;
                            border: none;
                            border-radius: 6px;
                            font-size: 1rem;
                            cursor: pointer;
                        }
                        .close-btn:hover { background: #5a67d8; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="success-icon">✓</div>
                        <h1>Calendar Connected!</h1>
                        <p>Your Google Calendar has been successfully connected to Jarvis.</p>
                        <p>You can now ask for your daily summary and hear your real calendar events!</p>
                        <button class="close-btn" onclick="window.close()">Close Window</button>
                    </div>
                    <script>
                        // Auto-close after 3 seconds
                        setTimeout(() => window.close(), 3000);
                    </script>
                </body>
            </html>
            """
        )
        
    except Exception as e:
        logger.error(f"Failed to exchange authorization code: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete authorization: {str(e)}"
        )


@router.get("/calendar/status", response_model=AuthStatus)
async def calendar_status(user_id: str = Depends(get_current_user)):
    """
    Check if calendar is authorized for authenticated user.
    
    Returns authorization status and whether token exists.
    """
    try:
        calendar_tool = get_calendar_tool(user_id=user_id)
        is_connected = calendar_tool.credentials is not None and calendar_tool.credentials.valid
        
        return AuthStatus(
            authorized=is_connected,
            calendar_connected=is_connected
        )
    except Exception as e:
        logger.error(f"Failed to check calendar status for {user_id}: {e}")
        return AuthStatus(authorized=False, calendar_connected=False)
