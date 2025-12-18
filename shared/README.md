# Mini Jarvis - Shared Schemas

Shared type definitions and schemas used by both frontend and backend.

## Structure

```
shared/
├── typescript/       # TypeScript types for frontend
│   └── index.ts     # Message types, interfaces
└── python/          # Pydantic schemas for backend
    └── schemas.py   # Matching Python models
```

## Philosophy

- **Single source of truth** for data contracts
- **Type safety** across the stack
- **Keep in sync** - TypeScript and Python schemas should mirror each other

## Message Schema

All WebSocket messages follow a common structure:

```typescript
{
  type: MessageType,
  timestamp: string,
  // ... type-specific fields
}
```

### Message Types

- `audio_chunk` - Streaming audio data (base64 encoded)
- `text_chunk` - Streaming text responses
- `start_stream` - Begin a new stream
- `end_stream` - Terminate a stream
- `error` - Error information

## Usage

### Frontend (TypeScript)
```typescript
import { Message, MessageType } from '@shared'
```

### Backend (Python)
```python
from shared.python.schemas import Message, MessageType
```
