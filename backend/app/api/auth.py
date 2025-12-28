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
                    <title>Link Established | Manas</title>
                    <style>
                        :root {
                            --primary: #22d3ee;
                            --background: #02040a;
                            --glass: rgba(255, 255, 255, 0.03);
                            --border: rgba(255, 255, 255, 0.1);
                        }
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background-color: var(--background);
                            color: white;
                            overflow: hidden;
                        }
                        .ambient-glow {
                            position: absolute;
                            width: 600px;
                            height: 600px;
                            background: radial-gradient(circle, rgba(34, 211, 238, 0.1) 0%, transparent 70%);
                            filter: blur(80px);
                            border-radius: 50%;
                            z-index: 1;
                            animation: pulse 8s infinite ease-in-out;
                        }
                        @keyframes pulse {
                            0%, 100% { transform: scale(1); opacity: 0.3; }
                            50% { transform: scale(1.2); opacity: 0.6; }
                        }
                        .container {
                            position: relative;
                            z-index: 10;
                            background: var(--glass);
                            backdrop-filter: blur(20px);
                            padding: 3.5rem;
                            border-radius: 2.5rem;
                            border: 1px solid var(--border);
                            text-align: center;
                            max-width: 440px;
                            width: 100%;
                            box-shadow: 0 0 100px rgba(34, 211, 238, 0.05);
                            animation: slideUp 0.8s cubic-bezier(0.2, 0.8, 0.2, 1);
                        }
                        @keyframes slideUp {
                            from { opacity: 0; transform: translateY(20px) scale(0.95); }
                            to { opacity: 1; transform: translateY(0) scale(1); }
                        }
                        .branding {
                            font-size: 1.5rem;
                            font-weight: 200;
                            letter-spacing: 0.5em;
                            text-transform: uppercase;
                            margin-bottom: 2rem;
                            color: white;
                            opacity: 0.9;
                        }
                        .branding span {
                            display: block;
                            font-size: 0.6rem;
                            font-weight: 700;
                            letter-spacing: 0.8em;
                            color: var(--primary);
                            margin-top: 0.5rem;
                            opacity: 0.6;
                        }
                        .icon-wrap {
                            position: relative;
                            width: 80px;
                            height: 80px;
                            margin: 0 auto 2rem;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            background: rgba(34, 211, 238, 0.1);
                            border-radius: 1.5rem;
                            border: 1px solid rgba(34, 211, 238, 0.2);
                        }
                        .icon-wrap svg { color: var(--primary); }
                        h1 { 
                            font-size: 1.25rem; 
                            font-weight: 500; 
                            margin-bottom: 0.75rem; 
                            letter-spacing: -0.02em;
                        }
                        p { 
                            color: rgba(255, 255, 255, 0.5); 
                            font-size: 0.875rem;
                            line-height: 1.6; 
                            margin-bottom: 2rem;
                        }
                        .close-btn {
                            padding: 0.875rem 2.5rem;
                            background: var(--primary);
                            color: #02040a;
                            border: none;
                            border-radius: 1rem;
                            font-size: 0.75rem;
                            font-weight: 700;
                            letter-spacing: 0.1em;
                            text-transform: uppercase;
                            cursor: pointer;
                            transition: all 0.2s;
                            box-shadow: 0 10px 20px rgba(34, 211, 238, 0.2);
                        }
                        .close-btn:hover { transform: scale(1.02); filter: brightness(1.1); }
                        .footer {
                            margin-top: 2.5rem;
                            font-size: 0.6rem;
                            font-weight: 700;
                            letter-spacing: 0.3em;
                            color: rgba(255, 255, 255, 0.15);
                            text-transform: uppercase;
                        }
                    </style>
                </head>
                <body>
                    <div class="ambient-glow"></div>
                    <div class="container">
                        <div class="branding">
                            MANAS
                            <span>Neural Link</span>
                        </div>
                        <div class="icon-wrap">
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"></rect><line x1="16" x2="16" y1="2" y2="6"></line><line x1="8" x2="8" y1="2" y2="6"></line><line x1="3" x2="21" y1="10" y2="10"></line></svg>
                        </div>
                        <h1>Calendar Connected</h1>
                        <p>Your temporal data stream has been successfully integrated. Manas is now synched with your schedule.</p>
                        <button class="close-btn" onclick="window.close()">Secure and Close</button>
                        <div class="footer">Link Established v2.5.0</div>
                    </div>
                    <script>
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
