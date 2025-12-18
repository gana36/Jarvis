# FastAPI entry point
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import voice
from app.config import setup_google_credentials

# Set up Google Cloud credentials from .env
setup_google_credentials()

app = FastAPI(
    title="Mini Jarvis API",
    description="Low-latency voice assistant backend",
    version="0.1.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])


@app.get("/")
async def root():
    return {"message": "Mini Jarvis API - Backend placeholder"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

