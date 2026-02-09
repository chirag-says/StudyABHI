'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    Play,
    Pause,
    RotateCcw,
    Coffee,
    BookOpen,
    ChevronUp,
    ChevronDown,
    Volume2,
    VolumeX
} from 'lucide-react';
import { Button } from '@/components/ui/button';

type TimerMode = 'focus' | 'shortBreak' | 'longBreak';

interface StudyTimerProps {
    onSessionComplete?: (mode: TimerMode, duration: number) => void;
    onModeChange?: (mode: TimerMode) => void;
    autoStart?: boolean;
}

const TIMER_PRESETS = {
    focus: 25 * 60, // 25 minutes
    shortBreak: 5 * 60, // 5 minutes
    longBreak: 15 * 60, // 15 minutes
};

export function StudyTimer({ onSessionComplete, onModeChange, autoStart = false }: StudyTimerProps) {
    const [mode, setMode] = useState<TimerMode>('focus');
    const [timeLeft, setTimeLeft] = useState(TIMER_PRESETS.focus);
    const [isRunning, setIsRunning] = useState(autoStart);
    const [sessionsCompleted, setSessionsCompleted] = useState(0);
    const [soundEnabled, setSoundEnabled] = useState(true);
    const [customDuration, setCustomDuration] = useState({
        focus: 25,
        shortBreak: 5,
        longBreak: 15
    });

    const intervalRef = useRef<NodeJS.Timeout | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    // Initialize audio
    useEffect(() => {
        audioRef.current = new Audio('/timer-complete.mp3');
        return () => {
            if (audioRef.current) {
                audioRef.current.pause();
            }
        };
    }, []);

    // Timer logic
    useEffect(() => {
        if (isRunning && timeLeft > 0) {
            intervalRef.current = setInterval(() => {
                setTimeLeft(prev => {
                    if (prev <= 1) {
                        handleTimerComplete();
                        return 0;
                    }
                    return prev - 1;
                });
            }, 1000);
        } else {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        }

        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        };
    }, [isRunning]);

    const handleTimerComplete = useCallback(() => {
        setIsRunning(false);

        // Play sound
        if (soundEnabled && audioRef.current) {
            audioRef.current.play().catch(() => { });
        }

        // Browser notification
        if (Notification.permission === 'granted') {
            new Notification('Timer Complete! 🎉', {
                body: mode === 'focus'
                    ? 'Great job! Time for a break.'
                    : 'Break is over. Ready to focus?',
                icon: '/favicon.ico'
            });
        }

        // Update sessions
        if (mode === 'focus') {
            const newSessions = sessionsCompleted + 1;
            setSessionsCompleted(newSessions);
            onSessionComplete?.(mode, TIMER_PRESETS[mode]);

            // Switch to break
            const nextMode = newSessions % 4 === 0 ? 'longBreak' : 'shortBreak';
            switchMode(nextMode);
        } else {
            onSessionComplete?.(mode, TIMER_PRESETS[mode]);
            switchMode('focus');
        }
    }, [mode, sessionsCompleted, soundEnabled, onSessionComplete]);

    const switchMode = (newMode: TimerMode) => {
        setMode(newMode);
        setTimeLeft(customDuration[newMode] * 60);
        setIsRunning(false);
        onModeChange?.(newMode);
    };

    const toggleTimer = () => {
        if (!isRunning && timeLeft === 0) {
            resetTimer();
        }
        setIsRunning(!isRunning);
    };

    const resetTimer = () => {
        setIsRunning(false);
        setTimeLeft(customDuration[mode] * 60);
    };

    const adjustTime = (delta: number) => {
        if (isRunning) return;
        const newDuration = Math.max(1, Math.min(120, customDuration[mode] + delta));
        setCustomDuration(prev => ({ ...prev, [mode]: newDuration }));
        setTimeLeft(newDuration * 60);
    };

    // Request notification permission
    useEffect(() => {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }, []);

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    const progress = ((customDuration[mode] * 60 - timeLeft) / (customDuration[mode] * 60)) * 100;

    const getModeColor = () => {
        switch (mode) {
            case 'focus': return 'from-blue-500 to-purple-600';
            case 'shortBreak': return 'from-green-500 to-emerald-600';
            case 'longBreak': return 'from-orange-500 to-amber-600';
        }
    };

    const getModeLabel = () => {
        switch (mode) {
            case 'focus': return 'Focus Session';
            case 'shortBreak': return 'Short Break';
            case 'longBreak': return 'Long Break';
        }
    };

    return (
        <div className="p-6 rounded-2xl bg-gradient-to-br from-card to-muted border">
            {/* Mode Tabs */}
            <div className="flex gap-2 mb-6">
                {[
                    { mode: 'focus' as TimerMode, icon: BookOpen, label: 'Focus' },
                    { mode: 'shortBreak' as TimerMode, icon: Coffee, label: 'Short' },
                    { mode: 'longBreak' as TimerMode, icon: Coffee, label: 'Long' },
                ].map(({ mode: m, icon: Icon, label }) => (
                    <button
                        key={m}
                        onClick={() => switchMode(m)}
                        className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg transition-all ${mode === m
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted hover:bg-muted/80'
                            }`}
                    >
                        <Icon className="w-4 h-4" />
                        <span className="text-sm font-medium">{label}</span>
                    </button>
                ))}
            </div>

            {/* Timer Display */}
            <div className="relative mb-6">
                {/* Progress Ring */}
                <div className="relative mx-auto w-48 h-48">
                    <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                        {/* Background Circle */}
                        <circle
                            cx="50"
                            cy="50"
                            r="45"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="8"
                            className="text-muted"
                        />
                        {/* Progress Circle */}
                        <circle
                            cx="50"
                            cy="50"
                            r="45"
                            fill="none"
                            stroke="url(#gradient)"
                            strokeWidth="8"
                            strokeLinecap="round"
                            strokeDasharray={`${progress * 2.83} 283`}
                            className="transition-all duration-1000"
                        />
                        <defs>
                            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" className={`stop-color-blue-500`} stopColor={mode === 'focus' ? '#3b82f6' : mode === 'shortBreak' ? '#22c55e' : '#f97316'} />
                                <stop offset="100%" className={`stop-color-purple-600`} stopColor={mode === 'focus' ? '#9333ea' : mode === 'shortBreak' ? '#10b981' : '#f59e0b'} />
                            </linearGradient>
                        </defs>
                    </svg>

                    {/* Time Display */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-4xl font-bold font-mono tabular-nums">
                            {formatTime(timeLeft)}
                        </span>
                        <span className="text-sm text-muted-foreground mt-1">
                            {getModeLabel()}
                        </span>
                    </div>
                </div>

                {/* Time Adjust Buttons */}
                {!isRunning && (
                    <div className="absolute right-0 top-1/2 -translate-y-1/2 flex flex-col gap-1">
                        <button
                            onClick={() => adjustTime(5)}
                            className="p-1 rounded hover:bg-muted transition-colors"
                            title="Add 5 minutes"
                        >
                            <ChevronUp className="w-5 h-5" />
                        </button>
                        <button
                            onClick={() => adjustTime(-5)}
                            className="p-1 rounded hover:bg-muted transition-colors"
                            title="Remove 5 minutes"
                        >
                            <ChevronDown className="w-5 h-5" />
                        </button>
                    </div>
                )}
            </div>

            {/* Controls */}
            <div className="flex items-center justify-center gap-4 mb-4">
                <Button
                    variant="outline"
                    size="icon"
                    onClick={resetTimer}
                    className="rounded-full"
                >
                    <RotateCcw className="w-4 h-4" />
                </Button>

                <Button
                    onClick={toggleTimer}
                    size="lg"
                    className={`rounded-full w-16 h-16 bg-gradient-to-r ${getModeColor()} hover:opacity-90`}
                >
                    {isRunning ? (
                        <Pause className="w-6 h-6" />
                    ) : (
                        <Play className="w-6 h-6 ml-1" />
                    )}
                </Button>

                <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setSoundEnabled(!soundEnabled)}
                    className="rounded-full"
                >
                    {soundEnabled ? (
                        <Volume2 className="w-4 h-4" />
                    ) : (
                        <VolumeX className="w-4 h-4" />
                    )}
                </Button>
            </div>

            {/* Session Counter */}
            <div className="flex items-center justify-center gap-2">
                {[1, 2, 3, 4].map(i => (
                    <div
                        key={i}
                        className={`w-3 h-3 rounded-full transition-colors ${i <= (sessionsCompleted % 4)
                            ? 'bg-primary'
                            : 'bg-muted'
                            }`}
                    />
                ))}
                <span className="text-sm text-muted-foreground ml-2">
                    {sessionsCompleted} sessions completed
                </span>
            </div>
        </div>
    );
}
