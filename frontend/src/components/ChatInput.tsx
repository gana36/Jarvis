import { useState, useRef, useEffect } from 'react';

interface Voice {
    id: string;
    name: string;
    description: string;
}

interface Message {
    role: 'user' | 'assistant';
    content: string;
    intent?: string;
    confidence?: number;
}

export default function ChatInput() {
    const [message, setMessage] = useState<string>('');
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [voices, setVoices] = useState<Voice[]>([]);
    const [selectedVoice, setSelectedVoice] = useState<string>('');
    const [error, setError] = useState<string | null>(null);
    const [playAudio, setPlayAudio] = useState<boolean>(true);

    const audioRef = useRef<HTMLAudioElement | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Load voices from backend on mount
    useEffect(() => {
        const loadVoices = async () => {
            try {
                const response = await fetch('http://localhost:8000/api/profile/voices');
                if (!response.ok) throw new Error('Failed to fetch voices');

                const data = await response.json();
                setVoices(data.voices);
                setSelectedVoice(data.default);
            } catch (err) {
                console.error('Failed to load voices:', err);
                // Fallback to a default voice ID
                setSelectedVoice('21m00Tcm4TlvDq8ikWAM');
            }
        };
        loadVoices();
    }, []);

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Auto-play audio when it's set
    useEffect(() => {
        if (audioRef.current && playAudio) {
            audioRef.current.play().catch(err => {
                console.error('Error playing audio:', err);
            });
        }
    }, [messages, playAudio]);

    const sendMessage = async () => {
        if (!message.trim() || isLoading) return;

        const userMessage = message.trim();
        setMessage('');
        setError(null);

        // Add user message to chat
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setIsLoading(true);

        try {
            const response = await fetch('/api/chat/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: userMessage,
                    voice_id: playAudio ? selectedVoice : null,
                }),
            });

            if (!response.ok) {
                throw new Error(`Request failed: ${response.statusText}`);
            }

            const result = await response.json();

            // Add assistant response to chat
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: result.ai_response,
                intent: result.intent,
                confidence: result.confidence,
            }]);

            // Play audio if available
            if (result.audio_base64 && playAudio) {
                try {
                    const audioData = atob(result.audio_base64);
                    const audioArray = new Uint8Array(audioData.length);
                    for (let i = 0; i < audioData.length; i++) {
                        audioArray[i] = audioData.charCodeAt(i);
                    }
                    const audioBlob = new Blob([audioArray], { type: 'audio/mpeg' });
                    const audioUrl = URL.createObjectURL(audioBlob);

                    const audio = new Audio(audioUrl);
                    audioRef.current = audio;

                    audio.onended = () => {
                        URL.revokeObjectURL(audioUrl);
                    };

                    audio.onerror = () => {
                        console.error('Audio playback error');
                        URL.revokeObjectURL(audioUrl);
                    };
                } catch (err) {
                    console.error('Error decoding audio:', err);
                }
            }
        } catch (err) {
            console.error('Error sending message:', err);
            setError('Failed to send message. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', maxWidth: '800px', width: '100%' }}>
            {/* Voice Settings */}
            <div style={{
                padding: '12px',
                backgroundColor: '#f9fafb',
                borderBottom: '1px solid #e5e7eb',
                display: 'flex',
                gap: '12px',
                alignItems: 'center',
                flexWrap: 'wrap',
            }}>
                <div style={{ flex: 1, minWidth: '200px' }}>
                    <label htmlFor="chat-voice-select" style={{ fontSize: '12px', color: '#666', marginRight: '8px' }}>
                        Voice:
                    </label>
                    <select
                        id="chat-voice-select"
                        value={selectedVoice}
                        onChange={(e) => setSelectedVoice(e.target.value)}
                        disabled={isLoading || voices.length === 0}
                        style={{
                            padding: '6px 8px',
                            fontSize: '13px',
                            borderRadius: '6px',
                            border: '1px solid #d1d5db',
                            backgroundColor: (isLoading || voices.length === 0) ? '#f3f4f6' : 'white',
                            cursor: (isLoading || voices.length === 0) ? 'not-allowed' : 'pointer',
                        }}
                    >
                        {voices.length === 0 ? (
                            <option value="">Loading voices...</option>
                        ) : (
                            voices.map(voice => (
                                <option key={voice.id} value={voice.id}>
                                    {voice.name} - {voice.description}
                                </option>
                            ))
                        )}
                    </select>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                    <input
                        type="checkbox"
                        checked={playAudio}
                        onChange={(e) => setPlayAudio(e.target.checked)}
                        disabled={isLoading}
                        style={{ cursor: isLoading ? 'not-allowed' : 'pointer' }}
                    />
                    Play audio responses
                </label>
            </div>

            {/* Messages Area */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '16px',
                backgroundColor: '#ffffff',
            }}>
                {messages.length === 0 ? (
                    <div style={{
                        textAlign: 'center',
                        color: '#9ca3af',
                        marginTop: '40px',
                        fontSize: '14px',
                    }}>
                        Start a conversation with Jarvis...
                    </div>
                ) : (
                    messages.map((msg, idx) => (
                        <div
                            key={idx}
                            style={{
                                marginBottom: '12px',
                                display: 'flex',
                                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                            }}
                        >
                            <div
                                style={{
                                    maxWidth: '70%',
                                    padding: '10px 14px',
                                    borderRadius: '12px',
                                    backgroundColor: msg.role === 'user' ? '#3b82f6' : '#f3f4f6',
                                    color: msg.role === 'user' ? 'white' : '#111',
                                }}
                            >
                                <div style={{ fontSize: '14px', lineHeight: '1.5' }}>
                                    {msg.content}
                                </div>
                                {msg.intent && (
                                    <div style={{
                                        fontSize: '10px',
                                        marginTop: '4px',
                                        opacity: 0.7,
                                        fontStyle: 'italic',
                                    }}>
                                        {msg.intent} ({Math.round((msg.confidence || 0) * 100)}%)
                                    </div>
                                )}
                            </div>
                        </div>
                    ))
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Error Message */}
            {error && (
                <div style={{
                    padding: '8px 16px',
                    backgroundColor: '#fee2e2',
                    color: '#dc2626',
                    fontSize: '13px',
                    borderTop: '1px solid #fecaca',
                }}>
                    {error}
                </div>
            )}

            {/* Input Area */}
            <div style={{
                padding: '12px',
                backgroundColor: '#ffffff',
                borderTop: '1px solid #e5e7eb',
                display: 'flex',
                gap: '8px',
            }}>
                <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Type your message... (Press Enter to send)"
                    disabled={isLoading}
                    rows={1}
                    style={{
                        flex: 1,
                        padding: '10px 12px',
                        fontSize: '14px',
                        borderRadius: '8px',
                        border: '1px solid #d1d5db',
                        resize: 'none',
                        fontFamily: 'inherit',
                        outline: 'none',
                        backgroundColor: isLoading ? '#f3f4f6' : 'white',
                    }}
                />
                <button
                    onClick={sendMessage}
                    disabled={isLoading || !message.trim()}
                    style={{
                        padding: '10px 20px',
                        fontSize: '14px',
                        borderRadius: '8px',
                        border: 'none',
                        backgroundColor: (isLoading || !message.trim()) ? '#9ca3af' : '#3b82f6',
                        color: 'white',
                        cursor: (isLoading || !message.trim()) ? 'not-allowed' : 'pointer',
                        fontWeight: '500',
                    }}
                >
                    {isLoading ? 'Sending...' : 'Send'}
                </button>
            </div>
        </div>
    );
}
