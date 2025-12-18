import { useState, useRef } from 'react';

type RecordingState = 'idle' | 'recording' | 'processing';

export default function PushToTalk() {
    const [state, setState] = useState<RecordingState>('idle');
    const [error, setError] = useState<string | null>(null);
    const [transcript, setTranscript] = useState<string>('');

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);

    const startRecording = async () => {
        try {
            setError(null);
            setTranscript(''); // Clear previous transcript on new recording

            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Create MediaRecorder with webm format
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm',
            });

            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            // Collect audio chunks
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            // Handle recording stop
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());

                // Upload to backend
                await uploadAudio(audioBlob);
            };

            mediaRecorder.start();
            setState('recording');
        } catch (err) {
            console.error('Error starting recording:', err);
            setError('Failed to access microphone');
            setState('idle');
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
            mediaRecorderRef.current.stop();
            setState('processing');
        }
    };

    const uploadAudio = async (audioBlob: Blob) => {
        try {
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');

            const response = await fetch('/api/voice/ingest', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('Upload successful:', result);

            // Display transcript if available
            if (result.transcript) {
                setTranscript(result.transcript);
            }

            setState('idle');
        } catch (err) {
            console.error('Error uploading audio:', err);
            setError('Failed to upload audio');
            setState('idle');
        }
    };

    const handleMouseDown = () => {
        if (state === 'idle') {
            startRecording();
        }
    };

    const handleMouseUp = () => {
        if (state === 'recording') {
            stopRecording();
        }
    };

    const getButtonText = () => {
        switch (state) {
            case 'idle':
                return 'Hold to Speak';
            case 'recording':
                return 'Recording...';
            case 'processing':
                return 'Processing...';
        }
    };

    return (
        <div>
            <button
                onMouseDown={handleMouseDown}
                onMouseUp={handleMouseUp}
                disabled={state === 'processing'}
                style={{
                    padding: '16px 32px',
                    fontSize: '16px',
                    cursor: state === 'processing' ? 'not-allowed' : 'pointer',
                    backgroundColor: state === 'recording' ? '#ef4444' : '#3b82f6',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                }}
            >
                {getButtonText()}
            </button>

            {error && (
                <div style={{ color: 'red', marginTop: '8px' }}>
                    Error: {error}
                </div>
            )}

            {transcript && (
                <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#f3f4f6', borderRadius: '8px' }}>
                    <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Transcript:</div>
                    <div style={{ fontSize: '16px', color: '#111' }}>{transcript}</div>
                </div>
            )}

            <div style={{ marginTop: '8px', color: '#666', fontSize: '12px' }}>
                State: {state}
            </div>
        </div>
    );
}
