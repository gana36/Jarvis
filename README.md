## MANAS

Intelligence that listens, and responds.

## Overview

MANAS is a voice-first personal AI assistant designed for fast, low-latency interaction. You speak; MANAS transcribes, routes the request to the right capability, and responds with both spoken output and structured UI cards.

It exists to make conversational control practical: quick back-and-forth, clear intent handling, and a lightweight memory layer for preferences and explicit recall—without requiring users to switch to typing as the primary interface.

## Features

- **Voice-driven interaction**: record a request from the browser, get a spoken response.
- **Intent-based tool execution**: classify the request and route it to a focused handler (tasks, calendar, email, search, etc.).
- **Visual responses alongside voice**: responses can include structured cards and optional “visual render” payloads.
- **Memory for preferences and explicit recall**: store user facts/preferences and retrieve relevant context when helpful.
- **Tool coverage**: tasks, calendar, email reading, web search, documents, writing, and code assistance (capability set is designed to expand).

## How MANAS Works (Conceptual)

1. The user speaks.
2. The request is transcribed.
3. Intent is inferred.
4. The request is routed to a tool or model.
5. A response is generated and spoken (with optional visual output).
6. Relevant context may be stored for later recall.

This repository implements the above flow as a frontend UI + backend API, with authentication and integrations layered on top.

## Getting Started

### Prerequisites

- **Node.js**: 18+ (npm 9+ recommended)
- **Python**: 3.10+
- **Google Cloud account**:
  - A project with Speech-to-Text enabled (and any other Google APIs you plan to use)
  - A service account key (JSON) for local development
- **ElevenLabs**:
  - An API key for voice synthesis
- **Firebase**:
  - A Firebase project for Authentication (Email/Password and/or Google sign-in)

### Environment variables

MANAS uses two environment files:

- `backend/.env` for the FastAPI backend
- `frontend/.env` for the Vite frontend

Create `backend/.env`:

```bash
# Google Cloud (choose one)
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
# or: GOOGLE_CREDENTIALS_JSON='{"type":"service_account", ... }'

# Project identity (recommended)
GOOGLE_PROJECT_ID=your-gcp-project-id

# Core model + voice
GEMINI_API_KEY=your_gemini_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Optional integrations (enable as needed)
# GOOGLE_OAUTH_CLIENT_ID=...
# GOOGLE_OAUTH_CLIENT_SECRET=...
# GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/auth/google/callback
#
# NEWS_API_KEY=...
# YOUCOM_API_KEY=...
# YELP_API_KEY=...
#
# QDRANT_URL=https://your-qdrant.cloud.qdrant.io:6333
# QDRANT_API_KEY=...
#
# OPENAI_API_KEY=...   # used as a Mem0 LLM/embedder if present
```

Create `frontend/.env`:

```bash
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
```

### Install dependencies

From the repository root:

```bash
npm run install:all
```

This installs workspace dependencies and sets up the backend virtualenv under `backend/venv`.

### Run locally

Start frontend + backend together:

```bash
npm run dev
```

Access points:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

### Start the voice interface

1. Open the frontend at `http://localhost:5173`.
2. Sign in (or create an account) via the login screen.
3. Click the microphone button once to start recording.
4. Speak your request.
5. Click the microphone button again to stop recording and send.

## Example Interaction

Spoken:

User: “Schedule a 25 minute focus block tomorrow morning and remind me 10 minutes before.”  
MANAS: “Done. I created a 25 minute focus block for tomorrow morning and set a reminder 10 minutes before.”

Intent routing sketch (TypeScript-style pseudocode):

```ts
type Intent =
  | 'TASK_CREATE'
  | 'CALENDAR_CREATE_EVENT'
  | 'EMAIL_READ'
  | 'LEARN'
  | 'GENERAL_CHAT';

async function handleUtterance(text: string) {
  const { intent, confidence } = await inferIntent(text);
  if (confidence < 0.6) return respondWithClarifyingQuestion();

  switch (intent) {
    case 'TASK_CREATE':
      return runTaskTool(text);
    case 'CALENDAR_CREATE_EVENT':
      return runCalendarTool(text);
    case 'EMAIL_READ':
      return runEmailTool(text);
    case 'LEARN':
      return runSearchTool(text);
    default:
      return runChatModel(text);
  }
}
```

## Built With

- **ElevenLabs**: voice synthesis / agents
- **Google Cloud AI**: Gemini / Vertex AI
- **Google Cloud infrastructure**: authentication and service integrations

## Project Status

MANAS is early-stage but functional. The codebase is organized to support additional tools and integrations with minimal coupling: add a new capability by introducing a handler, connecting it to intent routing, and exposing the resulting output through voice and/or UI cards.

## Contributing

Contributions are welcome.

- Use GitHub Issues for bugs, proposals, and feature requests.
- Pull requests should be small, scoped, and include a clear description of behavior changes.
- If you are adding an integration, include configuration notes (env vars, permissions, and any required API enablement).

## License (MIT)

MIT License

Copyright (c) 2025 MANAS contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
