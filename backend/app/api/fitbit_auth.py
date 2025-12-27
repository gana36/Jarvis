"""OAuth authentication endpoints for Fitbit health data"""
import base64
import json
import logging
import time
from pathlib import Path

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Token storage path
TOKEN_FILE = Path("fitbit_token.json")

# Fitbit OAuth scopes for health data
SCOPES = ['activity', 'heartrate', 'sleep', 'profile']


class FitbitAuthStatus(BaseModel):
    """Fitbit authorization status response"""
    authorized: bool
    fitbit_connected: bool


@router.get("/fitbit")
async def fitbit_auth():
    """
    Initiate Fitbit OAuth 2.0 flow.

    Redirects user to Fitbit OAuth consent screen.
    """
    settings = get_settings()

    if not settings.fitbit_client_id or not settings.fitbit_client_secret:
        raise HTTPException(
            status_code=500,
            detail="Fitbit OAuth not configured. Add FITBIT_CLIENT_ID and FITBIT_CLIENT_SECRET to .env"
        )

    # Build authorization URL
    scope_string = ' '.join(SCOPES)
    authorization_url = (
        f"https://www.fitbit.com/oauth2/authorize"
        f"?client_id={settings.fitbit_client_id}"
        f"&response_type=code"
        f"&scope={scope_string}"
        f"&redirect_uri={settings.fitbit_redirect_uri}"
    )

    logger.info(f"Redirecting to Fitbit OAuth: {authorization_url}")
    return RedirectResponse(url=authorization_url)


@router.get("/fitbit/callback")
async def fitbit_callback(code: str | None = None, error: str | None = None):
    """
    Handle OAuth callback from Fitbit.

    Args:
        code: Authorization code from Fitbit
        error: Error message if authorization failed
    """
    if error:
        logger.error(f"Fitbit OAuth authorization failed: {error}")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Authorization Failed</title></head>
                <body>
                    <h1>Authorization Failed</h1>
                    <p>Error: {error}</p>
                    <p><a href="/">Return to app</a></p>
                </body>
            </html>
            """,
            status_code=400
        )

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")

    settings = get_settings()

    try:
        # Prepare Basic Auth header (Fitbit requires this)
        credentials = f"{settings.fitbit_client_id}:{settings.fitbit_client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        # Exchange authorization code for tokens
        token_url = "https://api.fitbit.com/oauth2/token"
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.fitbit_redirect_uri
        }

        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status()

        token_response = response.json()

        # Calculate expiration timestamp
        expires_at = int(time.time()) + token_response.get('expires_in', 28800)

        # Save tokens to file
        token_data = {
            'access_token': token_response.get('access_token'),
            'refresh_token': token_response.get('refresh_token'),
            'expires_at': expires_at,
            'user_id': token_response.get('user_id'),
            'token_type': token_response.get('token_type', 'Bearer')
        }

        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)

        logger.info("OAuth tokens saved successfully")

        return HTMLResponse(
            content="""
            <html>
                <head>
                    <title>Fitbit Connected</title>
                    <style>
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #00B0FF 0%, #0081CB 100%);
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
                            background: #00B0FF;
                            color: white;
                            border: none;
                            border-radius: 6px;
                            font-size: 1rem;
                            cursor: pointer;
                        }
                        .close-btn:hover { background: #0081CB; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="success-icon">✓</div>
                        <h1>Fitbit Connected!</h1>
                        <p>Your Fitbit has been successfully connected to Jarvis.</p>
                        <p>You can now ask for your daily summary with health data!</p>
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

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to exchange authorization code: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete authorization: {str(e)}"
        )


@router.get("/fitbit/status", response_model=FitbitAuthStatus)
async def fitbit_status():
    """
    Check if Fitbit is authorized.

    Returns authorization status and whether token exists.
    """
    token_exists = TOKEN_FILE.exists()

    if not token_exists:
        return FitbitAuthStatus(authorized=False, fitbit_connected=False)

    # Try to load and validate token
    try:
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)

        # Check if required fields exist
        has_access_token = 'access_token' in token_data
        has_refresh_token = 'refresh_token' in token_data

        return FitbitAuthStatus(
            authorized=has_access_token and has_refresh_token,
            fitbit_connected=has_access_token and has_refresh_token
        )
    except Exception as e:
        logger.error(f"Failed to read token file: {e}")
        return FitbitAuthStatus(authorized=False, fitbit_connected=False)
