'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, ThumbsUp, ThumbsDown, FileText, X, ChevronLeft, ChevronRight, Loader2, BookOpen, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Button } from '@/components/ui/button';
import api, { getErrorMessage } from '@/services/api';
import { useParams } from 'next/navigation';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    citations?: Citation[];
    timestamp: Date;
    isStreaming?: boolean;
}

interface Citation {
    page: number;
    text: string;
    chunk_id?: string;
}

interface DocumentInfo {
    id: string;
    filename: string;
    original_filename: string;
    page_count?: number;
    status: string;
}

export default function StudyPage() {
    const params = useParams();
    const documentId = params?.id as string;

    const [document, setDocument] = useState<DocumentInfo | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [docLoading, setDocLoading] = useState(true);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Fetch document info
    useEffect(() => {
        if (documentId) {
            fetchDocument();
        }
    }, [documentId]);

    const fetchDocument = async () => {
        try {
            const response = await api.get<DocumentInfo>(`/documents/${documentId}`);
            setDocument(response.data);

            // Add welcome message
            setMessages([{
                id: 'welcome',
                role: 'assistant',
                content: `I'm ready to help you study **${response.data.original_filename}**! Ask me anything about the content.`,
                timestamp: new Date(),
            }]);
        } catch (error) {
            console.error('Failed to fetch document:', error);
        } finally {
            setDocLoading(false);
        }
    };

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Auto-resize textarea
    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInputValue(e.target.value);
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
    };

    const sendMessage = async () => {
        if (!inputValue.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: inputValue.trim(),
            timestamp: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setIsLoading(true);

        // Reset textarea height
        if (inputRef.current) {
            inputRef.current.style.height = 'auto';
        }

        // Create placeholder for streaming
        const assistantId = (Date.now() + 1).toString();
        setMessages(prev => [...prev, {
            id: assistantId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            isStreaming: true,
        }]);

        try {
            const response = await api.post<{
                answer: string;
                sources: Citation[];
            }>('/rag/query', {
                question: userMessage.content,
                document_ids: [documentId],
            });

            // Update with actual response
            setMessages(prev => prev.map(msg =>
                msg.id === assistantId
                    ? {
                        ...msg,
                        content: response.data.answer,
                        citations: response.data.sources,
                        isStreaming: false,
                    }
                    : msg
            ));
        } catch (error) {
            const errorMessage = getErrorMessage(error);
            setMessages(prev => prev.map(msg =>
                msg.id === assistantId
                    ? {
                        ...msg,
                        content: `Sorry, I couldn't process your question. ${errorMessage}`,
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

    const submitFeedback = async (messageId: string, helpful: boolean) => {
        try {
            await api.post(`/feedback/ai-answer/${messageId}`, null, {
                params: { helpful }
            });
        } catch (error) {
            console.error('Failed to submit feedback:', error);
        }
    };

    const suggestedQuestions = [
        "Summarize the main topics",
        "What are the key points?",
        "Explain the first chapter",
        "Create a study plan for this",
    ];

    if (docLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="min-h-screen flex bg-background">
            {/* Sidebar - PDF Info */}
            <aside className={`
        ${sidebarOpen ? 'w-80' : 'w-0'} 
        border-r bg-card transition-all duration-300 overflow-hidden flex-shrink-0
      `}>
                <div className="p-4 h-full flex flex-col">
                    {/* Document Info */}
                    <div className="flex items-start gap-3 pb-4 border-b">
                        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                            <FileText className="w-5 h-5 text-primary" />
                        </div>
                        <div className="min-w-0">
                            <h2 className="font-semibold truncate">{document?.original_filename}</h2>
                            <p className="text-sm text-muted-foreground">
                                {document?.page_count || 'Multiple'} pages
                            </p>
                        </div>
                    </div>

                    {/* Quick Actions */}
                    <div className="py-4 space-y-2">
                        <Button variant="outline" className="w-full justify-start" asChild>
                            <a href={`/quiz/generate?document=${documentId}`}>
                                <Sparkles className="w-4 h-4 mr-2" />
                                Generate Quiz
                            </a>
                        </Button>
                        <Button variant="outline" className="w-full justify-start">
                            <BookOpen className="w-4 h-4 mr-2" />
                            View Contents
                        </Button>
                    </div>

                    {/* Suggested Questions */}
                    <div className="py-4 border-t flex-1">
                        <h3 className="text-sm font-medium text-muted-foreground mb-3">Try asking:</h3>
                        <div className="space-y-2">
                            {suggestedQuestions.map((q, i) => (
                                <button
                                    key={i}
                                    onClick={() => setInputValue(q)}
                                    className="w-full text-left text-sm p-2 rounded-lg hover:bg-muted transition-colors"
                                >
                                    "{q}"
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </aside>

            {/* Toggle Sidebar */}
            <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-card border rounded-r-lg p-2 hover:bg-muted"
                style={{ left: sidebarOpen ? '320px' : '0' }}
            >
                {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>

            {/* Main Chat Area */}
            <main className="flex-1 flex flex-col min-w-0">
                {/* Header */}
                <header className="border-b p-4 bg-background/95 backdrop-blur">
                    <div className="flex items-center gap-3">
                        <Link href="/upload" className="mr-2 text-muted-foreground hover:text-foreground">
                            <ChevronLeft className="w-6 h-6" />
                        </Link>
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center">
                            <Sparkles className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="font-semibold">AI Study Assistant</h1>
                            <p className="text-sm text-muted-foreground">Ask questions about your PDF</p>
                        </div>
                    </div>
                </header>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {messages.map((message) => (
                        <div
                            key={message.id}
                            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div className={`
                max-w-[80%] rounded-2xl px-4 py-3
                ${message.role === 'user'
                                    ? 'bg-primary text-primary-foreground rounded-br-md'
                                    : 'bg-muted rounded-bl-md'
                                }
              `}>
                                {/* Message Content */}
                                {message.isStreaming ? (
                                    <div className="flex items-center gap-2">
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span className="text-sm">Thinking...</span>
                                    </div>
                                ) : (
                                    <div className="prose prose-sm dark:prose-invert max-w-none">
                                        <ReactMarkdown
                                            components={{
                                                // Customize link rendering if needed
                                                a: ({ node, ...props }) => <a target="_blank" rel="noopener noreferrer" className="text-primary underline" {...props} />,
                                                // Add more custom parsers if needed
                                            }}
                                        >
                                            {message.content}
                                        </ReactMarkdown>
                                    </div>
                                )}

                                {/* Citations */}
                                {message.citations && message.citations.length > 0 && (
                                    <div className="mt-3 pt-3 border-t border-muted-foreground/20">
                                        <p className="text-xs font-medium mb-2 opacity-70">📖 Sources:</p>
                                        <div className="space-y-1">
                                            {message.citations.slice(0, 3).map((citation, i) => (
                                                <div
                                                    key={i}
                                                    className="text-xs bg-background/50 rounded px-2 py-1"
                                                >
                                                    <span className="font-medium">Page {citation.page}:</span>{' '}
                                                    <span className="opacity-80">{citation.text.slice(0, 100)}...</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Feedback */}
                                {message.role === 'assistant' && !message.isStreaming && message.id !== 'welcome' && (
                                    <div className="mt-3 pt-2 border-t border-muted-foreground/20 flex items-center gap-2">
                                        <span className="text-xs opacity-60">Helpful?</span>
                                        <button
                                            onClick={() => submitFeedback(message.id, true)}
                                            className="p-1 rounded hover:bg-background/50 transition-colors"
                                        >
                                            <ThumbsUp className="w-3 h-3" />
                                        </button>
                                        <button
                                            onClick={() => submitFeedback(message.id, false)}
                                            className="p-1 rounded hover:bg-background/50 transition-colors"
                                        >
                                            <ThumbsDown className="w-3 h-3" />
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="border-t p-4 bg-background">
                    <div className="max-w-4xl mx-auto">
                        <div className="relative flex items-end gap-2 bg-muted rounded-2xl p-2">
                            <textarea
                                ref={inputRef}
                                value={inputValue}
                                onChange={handleInputChange}
                                onKeyDown={handleKeyDown}
                                placeholder="Ask about your study material..."
                                className="flex-1 bg-transparent resize-none px-3 py-2 focus:outline-none max-h-32"
                                rows={1}
                                disabled={isLoading}
                            />
                            <Button
                                onClick={sendMessage}
                                disabled={!inputValue.trim() || isLoading}
                                size="icon"
                                className="rounded-xl flex-shrink-0"
                            >
                                {isLoading ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Send className="w-4 h-4" />
                                )}
                            </Button>
                        </div>
                        <p className="text-xs text-center text-muted-foreground mt-2">
                            Press Enter to send • Shift+Enter for new line
                        </p>
                    </div>
                </div>
            </main>
        </div>
    );
}
