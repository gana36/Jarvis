import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Home, AlertTriangle } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="relative min-h-screen w-full flex items-center justify-center overflow-hidden bg-[#02040a]">
      {/* Ambient Background Glows */}
      <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-destructive/10 blur-[120px]" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-primary/5 blur-[120px]" />

      <div className="relative z-10 text-center px-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="flex flex-col items-center gap-6"
        >
          <div className="relative">
            <div className="p-8 rounded-[2.5rem] bg-destructive/10 border border-destructive/20 relative z-10">
              <AlertTriangle size={64} className="text-destructive" />
            </div>
            <motion.div
              animate={{ opacity: [0.2, 0.4, 0.2] }}
              transition={{ duration: 3, repeat: Infinity }}
              className="absolute inset-0 rounded-full bg-destructive/20 blur-3xl -z-10"
            />
          </div>

          <div className="space-y-4">
            <h1 className="text-8xl font-light tracking-[0.3em] text-white/90">404</h1>
            <div className="space-y-2">
              <h2 className="text-2xl font-light text-foreground tracking-tight">Signal Lost</h2>
              <p className="text-sm text-muted-foreground max-w-xs mx-auto font-light leading-relaxed">
                The neural path you are attempting to access does not exist in the current interface.
              </p>
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="pt-8"
          >
            <Link
              to="/"
              className="group flex items-center gap-3 px-8 py-4 rounded-2xl bg-white/[0.03] border border-white/10 text-[10px] font-bold tracking-[0.3em] text-primary uppercase hover:bg-primary hover:text-primary-foreground transition-all active:scale-95"
            >
              <Home size={14} className="group-hover:scale-110 transition-transform" />
              Return to Interface
            </Link>
          </motion.div>
        </motion.div>
      </div>

      <footer className="absolute bottom-8 left-0 w-full text-center">
        <span className="text-[10px] font-bold tracking-[0.4em] text-muted-foreground/20 uppercase">
          Transmission Interrupted
        </span>
      </footer>
    </div>
  );
}
