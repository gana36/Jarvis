"""OAuth authentication endpoints for Gmail access"""
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from google_auth_oauthlib.flow import Flow
from pydantic import BaseModel

from app.config import get_settings
from app.middleware import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Gmail OAuth scopes - read-only access to messages and labels
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email'
]


class GmailAuthStatus(BaseModel):
    """Gmail authorization status response"""
    authorized: bool
    gmail_connected: bool


@router.get("/google/gmail")
async def google_gmail_auth(user_id: str = "default"):
    """
    Initiate Google OAuth flow for Gmail access.
    
    Redirects user to Google OAuth consent screen.
    Can pass user_id as query param: /auth/google/gmail?user_id=abc123
    """
    settings = get_settings()
    
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(
            status_code=500,
            detail="OAuth not configured. Add GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET to .env"
        )
    
    # Use a different redirect URI for Gmail
    gmail_redirect_uri = settings.google_oauth_redirect_uri.replace("/google/callback", "/google/gmail/callback")
    
    # Create OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [gmail_redirect_uri],
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=gmail_redirect_uri
    )
    
    # Generate authorization URL
    # We pass user_id in the state parameter to associate the token with the correct user on callback
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        prompt='consent',  # Force re-consent to get fresh tokens
        state=user_id
    )
    
    logger.info(f"Redirecting user {user_id} to Google OAuth for Gmail: {authorization_url}")
    return RedirectResponse(url=authorization_url)


@router.get("/google/gmail/callback")
async def google_gmail_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    """
    Handle OAuth callback from Google for Gmail.
    
    Args:
        code: Authorization code from Google
        state: The user_id we passed in
        error: Error message if authorization failed
    """
    if error:
        logger.error(f"Gmail OAuth authorization failed: {error}")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Authorization Failed</title></head>
                <body>
                    <h1>❌ Gmail Authorization Failed</h1>
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
    gmail_redirect_uri = settings.google_oauth_redirect_uri.replace("/google/callback", "/google/gmail/callback")
    
    # Create OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [gmail_redirect_uri],
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=gmail_redirect_uri
    )
    
    try:
        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Save tokens using GmailTool which handles Firestore
        from app.services.gmail_tool import get_gmail_tool
        gmail_tool = get_gmail_tool(user_id=user_id)
        gmail_tool._save_credentials(credentials)
        
        logger.info(f"✓ Gmail OAuth tokens saved successfully for user {user_id}")
        
        return HTMLResponse(
            content="""
            <html>
                <head>
                    <title>Gmail Connected</title>
                    <style>
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #EA4335 0%, #FBBC05 50%, #34A853 100%);
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
                            background: #EA4335;
                            color: white;
                            border: none;
                            border-radius: 6px;
                            font-size: 1rem;
                            cursor: pointer;
                        }
                        .close-btn:hover { background: #C5221F; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="success-icon">📧</div>
                        <h1>Gmail Connected!</h1>
                        <p>Your Gmail has been successfully connected to Jarvis.</p>
                        <p>You can now ask about your emails and get summaries!</p>
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
        logger.error(f"Failed to exchange Gmail authorization code: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete Gmail authorization: {str(e)}"
        )


@router.get("/gmail/status", response_model=GmailAuthStatus)
async def gmail_status(user_id: str = "default"):
    """
    Check if Gmail is authorized for authenticated user.
    
    Returns authorization status and whether token exists.
    """
    try:
        from app.services.gmail_tool import get_gmail_tool
        gmail_tool = get_gmail_tool(user_id=user_id)
        is_connected = gmail_tool.credentials is not None and gmail_tool.credentials.valid
        
        return GmailAuthStatus(
            authorized=is_connected,
            gmail_connected=is_connected
        )
    except Exception as e:
        logger.error(f"Failed to check Gmail status for {user_id}: {e}")
        return GmailAuthStatus(authorized=False, gmail_connected=False)
