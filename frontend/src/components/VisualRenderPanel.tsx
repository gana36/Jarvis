import { motion, AnimatePresence } from 'framer-motion';
import { X, Copy, Check, Code } from 'lucide-react';
import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface VisualRenderPanelProps {
    isOpen: boolean;
    onClose: () => void;
    payload: string | null;
}

const MarkdownTable = ({ children }: { children: React.ReactNode }) => (
    <div className="my-8 overflow-x-auto rounded-2xl border border-white/10 bg-white/[0.03] shadow-inner">
        <table className="w-full text-sm text-left border-collapse min-w-[400px]">
            {children}
        </table>
    </div>
);

const CodeBlock = ({ inline, className, children, ...props }: { inline?: boolean, className?: string, children?: React.ReactNode }) => {
    const [copied, setCopied] = useState(false);
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';
    const content = String(children).replace(/\n$/, '');

    const handleCopy = () => {
        navigator.clipboard.writeText(content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    if (inline) {
        return (
            <code className="px-1.5 py-0.5 rounded bg-white/10 text-primary font-mono text-[11px]" {...props}>
                {children}
            </code>
        );
    }

    // Special handling for markdown blocks - render them as markdown!
    if (language === 'markdown') {
        return (
            <div className="my-4">
                <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={markdownComponents}
                >
                    {content}
                </ReactMarkdown>
            </div>
        );
    }

    return (
        <div className="relative my-8 group/code">
            <div className="absolute right-4 top-4 flex gap-2 opacity-0 group-hover/code:opacity-100 transition-opacity z-10">
                <button
                    onClick={handleCopy}
                    className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 transition-colors text-white/50 hover:text-white"
                    title="Copy code"
                >
                    {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                </button>
            </div>
            {language && (
                <div className="absolute left-4 top-0 -translate-y-1/2 px-2 py-0.5 rounded bg-primary/20 border border-primary/30 text-[10px] font-bold tracking-[0.2em] text-primary uppercase z-10">
                    {language}
                </div>
            )}
            <pre className="p-6 pt-10 rounded-2xl bg-black/40 border border-white/5 overflow-x-auto custom-scrollbar font-mono text-sm leading-relaxed text-indigo-100/90 selection:bg-primary/30 shadow-2xl">
                <code className={className} {...props}>
                    {children}
                </code>
            </pre>
        </div>
    );
};

const markdownComponents = {
    code: CodeBlock,
    h1: ({ children }: any) => <h1 className="text-2xl font-bold text-white mb-8 border-b border-white/10 pb-4 tracking-tight">{children}</h1>,
    h2: ({ children }: any) => <h2 className="text-xl font-bold text-white/90 mt-12 mb-6 flex items-center gap-3">
        <div className="w-1.5 h-7 bg-primary rounded-full shadow-[0_0_10px_rgba(var(--primary-rgb),0.5)]" />
        {children}
    </h2>,
    h3: ({ children }: any) => <h3 className="text-lg font-bold text-white/80 mt-8 mb-4">{children}</h3>,
    p: ({ children }: any) => <p className="text-foreground/80 leading-relaxed mb-6 font-medium">{children}</p>,
    ul: ({ children }: any) => <ul className="list-none space-y-3 mb-8 ml-1">{children}</ul>,
    li: ({ children }: any) => (
        <li className="flex gap-4 text-foreground/80 leading-relaxed">
            <div className="mt-2.5 w-2 h-2 rounded-full bg-primary/40 border border-primary/20 flex-shrink-0 animate-pulse" />
            <span>{children}</span>
        </li>
    ),
    table: MarkdownTable,
    thead: ({ children }: any) => <thead className="bg-white/5 text-primary/90 font-bold uppercase tracking-[0.15em] text-[10px]">{children}</thead>,
    th: ({ children }: any) => <th className="px-6 py-5 border-b border-white/10 first:rounded-tl-2xl last:rounded-tr-2xl">{children}</th>,
    td: ({ children }: any) => <td className="px-6 py-4 border-b border-white/5 text-foreground/75 font-medium">{children}</td>,
    blockquote: ({ children }: any) => (
        <blockquote className="border-l-4 border-primary/40 bg-primary/5 p-6 rounded-r-2xl my-8 italic text-foreground/90 leading-loose">
            {children}
        </blockquote>
    ),
    strong: ({ children }: any) => <strong className="text-white font-bold">{children}</strong>,
};

export const VisualRenderPanel = ({ isOpen, onClose, payload }: VisualRenderPanelProps) => {
    const [allCopied, setAllCopied] = useState(false);
    const [width, setWidth] = useState(() => {
        const saved = localStorage.getItem('manas-visual-panel-width');
        return saved ? parseInt(saved, 10) : 600;
    });
    const [isResizing, setIsResizing] = useState(false);
    const panelRef = useRef<HTMLDivElement>(null);

    const handleCopyAll = () => {
        if (payload) {
            navigator.clipboard.writeText(payload);
            setAllCopied(true);
            setTimeout(() => setAllCopied(false), 2000);
        }
    };

    const startResizing = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        setIsResizing(true);
    }, []);

    const stopResizing = useCallback(() => {
        setIsResizing(false);
    }, []);

    const resize = useCallback((e: MouseEvent) => {
        if (isResizing) {
            const newWidth = Math.max(320, Math.min(e.clientX, window.innerWidth - 100));
            setWidth(newWidth);
            localStorage.setItem('manas-visual-panel-width', newWidth.toString());
        }
    }, [isResizing]);

    useEffect(() => {
        window.addEventListener('mousemove', resize);
        window.addEventListener('mouseup', stopResizing);
        return () => {
            window.removeEventListener('mousemove', resize);
            window.removeEventListener('mouseup', stopResizing);
        };
    }, [resize, stopResizing]);

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop for mobile or for dismissal */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/40 backdrop-blur-md z-40 lg:hidden"
                    />

                    <motion.div
                        ref={panelRef}
                        initial={{ x: '-100%', opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        exit={{ x: '-100%', opacity: 0 }}
                        transition={{ type: 'spring', damping: 28, stiffness: 180 }}
                        style={{ width: width }}
                        className="fixed left-0 top-0 bottom-0 z-50 p-6 pointer-events-none"
                    >
                        <div className="h-full w-full glass-panel rounded-[2.5rem] shadow-[0_0_50px_rgba(0,0,0,0.5)] border-r border-white/10 flex flex-col pointer-events-auto overflow-hidden relative">
                            {/* Resize Handle */}
                            <div
                                onMouseDown={startResizing}
                                className={`absolute top-0 right-0 bottom-0 w-2 cursor-col-resize z-50 hover:bg-primary/20 transition-colors ${isResizing ? 'bg-primary/30' : ''}`}
                                title="Drag to resize"
                            />

                            {/* Ambient Glow */}
                            <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 blur-[100px] -translate-y-1/2 translate-x-1/2 rounded-full pointer-events-none" />
                            <div className="absolute bottom-0 left-0 w-64 h-64 bg-indigo-500/5 blur-[100px] translate-y-1/2 -translate-x-1/2 rounded-full pointer-events-none" />

                            {/* Header */}
                            <div className="p-8 border-b border-white/5 flex items-center justify-between relative z-10">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 rounded-2xl bg-primary/10 border border-primary/20 shadow-[0_0_20px_rgba(var(--primary-rgb),0.1)]">
                                        <Code size={22} className="text-primary" />
                                    </div>
                                    <div>
                                        <span className="text-[10px] font-bold tracking-[0.4em] text-primary/70 uppercase font-mono">
                                            Visual Intelligence
                                        </span>
                                        <h3 className="text-lg font-bold text-foreground/90 tracking-widest uppercase mt-0.5">
                                            Technical Protocol
                                        </h3>
                                    </div>
                                </div>
                                <button
                                    onClick={onClose}
                                    className="p-3 rounded-full hover:bg-white/10 transition-all text-muted-foreground hover:text-foreground active:scale-90 border border-transparent hover:border-white/10"
                                >
                                    <X size={20} />
                                </button>
                            </div>

                            {/* Content */}
                            <div className="flex-1 overflow-y-auto p-10 custom-scrollbar relative z-10">
                                <div className="max-w-none prose prose-invert">
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={markdownComponents}
                                    >
                                        {payload || ''}
                                    </ReactMarkdown>
                                </div>
                            </div>

                            {/* Footer */}
                            <div className="p-6 border-t border-white/5 bg-white/[0.03] flex justify-between items-center px-10 relative z-10">
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                    <span className="text-[10px] text-muted-foreground/50 font-mono tracking-widest uppercase">
                                        Rendering Active: High Fidelity
                                    </span>
                                </div>
                                <div className="flex gap-3">
                                    <button
                                        onClick={handleCopyAll}
                                        className="flex items-center gap-2.5 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition-all text-[10px] font-bold tracking-widest text-muted-foreground hover:text-foreground uppercase group"
                                    >
                                        {allCopied ? <Check size={14} className="text-green-400" /> : <Copy size={14} className="group-hover:scale-110 transition-transform" />}
                                        {allCopied ? 'Processed' : 'Copy Protocol'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
};
