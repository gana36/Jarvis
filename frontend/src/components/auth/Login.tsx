import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, Lock, LogIn, UserPlus, AlertCircle } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { JarvisOrb } from '../JarvisOrb';

export function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isSignUp, setIsSignUp] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const { signIn, signUp, signInWithGoogle } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            if (isSignUp) {
                await signUp(email, password);
            } else {
                await signIn(email, password);
            }
            navigate('/');
        } catch (err: any) {
            setError(err.message || 'Authentication failed');
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleSignIn = async () => {
        setError('');
        setLoading(true);

        try {
            await signInWithGoogle();
            navigate('/');
        } catch (err: any) {
            setError(err.message || 'Google sign-in failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="relative h-screen w-full flex items-center justify-center overflow-hidden bg-[#02040a]">
            {/* Immersive Background Core */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-40">
                <JarvisOrb state="idle" context="default" audioLevel={0.15} />
                <div className="absolute w-[800px] h-[800px] bg-primary/5 rounded-full blur-[150px]" />
            </div>

            <div className="relative z-10 w-full max-w-md px-6 flex flex-col items-center">
                {/* Auth Card - Floating Focal Point */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className="glass-panel w-full p-8 rounded-[2.5rem] shadow-[0_0_100px_rgba(34,211,238,0.1)] border border-white/10"
                >
                    <div className="text-center mb-8">
                        <motion.h1
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.3 }}
                            className="text-3xl font-light tracking-[0.3em] text-white uppercase mb-1"
                        >
                            Manas
                        </motion.h1>
                        <span className="text-[9px] font-bold tracking-[0.5em] text-primary uppercase opacity-60">Neural Interface</span>
                    </div>

                    <div className="flex justify-between items-center mb-6 border-b border-white/5 pb-4">
                        <h2 className="text-lg font-medium text-foreground tracking-tight">
                            {isSignUp ? 'Create Identity' : 'Secure Access'}
                        </h2>
                        <div className="p-2 rounded-xl bg-primary/10 border border-primary/20">
                            {isSignUp ? <UserPlus size={16} className="text-primary" /> : <LogIn size={16} className="text-primary" />}
                        </div>
                    </div>

                    <AnimatePresence mode="wait">
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="mb-6 p-3 rounded-xl bg-destructive/10 border border-destructive/20 flex items-center gap-3 text-destructive-foreground overflow-hidden"
                            >
                                <AlertCircle size={14} className="text-red-400 flex-shrink-0" />
                                <p className="text-[11px] font-medium leading-tight">{error}</p>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-1.5">
                            <label className="text-[9px] font-bold tracking-widest text-muted-foreground uppercase px-1">Email Address</label>
                            <div className="relative group">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={14} />
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    className="w-full pl-11 pr-4 py-3 bg-white/[0.03] border border-white/10 rounded-2xl text-sm text-white placeholder-white/20 outline-none focus:border-primary/50 focus:bg-white/[0.05] transition-all"
                                    placeholder="name@example.com"
                                />
                            </div>
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-[9px] font-bold tracking-widest text-muted-foreground uppercase px-1">Password</label>
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={14} />
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    minLength={6}
                                    className="w-full pl-11 pr-4 py-3 bg-white/[0.03] border border-white/10 rounded-2xl text-sm text-white placeholder-white/20 outline-none focus:border-primary/50 focus:bg-white/[0.05] transition-all"
                                    placeholder="••••••••"
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3.5 bg-primary text-primary-foreground text-xs font-bold rounded-2xl tracking-widest uppercase hover:brightness-110 active:scale-[0.98] transition-all disabled:opacity-50 shadow-lg shadow-primary/20 mt-2"
                        >
                            {loading ? (
                                <motion.div
                                    animate={{ rotate: 360 }}
                                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                                    className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full mx-auto"
                                />
                            ) : (
                                isSignUp ? 'Initialize Link' : 'Authorize Signal'
                            )}
                        </button>
                    </form>

                    <div className="relative my-6">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-white/5"></div>
                        </div>
                        <div className="relative flex justify-center text-[8px] font-bold tracking-widest text-muted-foreground/40 uppercase">
                            <span className="px-3 bg-card/60 backdrop-blur-xl">OR</span>
                        </div>
                    </div>

                    <button
                        onClick={handleGoogleSignIn}
                        disabled={loading}
                        className="w-full py-3 rounded-2xl bg-white/[0.03] border border-white/10 flex items-center justify-center gap-3 hover:bg-white/[0.06] active:scale-[0.98] transition-all group"
                    >
                        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                            <path fill="#34A85 Green" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                        </svg>
                        <span className="text-[11px] font-semibold text-white/70 group-hover:text-white transition-colors">Continue with Nexus</span>
                    </button>

                    <div className="mt-6 text-center">
                        <button
                            onClick={() => {
                                setIsSignUp(!isSignUp);
                                setError('');
                            }}
                            className="text-[9px] font-bold tracking-widest text-primary/60 hover:text-primary transition-colors uppercase"
                        >
                            {isSignUp
                                ? 'Existing Identity? Sign In'
                                : 'New Link Required? Request Access'}
                        </button>
                    </div>
                </motion.div>

                <footer className="mt-6 text-[9px] font-bold tracking-[0.2em] text-muted-foreground/20 uppercase flex items-center gap-3">
                    <span>INTERFACE v2.5.0</span>
                    <span className="opacity-50">|</span>
                    <span>Classified Access</span>
                </footer>
            </div>
        </div>
    );
}
