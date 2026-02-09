'use client';

import React from 'react';
import {
    TrendingUp,
    TrendingDown,
    Clock,
    Target,
    Flame,
    Award,
    AlertTriangle,
    Eye,
    Brain,
    Calendar
} from 'lucide-react';
import attentionService from '@/services/attention';

interface StudySession {
    date: Date;
    duration: number; // in minutes
    focusTime: number; // in minutes
    distractions: number;
    questionsAnswered: number;
    correctAnswers: number;
}

interface StudyStatsProps {
    currentSession: {
        startTime: Date | null;
        focusTime: number; // in seconds
        distractions: number;
        questionsAnswered: number;
        correctAnswers: number;
    };
    recentSessions?: StudySession[];
}

export function StudyStats({ currentSession, recentSessions = [] }: StudyStatsProps) {
    const [dailySummary, setDailySummary] = React.useState<any>(null);
    const [stats, setStats] = React.useState<any>(null);

    React.useEffect(() => {
        const loadStats = async () => {
            try {
                // Determine today's date string if needed, or rely on backend
                const summaries = await attentionService.getDailySummaries(1);
                if (summaries && summaries.length > 0) {
                    setDailySummary(summaries[0]);
                }
                const analytics = await attentionService.getAnalytics(7);
                setStats(analytics);
            } catch (error) {
                console.error("Failed to load study stats", error);
            }
        };

        loadStats();
        // Refresh every minute
        const interval = setInterval(loadStats, 60000);
        return () => clearInterval(interval);
    }, []);

    const formatDuration = (seconds: number) => {
        const totalMinutes = Math.floor(seconds / 60);
        const hrs = Math.floor(totalMinutes / 60);
        const mins = totalMinutes % 60;
        if (hrs > 0) {
            return `${hrs}h ${mins}m`;
        }
        return `${mins}m`;
    };

    const calculateFocusPercentage = () => {
        // Use current session data if active, otherwise fallback to daily summary or 0
        if (currentSession.startTime) {
            const elapsed = (Date.now() - currentSession.startTime.getTime()) / 1000;
            if (elapsed === 0) return 100;
            return Math.round((currentSession.focusTime / elapsed) * 100);
        }
        return dailySummary?.avg_focus_score || 0;
    };

    const focusPercentage = calculateFocusPercentage();

    const getStreakDays = () => {
        // This should ideally come from a dedicated user stats endpoint or daily summary check
        // For now, using a placeholder or calculated from recent sessions if available
        return 0; // stats?.current_streak || 0; 
    };

    const getTotalStudyTime = () => {
        // Combine daily summary total with current session
        const dailyTotal = dailySummary?.total_tracked_minutes || 0;
        const currentSessionMinutes = currentSession.focusTime / 60;
        // Avoid double counting if backend already updated
        return dailyTotal + currentSessionMinutes;
    };

    const getAverageAccuracy = () => {
        if (currentSession.questionsAnswered === 0) {
            if (recentSessions.length === 0) return 0;
            const totalQ = recentSessions.reduce((acc, s) => acc + s.questionsAnswered, 0);
            const totalCorrect = recentSessions.reduce((acc, s) => acc + s.correctAnswers, 0);
            return totalQ > 0 ? Math.round((totalCorrect / totalQ) * 100) : 0;
        }
        return Math.round((currentSession.correctAnswers / currentSession.questionsAnswered) * 100);
    };

    return (
        <div className="space-y-4">
            {/* Current Session Stats */}
            <div className="grid grid-cols-2 gap-3">
                {/* Focus Time */}
                <div className="p-4 rounded-xl bg-gradient-to-br from-green-500/10 to-emerald-500/5 border border-green-500/20">
                    <div className="flex items-center gap-2 mb-2">
                        <Eye className="w-4 h-4 text-green-500" />
                        <span className="text-xs text-muted-foreground">Focus Time</span>
                    </div>
                    <p className="text-2xl font-bold text-green-500">
                        {formatDuration(currentSession.focusTime)}
                    </p>
                </div>

                {/* Focus Rate */}
                <div className="p-4 rounded-xl bg-gradient-to-br from-blue-500/10 to-cyan-500/5 border border-blue-500/20">
                    <div className="flex items-center gap-2 mb-2">
                        <Target className="w-4 h-4 text-blue-500" />
                        <span className="text-xs text-muted-foreground">Focus Rate</span>
                    </div>
                    <div className="flex items-baseline gap-2">
                        <p className="text-2xl font-bold text-blue-500">{focusPercentage}%</p>
                        {focusPercentage >= 80 ? (
                            <TrendingUp className="w-4 h-4 text-green-500" />
                        ) : (
                            <TrendingDown className="w-4 h-4 text-red-500" />
                        )}
                    </div>
                </div>

                {/* Distractions */}
                <div className="p-4 rounded-xl bg-gradient-to-br from-yellow-500/10 to-orange-500/5 border border-yellow-500/20">
                    <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="w-4 h-4 text-yellow-500" />
                        <span className="text-xs text-muted-foreground">Distractions</span>
                    </div>
                    <p className="text-2xl font-bold text-yellow-500">
                        {currentSession.distractions}
                    </p>
                </div>

                {/* Quiz Accuracy */}
                <div className="p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-pink-500/5 border border-purple-500/20">
                    <div className="flex items-center gap-2 mb-2">
                        <Brain className="w-4 h-4 text-purple-500" />
                        <span className="text-xs text-muted-foreground">Quiz Accuracy</span>
                    </div>
                    <p className="text-2xl font-bold text-purple-500">
                        {getAverageAccuracy()}%
                    </p>
                </div>
            </div>

            {/* Streak & Achievements */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-orange-500/10 via-red-500/10 to-pink-500/10 border border-orange-500/20">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
                            <Flame className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <p className="text-lg font-bold">{getStreakDays()} Day Streak</p>
                            <p className="text-xs text-muted-foreground">Keep it going!</p>
                        </div>
                    </div>
                    <div className="flex gap-1">
                        {[1, 2, 3, 4, 5, 6, 7].map(day => (
                            <div
                                key={day}
                                className={`w-3 h-8 rounded-full ${day <= getStreakDays()
                                    ? 'bg-gradient-to-t from-orange-500 to-red-500'
                                    : 'bg-muted'
                                    }`}
                            />
                        ))}
                    </div>
                </div>
            </div>

            {/* Weekly Overview */}
            <div className="p-4 rounded-xl bg-muted/50 border">
                <div className="flex items-center gap-2 mb-4">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <span className="font-medium">This Week</span>
                </div>

                <div className="grid grid-cols-7 gap-1">
                    {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((day, i) => (
                        <div key={i} className="text-center">
                            <p className="text-xs text-muted-foreground mb-1">{day}</p>
                            <div className={`w-full aspect-square rounded-md ${i < 5 ? 'bg-primary/30' : 'bg-muted'
                                } flex items-center justify-center`}>
                                {i < 5 && (
                                    <div className={`w-2 h-2 rounded-full ${i < 3 ? 'bg-green-500' : 'bg-yellow-500'
                                        }`} />
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
                    <span>Total: {Math.round(getTotalStudyTime())} mins</span>
                    <span>{recentSessions.length + 1} sessions</span>
                </div>
            </div>

            {/* Achievement Badges */}
            <div className="p-4 rounded-xl bg-muted/50 border">
                <div className="flex items-center gap-2 mb-3">
                    <Award className="w-4 h-4 text-muted-foreground" />
                    <span className="font-medium">Achievements</span>
                </div>

                <div className="flex flex-wrap gap-2">
                    <div className="px-3 py-1.5 rounded-full bg-gradient-to-r from-yellow-500 to-orange-500 text-white text-xs font-medium flex items-center gap-1">
                        <Flame className="w-3 h-3" />
                        5 Day Streak
                    </div>
                    <div className="px-3 py-1.5 rounded-full bg-gradient-to-r from-green-500 to-emerald-500 text-white text-xs font-medium flex items-center gap-1">
                        <Eye className="w-3 h-3" />
                        Focus Master
                    </div>
                    <div className="px-3 py-1.5 rounded-full bg-muted text-muted-foreground text-xs font-medium flex items-center gap-1">
                        <Brain className="w-3 h-3" />
                        Quiz Ace
                    </div>
                    <div className="px-3 py-1.5 rounded-full bg-muted text-muted-foreground text-xs font-medium flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Early Bird
                    </div>
                </div>
            </div>
        </div>
    );
}
