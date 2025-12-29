import { motion } from 'framer-motion';

export type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking';
export type OrbContext = 'default' | 'morning' | 'focus' | 'weather' | 'memory' | 'analyze';

interface JarvisOrbProps {
  state: OrbState;
  context?: OrbContext;
  audioLevel?: number;
  isSwallowing?: boolean;
  uploadedFilesCount?: number;
  onFileDrop?: (files: File[]) => void;
  onClick?: () => void;
}

const contextColors = {
  default: { primary: '#22d3ee', secondary: '#06b6d4', tertiary: '#0891b2' },
  morning: { primary: '#38bdf8', secondary: '#0ea5e9', tertiary: '#0284c7' },
  focus: { primary: '#2dd4bf', secondary: '#14b8a6', tertiary: '#0d9488' },
  weather: { primary: '#60a5fa', secondary: '#3b82f6', tertiary: '#2563eb' },
  memory: { primary: '#a78bfa', secondary: '#8b5cf6', tertiary: '#7c3aed' },
  analyze: { primary: '#f59e0b', secondary: '#d97706', tertiary: '#b45309' },
};

export function JarvisOrb({
  state,
  context = 'default',
  audioLevel = 0,
  isSwallowing = false,
  uploadedFilesCount = 0,
  onFileDrop,
  onClick
}: JarvisOrbProps) {
  const colors = contextColors[context];

  return (
    <motion.div
      className="relative flex items-center justify-center cursor-pointer"
      style={{ width: 320, height: 320 }}
      onClick={onClick}
      onDragOver={(e) => {
        e.preventDefault();
        e.stopPropagation();
      }}
      onDrop={(e) => {
        e.preventDefault();
        e.stopPropagation();
        if (onFileDrop && e.dataTransfer.files.length > 0) {
          onFileDrop(Array.from(e.dataTransfer.files));
        }
      }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Outermost ambient glow */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: 480,
          height: 480,
          background: `radial-gradient(circle, ${colors.primary}20 0%, ${colors.secondary}10 40%, transparent 70%)`,
          filter: 'blur(20px)',
        }}
        animate={{
          scale: state === 'idle' ? [1, 1.1, 1] : state === 'speaking' ? [1, 1 + audioLevel * 0.2, 1] : 1.05,
          opacity: state === 'idle' ? [0.5, 0.8, 0.5] : 0.8,
        }}
        transition={{
          duration: state === 'idle' ? 5 : state === 'speaking' ? 0.12 : 2,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Secondary glow layer */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: 360,
          height: 360,
          background: `radial-gradient(circle, ${colors.primary}30 0%, ${colors.secondary}15 50%, transparent 75%)`,
          filter: 'blur(10px)',
        }}
        animate={{
          scale: state === 'idle' ? [1, 1.06, 1] : state === 'speaking' ? [1, 1 + audioLevel * 0.15, 1] : 1.03,
          opacity: state === 'idle' ? [0.6, 0.9, 0.6] : 0.9,
        }}
        transition={{
          duration: state === 'idle' ? 4 : state === 'speaking' ? 0.1 : 2,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Rotating outer ring - thinking state */}
      {state === 'thinking' && (
        <>
          <motion.div
            className="absolute rounded-full"
            style={{
              width: 280,
              height: 280,
              border: `2px dashed ${colors.primary}80`,
            }}
            animate={{ rotate: 360 }}
            transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
          />
          <motion.div
            className="absolute rounded-full"
            style={{
              width: 250,
              height: 250,
              border: `1.5px dashed ${colors.secondary}60`,
            }}
            animate={{ rotate: -360 }}
            transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
          />
          <motion.div
            className="absolute rounded-full"
            style={{
              width: 220,
              height: 220,
              border: `1px solid ${colors.tertiary}40`,
            }}
            animate={{ rotate: 360 }}
            transition={{ duration: 14, repeat: Infinity, ease: 'linear' }}
          />
        </>
      )}

      {/* Arc segments for thinking */}
      {state === 'thinking' && (
        <motion.svg
          className="absolute"
          style={{ width: 300, height: 300 }}
          viewBox="0 0 200 200"
          animate={{ rotate: 360 }}
          transition={{ duration: 12, repeat: Infinity, ease: 'linear' }}
        >
          {[0, 60, 120, 180, 240, 300].map((rotation, i) => (
            <motion.path
              key={i}
              d="M100,18 A82,82 0 0,1 150,30"
              fill="none"
              stroke={i % 2 === 0 ? colors.primary : colors.secondary}
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeOpacity={0.7}
              transform={`rotate(${rotation} 100 100)`}
              animate={{ strokeOpacity: [0.4, 0.9, 0.4] }}
              transition={{
                duration: 1.5,
                delay: i * 0.25,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          ))}
        </motion.svg>
      )}

      {/* Listening waveform rings */}
      {state === 'listening' && (
        <>
          {[0, 1, 2, 3, 4].map((i) => (
            <motion.div
              key={i}
              className="absolute rounded-full"
              style={{
                width: 160 + i * 40,
                height: 160 + i * 40,
                border: `2px solid ${colors.primary}`,
              }}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{
                opacity: [0.6, 0.2, 0],
                scale: [1, 1.4, 1.8],
              }}
              transition={{
                duration: 2.5,
                delay: i * 0.4,
                repeat: Infinity,
                ease: 'easeOut',
              }}
            />
          ))}
        </>
      )}

      {/* Speaking pulse rings */}
      {state === 'speaking' && (
        <>
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="absolute rounded-full"
              style={{
                width: 180 + i * 25,
                height: 180 + i * 25,
                background: `radial-gradient(circle, ${colors.primary}${Math.round(40 - i * 12).toString(16).padStart(2, '0')} 0%, transparent 60%)`,
              }}
              animate={{
                scale: [1, 1 + audioLevel * (0.3 - i * 0.08), 1],
                opacity: [0.5, 0.8, 0.5],
              }}
              transition={{
                duration: 0.15,
                delay: i * 0.03,
                repeat: Infinity,
                ease: 'easeOut',
              }}
            />
          ))}
        </>
      )}

      {/* Outer ring structure */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: 200,
          height: 200,
          background: `radial-gradient(circle, ${colors.primary}25 0%, ${colors.secondary}15 50%, transparent 100%)`,
          border: `1px solid ${colors.primary}40`,
          boxShadow: `inset 0 0 60px ${colors.primary}20, 0 0 50px ${colors.primary}20`,
        }}
        animate={{
          scale: state === 'speaking' ? [1, 1 + audioLevel * 0.08, 1] : 1,
        }}
        transition={{ duration: 0.1 }}
      />

      {/* Inner core structure */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: 170,
          height: 170,
          background: `radial-gradient(circle, ${colors.primary}35 0%, ${colors.secondary}25 50%, ${colors.tertiary}15 100%)`,
          border: `1px solid ${colors.primary}50`,
          boxShadow: `inset 0 0 50px ${colors.primary}30, 0 0 70px ${colors.primary}25`,
        }}
        animate={{
          scale: state === 'speaking' ? [1, 1 + audioLevel * 0.1, 1] : 1,
        }}
        transition={{ duration: 0.08 }}
      />

      {/* Core orb backdrop - solid base */}
      <div
        className="absolute rounded-full"
        style={{
          width: 144,
          height: 144,
          background: 'linear-gradient(145deg, hsl(220, 25%, 12%) 0%, hsl(220, 25%, 8%) 100%)',
          boxShadow: `0 0 80px ${colors.primary}40`,
        }}
      />

      {/* Core orb - the main visual element */}
      <motion.div
        className="relative rounded-full overflow-hidden"
        style={{
          width: 144,
          height: 144,
          background: `
            radial-gradient(circle at 30% 25%, ${colors.primary} 0%, transparent 40%),
            radial-gradient(circle at 70% 75%, ${colors.secondary}cc 0%, transparent 35%),
            radial-gradient(circle at 50% 50%, ${colors.primary}ee 0%, ${colors.secondary}aa 30%, ${colors.tertiary}88 55%, hsl(220, 25%, 15%) 100%)
          `,
          boxShadow: `
            0 0 100px ${colors.primary}90,
            0 0 180px ${colors.primary}50,
            0 0 280px ${colors.secondary}30,
            inset 0 0 80px ${colors.primary}60
          `,
          border: `2px solid ${colors.primary}90`,
        }}
        animate={{
          scale: isSwallowing
            ? [1, 1.2, 0.8, 1.1, 1]
            : state === 'idle'
              ? [1, 1.04, 1]
              : state === 'speaking'
                ? [1, 1 + audioLevel * 0.06, 1]
                : 1,
          rotate: isSwallowing ? [0, 15, -15, 10, -10, 0] : 0,
        }}
        transition={{
          duration: isSwallowing ? 0.6 : state === 'idle' ? 4 : 0.12,
          repeat: isSwallowing ? 0 : Infinity,
          ease: 'easeInOut',
        }}
      >
        {/* Specular highlight - top left */}
        <motion.div
          className="absolute rounded-full"
          style={{
            top: 12,
            left: 20,
            width: 80,
            height: 48,
            background: `radial-gradient(ellipse, ${colors.primary}60 0%, transparent 70%)`,
            filter: 'blur(6px)',
          }}
          animate={{
            opacity: [0.7, 1, 0.7],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />

        {/* Secondary highlight */}
        <motion.div
          className="absolute rounded-full"
          style={{
            bottom: 24,
            right: 16,
            width: 48,
            height: 32,
            background: `radial-gradient(ellipse, ${colors.secondary}40 0%, transparent 70%)`,
            filter: 'blur(4px)',
          }}
          animate={{
            opacity: [0.5, 0.8, 0.5],
          }}
          transition={{
            duration: 4,
            delay: 1,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />

        {/* Center bright point */}
        <motion.div
          className="absolute rounded-full"
          style={{
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: 32,
            height: 32,
            background: `radial-gradient(circle, white 0%, ${colors.primary} 50%, transparent 100%)`,
            boxShadow: `0 0 30px ${colors.primary}, 0 0 60px ${colors.primary}80`,
          }}
          animate={{
            scale: state === 'speaking' ? [1, 1 + audioLevel * 0.4, 1] : [1, 1.15, 1],
            opacity: state === 'speaking' ? [0.8, 1, 0.8] : [0.6, 0.85, 0.6],
          }}
          transition={{
            duration: state === 'speaking' ? 0.08 : 2.5,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />

        {/* Inner core pulse */}
        <motion.div
          className="absolute rounded-full"
          style={{
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: 12,
            height: 12,
            background: 'white',
            boxShadow: `0 0 15px white, 0 0 30px ${colors.primary}`,
          }}
          animate={{
            scale: state === 'speaking' ? [1, 1 + audioLevel * 0.5, 1] : [1, 1.3, 1],
            opacity: [0.9, 1, 0.9],
          }}
          transition={{
            duration: state === 'speaking' ? 0.06 : 1.5,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      </motion.div>

      {/* Floating particles around orb */}
      {state !== 'listening' && (
        <svg className="absolute pointer-events-none" style={{ width: 320, height: 320 }} viewBox="0 0 200 200">
          {[...Array(12)].map((_, i) => {
            const angle = (i / 12) * Math.PI * 2;
            const radius = 75 + (i % 3) * 8;
            const cx = 100 + Math.cos(angle) * radius;
            const cy = 100 + Math.sin(angle) * radius;
            return (
              <motion.circle
                key={i}
                cx={cx}
                cy={cy}
                fill={i % 2 === 0 ? colors.primary : colors.secondary}
                initial={{ opacity: 0.4, r: 2 + (i % 2) }}
                animate={{
                  opacity: [0.3, 0.9, 0.3],
                  r: i % 2 === 0 ? [2, 3, 2] : [3, 4, 3],
                }}
                transition={{
                  duration: 2.5 + (i % 3),
                  delay: i * 0.2,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
              />
            );
          })}
        </svg>
      )}
      {/* Uploaded files indicators - Orbiting dots */}
      {uploadedFilesCount > 0 && (
        <div className="absolute inset-0 pointer-events-none">
          {[...Array(uploadedFilesCount)].map((_, i) => (
            <motion.div
              key={`uploaded-${i}`}
              className="absolute rounded-full"
              style={{
                width: 8,
                height: 8,
                background: colors.primary,
                boxShadow: `0 0 10px ${colors.primary}`,
                left: '50%',
                top: '50%',
              }}
              animate={{
                x: [
                  Math.cos((i / uploadedFilesCount) * Math.PI * 2) * 110,
                  Math.cos((i / uploadedFilesCount) * Math.PI * 2 + Math.PI * 2) * 110
                ],
                y: [
                  Math.sin((i / uploadedFilesCount) * Math.PI * 2) * 110,
                  Math.sin((i / uploadedFilesCount) * Math.PI * 2 + Math.PI * 2) * 110
                ],
              }}
              transition={{
                duration: 10 + i * 2,
                repeat: Infinity,
                ease: 'linear',
              }}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}
