# FastAPI entry point

# Load .env file FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, voice, chat, tasks, profile, fitbit_auth, gmail_auth, files
from app.config import setup_google_credentials, get_settings

# Set up Google Cloud credentials from .env
setup_google_credentials()

# Set GOOGLE_CLOUD_PROJECT for Firebase (it needs this in OS env, not just Settings)
settings = get_settings()
if settings.google_project_id and not os.getenv('GOOGLE_CLOUD_PROJECT'):
    os.environ['GOOGLE_CLOUD_PROJECT'] = settings.google_project_id
    print(f"Set GOOGLE_CLOUD_PROJECT to {settings.google_project_id}")

app = FastAPI(
    title="Mini Manas API",
    description="Low-latency voice assistant backend",
    version="0.1.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(fitbit_auth.router, prefix="/auth", tags=["fitbit-auth"])
app.include_router(gmail_auth.router, prefix="/auth", tags=["gmail-auth"])
app.include_router(profile.router, prefix="/api", tags=["profile"])
app.include_router(files.router, prefix="/api/files", tags=["files"])


@app.get("/")
async def root():
    return {"message": "Mini Manas API - Backend placeholder"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

