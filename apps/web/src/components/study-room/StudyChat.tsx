'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
    FileText,
    Send,
    Loader2,
    Sparkles,
    ThumbsUp,
    ThumbsDown,
    MessageSquare,
    X,
    Minimize2,
    Maximize2
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Button } from '@/components/ui/button';
import api, { getErrorMessage } from '@/services/api';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    isStreaming?: boolean;
}

interface StudyChatProps {
    documentId?: string;
    documentName?: string;
    minimized?: boolean;
    onMinimizeToggle?: () => void;
}

export function StudyChat({
    documentId,
    documentName,
    minimized = false,
    onMinimizeToggle
}: StudyChatProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Initialize with welcome message
    useEffect(() => {
        const welcomeMsg = documentId
            ? `I'm here to help you study! Ask me anything about your document.`
            : `Hello! I'm your AI study assistant. Select a study material or ask me general questions about UPSC preparation.`;

        setMessages([{
            id: 'welcome',
            role: 'assistant',
            content: welcomeMsg,
            timestamp: new Date()
        }]);
    }, [documentId]);

    // Auto-scroll
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = async () => {
        if (!inputValue.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: inputValue.trim(),
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setIsLoading(true);

        // Reset textarea
        if (inputRef.current) {
            inputRef.current.style.height = 'auto';
        }

        // Placeholder for response
        const assistantId = (Date.now() + 1).toString();
        setMessages(prev => [...prev, {
            id: assistantId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            isStreaming: true
        }]);

        try {
            let response;
            if (documentId) {
                response = await api.post<{ answer: string }>('/rag/query', {
                    question: userMessage.content,
                    document_ids: [documentId]
                });
            } else {
                response = await api.post<{ answer: string }>('/chat/general', {
                    question: userMessage.content
                });
            }

            setMessages(prev => prev.map(msg =>
                msg.id === assistantId
                    ? { ...msg, content: response.data.answer, isStreaming: false }
                    : msg
            ));
        } catch (error) {
            const errorMessage = getErrorMessage(error);
            setMessages(prev => prev.map(msg =>
                msg.id === assistantId
                    ? {
                        ...msg,
                        content: `I apologize, but I couldn't process your question. ${errorMessage}`,
                        isStreaming: false
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

    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInputValue(e.target.value);
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 100) + 'px';
    };

    const suggestedQueries = [
        "Explain the key concepts",
        "Give me practice questions",
        "Summarize this topic",
        "What are the important points?"
    ];

    if (minimized) {
        return (
            <button
                onClick={onMinimizeToggle}
                className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-gradient-to-r from-primary to-blue-600 text-white shadow-lg hover:shadow-xl transition-all flex items-center justify-center z-50"
            >
                <MessageSquare className="w-6 h-6" />
            </button>
        );
    }

    return (
        <div className="h-full flex flex-col bg-card rounded-xl border overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-primary/10 to-blue-500/10">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center">
                        <Sparkles className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h3 className="font-semibold">AI Study Assistant</h3>
                        <p className="text-xs text-muted-foreground">
                            {documentName || 'Ask me anything'}
                        </p>
                    </div>
                </div>
                {onMinimizeToggle && (
                    <Button variant="ghost" size="icon" onClick={onMinimizeToggle}>
                        <Minimize2 className="w-4 h-4" />
                    </Button>
                )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${message.role === 'user'
                                ? 'bg-primary text-primary-foreground rounded-br-md'
                                : 'bg-muted rounded-bl-md'
                            }`}>
                            {message.isStreaming ? (
                                <div className="flex items-center gap-2">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    <span className="text-sm">Thinking...</span>
                                </div>
                            ) : (
                                <div className="prose prose-sm dark:prose-invert max-w-none">
                                    <ReactMarkdown>{message.content}</ReactMarkdown>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Suggested Queries */}
            {messages.length <= 1 && (
                <div className="px-4 pb-2">
                    <p className="text-xs text-muted-foreground mb-2">Suggestions:</p>
                    <div className="flex flex-wrap gap-2">
                        {suggestedQueries.map((query, i) => (
                            <button
                                key={i}
                                onClick={() => setInputValue(query)}
                                className="text-xs px-3 py-1.5 rounded-full bg-muted hover:bg-primary/10 transition-colors"
                            >
                                {query}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Input */}
            <div className="p-3 border-t">
                <div className="flex items-end gap-2 bg-muted rounded-xl p-2">
                    <textarea
                        ref={inputRef}
                        value={inputValue}
                        onChange={handleInputChange}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask a question..."
                        className="flex-1 bg-transparent resize-none px-2 py-1 focus:outline-none max-h-24 text-sm"
                        rows={1}
                        disabled={isLoading}
                    />
                    <Button
                        onClick={sendMessage}
                        disabled={!inputValue.trim() || isLoading}
                        size="icon"
                        className="rounded-lg flex-shrink-0 h-8 w-8"
                    >
                        {isLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Send className="w-4 h-4" />
                        )}
                    </Button>
                </div>
            </div>
        </div>
    );
}
