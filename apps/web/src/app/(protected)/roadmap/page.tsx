'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
    CheckCircle, Circle, Clock, Trophy, Target, Flame,
    BookOpen, Brain, FileText, Newspaper, ChevronRight,
    Play, CheckCheck, RotateCcw, Calendar, TrendingUp,
    ArrowRight, Loader2, Timer, Zap, AlertCircle, RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/services/api';

interface Task {
    id: string;
    title: string;
    description?: string;
    task_type: 'study' | 'quiz' | 'revision' | 'current_affairs' | 'practice';
    status: 'pending' | 'in_progress' | 'completed' | 'skipped';
    priority: number;
    scheduled_date?: string;
    due_date?: string;
    estimated_minutes?: number;
    actual_minutes?: number;
    topic_name?: string;
    topic_id?: string;
    subject_name?: string;
    is_revision?: boolean;
    scheduled_time_slot?: string;
}

interface Phase {
    name: string;
    start_date: string;
    end_date: string;
    progress: number;
    is_active: boolean;
    is_completed: boolean;
}

interface RoadmapData {
    has_plan: boolean;
    overall_progress: number;
    current_phase: number;
    total_phases: number;
    phase_name: string;
    phase_progress: number;
    today_tasks: Task[];
    upcoming_tasks: Task[];
    revision_due: Task[];
    completed_this_week: number;
    streak_days: number;
    target_exam_year?: number;
    days_to_prelims?: number;
    daily_goal_hours: number;
    phases: Phase[];
}

const taskTypeConfig = {
    study: { icon: BookOpen, color: 'text-blue-500', bgColor: 'bg-blue-500/10', label: 'Study' },
    quiz: { icon: Brain, color: 'text-purple-500', bgColor: 'bg-purple-500/10', label: 'Quiz' },
    revision: { icon: RotateCcw, color: 'text-orange-500', bgColor: 'bg-orange-500/10', label: 'Revision' },
    current_affairs: { icon: Newspaper, color: 'text-green-500', bgColor: 'bg-green-500/10', label: 'Current Affairs' },
    practice: { icon: FileText, color: 'text-teal-500', bgColor: 'bg-teal-500/10', label: 'Practice' }
};

const statusConfig = {
    pending: { icon: Circle, color: 'text-muted-foreground', label: 'Pending' },
    in_progress: { icon: Play, color: 'text-yellow-500', label: 'In Progress' },
    completed: { icon: CheckCircle, color: 'text-green-500', label: 'Completed' },
    skipped: { icon: AlertCircle, color: 'text-red-400', label: 'Skipped' }
};

export default function RoadmapPage() {
    const router = useRouter();
    const [roadmap, setRoadmap] = useState<RoadmapData | null>(null);
    const [loading, setLoading] = useState(true);
    const [updatingTask, setUpdatingTask] = useState<string | null>(null);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        fetchRoadmap();
    }, []);

    const fetchRoadmap = async () => {
        try {
            const response = await api.get<RoadmapData>('/roadmap/full');

            if (!response.data.has_plan) {
                router.push('/roadmap/onboarding');
                return;
            }

            setRoadmap(response.data);
        } catch (error) {
            console.error('Failed to fetch roadmap:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const handleRefresh = async () => {
        setRefreshing(true);
        await fetchRoadmap();
    };

    const updateTaskStatus = async (taskId: string, newStatus: string) => {
        if (!roadmap) return;

        setUpdatingTask(taskId);

        try {
            await api.patch(`/roadmap/tasks/${taskId}`, { status: newStatus });

            // Optimistically update UI
            const updateTaskList = (tasks: Task[]) =>
                tasks.map(task =>
                    task.id === taskId ? { ...task, status: newStatus as Task['status'] } : task
                );

            setRoadmap({
                ...roadmap,
                today_tasks: updateTaskList(roadmap.today_tasks),
                upcoming_tasks: updateTaskList(roadmap.upcoming_tasks),
                revision_due: updateTaskList(roadmap.revision_due),
                completed_this_week: newStatus === 'completed'
                    ? roadmap.completed_this_week + 1
                    : roadmap.completed_this_week
            });
        } catch (error) {
            console.error('Failed to update task:', error);
        } finally {
            setUpdatingTask(null);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
                    <p className="text-muted-foreground">Loading your roadmap...</p>
                </div>
            </div>
        );
    }

    if (!roadmap) return null;

    const completedTodayCount = roadmap.today_tasks.filter(t => t.status === 'completed').length;
    const totalTodayTasks = roadmap.today_tasks.length;
    const todayProgress = totalTodayTasks > 0 ? (completedTodayCount / totalTodayTasks) * 100 : 0;

    return (
        <div className="min-h-screen bg-gradient-to-br from-background via-primary/5 to-background">
            <div className="container py-8 px-4 md:px-6 max-w-7xl">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
                    <div>
                        <h1 className="text-3xl font-bold mb-2">Your Study Roadmap</h1>
                        <p className="text-muted-foreground">
                            UPSC {roadmap.target_exam_year} • {roadmap.days_to_prelims} days to Prelims
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleRefresh}
                            disabled={refreshing}
                        >
                            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                            Refresh
                        </Button>
                        <Button
                            size="sm"
                            onClick={() => router.push('/study-room')}
                        >
                            <Play className="w-4 h-4 mr-2" />
                            Start Studying
                        </Button>
                    </div>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                    <Card className="border-0 shadow-lg bg-gradient-to-br from-blue-500/10 to-blue-600/5">
                        <CardContent className="p-5">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-muted-foreground">Overall Progress</p>
                                    <p className="text-3xl font-bold mt-1">{Math.round(roadmap.overall_progress)}%</p>
                                </div>
                                <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                                    <TrendingUp className="w-6 h-6 text-blue-500" />
                                </div>
                            </div>
                            <div className="mt-3 h-2 bg-muted rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all"
                                    style={{ width: `${roadmap.overall_progress}%` }}
                                />
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-0 shadow-lg bg-gradient-to-br from-orange-500/10 to-orange-600/5">
                        <CardContent className="p-5">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-muted-foreground">Current Streak</p>
                                    <p className="text-3xl font-bold mt-1">{roadmap.streak_days} days</p>
                                </div>
                                <div className="w-12 h-12 rounded-full bg-orange-500/20 flex items-center justify-center">
                                    <Flame className="w-6 h-6 text-orange-500" />
                                </div>
                            </div>
                            <p className="text-sm text-muted-foreground mt-3">Keep going! 🔥</p>
                        </CardContent>
                    </Card>

                    <Card className="border-0 shadow-lg bg-gradient-to-br from-green-500/10 to-green-600/5">
                        <CardContent className="p-5">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-muted-foreground">Weekly Tasks</p>
                                    <p className="text-3xl font-bold mt-1">{roadmap.completed_this_week}</p>
                                </div>
                                <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center">
                                    <CheckCheck className="w-6 h-6 text-green-500" />
                                </div>
                            </div>
                            <p className="text-sm text-muted-foreground mt-3">Completed this week</p>
                        </CardContent>
                    </Card>

                    <Card className="border-0 shadow-lg bg-gradient-to-br from-purple-500/10 to-purple-600/5">
                        <CardContent className="p-5">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-muted-foreground">Current Phase</p>
                                    <p className="text-lg font-bold mt-1">{roadmap.phase_name}</p>
                                </div>
                                <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center">
                                    <Target className="w-6 h-6 text-purple-500" />
                                </div>
                            </div>
                            <p className="text-sm text-muted-foreground mt-3">
                                Phase {roadmap.current_phase} of {roadmap.total_phases}
                            </p>
                        </CardContent>
                    </Card>
                </div>

                {/* Phase Progress */}
                {roadmap.phases.length > 0 && (
                    <Card className="border-0 shadow-lg mb-8">
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Calendar className="w-5 h-5 text-primary" />
                                Preparation Phases
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="flex items-center gap-4 overflow-x-auto pb-2">
                                {roadmap.phases.map((phase, index) => (
                                    <div
                                        key={index}
                                        className={`flex-shrink-0 p-4 rounded-xl border-2 min-w-[200px] transition-all ${phase.is_active
                                                ? 'border-primary bg-primary/5'
                                                : phase.is_completed
                                                    ? 'border-green-500 bg-green-500/5'
                                                    : 'border-muted'
                                            }`}
                                    >
                                        <div className="flex items-center gap-2 mb-2">
                                            {phase.is_completed ? (
                                                <CheckCircle className="w-5 h-5 text-green-500" />
                                            ) : phase.is_active ? (
                                                <Play className="w-5 h-5 text-primary" />
                                            ) : (
                                                <Circle className="w-5 h-5 text-muted-foreground" />
                                            )}
                                            <span className="font-semibold">{phase.name}</span>
                                        </div>
                                        <div className="text-xs text-muted-foreground mb-2">
                                            {new Date(phase.start_date).toLocaleDateString()} - {new Date(phase.end_date).toLocaleDateString()}
                                        </div>
                                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                                            <div
                                                className={`h-full transition-all ${phase.is_completed ? 'bg-green-500' : 'bg-primary'
                                                    }`}
                                                style={{ width: `${phase.progress}%` }}
                                            />
                                        </div>
                                        <div className="text-xs text-right mt-1 text-muted-foreground">
                                            {Math.round(phase.progress)}%
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Main Content Grid */}
                <div className="grid lg:grid-cols-3 gap-6">
                    {/* Today's Tasks */}
                    <div className="lg:col-span-2 space-y-6">
                        <Card className="border-0 shadow-lg">
                            <CardHeader className="border-b">
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <Zap className="w-5 h-5 text-yellow-500" />
                                        Today's Tasks
                                    </CardTitle>
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm text-muted-foreground">
                                            {completedTodayCount}/{totalTodayTasks}
                                        </span>
                                        <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-green-500 transition-all"
                                                style={{ width: `${todayProgress}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="p-0">
                                {roadmap.today_tasks.length === 0 ? (
                                    <div className="p-8 text-center">
                                        <Trophy className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
                                        <p className="font-semibold">All done for today!</p>
                                        <p className="text-sm text-muted-foreground">Great job! Keep up the momentum.</p>
                                    </div>
                                ) : (
                                    <div className="divide-y">
                                        {roadmap.today_tasks.map((task) => (
                                            <TaskItem
                                                key={task.id}
                                                task={task}
                                                onStatusChange={updateTaskStatus}
                                                isUpdating={updatingTask === task.id}
                                            />
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        {/* Upcoming Tasks */}
                        <Card className="border-0 shadow-lg">
                            <CardHeader className="border-b">
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <Calendar className="w-5 h-5 text-blue-500" />
                                    Upcoming Tasks
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                {roadmap.upcoming_tasks.length === 0 ? (
                                    <div className="p-8 text-center text-muted-foreground">
                                        No upcoming tasks scheduled
                                    </div>
                                ) : (
                                    <div className="divide-y">
                                        {roadmap.upcoming_tasks.slice(0, 5).map((task) => (
                                            <TaskItem
                                                key={task.id}
                                                task={task}
                                                onStatusChange={updateTaskStatus}
                                                isUpdating={updatingTask === task.id}
                                                showDate
                                            />
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* Sidebar */}
                    <div className="space-y-6">
                        {/* Revision Due */}
                        <Card className="border-0 shadow-lg">
                            <CardHeader className="border-b">
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <RotateCcw className="w-5 h-5 text-orange-500" />
                                    Revision Due
                                    {roadmap.revision_due.length > 0 && (
                                        <span className="ml-auto bg-orange-500/20 text-orange-600 text-xs font-medium px-2 py-1 rounded-full">
                                            {roadmap.revision_due.length}
                                        </span>
                                    )}
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                {roadmap.revision_due.length === 0 ? (
                                    <div className="p-6 text-center text-muted-foreground">
                                        <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
                                        <p className="text-sm">No revisions due!</p>
                                    </div>
                                ) : (
                                    <div className="divide-y">
                                        {roadmap.revision_due.map((task) => (
                                            <TaskItem
                                                key={task.id}
                                                task={task}
                                                onStatusChange={updateTaskStatus}
                                                isUpdating={updatingTask === task.id}
                                                compact
                                            />
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        {/* Daily Goal */}
                        <Card className="border-0 shadow-lg bg-gradient-to-br from-primary/10 to-transparent">
                            <CardContent className="p-6">
                                <div className="text-center">
                                    <Timer className="w-10 h-10 text-primary mx-auto mb-3" />
                                    <h3 className="font-semibold mb-1">Daily Goal</h3>
                                    <p className="text-3xl font-bold text-primary">{roadmap.daily_goal_hours}</p>
                                    <p className="text-sm text-muted-foreground">hours/day</p>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Quick Actions */}
                        <Card className="border-0 shadow-lg">
                            <CardHeader>
                                <CardTitle className="text-lg">Quick Actions</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <Button
                                    variant="outline"
                                    className="w-full justify-between group hover:bg-primary hover:text-primary-foreground"
                                    onClick={() => router.push('/quiz')}
                                >
                                    <span className="flex items-center gap-2">
                                        <Brain className="w-4 h-4" />
                                        Take a Quiz
                                    </span>
                                    <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                                </Button>
                                <Button
                                    variant="outline"
                                    className="w-full justify-between group hover:bg-primary hover:text-primary-foreground"
                                    onClick={() => router.push('/materials')}
                                >
                                    <span className="flex items-center gap-2">
                                        <BookOpen className="w-4 h-4" />
                                        Study Materials
                                    </span>
                                    <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                                </Button>
                                <Button
                                    variant="outline"
                                    className="w-full justify-between group hover:bg-primary hover:text-primary-foreground"
                                    onClick={() => router.push('/tutor')}
                                >
                                    <span className="flex items-center gap-2">
                                        <Newspaper className="w-4 h-4" />
                                        AI Tutor
                                    </span>
                                    <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                                </Button>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Task Item Component
function TaskItem({
    task,
    onStatusChange,
    isUpdating,
    showDate = false,
    compact = false
}: {
    task: Task;
    onStatusChange: (id: string, status: string) => void;
    isUpdating: boolean;
    showDate?: boolean;
    compact?: boolean;
}) {
    const typeConfig = taskTypeConfig[task.task_type] || taskTypeConfig.study;
    const StatusIcon = statusConfig[task.status]?.icon || Circle;
    const TypeIcon = typeConfig.icon;

    const handleClick = () => {
        if (task.status === 'pending') {
            onStatusChange(task.id, 'in_progress');
        } else if (task.status === 'in_progress') {
            onStatusChange(task.id, 'completed');
        }
    };

    return (
        <div
            className={`p-4 hover:bg-muted/50 transition-colors ${compact ? 'py-3' : ''}`}
        >
            <div className="flex items-start gap-3">
                <button
                    onClick={handleClick}
                    disabled={task.status === 'completed' || task.status === 'skipped' || isUpdating}
                    className={`mt-1 rounded-full p-1 transition-all ${task.status === 'completed'
                            ? 'text-green-500'
                            : task.status === 'in_progress'
                                ? 'text-yellow-500 hover:bg-yellow-500/20'
                                : 'text-muted-foreground hover:bg-muted'
                        }`}
                >
                    {isUpdating ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                        <StatusIcon className="w-5 h-5" />
                    )}
                </button>

                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${typeConfig.bgColor} ${typeConfig.color}`}>
                            <TypeIcon className="w-3 h-3" />
                            {typeConfig.label}
                        </span>
                        {task.topic_name && (
                            <span className="text-xs text-muted-foreground">{task.topic_name}</span>
                        )}
                    </div>
                    <h4 className={`font-medium mt-1 ${task.status === 'completed' ? 'line-through text-muted-foreground' : ''}`}>
                        {task.title}
                    </h4>
                    {!compact && task.description && (
                        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                            {task.description}
                        </p>
                    )}
                    <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                        {task.estimated_minutes && (
                            <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {task.estimated_minutes} min
                            </span>
                        )}
                        {showDate && task.scheduled_date && (
                            <span>{new Date(task.scheduled_date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                        )}
                        {task.scheduled_time_slot && (
                            <span className="capitalize">{task.scheduled_time_slot}</span>
                        )}
                    </div>
                </div>

                {task.status !== 'completed' && task.status !== 'skipped' && (
                    <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => onStatusChange(task.id, task.status === 'pending' ? 'in_progress' : 'completed')}
                        disabled={isUpdating}
                        className="shrink-0"
                    >
                        {task.status === 'pending' ? 'Start' : 'Complete'}
                        <ArrowRight className="w-4 h-4 ml-1" />
                    </Button>
                )}
            </div>
        </div>
    );
}
