'use client';

import React, { useState, useEffect } from 'react';
import { Trophy, Target, TrendingUp, BookOpen, RotateCcw, ArrowRight, CheckCircle, XCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import api, { getErrorMessage } from '@/services/api';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';

interface QuizResult {
    attempt_id: string;
    quiz_id: string;
    quiz_title: string;
    total_questions: number;
    correct_answers: number;
    wrong_answers: number;
    skipped_questions: number;
    score_percentage: number;
    passed: boolean;
    time_spent_seconds?: number;
    topic_performance: TopicPerformance[];
    question_results: QuestionResult[];
}

interface TopicPerformance {
    topic_id: string;
    topic_name: string;
    correct: number;
    total: number;
    percentage: number;
    is_weak: boolean;
}

interface QuestionResult {
    question_id: string;
    question_text: string;
    options: string[];
    correct_option: number;
    selected_option: number | null;
    is_correct: boolean;
    explanation?: string;
}

export default function QuizResultPage() {
    const params = useParams();
    const router = useRouter();
    const attemptId = params?.attemptId as string;

    const [result, setResult] = useState<QuizResult | null>(null);
    const [showAnswers, setShowAnswers] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (attemptId) {
            fetchResult();
        }
    }, [attemptId]);

    const fetchResult = async () => {
        try {
            const response = await api.get<QuizResult>(`/quiz/attempts/${attemptId}/result`);
            setResult(response.data);
        } catch (error) {
            console.error('Failed to fetch result:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}m ${secs}s`;
    };

    const getScoreColor = (percentage: number): string => {
        if (percentage >= 80) return 'text-green-600 dark:text-green-400';
        if (percentage >= 60) return 'text-yellow-600 dark:text-yellow-400';
        return 'text-red-600 dark:text-red-400';
    };

    const getScoreBg = (percentage: number): string => {
        if (percentage >= 80) return 'from-green-500 to-emerald-600';
        if (percentage >= 60) return 'from-yellow-500 to-orange-500';
        return 'from-red-500 to-rose-600';
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <Loader2 className="w-10 h-10 animate-spin text-primary" />
            </div>
        );
    }

    if (!result) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <p className="text-muted-foreground">Result not found</p>
            </div>
        );
    }

    const weakTopics = result.topic_performance.filter(t => t.is_weak);

    return (
        <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
            {/* Hero Section */}
            <div className={`bg-gradient-to-br ${getScoreBg(result.score_percentage)} text-white py-16`}>
                <div className="container text-center">
                    {/* Trophy Icon */}
                    <div className="w-20 h-20 mx-auto mb-6 bg-white/20 rounded-full flex items-center justify-center backdrop-blur">
                        <Trophy className="w-10 h-10" />
                    </div>

                    {/* Score */}
                    <div className="mb-4">
                        <span className="text-6xl font-bold">{Math.round(result.score_percentage)}%</span>
                    </div>

                    {/* Status */}
                    <p className="text-xl mb-2">
                        {result.passed ? '🎉 Congratulations! You passed!' : '💪 Keep practicing!'}
                    </p>
                    <p className="opacity-80">
                        {result.correct_answers} of {result.total_questions} correct
                    </p>
                </div>
            </div>

            <div className="container py-8 -mt-8">
                {/* Stats Cards */}
                <div className="grid md:grid-cols-4 gap-4 mb-8">
                    <div className="bg-card border rounded-xl p-4 text-center">
                        <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
                        <p className="text-2xl font-bold text-green-600">{result.correct_answers}</p>
                        <p className="text-sm text-muted-foreground">Correct</p>
                    </div>
                    <div className="bg-card border rounded-xl p-4 text-center">
                        <XCircle className="w-8 h-8 mx-auto mb-2 text-red-500" />
                        <p className="text-2xl font-bold text-red-600">{result.wrong_answers}</p>
                        <p className="text-sm text-muted-foreground">Wrong</p>
                    </div>
                    <div className="bg-card border rounded-xl p-4 text-center">
                        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-yellow-500" />
                        <p className="text-2xl font-bold text-yellow-600">{result.skipped_questions}</p>
                        <p className="text-sm text-muted-foreground">Skipped</p>
                    </div>
                    <div className="bg-card border rounded-xl p-4 text-center">
                        <Target className="w-8 h-8 mx-auto mb-2 text-primary" />
                        <p className="text-2xl font-bold">{result.time_spent_seconds ? formatTime(result.time_spent_seconds) : '-'}</p>
                        <p className="text-sm text-muted-foreground">Time Spent</p>
                    </div>
                </div>

                {/* Topic Performance */}
                {result.topic_performance.length > 0 && (
                    <section className="bg-card border rounded-xl p-6 mb-8">
                        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-primary" />
                            Topic-wise Performance
                        </h2>
                        <div className="space-y-4">
                            {result.topic_performance.map((topic) => (
                                <div key={topic.topic_id}>
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="font-medium">{topic.topic_name}</span>
                                        <span className={`text-sm font-medium ${getScoreColor(topic.percentage)}`}>
                                            {topic.correct}/{topic.total} ({Math.round(topic.percentage)}%)
                                        </span>
                                    </div>
                                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                                        <div
                                            className={`h-full rounded-full transition-all duration-500 ${topic.percentage >= 80 ? 'bg-green-500' :
                                                topic.percentage >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                                                }`}
                                            style={{ width: `${topic.percentage}%` }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Weak Areas */}
                {weakTopics.length > 0 && (
                    <section className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 mb-8">
                        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2 text-red-800 dark:text-red-200">
                            <AlertTriangle className="w-5 h-5" />
                            Areas to Improve
                        </h2>
                        <div className="grid md:grid-cols-2 gap-4">
                            {weakTopics.map((topic) => (
                                <div
                                    key={topic.topic_id}
                                    className="flex items-center justify-between bg-white dark:bg-background/50 rounded-lg p-4"
                                >
                                    <div>
                                        <p className="font-medium">{topic.topic_name}</p>
                                        <p className="text-sm text-muted-foreground">
                                            Score: {Math.round(topic.percentage)}%
                                        </p>
                                    </div>
                                    <Button size="sm" variant="outline" asChild>
                                        <Link href={`/study?topic=${topic.topic_id}`}>
                                            Revise
                                            <BookOpen className="w-4 h-4 ml-1" />
                                        </Link>
                                    </Button>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Question Review Toggle */}
                <section className="bg-card border rounded-xl p-6 mb-8">
                    <Button
                        variant="outline"
                        onClick={() => setShowAnswers(!showAnswers)}
                        className="w-full"
                    >
                        {showAnswers ? 'Hide' : 'Review'} Answers
                    </Button>

                    {showAnswers && (
                        <div className="mt-6 space-y-6">
                            {result.question_results.map((q, index) => (
                                <div
                                    key={q.question_id}
                                    className={`p-4 rounded-xl border-2 ${q.is_correct ? 'border-green-200 bg-green-50/50 dark:bg-green-900/10' :
                                        q.selected_option === null ? 'border-yellow-200 bg-yellow-50/50 dark:bg-yellow-900/10' :
                                            'border-red-200 bg-red-50/50 dark:bg-red-900/10'
                                        }`}
                                >
                                    <div className="flex items-start gap-3">
                                        <span className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${q.is_correct ? 'bg-green-500' :
                                            q.selected_option === null ? 'bg-yellow-500' : 'bg-red-500'
                                            } text-white text-sm font-medium`}>
                                            {index + 1}
                                        </span>
                                        <div className="flex-1">
                                            <p className="font-medium mb-3">{q.question_text}</p>

                                            <div className="space-y-2">
                                                {q.options.map((option, optIndex) => (
                                                    <div
                                                        key={optIndex}
                                                        className={`p-3 rounded-lg border ${optIndex === q.correct_option
                                                            ? 'border-green-500 bg-green-100 dark:bg-green-900/30'
                                                            : optIndex === q.selected_option && !q.is_correct
                                                                ? 'border-red-500 bg-red-100 dark:bg-red-900/30'
                                                                : 'border-transparent bg-muted/50'
                                                            }`}
                                                    >
                                                        <div className="flex items-center gap-2">
                                                            <span className="w-6 h-6 rounded-full bg-background border flex items-center justify-center text-xs">
                                                                {String.fromCharCode(65 + optIndex)}
                                                            </span>
                                                            <span>{option}</span>
                                                            {optIndex === q.correct_option && (
                                                                <CheckCircle className="w-4 h-4 text-green-600 ml-auto" />
                                                            )}
                                                            {optIndex === q.selected_option && optIndex !== q.correct_option && (
                                                                <XCircle className="w-4 h-4 text-red-600 ml-auto" />
                                                            )}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>

                                            {q.explanation && (
                                                <div className="mt-3 p-3 bg-muted rounded-lg">
                                                    <p className="text-sm font-medium mb-1">Explanation:</p>
                                                    <p className="text-sm text-muted-foreground">{q.explanation}</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </section>

                {/* Action Buttons */}
                <div className="flex flex-wrap gap-4 justify-center">
                    <Button variant="outline" size="lg" asChild>
                        <Link href={`/quiz/${result.quiz_id}`}>
                            <RotateCcw className="w-4 h-4 mr-2" />
                            Retake Quiz
                        </Link>
                    </Button>

                    {weakTopics.length > 0 && (
                        <Button size="lg" asChild>
                            <Link href={`/roadmap?add_topics=${weakTopics.map(t => t.topic_id).join(',')}`}>
                                Add to Roadmap
                                <ArrowRight className="w-4 h-4 ml-2" />
                            </Link>
                        </Button>
                    )}

                    <Button variant="secondary" size="lg" asChild>
                        <Link href="/dashboard">
                            Back to Dashboard
                        </Link>
                    </Button>
                </div>
            </div>
        </div>
    );
}
