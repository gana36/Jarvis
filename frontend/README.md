# Mini Jarvis - Frontend

React + Vite + TypeScript frontend for the voice assistant.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast build tool and dev server

## Development

```bash
npm install
npm run dev
```

The dev server runs on `http://localhost:5173` with proxy to backend on port 8000.

## Structure

```
src/
├── main.tsx          # Entry point
├── components/       # React components (to be added)
├── hooks/            # Custom hooks (to be added)
├── services/         # API & WebSocket clients (to be added)
└── types/            # TypeScript types (to be added)
```

## Key Features (Planned)

- WebSocket-based streaming audio
- Real-time voice activity detection
- Streaming text responses
- Low-latency audio playback
