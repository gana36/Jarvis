"""
Shared Python schemas using Pydantic
Keep in sync with TypeScript types
"""
from datetime import datetime
from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Message types for WebSocket communication"""

    AUDIO_CHUNK = "audio_chunk"
    TEXT_CHUNK = "text_chunk"
    START_STREAM = "start_stream"
    END_STREAM = "end_stream"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    """Base WebSocket message"""

    type: MessageType
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AudioChunkMessage(WebSocketMessage):
    """Audio streaming message"""

    type: Literal[MessageType.AUDIO_CHUNK] = MessageType.AUDIO_CHUNK
    data: str  # base64 encoded audio
    sequence_number: int


class TextChunkMessage(WebSocketMessage):
    """Text streaming message"""

    type: Literal[MessageType.TEXT_CHUNK] = MessageType.TEXT_CHUNK
    text: str
    is_final: bool = False


class StreamControlMessage(WebSocketMessage):
    """Stream control message"""

    type: Literal[MessageType.START_STREAM, MessageType.END_STREAM]
    stream_id: str


class ErrorMessage(WebSocketMessage):
    """Error message"""

    type: Literal[MessageType.ERROR] = MessageType.ERROR
    error: str
    code: str | None = None


# Union type for all messages
Message = Union[AudioChunkMessage, TextChunkMessage, StreamControlMessage, ErrorMessage]
