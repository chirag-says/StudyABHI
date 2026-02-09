'use client';

import React, { useState, useEffect } from 'react';
import {
    Brain,
    ChevronRight,
    Check,
    X,
    Trophy,
    RotateCcw,
    Loader2,
    Sparkles
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import api from '@/services/api';

interface QuizQuestion {
    id: string;
    question: string;
    options: string[];
    correct_answer: number;
    explanation?: string;
}

interface QuickQuizProps {
    documentId?: string;
    topicId?: string;
    questionsCount?: number;
}

export function QuickQuiz({ documentId, topicId, questionsCount = 5 }: QuickQuizProps) {
    const [questions, setQuestions] = useState<QuizQuestion[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
    const [showResult, setShowResult] = useState(false);
    const [score, setScore] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [isComplete, setIsComplete] = useState(false);
    const [answers, setAnswers] = useState<(number | null)[]>([]);

    const loadQuestions = async () => {
        setIsLoading(true);
        try {
            const params: any = { count: questionsCount };
            if (documentId) params.document_id = documentId;
            if (topicId) params.topic_id = topicId;

            const response = await api.get<{ questions: QuizQuestion[] }>('/quiz/quick', { params });
            setQuestions(response.data.questions);
            setAnswers(new Array(response.data.questions.length).fill(null));
        } catch (error) {
            console.error('Failed to load quiz:', error);
            // Use fallback questions for demo
            setQuestions(fallbackQuestions);
            setAnswers(new Array(fallbackQuestions.length).fill(null));
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadQuestions();
    }, [documentId, topicId]);

    const handleAnswer = (answerIndex: number) => {
        if (showResult) return;

        setSelectedAnswer(answerIndex);
        setShowResult(true);

        const newAnswers = [...answers];
        newAnswers[currentIndex] = answerIndex;
        setAnswers(newAnswers);

        if (answerIndex === questions[currentIndex].correct_answer) {
            setScore(prev => prev + 1);
        }
    };

    const nextQuestion = () => {
        if (currentIndex < questions.length - 1) {
            setCurrentIndex(prev => prev + 1);
            setSelectedAnswer(null);
            setShowResult(false);
        } else {
            setIsComplete(true);
        }
    };

    const restartQuiz = () => {
        setCurrentIndex(0);
        setSelectedAnswer(null);
        setShowResult(false);
        setScore(0);
        setIsComplete(false);
        setAnswers(new Array(questions.length).fill(null));
    };

    const regenerateQuiz = () => {
        restartQuiz();
        loadQuestions();
    };

    if (isLoading) {
        return (
            <div className="p-6 rounded-2xl bg-gradient-to-br from-card to-muted border text-center">
                <Loader2 className="w-8 h-8 mx-auto animate-spin text-primary mb-3" />
                <p className="text-muted-foreground">Generating quiz questions...</p>
            </div>
        );
    }

    if (questions.length === 0) {
        return (
            <div className="p-6 rounded-2xl bg-gradient-to-br from-card to-muted border text-center">
                <Brain className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
                <p className="text-muted-foreground mb-4">No quiz available for this content.</p>
                <Button onClick={loadQuestions} variant="outline">
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generate Quiz
                </Button>
            </div>
        );
    }

    if (isComplete) {
        const percentage = Math.round((score / questions.length) * 100);

        return (
            <div className="p-6 rounded-2xl bg-gradient-to-br from-card to-muted border">
                <div className="text-center">
                    <div className={`w-20 h-20 mx-auto rounded-full flex items-center justify-center mb-4 ${percentage >= 80 ? 'bg-green-500/20' :
                            percentage >= 60 ? 'bg-yellow-500/20' :
                                'bg-red-500/20'
                        }`}>
                        <Trophy className={`w-10 h-10 ${percentage >= 80 ? 'text-green-500' :
                                percentage >= 60 ? 'text-yellow-500' :
                                    'text-red-500'
                            }`} />
                    </div>

                    <h3 className="text-2xl font-bold mb-2">Quiz Complete!</h3>
                    <p className="text-muted-foreground mb-4">
                        You scored {score} out of {questions.length}
                    </p>

                    {/* Score Ring */}
                    <div className="relative w-32 h-32 mx-auto mb-6">
                        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                            <circle
                                cx="50"
                                cy="50"
                                r="40"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="10"
                                className="text-muted"
                            />
                            <circle
                                cx="50"
                                cy="50"
                                r="40"
                                fill="none"
                                stroke={percentage >= 80 ? '#22c55e' : percentage >= 60 ? '#eab308' : '#ef4444'}
                                strokeWidth="10"
                                strokeLinecap="round"
                                strokeDasharray={`${percentage * 2.51} 251`}
                            />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className="text-3xl font-bold">{percentage}%</span>
                        </div>
                    </div>

                    {/* Message based on score */}
                    <p className="text-lg mb-6">
                        {percentage >= 80 ? '🎉 Excellent work! You\'re mastering this topic!' :
                            percentage >= 60 ? '👍 Good job! Keep practicing to improve!' :
                                '💪 Keep studying! Review the material and try again.'}
                    </p>

                    {/* Answer Summary */}
                    <div className="flex justify-center gap-2 mb-6">
                        {answers.map((answer, i) => (
                            <div
                                key={i}
                                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${answer === questions[i].correct_answer
                                        ? 'bg-green-500 text-white'
                                        : 'bg-red-500 text-white'
                                    }`}
                            >
                                {i + 1}
                            </div>
                        ))}
                    </div>

                    <div className="flex gap-3 justify-center">
                        <Button onClick={restartQuiz} variant="outline">
                            <RotateCcw className="w-4 h-4 mr-2" />
                            Try Again
                        </Button>
                        <Button onClick={regenerateQuiz}>
                            <Sparkles className="w-4 h-4 mr-2" />
                            New Quiz
                        </Button>
                    </div>
                </div>
            </div>
        );
    }

    const currentQuestion = questions[currentIndex];

    return (
        <div className="p-6 rounded-2xl bg-gradient-to-br from-card to-muted border">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                    <Brain className="w-5 h-5 text-primary" />
                    <span className="font-semibold">Quick Quiz</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                        {currentIndex + 1} / {questions.length}
                    </span>
                    {/* Progress dots */}
                    <div className="flex gap-1">
                        {questions.map((_, i) => (
                            <div
                                key={i}
                                className={`w-2 h-2 rounded-full transition-colors ${i < currentIndex
                                        ? answers[i] === questions[i].correct_answer
                                            ? 'bg-green-500'
                                            : 'bg-red-500'
                                        : i === currentIndex
                                            ? 'bg-primary'
                                            : 'bg-muted'
                                    }`}
                            />
                        ))}
                    </div>
                </div>
            </div>

            {/* Question */}
            <div className="mb-6">
                <p className="text-lg font-medium">{currentQuestion.question}</p>
            </div>

            {/* Options */}
            <div className="space-y-3 mb-6">
                {currentQuestion.options.map((option, index) => {
                    const isSelected = selectedAnswer === index;
                    const isCorrect = index === currentQuestion.correct_answer;
                    const showCorrect = showResult && isCorrect;
                    const showWrong = showResult && isSelected && !isCorrect;

                    return (
                        <button
                            key={index}
                            onClick={() => handleAnswer(index)}
                            disabled={showResult}
                            className={`w-full p-4 rounded-xl text-left transition-all flex items-center gap-3 ${showCorrect
                                    ? 'bg-green-500/20 border-2 border-green-500'
                                    : showWrong
                                        ? 'bg-red-500/20 border-2 border-red-500'
                                        : isSelected
                                            ? 'bg-primary/20 border-2 border-primary'
                                            : 'bg-muted/50 border-2 border-transparent hover:bg-muted'
                                }`}
                        >
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${showCorrect
                                    ? 'bg-green-500 text-white'
                                    : showWrong
                                        ? 'bg-red-500 text-white'
                                        : 'bg-muted'
                                }`}>
                                {showCorrect ? <Check className="w-4 h-4" /> :
                                    showWrong ? <X className="w-4 h-4" /> :
                                        String.fromCharCode(65 + index)}
                            </div>
                            <span className="flex-1">{option}</span>
                        </button>
                    );
                })}
            </div>

            {/* Explanation */}
            {showResult && currentQuestion.explanation && (
                <div className="p-4 rounded-lg bg-primary/5 border border-primary/20 mb-4">
                    <p className="text-sm">
                        <span className="font-medium">Explanation:</span> {currentQuestion.explanation}
                    </p>
                </div>
            )}

            {/* Next Button */}
            {showResult && (
                <Button onClick={nextQuestion} className="w-full">
                    {currentIndex < questions.length - 1 ? (
                        <>
                            Next Question
                            <ChevronRight className="w-4 h-4 ml-2" />
                        </>
                    ) : (
                        <>
                            See Results
                            <Trophy className="w-4 h-4 ml-2" />
                        </>
                    )}
                </Button>
            )}
        </div>
    );
}

// Fallback questions for demo
const fallbackQuestions: QuizQuestion[] = [
    {
        id: '1',
        question: 'What is the primary function of the Parliament in India?',
        options: [
            'To enforce laws',
            'To make laws',
            'To interpret laws',
            'To implement policies'
        ],
        correct_answer: 1,
        explanation: 'The Parliament is the supreme legislative body of India, and its primary function is to make laws for the country.'
    },
    {
        id: '2',
        question: 'Which article of the Indian Constitution deals with the Right to Equality?',
        options: [
            'Article 14-18',
            'Article 19-22',
            'Article 23-24',
            'Article 25-28'
        ],
        correct_answer: 0,
        explanation: 'Articles 14-18 of the Indian Constitution deal with the Right to Equality, which includes equality before law, prohibition of discrimination, abolition of untouchability, etc.'
    },
    {
        id: '3',
        question: 'The Indus Valley Civilization was primarily known for:',
        options: [
            'Iron tools',
            'Urban planning',
            'Horse domestication',
            'Paper production'
        ],
        correct_answer: 1,
        explanation: 'The Indus Valley Civilization is particularly famous for its advanced urban planning, including well-organized cities like Mohenjo-daro and Harappa with grid patterns and drainage systems.'
    },
    {
        id: '4',
        question: 'Which institution releases the Human Development Index (HDI)?',
        options: [
            'World Bank',
            'IMF',
            'UNDP',
            'WHO'
        ],
        correct_answer: 2,
        explanation: 'The Human Development Index (HDI) is released by the United Nations Development Programme (UNDP) as part of its annual Human Development Report.'
    },
    {
        id: '5',
        question: 'The monsoon in India is caused by:',
        options: [
            'Western disturbances',
            'Trade winds',
            'Seasonal reversal of wind direction',
            'Jet streams'
        ],
        correct_answer: 2,
        explanation: 'The Indian monsoon is caused by the seasonal reversal of wind direction, bringing moisture-laden winds from the Indian Ocean during summer.'
    }
];
