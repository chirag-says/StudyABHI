    'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Sparkles, Loader2, FileText, Settings, BookOpen, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import api, { getErrorMessage } from '@/services/api';

interface DocumentInfo {
    id: string;
    filename: string;
    original_filename: string;
}

export default function GenerateQuizPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const documentId = searchParams?.get('document');

    const [document, setDocument] = useState<DocumentInfo | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [difficulty, setDifficulty] = useState('medium');
    const [questionCount, setQuestionCount] = useState(10);
    const [docLoading, setDocLoading] = useState(true);

    useEffect(() => {
        if (documentId) {
            fetchDocument();
        } else {
            setDocLoading(false);
        }
    }, [documentId]);

    const fetchDocument = async () => {
        try {
            const response = await api.get<DocumentInfo>(`/documents/${documentId}`);
            setDocument(response.data);
        } catch (error) {
            console.error('Failed to fetch document:', error);
        } finally {
            setDocLoading(false);
        }
    };

    const handleGenerate = async () => {
        if (!documentId) return;

        setIsLoading(true);
        try {
            const response = await api.post<{ id: string }>('/quiz/generate-from-document', {
                document_id: documentId,
                title: `Quiz: ${document?.original_filename || 'Study Material'}`,
                question_count: questionCount,
                difficulty: difficulty,
                time_limit_minutes: questionCount * 1.5, // 1.5 mins per question
            });

            // Redirect to the new quiz
            router.push(`/quiz/${response.data.id}`);
        } catch (error) {
            alert(getErrorMessage(error));
            setIsLoading(false);
        }
    };

    if (docLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    if (!documentId) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center p-6">
                    <AlertCircle className="w-10 h-10 text-destructive mx-auto mb-4" />
                    <h1 className="text-xl font-semibold mb-2">No Document Selected</h1>
                    <p className="text-muted-foreground mb-4">
                        Please select a document from your dashboard to generate a quiz.
                    </p>
                    <Button onClick={() => router.push('/dashboard')}>
                        Go to Dashboard
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background p-6 flex flex-col items-center justify-center">
            <div className="max-w-md w-full">
                <div className="text-center mb-8">
                    <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                        <Sparkles className="w-8 h-8 text-primary" />
                    </div>
                    <h1 className="text-3xl font-bold">Generate Quiz</h1>
                    <p className="text-muted-foreground mt-2">
                        Create a personalized quiz from your study material
                    </p>
                </div>

                <div className="bg-card border rounded-2xl p-6 shadow-sm">
                    {/* Document Info */}
                    <div className="flex items-center gap-3 p-3 bg-muted rounded-xl mb-6">
                        <div className="w-10 h-10 bg-background rounded-lg flex items-center justify-center border">
                            <FileText className="w-5 h-5 text-muted-foreground" />
                        </div>
                        <div className="min-w-0">
                            <p className="text-sm font-medium text-muted-foreground">Source Document</p>
                            <p className="font-medium truncate">{document?.original_filename || 'Unknown Document'}</p>
                        </div>
                    </div>

                    {/* Settings */}
                    <div className="space-y-4 mb-6">
                        <div>
                            <label className="text-sm font-medium mb-1.5 block">Difficulty Level</label>
                            <div className="grid grid-cols-3 gap-2">
                                {['easy', 'medium', 'hard'].map((level) => (
                                    <button
                                        key={level}
                                        onClick={() => setDifficulty(level)}
                                        className={`
                                            py-2 px-3 rounded-lg text-sm font-medium capitalize border transition-all
                                            ${difficulty === level
                                                ? 'bg-primary text-primary-foreground border-primary'
                                                : 'bg-background hover:bg-muted'
                                            }
                                        `}
                                    >
                                        {level}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <label className="text-sm font-medium mb-1.5 block">Number of Questions</label>
                            <div className="grid grid-cols-3 gap-2">
                                {[5, 10, 15].map((count) => (
                                    <button
                                        key={count}
                                        onClick={() => setQuestionCount(count)}
                                        className={`
                                            py-2 px-3 rounded-lg text-sm font-medium border transition-all
                                            ${questionCount === count
                                                ? 'bg-primary text-primary-foreground border-primary'
                                                : 'bg-background hover:bg-muted'
                                            }
                                        `}
                                    >
                                        {count} Questions
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <Button
                        onClick={handleGenerate}
                        className="w-full h-11 text-base"
                        disabled={isLoading}
                    >
                        {isLoading ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                Generating Quiz...
                            </>
                        ) : (
                            <>
                                <Sparkles className="w-4 h-4 mr-2" />
                                Generate Quiz Now
                            </>
                        )}
                    </Button>
                </div>

                <div className="mt-6 text-center">
                    <button
                        onClick={() => router.back()}
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                        Cancel and go back
                    </button>
                </div>
            </div>
        </div>
    );
}
