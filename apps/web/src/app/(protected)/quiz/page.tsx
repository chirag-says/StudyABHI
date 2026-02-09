'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Brain, Clock, Trophy, ChevronRight, Loader2, Sparkles, FileText, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import api from '@/services/api';

interface Quiz {
    id: string;
    title: string;
    description?: string;
    question_count: number;
    time_limit_minutes?: number;
    difficulty: 'easy' | 'medium' | 'hard';
    topic_name?: string;
    last_attempt_score?: number;
}

interface QuizHistory {
    attempt_id: string;
    quiz_id: string;
    quiz_title: string;
    score_percentage: number;
    completed_at: string;
}

export default function QuizIndexPage() {
    const [availableQuizzes, setAvailableQuizzes] = useState<Quiz[]>([]);
    const [recentAttempts, setRecentAttempts] = useState<QuizHistory[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchQuizzes();
    }, []);

    const fetchQuizzes = async () => {
        try {
            const [quizzesRes, historyRes] = await Promise.all([
                api.get<{ quizzes: Quiz[] }>('/quiz').catch(() => ({ data: { quizzes: [] } })),
                api.get<{ attempts: QuizHistory[] }>('/quiz/history').catch(() => ({ data: { attempts: [] } })),
            ]);
            setAvailableQuizzes(quizzesRes.data.quizzes || []);
            setRecentAttempts(historyRes.data.attempts || []);
        } catch (error) {
            console.error('Failed to fetch quizzes:', error);
        } finally {
            setLoading(false);
        }
    };

    const getDifficultyColor = (difficulty: string) => {
        switch (difficulty) {
            case 'easy': return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
            case 'medium': return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
            case 'hard': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
            default: return 'bg-muted';
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-IN', {
            day: 'numeric',
            month: 'short',
        });
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 p-6 lg:p-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold">Quizzes</h1>
                <p className="text-muted-foreground mt-1">Test your knowledge with AI-generated quizzes</p>
            </div>

            <div className="grid lg:grid-cols-3 gap-8">
                {/* Main Content */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Generate Quiz CTA */}
                    <div className="bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/20 rounded-xl p-6">
                        <div className="flex items-start gap-4">
                            <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center flex-shrink-0">
                                <Sparkles className="w-6 h-6 text-primary" />
                            </div>
                            <div className="flex-1">
                                <h2 className="text-xl font-semibold">Generate a Custom Quiz</h2>
                                <p className="text-muted-foreground mt-1">
                                    Upload a PDF and our AI will create quiz questions based on the content
                                </p>
                                <Button className="mt-4" asChild>
                                    <Link href="/upload">
                                        <Plus className="w-4 h-4 mr-2" />
                                        Upload PDF to Generate Quiz
                                    </Link>
                                </Button>
                            </div>
                        </div>
                    </div>

                    {/* Available Quizzes */}
                    <section>
                        <h2 className="text-xl font-semibold mb-4">Available Quizzes</h2>
                        {availableQuizzes.length > 0 ? (
                            <div className="grid md:grid-cols-2 gap-4">
                                {availableQuizzes.map((quiz) => (
                                    <Link
                                        key={quiz.id}
                                        href={`/quiz/${quiz.id}`}
                                        className="group block bg-card border rounded-xl p-5 hover:shadow-lg transition-all"
                                    >
                                        <div className="flex items-start justify-between mb-3">
                                            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                                                <Brain className="w-5 h-5 text-primary" />
                                            </div>
                                            <span className={`text-xs px-2 py-1 rounded-full ${getDifficultyColor(quiz.difficulty)}`}>
                                                {quiz.difficulty}
                                            </span>
                                        </div>
                                        <h3 className="font-semibold group-hover:text-primary transition-colors">
                                            {quiz.title}
                                        </h3>
                                        {quiz.description && (
                                            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                                                {quiz.description}
                                            </p>
                                        )}
                                        <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
                                            <span className="flex items-center gap-1">
                                                <FileText className="w-4 h-4" />
                                                {quiz.question_count} questions
                                            </span>
                                            {quiz.time_limit_minutes && (
                                                <span className="flex items-center gap-1">
                                                    <Clock className="w-4 h-4" />
                                                    {quiz.time_limit_minutes}m
                                                </span>
                                            )}
                                        </div>
                                        {quiz.last_attempt_score !== undefined && (
                                            <div className="mt-3 pt-3 border-t">
                                                <span className="text-sm">
                                                    Last score: <strong className="text-primary">{quiz.last_attempt_score}%</strong>
                                                </span>
                                            </div>
                                        )}
                                    </Link>
                                ))}
                            </div>
                        ) : (
                            <div className="bg-card border rounded-xl p-8 text-center">
                                <Brain className="w-12 h-12 mx-auto text-muted-foreground/50" />
                                <p className="mt-4 text-muted-foreground">No quizzes available yet</p>
                                <p className="text-sm text-muted-foreground">Upload a PDF to generate your first quiz</p>
                            </div>
                        )}
                    </section>
                </div>

                {/* Sidebar - Recent Attempts */}
                <div>
                    <h2 className="text-xl font-semibold mb-4">Recent Attempts</h2>
                    <div className="bg-card border rounded-xl overflow-hidden">
                        {recentAttempts.length > 0 ? (
                            <div className="divide-y">
                                {recentAttempts.slice(0, 5).map((attempt) => (
                                    <Link
                                        key={attempt.attempt_id}
                                        href={`/quiz/result/${attempt.attempt_id}`}
                                        className="flex items-center gap-3 p-4 hover:bg-muted transition-colors"
                                    >
                                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${attempt.score_percentage >= 70
                                                ? 'bg-green-100 text-green-600'
                                                : 'bg-yellow-100 text-yellow-600'
                                            }`}>
                                            <Trophy className="w-5 h-5" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="font-medium truncate text-sm">{attempt.quiz_title}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {formatDate(attempt.completed_at)}
                                            </p>
                                        </div>
                                        <span className="font-bold text-primary">{attempt.score_percentage}%</span>
                                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                                    </Link>
                                ))}
                            </div>
                        ) : (
                            <div className="p-6 text-center text-muted-foreground text-sm">
                                No quiz attempts yet
                            </div>
                        )}
                    </div>

                    {/* Quick Stats */}
                    <div className="mt-6 bg-card border rounded-xl p-4 space-y-4">
                        <h3 className="font-semibold">Your Stats</h3>
                        <div className="grid grid-cols-2 gap-4 text-center">
                            <div className="p-3 bg-muted rounded-lg">
                                <p className="text-2xl font-bold text-primary">{recentAttempts.length}</p>
                                <p className="text-xs text-muted-foreground">Quizzes Taken</p>
                            </div>
                            <div className="p-3 bg-muted rounded-lg">
                                <p className="text-2xl font-bold text-primary">
                                    {recentAttempts.length > 0
                                        ? Math.round(recentAttempts.reduce((a, b) => a + b.score_percentage, 0) / recentAttempts.length)
                                        : 0}%
                                </p>
                                <p className="text-xs text-muted-foreground">Avg Score</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
