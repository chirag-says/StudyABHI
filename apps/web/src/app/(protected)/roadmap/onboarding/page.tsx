'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
    Target, ArrowRight, ArrowLeft, CheckCircle, Clock,
    GraduationCap, Briefcase, Sun, Moon, Sunrise, Sunset,
    BookOpen, Zap, Coffee, Timer, Loader2, AlertTriangle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import api, { getErrorMessage } from '@/services/api';

interface OnboardingData {
    target_exam_year: number;
    preparation_level: string;
    study_preference: string;
    daily_study_hours: number;
    optional_subject: string;
    is_working: boolean;
    preferred_study_time: string;
    medium: string;
}

const OPTIONAL_SUBJECTS = [
    "Geography", "History", "Political Science", "Public Administration",
    "Sociology", "Philosophy", "Psychology", "Economics", "Law",
    "Anthropology", "Medical Science", "Literature", "Mathematics", "Other"
];

export default function OnboardingPage() {
    const router = useRouter();
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [checkingStatus, setCheckingStatus] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const totalSteps = 5;

    const [data, setData] = useState<OnboardingData>({
        target_exam_year: new Date().getFullYear() + 1,
        preparation_level: 'beginner',
        study_preference: 'moderate',
        daily_study_hours: 6,
        optional_subject: '',
        is_working: false,
        preferred_study_time: 'morning',
        medium: 'english'
    });

    useEffect(() => {
        const checkOnboarding = async () => {
            try {
                const response = await api.get('/roadmap/onboarding/status');
                if (response.data.onboarding_completed) {
                    router.push('/roadmap');
                }
            } catch (err) {
                console.error('Error checking onboarding status:', err);
            } finally {
                setCheckingStatus(false);
            }
        };
        checkOnboarding();
    }, [router]);

    const handleSubmit = async () => {
        setLoading(true);
        setError(null);
        try {
            console.log('Submitting onboarding data:', data);
            await api.post('/roadmap/onboarding/complete', data);
            router.push('/roadmap');
        } catch (err) {
            console.error('Failed to complete onboarding:', err);
            const errorMsg = getErrorMessage(err);
            setError(errorMsg);
            setLoading(false);
        }
    };

    const updateData = (updates: Partial<OnboardingData>) => {
        setData(prev => ({ ...prev, ...updates }));
    };

    if (checkingStatus) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-primary/5 to-background">
                <Loader2 className="w-10 h-10 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-background via-primary/5 to-background">
            {/* Progress Bar */}
            <div className="fixed top-0 left-0 right-0 h-1 bg-muted z-50">
                <div
                    className="h-full bg-gradient-to-r from-primary to-primary/70 transition-all duration-500"
                    style={{ width: `${(step / totalSteps) * 100}%` }}
                />
            </div>

            <div className="container max-w-3xl py-12 px-4">
                {/* Header */}
                <div className="text-center mb-12">
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 rounded-full text-primary text-sm font-medium mb-6">
                        <Target className="w-4 h-4" />
                        UPSC Preparation Roadmap
                    </div>
                    <h1 className="text-4xl font-bold mb-4">
                        Let&apos;s Create Your{' '}
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-primary/60">
                            Personalized Study Plan
                        </span>
                    </h1>
                    <p className="text-muted-foreground text-lg">
                        Answer a few questions to get a tailored roadmap for your UPSC journey
                    </p>
                </div>

                {/* Step Content */}
                <div className="bg-card border rounded-2xl p-8 shadow-lg mb-8">
                    {/* Step 1: Target Year */}
                    {step === 1 && (
                        <div className="space-y-6">
                            <div className="flex items-center gap-3 text-sm text-muted-foreground mb-4">
                                <span className="bg-primary/10 text-primary px-3 py-1 rounded-full">Step 1 of {totalSteps}</span>
                                Target Exam
                            </div>
                            <h2 className="text-2xl font-bold">Which year&apos;s UPSC exam are you targeting?</h2>
                            <p className="text-muted-foreground">
                                This helps us calculate the optimal study schedule based on available time.
                            </p>

                            <div className="grid grid-cols-3 gap-4 mt-8">
                                {[0, 1, 2].map(offset => {
                                    const year = new Date().getFullYear() + offset;
                                    return (
                                        <button
                                            key={year}
                                            onClick={() => updateData({ target_exam_year: year })}
                                            className={`p-6 rounded-xl border-2 transition-all ${data.target_exam_year === year
                                                ? 'border-primary bg-primary/10 ring-2 ring-primary/20'
                                                : 'border-muted hover:border-primary/50'
                                                }`}
                                        >
                                            <div className="text-3xl font-bold">{year}</div>
                                            <div className="text-sm text-muted-foreground mt-1">
                                                {offset === 0 ? 'This Year' : offset === 1 ? 'Next Year' : `${year}`}
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Step 2: Preparation Level */}
                    {step === 2 && (
                        <div className="space-y-6">
                            <div className="flex items-center gap-3 text-sm text-muted-foreground mb-4">
                                <span className="bg-primary/10 text-primary px-3 py-1 rounded-full">Step 2 of {totalSteps}</span>
                                Current Level
                            </div>
                            <h2 className="text-2xl font-bold">What&apos;s your current preparation level?</h2>
                            <p className="text-muted-foreground">
                                Be honest - this helps us optimize your study plan.
                            </p>

                            <div className="space-y-4 mt-8">
                                {[
                                    { value: 'beginner', label: 'Complete Beginner', desc: "Just starting, haven't read any UPSC-specific material yet", icon: '🌱' },
                                    { value: 'foundation', label: 'Foundation Level', desc: 'Read some NCERTs, familiar with basic concepts', icon: '📚' },
                                    { value: 'intermediate', label: 'Intermediate', desc: 'Covered 30-50% of syllabus, attempted some mocks', icon: '📈' },
                                    { value: 'advanced', label: 'Advanced', desc: 'Covered most syllabus, appeared in prelims before', icon: '🎯' }
                                ].map(level => (
                                    <button
                                        key={level.value}
                                        onClick={() => updateData({ preparation_level: level.value })}
                                        className={`w-full p-5 rounded-xl border-2 text-left transition-all flex items-start gap-4 ${data.preparation_level === level.value
                                            ? 'border-primary bg-primary/10 ring-2 ring-primary/20'
                                            : 'border-muted hover:border-primary/50'
                                            }`}
                                    >
                                        <span className="text-3xl">{level.icon}</span>
                                        <div>
                                            <div className="font-semibold text-lg">{level.label}</div>
                                            <div className="text-sm text-muted-foreground">{level.desc}</div>
                                        </div>
                                        {data.preparation_level === level.value && (
                                            <CheckCircle className="w-6 h-6 text-primary ml-auto shrink-0" />
                                        )}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 3: Study Preference */}
                    {step === 3 && (
                        <div className="space-y-6">
                            <div className="flex items-center gap-3 text-sm text-muted-foreground mb-4">
                                <span className="bg-primary/10 text-primary px-3 py-1 rounded-full">Step 3 of {totalSteps}</span>
                                Study Style
                            </div>
                            <h2 className="text-2xl font-bold">How many hours can you study daily?</h2>
                            <p className="text-muted-foreground">
                                Consider your other commitments and be realistic.
                            </p>

                            <div className="grid grid-cols-2 gap-4 mt-8">
                                {[
                                    { value: 'part_time', hours: 3, label: 'Part Time', desc: '2-3 hours/day', icon: Coffee },
                                    { value: 'relaxed', hours: 4, label: 'Relaxed', desc: '4-5 hours/day', icon: Timer },
                                    { value: 'moderate', hours: 6, label: 'Moderate', desc: '6-7 hours/day', icon: BookOpen },
                                    { value: 'intensive', hours: 8, label: 'Intensive', desc: '8-10 hours/day', icon: Zap }
                                ].map(pref => {
                                    const Icon = pref.icon;
                                    return (
                                        <button
                                            key={pref.value}
                                            onClick={() => updateData({
                                                study_preference: pref.value,
                                                daily_study_hours: pref.hours
                                            })}
                                            className={`p-6 rounded-xl border-2 text-left transition-all ${data.study_preference === pref.value
                                                ? 'border-primary bg-primary/10 ring-2 ring-primary/20'
                                                : 'border-muted hover:border-primary/50'
                                                }`}
                                        >
                                            <Icon className={`w-8 h-8 mb-3 ${data.study_preference === pref.value ? 'text-primary' : 'text-muted-foreground'}`} />
                                            <div className="font-semibold text-lg">{pref.label}</div>
                                            <div className="text-sm text-muted-foreground">{pref.desc}</div>
                                        </button>
                                    );
                                })}
                            </div>

                            <div className="mt-6 p-4 bg-muted/50 rounded-lg">
                                <label className="flex items-center gap-3 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={data.is_working}
                                        onChange={(e) => updateData({ is_working: e.target.checked })}
                                        className="w-5 h-5 rounded accent-primary"
                                    />
                                    <div>
                                        <span className="font-medium flex items-center gap-2">
                                            <Briefcase className="w-4 h-4" />
                                            I&apos;m a working professional
                                        </span>
                                        <span className="text-sm text-muted-foreground block">
                                            We&apos;ll optimize your plan for limited study time
                                        </span>
                                    </div>
                                </label>
                            </div>
                        </div>
                    )}

                    {/* Step 4: Study Time Preference */}
                    {step === 4 && (
                        <div className="space-y-6">
                            <div className="flex items-center gap-3 text-sm text-muted-foreground mb-4">
                                <span className="bg-primary/10 text-primary px-3 py-1 rounded-full">Step 4 of {totalSteps}</span>
                                Schedule
                            </div>
                            <h2 className="text-2xl font-bold">When do you prefer to study?</h2>
                            <p className="text-muted-foreground">
                                We&apos;ll schedule your most important tasks during your peak hours.
                            </p>

                            <div className="grid grid-cols-2 gap-4 mt-8">
                                {[
                                    { value: 'morning', label: 'Early Morning', time: '5 AM - 10 AM', icon: Sunrise, color: 'text-orange-500' },
                                    { value: 'afternoon', label: 'Afternoon', time: '12 PM - 5 PM', icon: Sun, color: 'text-yellow-500' },
                                    { value: 'evening', label: 'Evening', time: '5 PM - 9 PM', icon: Sunset, color: 'text-purple-500' },
                                    { value: 'night', label: 'Night Owl', time: '9 PM - 2 AM', icon: Moon, color: 'text-blue-500' }
                                ].map(time => {
                                    const Icon = time.icon;
                                    return (
                                        <button
                                            key={time.value}
                                            onClick={() => updateData({ preferred_study_time: time.value })}
                                            className={`p-6 rounded-xl border-2 text-left transition-all ${data.preferred_study_time === time.value
                                                ? 'border-primary bg-primary/10 ring-2 ring-primary/20'
                                                : 'border-muted hover:border-primary/50'
                                                }`}
                                        >
                                            <Icon className={`w-8 h-8 mb-3 ${time.color}`} />
                                            <div className="font-semibold">{time.label}</div>
                                            <div className="text-sm text-muted-foreground">{time.time}</div>
                                        </button>
                                    );
                                })}
                            </div>

                            <div className="mt-6">
                                <label className="block text-sm font-medium mb-2">Preferred Medium</label>
                                <div className="flex gap-4">
                                    {['english', 'hindi'].map(medium => (
                                        <button
                                            key={medium}
                                            onClick={() => updateData({ medium })}
                                            className={`flex-1 py-3 px-4 rounded-lg border-2 transition-all capitalize ${data.medium === medium
                                                ? 'border-primary bg-primary/10'
                                                : 'border-muted hover:border-primary/50'
                                                }`}
                                        >
                                            {medium}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 5: Optional Subject */}
                    {step === 5 && (
                        <div className="space-y-6">
                            <div className="flex items-center gap-3 text-sm text-muted-foreground mb-4">
                                <span className="bg-primary/10 text-primary px-3 py-1 rounded-full">Step 5 of {totalSteps}</span>
                                Optional Subject
                            </div>
                            <h2 className="text-2xl font-bold">Have you decided on an Optional Subject?</h2>
                            <p className="text-muted-foreground">
                                This is for Mains. If undecided, we&apos;ll help you explore options later.
                            </p>

                            <div className="grid grid-cols-3 gap-3 mt-8">
                                <button
                                    onClick={() => updateData({ optional_subject: '' })}
                                    className={`p-4 rounded-xl border-2 text-center transition-all ${!data.optional_subject
                                        ? 'border-primary bg-primary/10 ring-2 ring-primary/20'
                                        : 'border-muted hover:border-primary/50'
                                        }`}
                                >
                                    <div className="font-medium">Not Decided</div>
                                </button>
                                {OPTIONAL_SUBJECTS.map(subject => (
                                    <button
                                        key={subject}
                                        onClick={() => updateData({ optional_subject: subject })}
                                        className={`p-4 rounded-xl border-2 text-center transition-all ${data.optional_subject === subject
                                            ? 'border-primary bg-primary/10 ring-2 ring-primary/20'
                                            : 'border-muted hover:border-primary/50'
                                            }`}
                                    >
                                        <div className="font-medium text-sm">{subject}</div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Navigation */}
                <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between">
                        {step > 1 ? (
                            <Button
                                variant="outline"
                                onClick={() => setStep(step - 1)}
                                className="gap-2"
                            >
                                <ArrowLeft className="w-4 h-4" />
                                Back
                            </Button>
                        ) : (
                            <div />
                        )}

                        {step < totalSteps ? (
                            <Button
                                onClick={() => setStep(step + 1)}
                                className="gap-2"
                                size="lg"
                            >
                                Continue
                                <ArrowRight className="w-4 h-4" />
                            </Button>
                        ) : (
                            <Button
                                onClick={handleSubmit}
                                disabled={loading}
                                className="gap-2"
                                size="lg"
                            >
                                {loading ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Creating Plan...
                                    </>
                                ) : (
                                    <>
                                        <GraduationCap className="w-4 h-4" />
                                        Start My Journey
                                    </>
                                )}
                            </Button>
                        )}
                    </div>

                    {/* Error Message */}
                    {error && (
                        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3">
                            <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                            <div>
                                <p className="font-medium text-red-600">Failed to create study plan</p>
                                <p className="text-sm text-red-500">{error}</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Summary Preview */}
                {step === 5 && (
                    <div className="mt-8 p-6 bg-gradient-to-r from-primary/5 to-transparent border rounded-xl">
                        <h3 className="font-semibold mb-4 flex items-center gap-2">
                            <Clock className="w-5 h-5 text-primary" />
                            Your Plan Summary
                        </h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div className="bg-background p-3 rounded-lg">
                                <div className="text-muted-foreground">Target</div>
                                <div className="font-bold">UPSC {data.target_exam_year}</div>
                            </div>
                            <div className="bg-background p-3 rounded-lg">
                                <div className="text-muted-foreground">Level</div>
                                <div className="font-bold capitalize">{data.preparation_level}</div>
                            </div>
                            <div className="bg-background p-3 rounded-lg">
                                <div className="text-muted-foreground">Daily Hours</div>
                                <div className="font-bold">{data.daily_study_hours} hours</div>
                            </div>
                            <div className="bg-background p-3 rounded-lg">
                                <div className="text-muted-foreground">Study Time</div>
                                <div className="font-bold capitalize">{data.preferred_study_time}</div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
