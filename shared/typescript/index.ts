/**
 * Shared TypeScript types and schemas
 * Keep in sync with Python Pydantic models
 */

// Message types for WebSocket communication
export enum MessageType {
    AUDIO_CHUNK = 'audio_chunk',
    TEXT_CHUNK = 'text_chunk',
    START_STREAM = 'start_stream',
    END_STREAM = 'end_stream',
    ERROR = 'error',
}

// WebSocket message base interface
export interface WebSocketMessage {
    type: MessageType;
    timestamp: string;
}

// Audio streaming interfaces
export interface AudioChunkMessage extends WebSocketMessage {
    type: MessageType.AUDIO_CHUNK;
    data: string; // base64 encoded audio
    sequenceNumber: number;
}

export interface TextChunkMessage extends WebSocketMessage {
    type: MessageType.TEXT_CHUNK;
    text: string;
    isFinal: boolean;
}

// Stream control
export interface StreamControlMessage extends WebSocketMessage {
    type: MessageType.START_STREAM | MessageType.END_STREAM;
    streamId: string;
}

// Error handling
export interface ErrorMessage extends WebSocketMessage {
    type: MessageType.ERROR;
    error: string;
    code?: string;
}

// Union type for all messages
export type Message =
    | AudioChunkMessage
    | TextChunkMessage
    | StreamControlMessage
    | ErrorMessage;
