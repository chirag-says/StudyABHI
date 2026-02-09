'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Clock, ChevronLeft, ChevronRight, Flag, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import api, { getErrorMessage } from '@/services/api';
import { useParams, useRouter } from 'next/navigation';

interface Question {
    id: string;
    question_text: string;
    options: string[];
    question_type: string;
}

interface Quiz {
    id: string;
    title: string;
    description?: string;
    time_limit_minutes?: number;
    questions: Question[];
}

interface Answer {
    question_id: string;
    selected_option: number | null;
    flagged: boolean;
}

export default function QuizTakePage() {
    const params = useParams();
    const router = useRouter();
    const quizId = params?.id as string;

    const [quiz, setQuiz] = useState<Quiz | null>(null);
    const [attemptId, setAttemptId] = useState<string | null>(null);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [answers, setAnswers] = useState<Map<string, Answer>>(new Map());
    const [timeRemaining, setTimeRemaining] = useState<number | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);

    // Fetch quiz and start attempt
    useEffect(() => {
        if (quizId) {
            startQuiz();
        }
    }, [quizId]);

    // Timer
    useEffect(() => {
        if (timeRemaining === null || timeRemaining <= 0) return;

        const timer = setInterval(() => {
            setTimeRemaining(prev => {
                if (prev === null || prev <= 1) {
                    // Auto-submit when time runs out
                    handleSubmit();
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => clearInterval(timer);
    }, [timeRemaining]);

    const startQuiz = async () => {
        try {
            // Fetch quiz
            const quizResponse = await api.get<Quiz>(`/quiz/${quizId}`);
            setQuiz(quizResponse.data);

            // Start attempt
            const attemptResponse = await api.post<{ attempt_id: string }>(`/quiz/${quizId}/start`);
            setAttemptId(attemptResponse.data.attempt_id);

            // Initialize answers
            const initialAnswers = new Map<string, Answer>();
            quizResponse.data.questions.forEach(q => {
                initialAnswers.set(q.id, {
                    question_id: q.id,
                    selected_option: null,
                    flagged: false,
                });
            });
            setAnswers(initialAnswers);

            // Set timer
            if (quizResponse.data.time_limit_minutes) {
                setTimeRemaining(quizResponse.data.time_limit_minutes * 60);
            }
        } catch (error) {
            console.error('Failed to start quiz:', error);
            alert(getErrorMessage(error));
        } finally {
            setIsLoading(false);
        }
    };

    const currentQuestion = quiz?.questions[currentIndex];
    const currentAnswer = currentQuestion ? answers.get(currentQuestion.id) : null;

    const selectOption = (optionIndex: number) => {
        if (!currentQuestion) return;

        setAnswers(prev => {
            const newAnswers = new Map(prev);
            newAnswers.set(currentQuestion.id, {
                ...prev.get(currentQuestion.id)!,
                selected_option: optionIndex,
            });
            return newAnswers;
        });

        // Save answer to backend
        saveAnswer(currentQuestion.id, optionIndex);
    };

    const saveAnswer = async (questionId: string, optionIndex: number) => {
        if (!attemptId) return;

        try {
            await api.post(`/quiz/attempts/${attemptId}/answer`, {
                question_id: questionId,
                selected_option: optionIndex,
            });
        } catch (error) {
            console.error('Failed to save answer:', error);
        }
    };

    const toggleFlag = () => {
        if (!currentQuestion) return;

        setAnswers(prev => {
            const newAnswers = new Map(prev);
            const current = prev.get(currentQuestion.id)!;
            newAnswers.set(currentQuestion.id, {
                ...current,
                flagged: !current.flagged,
            });
            return newAnswers;
        });
    };

    const goToQuestion = (index: number) => {
        if (index >= 0 && index < (quiz?.questions.length || 0)) {
            setCurrentIndex(index);
        }
    };

    const handleSubmit = async () => {
        if (!attemptId) return;

        setIsSubmitting(true);
        try {
            await api.post(`/quiz/attempts/${attemptId}/complete`);
            router.push(`/quiz/result/${attemptId}`);
        } catch (error) {
            alert(getErrorMessage(error));
            setIsSubmitting(false);
        }
    };

    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const getAnsweredCount = (): number => {
        let count = 0;
        answers.forEach(a => {
            if (a.selected_option !== null) count++;
        });
        return count;
    };

    const getFlaggedCount = (): number => {
        let count = 0;
        answers.forEach(a => {
            if (a.flagged) count++;
        });
        return count;
    };

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <div className="text-center">
                    <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto" />
                    <p className="mt-4 text-muted-foreground">Loading quiz...</p>
                </div>
            </div>
        );
    }

    if (!quiz || !currentQuestion) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <p className="text-muted-foreground">Quiz not found</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background flex flex-col">
            {/* Header */}
            <header className="border-b bg-card sticky top-0 z-10">
                <div className="container py-4">
                    <div className="flex items-center justify-between">
                        {/* Quiz Title */}
                        <div>
                            <h1 className="font-semibold">{quiz.title}</h1>
                            <p className="text-sm text-muted-foreground">
                                Question {currentIndex + 1} of {quiz.questions.length}
                            </p>
                        </div>

                        {/* Timer */}
                        {timeRemaining !== null && (
                            <div className={`
                flex items-center gap-2 px-4 py-2 rounded-full font-mono text-lg
                ${timeRemaining < 60 ? 'bg-destructive/10 text-destructive animate-pulse' : 'bg-muted'}
              `}>
                                <Clock className="w-5 h-5" />
                                {formatTime(timeRemaining)}
                            </div>
                        )}

                        {/* Submit Button */}
                        <Button onClick={() => setShowConfirm(true)} variant="outline">
                            Submit Quiz
                        </Button>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 container py-8">
                <div className="max-w-3xl mx-auto">
                    {/* Question Card */}
                    <div className="bg-card border rounded-2xl p-6 mb-6">
                        {/* Question Number & Flag */}
                        <div className="flex items-center justify-between mb-4">
                            <span className="bg-primary/10 text-primary px-3 py-1 rounded-full text-sm font-medium">
                                Q{currentIndex + 1}
                            </span>
                            <button
                                onClick={toggleFlag}
                                className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm transition-colors
                  ${currentAnswer?.flagged
                                        ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                                        : 'hover:bg-muted'
                                    }
                `}
                            >
                                <Flag className="w-4 h-4" />
                                {currentAnswer?.flagged ? 'Flagged' : 'Flag for review'}
                            </button>
                        </div>

                        {/* Question Text */}
                        <h2 className="text-xl font-medium mb-6">{currentQuestion.question_text}</h2>

                        {/* Options */}
                        <div className="space-y-3">
                            {currentQuestion.options.map((option, index) => (
                                <button
                                    key={index}
                                    onClick={() => selectOption(index)}
                                    className={`
                    w-full text-left p-4 rounded-xl border-2 transition-all
                    ${currentAnswer?.selected_option === index
                                            ? 'border-primary bg-primary/5'
                                            : 'border-transparent bg-muted hover:border-primary/30'
                                        }
                  `}
                                >
                                    <div className="flex items-center gap-3">
                                        <span className={`
                      w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0
                      ${currentAnswer?.selected_option === index
                                                ? 'bg-primary text-primary-foreground'
                                                : 'bg-background border'
                                            }
                    `}>
                                            {String.fromCharCode(65 + index)}
                                        </span>
                                        <span>{option}</span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Navigation */}
                    <div className="flex items-center justify-between">
                        <Button
                            variant="outline"
                            onClick={() => goToQuestion(currentIndex - 1)}
                            disabled={currentIndex === 0}
                        >
                            <ChevronLeft className="w-4 h-4 mr-1" />
                            Previous
                        </Button>

                        {currentIndex === quiz.questions.length - 1 ? (
                            <Button onClick={() => setShowConfirm(true)}>
                                Finish Quiz
                            </Button>
                        ) : (
                            <Button onClick={() => goToQuestion(currentIndex + 1)}>
                                Next
                                <ChevronRight className="w-4 h-4 ml-1" />
                            </Button>
                        )}
                    </div>
                </div>
            </main>

            {/* Question Navigator */}
            <div className="border-t bg-card p-4">
                <div className="container">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-4 text-sm">
                            <span className="flex items-center gap-1">
                                <CheckCircle className="w-4 h-4 text-green-500" />
                                {getAnsweredCount()} answered
                            </span>
                            <span className="flex items-center gap-1">
                                <Flag className="w-4 h-4 text-yellow-500" />
                                {getFlaggedCount()} flagged
                            </span>
                        </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        {quiz.questions.map((q, index) => {
                            const answer = answers.get(q.id);
                            return (
                                <button
                                    key={q.id}
                                    onClick={() => goToQuestion(index)}
                                    className={`
                    w-10 h-10 rounded-lg text-sm font-medium transition-all
                    ${index === currentIndex ? 'ring-2 ring-primary ring-offset-2' : ''}
                    ${answer?.selected_option !== null
                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                            : 'bg-muted'
                                        }
                    ${answer?.flagged ? 'ring-2 ring-yellow-400' : ''}
                  `}
                                >
                                    {index + 1}
                                </button>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Confirm Submit Modal */}
            {showConfirm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-card rounded-2xl p-6 max-w-md w-full">
                        <h3 className="text-xl font-semibold mb-2">Submit Quiz?</h3>
                        <p className="text-muted-foreground mb-4">
                            You've answered {getAnsweredCount()} of {quiz.questions.length} questions.
                            {getFlaggedCount() > 0 && ` ${getFlaggedCount()} questions are flagged for review.`}
                        </p>

                        {getAnsweredCount() < quiz.questions.length && (
                            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 mb-4">
                                <div className="flex items-start gap-2">
                                    <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                                    <p className="text-sm text-yellow-800 dark:text-yellow-200">
                                        You have {quiz.questions.length - getAnsweredCount()} unanswered questions.
                                    </p>
                                </div>
                            </div>
                        )}

                        <div className="flex gap-3">
                            <Button
                                variant="outline"
                                onClick={() => setShowConfirm(false)}
                                className="flex-1"
                                disabled={isSubmitting}
                            >
                                Continue Quiz
                            </Button>
                            <Button
                                onClick={handleSubmit}
                                className="flex-1"
                                disabled={isSubmitting}
                            >
                                {isSubmitting ? (
                                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                ) : null}
                                Submit
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
