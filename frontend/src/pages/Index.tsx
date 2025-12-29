import { useState, useCallback, useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Settings, Mic } from 'lucide-react';
import { JarvisOrb, OrbState, OrbContext } from '@/components/JarvisOrb';
import { AcknowledgmentCard, CardType } from '@/components/AcknowledgmentCard';
import { LiveUnderstanding } from '@/components/LiveUnderstanding';
import { StatusIndicator } from '@/components/StatusIndicator';
import { SettingsPanel } from '@/components/SettingsPanel';
import { TasksView } from '@/components/TasksView';
import { ProfileView } from '@/components/ProfileView';
import { voiceAPI, chatAPI, profileAPI, filesAPI } from '@/services/api';

interface Card {
  id: string;
  type: CardType;
  title: string;
  subtitle?: string;
  data?: any;
  isCitation?: boolean;
}

export default function Index() {
  const [orbState, setOrbState] = useState<OrbState>('idle');
  const [orbContext, setOrbContext] = useState<OrbContext>('default');
  const [cards, setCards] = useState<Card[]>([]);
  const [citationCards, setCitationCards] = useState<Card[]>([]);
  const [showUnderstanding, setShowUnderstanding] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [selectedVoice, setSelectedVoice] = useState<string>('');
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [entities] = useState<any[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const [currentView, setCurrentView] = useState<'main' | 'tasks' | 'profile'>('main');
  const [isRecording, setIsRecording] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [isTextPanelOpen, setIsTextPanelOpen] = useState(false);
  const [currentIntent, setCurrentIntent] = useState<string>('');
  const [pendingFileIds, setPendingFileIds] = useState<string[]>([]);
  const [isSwallowing, setIsSwallowing] = useState(false);
  const [isAnalysisMode, setIsAnalysisMode] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load voices and profile on mount
  useEffect(() => {
    loadVoices();
  }, []);

  const loadVoices = async () => {
    try {
      const data = await profileAPI.getVoices();
      setSelectedVoice(data.default);

      // Also load user's preferred voice
      try {
        const profile = await profileAPI.getProfile();
        if (profile.preferred_voice) {
          setSelectedVoice(profile.preferred_voice);
        }
      } catch (err) {
        console.log('Profile not loaded, using default voice');
      }
    } catch (err) {
      console.error('Failed to load voices:', err);
      selectedVoice || setSelectedVoice('21m00Tcm4TlvDq8ikWAM'); // Default fallback
    }
  };

  // Simulate audio level changes when speaking
  useEffect(() => {
    if (orbState === 'speaking') {
      const interval = setInterval(() => {
        setAudioLevel(0.3 + Math.random() * 0.7);
      }, 100);
      return () => clearInterval(interval);
    } else {
      setAudioLevel(0);
    }
  }, [orbState]);

  const clearCards = useCallback((clearPersistent = false) => {
    if (clearPersistent) {
      // Clear all cards including persistent ones (news, learn)
      setCards([]);
      setCitationCards([]);
      setCurrentIntent('');
    } else {
      // Only clear non-persistent cards (weather, task, calendar, info)
      // Keep news and memory (learn) cards as they are "persistent briefings"
      setCards(prev => prev.filter(card =>
        card.type === 'news' || card.type === 'memory'
      ));
      // Citation cards are for Learn intent and should persist
    }
  }, []);

  const startRecording = async () => {
    console.log('🎤 Starting recording...');

    // Clear all cards (including persistent ones) when starting new recording
    clearCards(true);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('✅ Got media stream');

      // Create MediaRecorder with proper options
      const options = { mimeType: 'audio/webm' };
      const recorder = new MediaRecorder(stream, options);
      console.log('✅ Created MediaRecorder');

      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        console.log('📦 Data available:', event.data.size, 'bytes');
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        console.log('⏹️ Recording stopped, chunks:', audioChunksRef.current.length);
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        console.log('📦 Created blob:', audioBlob.size, 'bytes');

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());

        // Only upload if we have substantial audio data
        if (audioBlob.size > 1000) {
          await uploadAudio(audioBlob);
        } else {
          console.warn('⚠️ Audio too short, not uploading');
          setOrbState('idle');
          setShowUnderstanding(false);
          setCards([{
            id: Date.now().toString(),
            type: 'info',
            title: 'Recording too short',
            subtitle: 'Please hold the button longer while speaking',
          }]);
        }
      };

      // Start recording with 100ms timeslice to ensure data is captured
      recorder.start(100);
      console.log('▶️ MediaRecorder started, state:', recorder.state);
    } catch (err) {
      console.error('❌ Error starting recording:', err);
      setOrbState('idle');
      setShowUnderstanding(false);

      // Show error card
      setCards([{
        id: Date.now().toString(),
        type: 'info',
        title: 'Microphone access denied or unavailable',
        subtitle: 'Please allow microphone permissions',
      }]);
    }
  };

  const stopRecording = () => {
    console.log('🛑 Stop recording called');
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      console.log('⏸️ Stopping MediaRecorder');
      mediaRecorderRef.current.stop();
    } else {
      console.log('⚠️ MediaRecorder not recording, state:', mediaRecorderRef.current?.state);
    }
  };

  const uploadAudio = async (audioBlob: Blob) => {
    clearCards(true);
    setOrbState('thinking');
    setShowUnderstanding(false);

    // Clear pending files and exit analysis mode immediately for better UX
    const filesToUpload = [...pendingFileIds];
    setPendingFileIds([]);
    setIsAnalysisMode(false);
    setOrbContext('default');

    try {
      const result = await voiceAPI.ingestAudio(audioBlob, selectedVoice, filesToUpload);

      // Only process if we got a valid transcript
      if (!result.transcript || result.transcript.trim() === '') {
        console.warn('⚠️ Empty transcript received');
        setOrbState('idle');
        setCards([{
          id: Date.now().toString(),
          type: 'info',
          title: 'No speech detected',
          subtitle: 'Please speak more clearly or check your microphone',
        }]);
        return;
      }

      console.log('📝 Transcript:', result.transcript);
      console.log('🤖 AI Response:', result.ai_response);

      // Change context based on intent
      if (result.intent) {
        setCurrentIntent(result.intent);
        const intentLower = result.intent.toLowerCase();
        if (intentLower.includes('calendar') || intentLower.includes('summary')) {
          setOrbContext('default');
        } else if (intentLower.includes('task')) {
          setOrbContext('focus');
        } else if (intentLower.includes('weather')) {
          setOrbContext('weather');
        } else if (intentLower.includes('learn') || intentLower.includes('educational') || intentLower.includes('news')) {
          setOrbContext('memory');
        }
      } else {
        setCurrentIntent('GENERAL_CHAT');
      }

      // Add acknowledgment card
      if (result.ai_response) {
        const intentLower = result.intent?.toLowerCase() || '';
        let cardType: CardType = 'info';

        if (intentLower.includes('weather')) {
          cardType = 'weather';
        } else if (intentLower.includes('task')) {
          cardType = 'task';
        } else if (intentLower.includes('calendar') || intentLower.includes('summary')) {
          cardType = 'calendar';
        } else if (intentLower.includes('learn') || intentLower.includes('educational') || intentLower.includes('remember')) {
          cardType = 'memory';
        } else if (intentLower.includes('news')) {
          cardType = 'news';
        } else if (intentLower.includes('restaurant')) {
          cardType = 'restaurant';
        }

        const mainCard: Card = {
          id: Date.now().toString(),
          type: cardType,
          title: result.ai_response.substring(0, 100) + (result.ai_response.length > 100 ? '...' : ''),
          subtitle: result.intent || 'RESPONSE',
          data: result.data,
        };

        setCards([mainCard]);

        // Handle citations for Learn intent
        if (cardType === 'memory' && result.data?.citations) {
          const citations = result.data.citations.map((citation: any, idx: number) => {
            // Handle both old string format and new object format
            const url = typeof citation === 'string' ? citation : citation.url;
            const title = typeof citation === 'string' ? citation : citation.title;
            const thumbnail = typeof citation === 'string' ? null : citation.thumbnail;

            return {
              id: `cit-${Date.now()}-${idx}`,
              type: 'info' as CardType,
              title: title || url,
              isCitation: true,
              data: { url, title, thumbnail }
            };
          });
          setCitationCards(citations);
        }
      }

      setOrbState('speaking');

      // Play audio if available
      if (result.audio_base64) {
        try {
          const audioData = atob(result.audio_base64);
          const audioArray = new Uint8Array(audioData.length);
          for (let i = 0; i < audioData.length; i++) {
            audioArray[i] = audioData.charCodeAt(i);
          }
          const audioBlob = new Blob([audioArray], { type: 'audio/mpeg' });
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);

          audio.onended = () => {
            setOrbState('idle');
            // Don't clear persistent cards (news, learn) when audio ends
            clearCards(false);
            URL.revokeObjectURL(audioUrl);
          };

          audio.onerror = () => {
            setOrbState('idle');
            clearCards();
            URL.revokeObjectURL(audioUrl);
          };

          audio.play();
        } catch (err) {
          console.error('Error playing audio:', err);
          setTimeout(() => setOrbState('idle'), 2500);
        }
      } else {
        // No audio, just show the text response for a bit
        setTimeout(() => {
          setOrbState('idle');
          // Don't clear persistent cards (news, learn) when timeout ends
          clearCards(false);
        }, 5000);
      }
    } catch (err) {
      console.error('Error uploading audio:', err);
      setOrbState('idle');

      // Show error card
      setCards([{
        id: Date.now().toString(),
        type: 'info',
        title: 'Sorry, I encountered an error processing your request.',
        subtitle: 'Please try again',
      }]);
    }
  };

  const handleTextSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = textInput.trim();
    if (!trimmed) return;

    console.log('📝 Typed command:', trimmed);
    clearCards(true);
    setOrbState('thinking');
    setCurrentTranscript(trimmed);
    setTextInput('');

    // Clear pending files and exit analysis mode immediately for better UX
    const filesToProcess = [...pendingFileIds];
    setPendingFileIds([]);
    setIsAnalysisMode(false);
    setOrbContext('default');

    try {
      const result = await chatAPI.sendMessage(trimmed, selectedVoice, filesToProcess);

      if (!result.success) {
        setOrbState('idle');
        setCards([{
          id: Date.now().toString(),
          type: 'info',
          title: result.ai_response,
        }]);
        return;
      }

      // Update context based on intent
      if (result.intent) {
        setCurrentIntent(result.intent);
        const intentLower = result.intent.toLowerCase();
        if (intentLower.includes('calendar') || intentLower.includes('summary')) setOrbContext('default');
        else if (intentLower.includes('task')) setOrbContext('focus');
        else if (intentLower.includes('weather')) setOrbContext('weather');
        else if (intentLower.includes('learn') || intentLower.includes('news')) setOrbContext('memory');
      } else {
        setCurrentIntent('GENERAL_CHAT');
      }

      // Add card
      if (result.ai_response) {
        const intentLower = result.intent?.toLowerCase() || '';
        let cardType: CardType = 'info';
        if (intentLower.includes('weather')) cardType = 'weather';
        else if (intentLower.includes('task')) cardType = 'task';
        else if (intentLower.includes('calendar')) cardType = 'calendar';
        else if (intentLower.includes('learn')) cardType = 'memory';
        else if (intentLower.includes('news')) cardType = 'news';
        else if (intentLower.includes('restaurant')) cardType = 'restaurant';
        else if (intentLower.includes('email')) cardType = 'email';

        setCards([{
          id: Date.now().toString(),
          type: cardType,
          title: result.ai_response,
          subtitle: result.intent,
          data: result.data,
        }]);

        // Handle citations
        if (cardType === 'memory' && result.data?.citations) {
          const citations = result.data.citations.map((citation: any, idx: number) => {
            const url = typeof citation === 'string' ? citation : citation.url;
            const title = typeof citation === 'string' ? citation : citation.title;
            const thumbnail = typeof citation === 'string' ? null : citation.thumbnail;

            return {
              id: `cit-${Date.now()}-${idx}`,
              type: 'info' as CardType,
              title: title || url,
              isCitation: true,
              data: { url, title, thumbnail }
            };
          });
          setCitationCards(citations);
        }
      }

      // Play TTS
      if (result.audio_base64) {
        setOrbState('speaking');
        const byteCharacters = atob(result.audio_base64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const audioBlob = new Blob([byteArray], { type: 'audio/mpeg' });
        const audio = new Audio(URL.createObjectURL(audioBlob));
        audio.onended = () => setOrbState('idle');
        audio.play().catch(() => setOrbState('idle'));
      } else {
        setOrbState('idle');
      }
    } catch (err) {
      console.error('Text error:', err);
      setOrbState('idle');
      setCards([{
        id: Date.now().toString(),
        type: 'info',
        title: 'Error processing command',
      }]);
    }
  };

  const handleMicClick = useCallback(() => {
    if (isRecording) {
      // Stop recording
      console.log('🔵 Stopping recording...');
      stopRecording();
      setIsRecording(false);
    } else {
      // Start recording
      console.log('🔴 Starting recording...');
      setOrbState('listening');
      setShowUnderstanding(true);
      setCurrentTranscript('🎤 Recording... Click again to stop');
      setIsRecording(true);
      startRecording();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRecording]);

  const removeCard = useCallback((id: string) => {
    setCards((prev) => prev.filter((card) => card.id !== id));
  }, []);

  const removeCitation = useCallback((id: string) => {
    setCitationCards((prev) => prev.filter((card) => card.id !== id));
  }, []);

  const handleFilesUpload = async (files: File[]) => {
    setIsSwallowing(true);
    const newFileIds: string[] = [];

    for (const file of files) {
      try {
        console.log(`📤 Uploading file: ${file.name}`);
        const response = await filesAPI.upload(file);
        newFileIds.push(response.file_id);
      } catch (err) {
        console.error(`Failed to upload ${file.name}:`, err);
        setCards(prev => [{
          id: Date.now().toString(),
          type: 'info',
          title: `Failed to upload ${file.name}`,
          subtitle: 'ERROR',
        }, ...prev]);
      }
    }

    if (newFileIds.length > 0) {
      setPendingFileIds(newFileIds);
      setIsAnalysisMode(true);
      setOrbContext('analyze');
      console.log(`✅ Uploaded ${newFileIds.length} files. Entered Analysis Mode (Replacing previous files if any).`);

      // Replace existing acknowledgement cards with fresh one
      setCards(prev => [
        {
          id: `ack-${Date.now()}`,
          type: 'info',
          title: 'Document Transferred',
          subtitle: 'ANALYSIS MODE ACTIVE',
          data: { message: 'Manas is ready to analyze your file. Ask a question or request a summary.' }
        },
        ...prev.filter(c => !c.id.startsWith('ack-'))
      ]);
    }

    // End swallow animation after a bit
    setTimeout(() => setIsSwallowing(false), 800);
  };

  const handleOrbClick = () => {
    fileInputRef.current?.click();
  };

  const handleNavigate = (view: 'tasks' | 'profile') => {
    setCurrentView(view);
  };

  // Show alternate views
  if (currentView === 'tasks') {
    return <TasksView onBack={() => setCurrentView('main')} />;
  }

  if (currentView === 'profile') {
    return <ProfileView onBack={() => setCurrentView('main')} />;
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      {/* Background gradient layers */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Base radial gradient */}
        <div
          className="absolute inset-0"
          style={{
            background: 'radial-gradient(ellipse at 50% 40%, hsl(220, 25%, 8%) 0%, hsl(230, 25%, 5%) 60%, hsl(230, 30%, 3%) 100%)',
          }}
        />

        {/* Subtle grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `
              linear-gradient(hsl(185, 85%, 50%) 1px, transparent 1px),
              linear-gradient(90deg, hsl(185, 85%, 50%) 1px, transparent 1px)
            `,
            backgroundSize: '60px 60px',
          }}
        />

        {/* Ambient orb glow */}
        <motion.div
          className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full"
          style={{
            background: 'radial-gradient(circle, hsl(185, 85%, 50% / 0.08) 0%, transparent 60%)',
          }}
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.5, 0.8, 0.5],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      </div>

      {/* Header with status and settings */}
      <header className="absolute top-0 left-0 right-0 z-10 p-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-medium tracking-wide text-foreground/90 text-mono">
            MANAS
          </h1>
          <StatusIndicator state={orbState} />
        </div>
        <button
          onClick={() => setShowSettings(true)}
          className="p-2 rounded-lg hover:bg-muted/30 transition-colors"
        >
          <Settings size={20} className="text-muted-foreground" />
        </button>
      </header>

      {/* Settings Panel */}
      <AnimatePresence>
        {showSettings && (
          <SettingsPanel
            isOpen={showSettings}
            onClose={() => setShowSettings(false)}
            onNavigate={handleNavigate}
          />
        )}
      </AnimatePresence>

      {/* Main content area */}
      <main className="relative flex flex-col items-center justify-center min-h-screen px-6">
        {/* Central orb */}
        <div className="relative flex items-center justify-center mb-16">
          <JarvisOrb
            state={orbState}
            context={isAnalysisMode ? 'analyze' : orbContext}
            audioLevel={audioLevel}
            isSwallowing={isSwallowing}
            uploadedFilesCount={pendingFileIds.length}
            onFileDrop={handleFilesUpload}
            onClick={handleOrbClick}
          />
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            multiple
            onChange={(e) => {
              if (e.target.files) {
                handleFilesUpload(Array.from(e.target.files));
              }
            }}
          />
        </div>

        {/* Live understanding panel */}
        <div className="absolute bottom-40 left-1/2 -translate-x-1/2">
          <LiveUnderstanding
            isVisible={showUnderstanding}
            intent={currentTranscript}
            entities={entities}
          />
        </div>
      </main>

      {/* Microphone button */}
      <div className="fixed bottom-12 left-1/2 -translate-x-1/2 z-20">
        <button
          onClick={handleMicClick}
          className={`relative flex items-center justify-center w-16 h-16 rounded-full glass-panel cursor-pointer select-none transition-all ${isRecording ? 'scale-110' : 'hover:scale-105'
            }`}
          style={{
            borderWidth: 2,
            borderColor: isRecording ? 'hsl(185, 85%, 50%)' : 'hsl(220, 20%, 18%)',
          }}
        >
          {/* Glow effect when active */}
          {isRecording && (
            <>
              <motion.div
                className="absolute inset-0 rounded-full"
                style={{
                  background: 'radial-gradient(circle, hsl(185, 85%, 50% / 0.3) 0%, transparent 70%)',
                  filter: 'blur(10px)',
                }}
                animate={{
                  scale: [1, 1.5, 1],
                  opacity: [0.5, 0.8, 0.5],
                }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
              />
              <motion.div
                className="absolute inset-0 rounded-full"
                style={{
                  boxShadow: '0 0 30px hsl(185, 85%, 50% / 0.5), 0 0 60px hsl(185, 85%, 50% / 0.3)',
                }}
                animate={{
                  opacity: [0.6, 1, 0.6],
                }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
              />
            </>
          )}

          {/* Microphone icon */}
          <motion.div
            style={{
              color: isRecording ? 'hsl(185, 85%, 50%)' : 'hsl(210, 20%, 98%)',
            }}
          >
            <Mic size={24} />
          </motion.div>
        </button>
      </div>

      {/* Collapsible Text Input Panel (bottom-right) */}
      <div className="fixed bottom-12 right-6 z-20">
        {!isTextPanelOpen ? (
          <button
            onClick={() => setIsTextPanelOpen(true)}
            className="flex items-center justify-center w-12 h-12 rounded-full glass-panel hover:scale-105 transition-all"
            style={{
              borderWidth: 2,
              borderColor: 'hsl(220, 20%, 18%)',
            }}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="M6 8h.01" />
              <path d="M10 8h.01" />
              <path d="M14 8h.01" />
              <path d="M18 8h.01" />
              <path d="M8 12h.01" />
              <path d="M12 12h.01" />
              <path d="M16 12h.01" />
              <path d="M7 16h10" />
            </svg>
          </button>
        ) : (
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass-panel p-4 rounded-2xl w-80"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-muted-foreground font-medium">TYPE COMMAND</span>
              <button
                onClick={() => setIsTextPanelOpen(false)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <form onSubmit={(e) => { handleTextSubmit(e); setIsTextPanelOpen(false); }}>
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Type your command..."
                disabled={isRecording}
                autoFocus
                className="w-full px-4 py-3 rounded-xl bg-background/50 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 disabled:opacity-50"
              />
              <div className="mt-2 text-xs text-muted-foreground/70">
                Press Enter to send
              </div>
            </form>
          </motion.div>
        )}
      </div>

      {/* Left side area for citations */}
      <div className="fixed left-6 top-32 bottom-32 z-30 pointer-events-none flex flex-col items-start gap-6 w-full max-w-sm">
        <div className="w-full flex flex-col items-start gap-4 pointer-events-auto">
          <AnimatePresence mode="popLayout">
            {citationCards.map((card) => (
              <AcknowledgmentCard
                key={card.id}
                type={card.type}
                title={card.title}
                data={card.data}
                isCitation={true}
                onDismiss={() => removeCitation(card.id)}
              />
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Prominent response area - repositioned to side */}
      <div className="fixed right-6 top-32 bottom-32 z-30 pointer-events-none flex flex-col items-end gap-6 w-full max-w-xl">
        <div className="w-full flex flex-col items-end gap-6 pointer-events-auto">
          <AnimatePresence mode="popLayout">
            {cards.map((card, index) => (
              <AcknowledgmentCard
                key={card.id}
                type={card.type}
                title={card.title}
                subtitle={card.subtitle}
                data={card.data}
                index={index}
                onDismiss={() => removeCard(card.id)}
              />
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Context indicator */}
      <motion.div
        className="fixed bottom-6 left-6 text-[10px] tracking-widest text-muted-foreground/50 text-mono flex items-center gap-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
      >
        <div className="w-1.5 h-1.5 rounded-full bg-primary/30 animate-pulse" />
        INTENT: {currentIntent || 'IDLE'} | CONTEXT: {orbContext.toUpperCase()}
      </motion.div>
    </div>
  );
}
