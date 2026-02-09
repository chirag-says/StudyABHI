'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
    BookOpen,
    Brain,
    Camera,
    CameraOff,
    ChevronLeft,
    ChevronRight,
    Clock,
    Eye,
    FileText,
    LayoutGrid,
    Maximize2,
    MessageSquare,
    Minimize2,
    PanelLeftClose,
    PanelLeftOpen,
    Settings,
    Sparkles,
    Target,
    X,
    ExternalLink,
    Download
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
    FocusTracker,
    StudyTimer,
    QuickQuiz,
    StudyStats,
    MaterialsPanel,
    StudyChat
} from '@/components/study-room';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

type ViewMode = 'full' | 'focus' | 'quiz';
type PanelSection = 'materials' | 'quiz' | 'chat';

// PDF Viewer Modal Component
function PDFViewerModal({
    isOpen,
    onClose,
    pdfUrl,
    title
}: {
    isOpen: boolean;
    onClose: () => void;
    pdfUrl: string;
    title: string;
}) {
    const [isMobile, setIsMobile] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);

    useEffect(() => {
        const checkMobile = () => setIsMobile(window.innerWidth < 768);
        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'unset';
        }
        return () => {
            document.body.style.overflow = 'unset';
        };
    }, [isOpen]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            {/* Close on backdrop click */}
            <div className="absolute inset-0" onClick={onClose} />

            {isMobile ? (
                // iPhone 14 Frame for Mobile
                <div className="relative z-10 animate-in fade-in zoom-in-95 duration-200">
                    <div className="relative mx-auto" style={{ width: '320px' }}>
                        {/* iPhone Frame */}
                        <div className="relative bg-black rounded-[45px] p-3 shadow-2xl">
                            {/* Dynamic Island */}
                            <div className="absolute top-5 left-1/2 -translate-x-1/2 w-24 h-7 bg-black rounded-full z-20" />

                            {/* Screen */}
                            <div className="relative bg-white rounded-[35px] overflow-hidden" style={{ height: '650px' }}>
                                {/* Status Bar */}
                                <div className="absolute top-0 left-0 right-0 h-12 bg-gradient-to-b from-gray-200 to-transparent z-10 flex items-center justify-between px-6 pt-2">
                                    <span className="text-xs font-semibold">9:41</span>
                                    <div className="flex items-center gap-1">
                                        <div className="w-4 h-2 border border-current rounded-sm">
                                            <div className="w-full h-full bg-current rounded-sm" style={{ width: '80%' }} />
                                        </div>
                                    </div>
                                </div>

                                {/* Header Bar */}
                                <div className="absolute top-12 left-0 right-0 h-12 bg-white border-b flex items-center justify-between px-4 z-10">
                                    <button onClick={onClose} className="text-primary font-medium text-sm">
                                        Close
                                    </button>
                                    <span className="text-sm font-semibold truncate max-w-[150px]">{title}</span>
                                    <button
                                        onClick={() => window.open(pdfUrl, '_blank')}
                                        className="text-primary"
                                    >
                                        <ExternalLink className="w-4 h-4" />
                                    </button>
                                </div>

                                {/* PDF Content */}
                                <iframe
                                    src={pdfUrl}
                                    className="w-full h-full pt-24"
                                    style={{ border: 'none' }}
                                />

                                {/* Home Indicator */}
                                <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1 bg-black/20 rounded-full" />
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                // MacBook Frame for Desktop
                <div className={cn(
                    "relative z-10 animate-in fade-in zoom-in-95 duration-200 transition-all",
                    isFullscreen ? "w-full h-full" : "w-[90%] max-w-5xl"
                )}>
                    <div className={cn(
                        "relative mx-auto",
                        isFullscreen ? "w-full h-full" : ""
                    )}>
                        {/* MacBook Frame */}
                        <div className={cn(
                            "bg-[#2D2D2D] shadow-2xl",
                            isFullscreen ? "rounded-none" : "rounded-xl"
                        )}>
                            {/* Menu Bar */}
                            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700">
                                <div className="flex items-center gap-2">
                                    {/* Traffic Lights */}
                                    <button
                                        onClick={onClose}
                                        className="w-3 h-3 rounded-full bg-[#FF5F57] hover:bg-[#FF5F57]/80 flex items-center justify-center group"
                                    >
                                        <X className="w-2 h-2 text-[#4A0002] opacity-0 group-hover:opacity-100" />
                                    </button>
                                    <button className="w-3 h-3 rounded-full bg-[#FEBC2E] hover:bg-[#FEBC2E]/80 flex items-center justify-center group">
                                        <Minimize2 className="w-2 h-2 text-[#985700] opacity-0 group-hover:opacity-100" />
                                    </button>
                                    <button
                                        onClick={() => setIsFullscreen(!isFullscreen)}
                                        className="w-3 h-3 rounded-full bg-[#28C840] hover:bg-[#28C840]/80 flex items-center justify-center group"
                                    >
                                        <Maximize2 className="w-2 h-2 text-[#006500] opacity-0 group-hover:opacity-100" />
                                    </button>
                                </div>

                                {/* Title */}
                                <div className="flex-1 text-center">
                                    <span className="text-gray-300 text-sm font-medium truncate">{title}</span>
                                </div>

                                {/* Actions */}
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => window.open(pdfUrl, '_blank')}
                                        className="text-gray-400 hover:text-white p-1"
                                        title="Open in new tab"
                                    >
                                        <ExternalLink className="w-4 h-4" />
                                    </button>
                                    <a
                                        href={pdfUrl}
                                        download
                                        className="text-gray-400 hover:text-white p-1"
                                        title="Download"
                                    >
                                        <Download className="w-4 h-4" />
                                    </a>
                                </div>
                            </div>

                            {/* Content Area */}
                            <div className={cn(
                                "bg-[#1E1E1E]",
                                isFullscreen ? "h-[calc(100vh-40px)]" : "h-[70vh]"
                            )}>
                                <iframe
                                    src={pdfUrl}
                                    className="w-full h-full"
                                    style={{ border: 'none' }}
                                />
                            </div>
                        </div>

                        {/* MacBook Bottom Stand (only when not fullscreen) */}
                        {!isFullscreen && (
                            <div className="relative mx-auto">
                                <div className="w-1/4 h-3 mx-auto bg-gradient-to-b from-[#2D2D2D] to-[#1a1a1a] rounded-b-lg" />
                                <div className="w-1/3 h-1 mx-auto bg-[#1a1a1a] rounded-b-xl" />
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default function StudyRoomPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const documentId = searchParams?.get('document');
    const documentName = searchParams?.get('name');

    // State
    const [focusTrackingEnabled, setFocusTrackingEnabled] = useState(false);
    const [showPreview, setShowPreview] = useState(false);
    const [leftPanelOpen, setLeftPanelOpen] = useState(true);
    const [rightPanelOpen, setRightPanelOpen] = useState(true);
    const [activeRightPanel, setActiveRightPanel] = useState<PanelSection>('chat');
    const [viewMode, setViewMode] = useState<ViewMode>('full');
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [sessionStartTime, setSessionStartTime] = useState<Date | null>(null);
    const [showSettingsModal, setShowSettingsModal] = useState(false);
    const [selectedMaterialUrl, setSelectedMaterialUrl] = useState<string | null>(null);
    const [selectedMaterialName, setSelectedMaterialName] = useState<string | null>(null);
    const [timerAutoStart, setTimerAutoStart] = useState(false);
    const [pdfViewer, setPdfViewer] = useState<{ isOpen: boolean; url: string; title: string }>({
        isOpen: false,
        url: '',
        title: ''
    });

    // Session tracking
    const [sessionStats, setSessionStats] = useState({
        startTime: null as Date | null,
        focusTime: 0,
        distractions: 0,
        questionsAnswered: 0,
        correctAnswers: 0
    });

    // Initialize session
    useEffect(() => {
        const startTime = new Date();
        setSessionStartTime(startTime);
        setSessionStats(prev => ({ ...prev, startTime }));

        // Request fullscreen hint for focus mode
        if (viewMode === 'focus') {
            document.body.requestFullscreen?.().catch(() => { });
        }

        return () => {
            // Save session on unmount
            console.log('Session ended:', sessionStats);
        };
    }, []);

    // Handle focus changes
    const handleFocusChange = useCallback((isFocused: boolean) => {
        if (isFocused) {
            // Resume focus time tracking
        } else {
            // Pause focus time tracking
        }
    }, []);

    // Handle distraction
    const handleDistraction = useCallback(() => {
        setSessionStats(prev => ({
            ...prev,
            distractions: prev.distractions + 1
        }));

        // Optional: Show distraction notification
        if (Notification.permission === 'granted') {
            // Don't spam notifications, but can add a subtle one
        }
    }, []);

    // Update focus time
    useEffect(() => {
        if (!focusTrackingEnabled) return;

        const interval = setInterval(() => {
            setSessionStats(prev => ({
                ...prev,
                focusTime: prev.focusTime + 1
            }));
        }, 1000);

        return () => clearInterval(interval);
    }, [focusTrackingEnabled]);

    // Handle quiz answer
    const handleQuizAnswer = (isCorrect: boolean) => {
        setSessionStats(prev => ({
            ...prev,
            questionsAnswered: prev.questionsAnswered + 1,
            correctAnswers: prev.correctAnswers + (isCorrect ? 1 : 0)
        }));
    };

    // Toggle fullscreen
    const toggleFullscreen = () => {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen?.();
            setIsFullscreen(true);
        } else {
            document.exitFullscreen?.();
            setIsFullscreen(false);
        }
    };

    const handleMaterialSelect = (material: any) => {
        // Set the selected material URL and name
        setSelectedMaterialUrl(material.url);
        setSelectedMaterialName(material.name);

        // Open PDF overlay
        setPdfViewer({
            isOpen: true,
            url: material.url,
            title: material.name
        });

        // Auto-start the timer
        setTimerAutoStart(true);

        // Update URL with document info
        router.push(`/study-room?document=${material.categoryId}-${material.filename}&name=${encodeURIComponent(material.name)}`, { scroll: false });
    };

    const closePdfViewer = () => {
        setPdfViewer({ isOpen: false, url: '', title: '' });
    };

    return (
        <div className="h-screen flex flex-col bg-background overflow-hidden">
            {/* PDF Viewer Modal */}
            <PDFViewerModal
                isOpen={pdfViewer.isOpen}
                onClose={closePdfViewer}
                pdfUrl={pdfViewer.url}
                title={pdfViewer.title}
            />
            {/* Top Bar */}
            <header className="h-14 border-b flex items-center justify-between px-4 bg-card/50 backdrop-blur-sm flex-shrink-0">
                <div className="flex items-center gap-4">
                    <Link href="/dashboard" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                        <ChevronLeft className="w-5 h-5" />
                        <span className="hidden sm:inline text-sm">Dashboard</span>
                    </Link>

                    <div className="h-6 w-px bg-border" />

                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center">
                            <BookOpen className="w-4 h-4 text-white" />
                        </div>
                        <div className="hidden sm:block">
                            <h1 className="font-semibold text-sm">Study Room</h1>
                            <p className="text-xs text-muted-foreground">
                                {documentName || 'Focus Mode Active'}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Center - View Mode Toggle */}
                <div className="hidden md:flex items-center gap-1 p-1 bg-muted rounded-lg">
                    {[
                        { mode: 'full' as ViewMode, icon: LayoutGrid, label: 'Full' },
                        { mode: 'focus' as ViewMode, icon: Target, label: 'Focus' },
                        { mode: 'quiz' as ViewMode, icon: Brain, label: 'Quiz' },
                    ].map(({ mode, icon: Icon, label }) => (
                        <button
                            key={mode}
                            onClick={() => setViewMode(mode)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${viewMode === mode
                                ? 'bg-background shadow-sm'
                                : 'hover:bg-background/50'
                                }`}
                        >
                            <Icon className="w-4 h-4" />
                            <span>{label}</span>
                        </button>
                    ))}
                </div>

                {/* Right Actions */}
                <div className="flex items-center gap-2">
                    {/* Focus Tracking Toggle */}
                    <Button
                        variant={focusTrackingEnabled ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setFocusTrackingEnabled(!focusTrackingEnabled)}
                        className={focusTrackingEnabled ? 'bg-green-600 hover:bg-green-700' : ''}
                    >
                        {focusTrackingEnabled ? (
                            <>
                                <Eye className="w-4 h-4 mr-1.5" />
                                <span className="hidden sm:inline">Tracking On</span>
                            </>
                        ) : (
                            <>
                                <CameraOff className="w-4 h-4 mr-1.5" />
                                <span className="hidden sm:inline">Tracking Off</span>
                            </>
                        )}
                    </Button>

                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={toggleFullscreen}
                        title="Toggle Fullscreen"
                    >
                        {isFullscreen ? (
                            <Minimize2 className="w-4 h-4" />
                        ) : (
                            <Maximize2 className="w-4 h-4" />
                        )}
                    </Button>

                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setShowSettingsModal(true)}
                    >
                        <Settings className="w-4 h-4" />
                    </Button>
                </div>
            </header>

            {/* Main Content */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Panel - Materials */}
                {viewMode !== 'focus' && (
                    <>
                        <aside className={`border-r bg-card/50 transition-all duration-300 flex-shrink-0 ${leftPanelOpen ? 'w-72' : 'w-0'
                            } overflow-hidden`}>
                            <MaterialsPanel
                                onMaterialSelect={handleMaterialSelect}
                                currentMaterialId={documentId || undefined}
                            />
                        </aside>

                        {/* Left Panel Toggle */}
                        <button
                            onClick={() => setLeftPanelOpen(!leftPanelOpen)}
                            className="flex-shrink-0 w-6 flex items-center justify-center hover:bg-muted transition-colors border-r"
                        >
                            {leftPanelOpen ? (
                                <PanelLeftClose className="w-4 h-4 text-muted-foreground" />
                            ) : (
                                <PanelLeftOpen className="w-4 h-4 text-muted-foreground" />
                            )}
                        </button>
                    </>
                )}

                {/* Center - Main Study Area */}
                <main className="flex-1 flex flex-col overflow-hidden p-4 md:p-6">
                    <div className="flex-1 grid gap-4 md:gap-6 overflow-auto" style={{
                        gridTemplateColumns: viewMode === 'focus'
                            ? '1fr'
                            : viewMode === 'quiz'
                                ? '1fr'
                                : 'minmax(0, 1fr) 320px'
                    }}>
                        {/* Primary Content Area */}
                        <div className="space-y-4 md:space-y-6">
                            {/* Focus Tracker - Prominent when enabled */}
                            {focusTrackingEnabled && (
                                <FocusTracker
                                    enabled={focusTrackingEnabled}
                                    showPreview={showPreview}
                                    onFocusChange={handleFocusChange}
                                    onDistraction={handleDistraction}
                                />
                            )}

                            {/* Study Timer */}
                            {/* Study Timer */}
                            <StudyTimer
                                key={documentId || 'timer'}
                                autoStart={timerAutoStart}
                                onSessionComplete={(mode, duration) => {
                                    console.log(`Completed ${mode} session: ${duration}s`);
                                }}
                                onModeChange={(mode) => {
                                    console.log(`Switched to ${mode} mode`);
                                }}
                            />

                            {/* Study Stats */}
                            <StudyStats currentSession={sessionStats} />
                        </div>

                        {/* Secondary Content - Quiz or Chat */}
                        {viewMode !== 'focus' && (
                            <div className="space-y-4 md:space-y-6 overflow-hidden">
                                <QuickQuiz documentId={documentId || undefined} />
                            </div>
                        )}


                    </div>
                </main>

                {/* Right Panel Toggle */}
                {viewMode === 'full' && (
                    <>
                        <button
                            onClick={() => setRightPanelOpen(!rightPanelOpen)}
                            className="flex-shrink-0 w-6 flex items-center justify-center hover:bg-muted transition-colors border-l"
                        >
                            {rightPanelOpen ? (
                                <ChevronRight className="w-4 h-4 text-muted-foreground" />
                            ) : (
                                <ChevronLeft className="w-4 h-4 text-muted-foreground" />
                            )}
                        </button>

                        {/* Right Panel - Chat */}
                        <aside className={`border-l bg-card/50 transition-all duration-300 flex-shrink-0 ${rightPanelOpen ? 'w-80' : 'w-0'
                            } overflow-hidden`}>
                            <div className="h-full">
                                <StudyChat
                                    documentId={documentId || undefined}
                                    documentName={documentName || undefined}
                                />
                            </div>
                        </aside>
                    </>
                )}
            </div>

            {/* Settings Modal */}
            {showSettingsModal && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-card rounded-2xl w-full max-w-md p-6 max-h-[80vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-bold">Study Room Settings</h2>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => setShowSettingsModal(false)}
                            >
                                <X className="w-5 h-5" />
                            </Button>
                        </div>

                        <div className="space-y-6">
                            {/* Focus Tracking Settings */}
                            <div>
                                <h3 className="font-semibold mb-3 flex items-center gap-2">
                                    <Eye className="w-4 h-4" />
                                    Focus Tracking
                                </h3>
                                <div className="space-y-3">
                                    <label className="flex items-center justify-between p-3 rounded-lg bg-muted">
                                        <span className="text-sm">Enable camera tracking</span>
                                        <input
                                            type="checkbox"
                                            checked={focusTrackingEnabled}
                                            onChange={(e) => setFocusTrackingEnabled(e.target.checked)}
                                            className="w-4 h-4"
                                        />
                                    </label>
                                    <label className="flex items-center justify-between p-3 rounded-lg bg-muted">
                                        <span className="text-sm">Show camera preview</span>
                                        <input
                                            type="checkbox"
                                            checked={showPreview}
                                            onChange={(e) => setShowPreview(e.target.checked)}
                                            className="w-4 h-4"
                                        />
                                    </label>
                                </div>
                            </div>

                            {/* Notifications */}
                            <div>
                                <h3 className="font-semibold mb-3 flex items-center gap-2">
                                    <MessageSquare className="w-4 h-4" />
                                    Notifications
                                </h3>
                                <div className="space-y-3">
                                    <label className="flex items-center justify-between p-3 rounded-lg bg-muted">
                                        <span className="text-sm">Distraction alerts</span>
                                        <input type="checkbox" defaultChecked className="w-4 h-4" />
                                    </label>
                                    <label className="flex items-center justify-between p-3 rounded-lg bg-muted">
                                        <span className="text-sm">Break reminders</span>
                                        <input type="checkbox" defaultChecked className="w-4 h-4" />
                                    </label>
                                </div>
                            </div>

                            {/* Display */}
                            <div>
                                <h3 className="font-semibold mb-3 flex items-center gap-2">
                                    <LayoutGrid className="w-4 h-4" />
                                    Display
                                </h3>
                                <div className="space-y-3">
                                    <label className="flex items-center justify-between p-3 rounded-lg bg-muted">
                                        <span className="text-sm">Dark mode</span>
                                        <input type="checkbox" defaultChecked className="w-4 h-4" />
                                    </label>
                                    <label className="flex items-center justify-between p-3 rounded-lg bg-muted">
                                        <span className="text-sm">Compact view</span>
                                        <input type="checkbox" className="w-4 h-4" />
                                    </label>
                                </div>
                            </div>
                        </div>

                        <div className="mt-6 pt-6 border-t">
                            <Button
                                className="w-full"
                                onClick={() => setShowSettingsModal(false)}
                            >
                                Save Settings
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* Floating Chat Button (when chat panel is closed) */}
            {!rightPanelOpen && viewMode === 'full' && (
                <button
                    onClick={() => setRightPanelOpen(true)}
                    className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-gradient-to-r from-primary to-blue-600 text-white shadow-lg hover:shadow-xl transition-all flex items-center justify-center z-40"
                >
                    <MessageSquare className="w-6 h-6" />
                </button>
            )}
        </div>
    );
}
