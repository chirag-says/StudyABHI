'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Send, Loader2, Bot, BookOpen, MessageSquare, Lightbulb } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { Button } from '@/components/ui/button';
import api, { getErrorMessage } from '@/services/api';
import { useAuthStore } from '@/stores/auth-store';

/**
 * Fix common LLM markdown artifacts before rendering:
 * - Unclosed **bold** markers (odd count per line → remove dangling opener)
 * - Trailing ** with no opening pair
 */
function sanitizeMarkdown(text: string): string {
    return text.split('\n').map(line => {
        const count = (line.match(/\*\*/g) || []).length;
        if (count % 2 !== 0) {
            // Remove the lone ** (typically at start: "**Some text.")
            return line.replace(/\*\*/, '');
        }
        return line;
    }).join('\n');
}


interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    isStreaming?: boolean;
}

const SUGGESTED_QUESTIONS = [
    'What are the Fundamental Rights in the Indian Constitution?',
    'Explain the Directive Principles of State Policy',
    'What is the significance of the Preamble?',
    'Describe the powers of the President of India',
    'What are the key features of Indian Federalism?',
    'Explain the role of UPSC in civil services recruitment',
];

const MOTIVATIONAL_QUOTES = [
    { quote: "You have a right to perform your prescribed duty, but you are not entitled to the fruits of action.", author: "Lord Krishna (Bhagavad Gita 2.47)" },
    { quote: "For him who has conquered the mind, the mind is the best of friends; but for one who has failed to do so, his mind will remain the greatest enemy.", author: "Lord Krishna (Bhagavad Gita 6.6)" },
    { quote: "Perform your duty equipoised, O Arjuna, abandoning all attachment to success or failure. Such equanimity is called yoga.", author: "Lord Krishna (Bhagavad Gita 2.48)" },
    { quote: "No one who does good work will ever come to a bad end, either here or in the world to come.", author: "Lord Krishna (Bhagavad Gita 6.40)" },
    { quote: "As the ignorant perform their duties with attachment to results, the learned may similarly act, but without attachment, for the sake of leading people on the right path.", author: "Lord Krishna (Bhagavad Gita 3.25)" },
];

export default function ChatPage() {
    const { user } = useAuthStore();
    const searchParams = useSearchParams();
    const firstName = user?.full_name?.split(' ')[0] || 'Abhitha';

    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionHistory, setSessionHistory] = useState<{ role: string; content: string }[]>([]);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    const randomQuote = MOTIVATIONAL_QUOTES[Math.floor(Math.random() * MOTIVATIONAL_QUOTES.length)];

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Auto-send question from roadmap ?q= param
    useEffect(() => {
        const q = searchParams?.get('q');
        if (q && messages.length === 0 && !isLoading) {
            setInputValue(q);
            // Small delay to let the page mount fully
            const timer = setTimeout(() => {
                sendMessage(q);
            }, 500);
            return () => clearTimeout(timer);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [searchParams]);

    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInputValue(e.target.value);
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
    };

    const sendMessage = async (questionOverride?: string) => {
        const question = questionOverride || inputValue.trim();
        if (!question || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: question,
            timestamp: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setIsLoading(true);

        if (inputRef.current) {
            inputRef.current.style.height = 'auto';
        }

        const assistantId = (Date.now() + 1).toString();
        setMessages(prev => [...prev, {
            id: assistantId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            isStreaming: true,
        }]);

        try {
            // Read token from Zustand persisted storage
            const authRaw = localStorage.getItem('upsc-auth-storage');
            const token = authRaw ? JSON.parse(authRaw)?.state?.accessToken : null;

            const response = await fetch('http://localhost:8000/api/v1/chat/general/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    question,
                    history: sessionHistory.slice(-10),
                    language: 'en',
                    stream: true,
                }),
            });

            if (!response.ok || !response.body) {
                throw new Error(`Server error: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullContent = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') break;

                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.content) {
                            fullContent += parsed.content;
                            // Update message in real-time as tokens arrive
                            setMessages(prev => prev.map(msg =>
                                msg.id === assistantId
                                    ? { ...msg, content: fullContent, isStreaming: true }
                                    : msg
                            ));
                            // Auto-scroll as content streams in
                            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
                        }
                        if (parsed.error) throw new Error(parsed.error);
                    } catch (_) {
                        // skip malformed chunks
                    }
                }
            }

            // Mark streaming complete
            setMessages(prev => prev.map(msg =>
                msg.id === assistantId
                    ? { ...msg, content: fullContent, isStreaming: false }
                    : msg
            ));

            // Update conversation history for multi-turn
            setSessionHistory(prev => [
                ...prev,
                { role: 'user', content: question },
                { role: 'assistant', content: fullContent },
            ]);

        } catch (error) {
            const errMsg = error instanceof Error ? error.message : 'Unknown error';
            setMessages(prev => prev.map(msg =>
                msg.id === assistantId
                    ? {
                        ...msg,
                        content: `I'm having trouble connecting right now. Please try again.\n\n*Error: ${errMsg}*`,
                        isStreaming: false,
                    }
                    : msg
            ));
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const isEmpty = messages.length === 0;

    return (
        <div className="flex flex-col h-screen bg-background">
            {/* Header */}
            <header className="border-b bg-background/95 backdrop-blur px-6 py-4 flex items-center gap-4 flex-shrink-0">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/25">
                    <Bot className="w-5 h-5 text-white" />
                </div>
                <div>
                    <h1 className="font-semibold text-lg">AI Study Chat</h1>
                    <p className="text-xs text-muted-foreground">Powered by Llama 3.1 · UPSC Expert</p>
                </div>
            </header>

            {/* Messages / Empty State */}
            <div className="flex-1 overflow-y-auto">
                {isEmpty ? (
                    /* Welcome Screen */
                    <div className="max-w-2xl mx-auto px-6 py-12 space-y-10">
                        {/* Greeting */}
                        <div className="text-center space-y-3">
                            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center mx-auto shadow-xl shadow-violet-500/30">
                                <Bot className="w-8 h-8 text-white" />
                            </div>
                            <h2 className="text-2xl font-bold">
                                Hi {firstName}!
                            </h2>
                            <p className="text-muted-foreground">
                                Ask me anything about UPSC preparation. I'm here to help you understand concepts, explain topics, and guide your study journey.
                            </p>
                        </div>

                        {/* Motivational Quote */}
                        <div className="bg-gradient-to-r from-violet-500/10 to-indigo-500/10 border border-violet-200 dark:border-violet-800 rounded-2xl p-5 text-center">
                            <p className="italic text-muted-foreground">"{randomQuote.quote}"</p>
                            <p className="text-sm font-medium mt-2 text-violet-600 dark:text-violet-400">— {randomQuote.author}</p>
                        </div>

                        {/* Suggested Questions */}
                        <div>
                            <div className="flex items-center gap-2 mb-4">
                                <Lightbulb className="w-4 h-4 text-amber-500" />
                                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Try asking</h3>
                            </div>
                            <div className="grid sm:grid-cols-2 gap-3">
                                {SUGGESTED_QUESTIONS.map((q, i) => (
                                    <button
                                        key={i}
                                        onClick={() => sendMessage(q)}
                                        className="text-left p-4 rounded-xl border bg-card hover:bg-muted hover:border-violet-300 dark:hover:border-violet-700 transition-all text-sm group"
                                    >
                                        <MessageSquare className="w-4 h-4 text-violet-500 mb-2 group-hover:scale-110 transition-transform" />
                                        {q}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Quick tip */}
                        <div className="flex items-start gap-3 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
                            <BookOpen className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-blue-700 dark:text-blue-400">
                                <strong>Tip:</strong> Upload a PDF from the sidebar and ask questions specifically about that document in the Study Materials page for citation-backed answers.
                            </div>
                        </div>
                    </div>
                ) : (
                    /* Chat Messages */
                    <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
                        {messages.map((message) => (
                            <div
                                key={message.id}
                                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} gap-3`}
                            >
                                {message.role === 'assistant' && (
                                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center flex-shrink-0 mt-1 shadow-md shadow-violet-500/20">
                                        <Bot className="w-4 h-4 text-white" />
                                    </div>
                                )}
                                <div className={`
                                    rounded-2xl px-4 py-3 shadow-sm
                                    ${message.role === 'user'
                                        ? 'max-w-[75%] bg-gradient-to-br from-violet-600 to-indigo-600 text-white rounded-br-md'
                                        : 'w-full bg-card border rounded-bl-md'
                                    }
                                `}>
                                    {message.isStreaming && !message.content ? (
                                        <div className="flex items-center gap-2 py-1">
                                            <div className="flex gap-1">
                                                <span className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                                <span className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                                <span className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                            </div>
                                            <span className="text-sm text-muted-foreground">Thinking...</span>
                                        </div>
                                    ) : (
                                        <div className={`prose prose-sm max-w-none ${
                                            message.role === 'user' ? 'prose-invert' : 'dark:prose-invert'
                                        }`}>
                                            <ReactMarkdown
                                                remarkPlugins={[remarkGfm]}
                                                rehypePlugins={[rehypeRaw]}
                                                components={{
                                                    a: ({ node, ...props }) => (
                                                        <a target="_blank" rel="noopener noreferrer" className="text-violet-500 underline" {...props} />
                                                    ),
                                                    table: ({ node, ...props }) => (
                                                        <div className="overflow-x-auto my-3 -mx-4">
                                                            <table className="w-full border-collapse text-xs" style={{minWidth:'600px'}} {...props} />
                                                        </div>
                                                    ),
                                                    thead: ({ node, ...props }) => (
                                                        <thead className="bg-violet-50 dark:bg-violet-950/40" {...props} />
                                                    ),
                                                    th: ({ node, ...props }) => (
                                                        <th className="border border-violet-200 dark:border-violet-800 px-3 py-2 text-left font-semibold text-violet-700 dark:text-violet-300 whitespace-nowrap" {...props} />
                                                    ),
                                                    td: ({ node, ...props }) => (
                                                        <td className="border border-slate-200 dark:border-slate-700 px-3 py-2 align-top min-w-[120px]" {...props} />
                                                    ),
                                                    tr: ({ node, ...props }) => (
                                                        <tr className="even:bg-slate-50 dark:even:bg-slate-900/30" {...props} />
                                                    ),
                                                    h1: ({ node, ...props }) => <h1 className="text-base font-bold mt-4 mb-2 text-violet-700 dark:text-violet-300" {...props} />,
                                                    h2: ({ node, ...props }) => <h2 className="text-sm font-bold mt-3 mb-1.5 text-violet-600 dark:text-violet-400 border-b border-violet-100 dark:border-violet-900 pb-1" {...props} />,
                                                    h3: ({ node, ...props }) => <h3 className="text-sm font-semibold mt-2 mb-1" {...props} />,
                                                    code: ({ node, inline, ...props }: any) => inline
                                                        ? <code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded text-xs font-mono" {...props} />
                                                        : <pre className="bg-slate-100 dark:bg-slate-800 p-3 rounded-lg overflow-x-auto my-2"><code className="text-xs font-mono" {...props} /></pre>,
                                                    blockquote: ({ node, ...props }) => (
                                                        <blockquote className="border-l-4 border-violet-400 pl-3 italic text-muted-foreground my-2" {...props} />
                                                    ),
                                                }}
                                            >
                                                {sanitizeMarkdown(message.content)}
                                            </ReactMarkdown>
                                        </div>
                                    )}
                                </div>
                                {message.role === 'user' && (
                                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-slate-600 to-slate-700 flex items-center justify-center flex-shrink-0 mt-1 text-white text-xs font-bold shadow-md">
                                        {firstName.charAt(0)}
                                    </div>
                                )}
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="border-t bg-background/95 backdrop-blur px-4 py-4 flex-shrink-0">
                <div className="max-w-3xl mx-auto">
                    <div className="relative flex items-end gap-3 bg-muted/60 border rounded-2xl p-2 focus-within:border-violet-400 focus-within:shadow-md focus-within:shadow-violet-500/10 transition-all">
                        <textarea
                            ref={inputRef}
                            value={inputValue}
                            onChange={handleInputChange}
                            onKeyDown={handleKeyDown}
                            placeholder={`Ask anything about UPSC, ${firstName}...`}
                            className="flex-1 bg-transparent resize-none px-3 py-2 focus:outline-none max-h-32 text-sm"
                            rows={1}
                            disabled={isLoading}
                        />
                        <Button
                            onClick={() => sendMessage()}
                            disabled={!inputValue.trim() || isLoading}
                            size="icon"
                            className="rounded-xl flex-shrink-0 bg-gradient-to-br from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 shadow-lg shadow-violet-500/30"
                        >
                            {isLoading ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Send className="w-4 h-4" />
                            )}
                        </Button>
                    </div>
                    <p className="text-xs text-center text-muted-foreground mt-2">
                        Enter to send · Shift+Enter for new line · Answers grounded in UPSC syllabus
                    </p>
                </div>
            </div>
        </div>
    );
}
