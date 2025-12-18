# Mini Jarvis - Backend

FastAPI backend for the voice assistant with WebSocket streaming support.

## Tech Stack

- **FastAPI** - Modern async web framework
- **Pydantic** - Data validation and settings
- **WebSockets** - Real-time bidirectional communication
- **Uvicorn** - ASGI server

## Development

```bash
# Install dependencies
pip install -e .

# Run dev server
uvicorn app.main:app --reload
```

The API runs on `http://localhost:8000` with auto-reload enabled.

## API Documentation

When running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Structure

```
app/
├── main.py           # FastAPI application entry point
├── config.py         # Configuration settings (to be added)
├── api/              # API routes (to be added)
│   ├── rest/         # REST endpoints
│   └── websocket/    # WebSocket endpoints
├── services/         # Business logic (to be added)
└── models/           # Database models (if needed)

tests/                # Test suite (to be added)
```

## Key Features (Planned)

- WebSocket streaming for audio I/O
- Chunked response streaming
- Low-latency audio processing
- Health monitoring endpoints
