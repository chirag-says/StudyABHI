'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/stores/auth-store';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
    BookOpen, Brain, Clock, Target, TrendingUp, Upload, MessageSquare,
    FileText, ChevronRight, CheckCircle, Circle, Loader2, Sparkles
} from 'lucide-react';
import api from '@/services/api';

interface DashboardData {
    stats: {
        study_hours_week: number;
        quizzes_completed: number;
        topics_covered: number;
        total_topics: number;
        avg_score: number;
    };
    today_tasks: {
        id: string;
        title: string;
        type: string;
        status: 'pending' | 'completed';
        estimated_minutes?: number;
    }[];
    recent_documents: {
        id: string;
        filename: string;
        created_at: string;
        status: string;
    }[];
    streak_days: number;
}

export default function DashboardPage() {
    const { user } = useAuthStore();
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDashboard();
    }, []);

    const fetchDashboard = async () => {
        try {
            const [statsRes, tasksRes, docsRes] = await Promise.all([
                api.get('/learning/stats').catch(() => ({ data: null })),
                api.get('/learning/roadmap/today').catch(() => ({ data: { tasks: [] } })),
                api.get('/documents?limit=3').catch(() => ({ data: { documents: [], items: [] } })),
            ]);

            // Map task_type to type for compatibility
            const tasks = (tasksRes.data?.tasks || []).map((t: any) => ({
                ...t,
                type: t.type || t.task_type || 'study',
            }));

            // Handle both documents and items properties
            const docs = docsRes.data?.documents || docsRes.data?.items || [];

            setData({
                stats: statsRes.data || {
                    study_hours_week: 0,
                    quizzes_completed: 0,
                    topics_covered: 0,
                    total_topics: 100,
                    avg_score: 0,
                },
                today_tasks: tasks,
                recent_documents: docs,
                streak_days: statsRes.data?.streak_days || 0,
            });
        } catch (error) {
            console.error('Failed to fetch dashboard:', error);
            // Set mock data for demo
            setData({
                stats: {
                    study_hours_week: 24.5,
                    quizzes_completed: 18,
                    topics_covered: 42,
                    total_topics: 120,
                    avg_score: 78,
                },
                today_tasks: [
                    { id: '1', title: 'Read Indian Polity Ch. 3', type: 'study', status: 'completed', estimated_minutes: 45 },
                    { id: '2', title: 'Quiz: Fundamental Rights', type: 'quiz', status: 'pending', estimated_minutes: 20 },
                    { id: '3', title: 'Review yesterday\'s notes', type: 'revision', status: 'pending', estimated_minutes: 15 },
                ],
                recent_documents: [
                    { id: '1', filename: 'NCERT_Polity.pdf', created_at: new Date().toISOString(), status: 'completed' },
                    { id: '2', filename: 'Economics_Notes.pdf', created_at: new Date(Date.now() - 86400000).toISOString(), status: 'completed' },
                ],
                streak_days: 5,
            });
        } finally {
            setLoading(false);
        }
    };

    const updateTaskStatus = async (taskId: string, completed: boolean) => {
        try {
            await api.patch(`/learning/roadmap/task/${taskId}`, {
                status: completed ? 'completed' : 'pending'
            });

            setData(prev => prev ? {
                ...prev,
                today_tasks: prev.today_tasks.map(t =>
                    t.id === taskId ? { ...t, status: completed ? 'completed' : 'pending' } : t
                )
            } : null);
        } catch (error) {
            console.error('Failed to update task:', error);
        }
    };

    const getGreeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good morning';
        if (hour < 17) return 'Good afternoon';
        return 'Good evening';
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

    const stats = data?.stats || { study_hours_week: 0, quizzes_completed: 0, topics_covered: 0, total_topics: 100, avg_score: 0 };
    const completedTasks = data?.today_tasks.filter(t => t.status === 'completed').length || 0;
    const totalTasks = data?.today_tasks.length || 0;

    return (
        <div className="p-6 lg:p-8 space-y-8">
            {/* Welcome Header */}
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold">
                        {getGreeting()}, {user?.full_name?.split(' ')[0] || 'Aspirant'}! 👋
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Here's your study progress for today
                    </p>
                </div>
                {data?.streak_days ? (
                    <div className="flex items-center gap-2 bg-gradient-to-r from-orange-500/10 to-yellow-500/10 px-4 py-2 rounded-full">
                        <span className="text-2xl">🔥</span>
                        <span className="font-bold text-orange-600 dark:text-orange-400">
                            {data.streak_days} day streak!
                        </span>
                    </div>
                ) : null}
            </div>

            {/* Stats Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-200 dark:border-blue-800">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Study Hours
                        </CardTitle>
                        <Clock className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.study_hours_week}h</div>
                        <p className="text-xs text-muted-foreground">This week</p>
                    </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border-purple-200 dark:border-purple-800">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Quizzes Done
                        </CardTitle>
                        <Brain className="h-4 w-4 text-purple-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.quizzes_completed}</div>
                        <p className="text-xs text-muted-foreground">Total attempts</p>
                    </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-green-500/10 to-green-600/5 border-green-200 dark:border-green-800">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Topics Covered
                        </CardTitle>
                        <BookOpen className="h-4 w-4 text-green-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.topics_covered}</div>
                        <p className="text-xs text-muted-foreground">
                            {Math.round((stats.topics_covered / stats.total_topics) * 100)}% complete
                        </p>
                    </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-amber-500/10 to-amber-600/5 border-amber-200 dark:border-amber-800">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Avg. Score
                        </CardTitle>
                        <Target className="h-4 w-4 text-amber-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.avg_score}%</div>
                        <p className="text-xs text-muted-foreground">Last 10 quizzes</p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
                {/* Today's Study Plan */}
                <Card className="lg:col-span-2">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle>Today's Study Plan</CardTitle>
                            <CardDescription>
                                {completedTasks}/{totalTasks} tasks completed
                            </CardDescription>
                        </div>
                        <Button variant="ghost" size="sm" asChild>
                            <Link href="/roadmap">
                                View all
                                <ChevronRight className="w-4 h-4 ml-1" />
                            </Link>
                        </Button>
                    </CardHeader>
                    <CardContent>
                        {data?.today_tasks.length ? (
                            <div className="space-y-3">
                                {data.today_tasks.map((task) => (
                                    <div
                                        key={task.id}
                                        className={`flex items-center gap-4 p-3 rounded-lg border transition-colors ${task.status === 'completed' ? 'bg-muted/50 opacity-60' : 'hover:bg-muted/50'
                                            }`}
                                    >
                                        <button
                                            onClick={() => updateTaskStatus(task.id, task.status !== 'completed')}
                                            className="flex-shrink-0"
                                        >
                                            {task.status === 'completed' ? (
                                                <CheckCircle className="w-5 h-5 text-green-500" />
                                            ) : (
                                                <Circle className="w-5 h-5 text-muted-foreground hover:text-primary" />
                                            )}
                                        </button>
                                        <div className="flex-1">
                                            <p className={`font-medium ${task.status === 'completed' ? 'line-through' : ''}`}>
                                                {task.title}
                                            </p>
                                            {task.estimated_minutes && (
                                                <p className="text-sm text-muted-foreground">
                                                    ~{task.estimated_minutes} min
                                                </p>
                                            )}
                                        </div>
                                        <span className={`text-xs px-2 py-1 rounded-full ${task.type === 'quiz' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' :
                                            task.type === 'revision' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                                'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                                            }`}>
                                            {task.type}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">
                                <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500" />
                                <p>No tasks for today!</p>
                                <p className="text-sm">Upload a PDF to get started</p>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Quick Actions + Recent Documents */}
                <div className="space-y-6">
                    {/* Quick Actions */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Quick Actions</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <Button className="w-full justify-start" asChild>
                                <Link href="/upload">
                                    <Upload className="w-4 h-4 mr-2" />
                                    Upload Study Material
                                </Link>
                            </Button>
                            <Button variant="outline" className="w-full justify-start" asChild>
                                <Link href="/study">
                                    <Sparkles className="w-4 h-4 mr-2" />
                                    Ask AI Tutor
                                </Link>
                            </Button>
                            <Button variant="outline" className="w-full justify-start" asChild>
                                <Link href="/quiz">
                                    <Brain className="w-4 h-4 mr-2" />
                                    Take a Quiz
                                </Link>
                            </Button>
                        </CardContent>
                    </Card>

                    {/* Recent Documents */}
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle>Recent Uploads</CardTitle>
                            <Button variant="ghost" size="sm" asChild>
                                <Link href="/upload">
                                    View all
                                </Link>
                            </Button>
                        </CardHeader>
                        <CardContent>
                            {data?.recent_documents.length ? (
                                <div className="space-y-3">
                                    {data.recent_documents.map((doc) => (
                                        <Link
                                            key={doc.id}
                                            href={`/study/${doc.id}`}
                                            className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted transition-colors"
                                        >
                                            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                                                <FileText className="w-5 h-5 text-primary" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="font-medium truncate text-sm">{doc.filename}</p>
                                                <p className="text-xs text-muted-foreground">
                                                    {formatDate(doc.created_at)}
                                                </p>
                                            </div>
                                            <ChevronRight className="w-4 h-4 text-muted-foreground" />
                                        </Link>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-4 text-muted-foreground text-sm">
                                    No documents yet
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Motivation Quote */}
            <Card className="bg-gradient-to-r from-primary/5 to-primary/10 border-primary/20">
                <CardContent className="py-6">
                    <p className="text-center italic text-muted-foreground">
                        "The will to succeed is important, but what's more important is the will to prepare."
                    </p>
                    <p className="text-center text-sm text-muted-foreground mt-2">— Bobby Knight</p>
                </CardContent>
            </Card>
        </div>
    );
}
