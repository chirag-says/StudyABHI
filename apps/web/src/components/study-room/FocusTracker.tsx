'use client';

import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
    Camera,
    CameraOff,
    Eye,
    EyeOff,
    AlertTriangle,
    Loader2,
    Activity,
    Brain,
    Shield,
    ZapOff,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import attentionService from '@/services/attention';

import {
    // Math utilities
    calculateAverageEAR,
    estimateGaze,
    getMostFrequent,
    classifyFatigue,
    computeDistractionScore,
    // Constants
    EAR_THRESHOLD,
    BLINK_MIN_FRAMES,
    BLINK_MAX_FRAMES,
    FOCUS_BUFFER_SIZE,
    FRAME_INTERVAL_MS,
    NO_FACE_AWAY_FRAMES,
    // Types
    type FocusState,
    type FatigueState,
    type GazeResult,
} from './focus-tracker-utils';

// ────────────────────────────────────────────────────────────
// Props & exported types
// ────────────────────────────────────────────────────────────

interface FocusTrackerProps {
    onFocusChange?: (isFocused: boolean) => void;
    onDistraction?: () => void;
    enabled: boolean;
    showPreview?: boolean;
}

interface FocusStats {
    focusedTime: number;
    distractionCount: number;
    lastDistractionTime: Date | null;
    currentStreak: number;
    longestStreak: number;
}

// Extended metrics shown in the UI
interface ExtendedMetrics {
    blinkCount: number;
    blinkRate: number; // blinks / min
    fatigue: FatigueState;
    distractionScore: number;
    eyeClosedDurationS: number;
    gazeSwitchFreq: number;
    lookAwayDurationS: number;
}

const INITIAL_METRICS: ExtendedMetrics = {
    blinkCount: 0,
    blinkRate: 0,
    fatigue: 'alert',
    distractionScore: 0,
    eyeClosedDurationS: 0,
    gazeSwitchFreq: 0,
    lookAwayDurationS: 0,
};

// ────────────────────────────────────────────────────────────
// Component
// ────────────────────────────────────────────────────────────

export function FocusTracker({
    onFocusChange,
    onDistraction,
    enabled,
    showPreview = false,
}: FocusTrackerProps) {
    // ── DOM refs ──
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    // ── Lifecycle refs ──
    const streamRef = useRef<MediaStream | null>(null);
    const landmarkerRef = useRef<any>(null); // FaceLandmarker instance
    const animationRef = useRef<number | null>(null);
    const isRunningRef = useRef(false);
    const lastFrameTimeRef = useRef(0);

    // ── Detection counters (refs to avoid re-renders) ──
    const noFaceCountRef = useRef(0);
    const closedEyeFramesRef = useRef(0);
    const eyeClosedStartRef = useRef<number | null>(null);

    // Blink tracking
    const blinkCountRef = useRef(0);
    const blinkTimestampsRef = useRef<number[]>([]); // for rolling blink rate

    // Gaze tracking
    const lastGazeDirectionRef = useRef<string>('focused');
    const gazeSwitchCountRef = useRef(0);
    const gazeSwitchTimestampsRef = useRef<number[]>([]);
    const lookAwayStartRef = useRef<number | null>(null);
    const totalLookAwayMsRef = useRef(0);

    // No-face ratio tracking
    const recentFramesRef = useRef<boolean[]>([]); // true = face present

    // Smoothing buffer
    const focusBufferRef = useRef<FocusState[]>([]);
    const lastEmittedStateRef = useRef<FocusState>('focused');
    const lastFocusedRef = useRef(true);

    // Session start timestamp
    const sessionStartRef = useRef<number>(Date.now());

    // ── React state (only updated when smoothed value changes) ──
    const [isModelLoading, setIsModelLoading] = useState(false);
    const [isModelReady, setIsModelReady] = useState(false);
    const [isCameraActive, setIsCameraActive] = useState(false);
    const [cameraError, setCameraError] = useState<string | null>(null);
    const [currentFocus, setCurrentFocus] = useState<FocusState>('focused');
    const [metrics, setMetrics] = useState<ExtendedMetrics>(INITIAL_METRICS);
    const [stats, setStats] = useState<FocusStats>({
        focusedTime: 0,
        distractionCount: 0,
        lastDistractionTime: null,
        currentStreak: 0,
        longestStreak: 0,
    });

    // ────────────────────────────────────────────────────────────
    // 1. Load MediaPipe FaceLandmarker
    // ────────────────────────────────────────────────────────────

    const loadModel = useCallback(async () => {
        if (landmarkerRef.current) return;

        setIsModelLoading(true);
        try {
            const vision = await import('@mediapipe/tasks-vision');
            const { FaceLandmarker, FilesetResolver } = vision;

            const filesetResolver = await FilesetResolver.forVisionTasks(
                'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.32/wasm',
            );

            const landmarker = await FaceLandmarker.createFromOptions(filesetResolver, {
                baseOptions: {
                    modelAssetPath:
                        'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
                    delegate: 'GPU',
                },
                runningMode: 'VIDEO',
                numFaces: 1,
                outputFaceBlendshapes: false,
                outputFacialTransformationMatrixes: false,
            });

            landmarkerRef.current = landmarker;
            setIsModelReady(true);
            console.log('[FocusTracker] FaceLandmarker loaded ✓');
        } catch (error) {
            console.error('[FocusTracker] Model load error:', error);
            setCameraError('Failed to load the AI model. Please refresh the page.');
        } finally {
            setIsModelLoading(false);
        }
    }, []);

    // ────────────────────────────────────────────────────────────
    // 2. Camera start / stop
    // ────────────────────────────────────────────────────────────

    const startCamera = useCallback(async () => {
        if (!enabled) return;
        if (!navigator.mediaDevices?.getUserMedia) {
            setCameraError('Camera API not available (secure context required).');
            return;
        }

        try {
            setCameraError(null);

            let stream: MediaStream;
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
                });
            } catch {
                console.warn('[FocusTracker] Ideal constraints failed, trying basic');
                stream = await navigator.mediaDevices.getUserMedia({ video: true });
            }

            streamRef.current = stream;

            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                try {
                    await videoRef.current.play();
                    setIsCameraActive(true);
                    console.log('[FocusTracker] Camera started ✓');
                } catch (e: any) {
                    if (e.name === 'AbortError' || e.message?.includes('interrupted')) return;
                    throw e;
                }
            }
        } catch (error: any) {
            console.error('[FocusTracker] Camera error:', error);
            if (error.name === 'NotAllowedError') {
                setCameraError('Camera access denied. Please allow camera access in browser settings.');
            } else if (error.name === 'NotFoundError') {
                setCameraError('No camera found. Please connect a camera.');
            } else if (error.name === 'NotReadableError') {
                setCameraError('Camera is in use by another application.');
            } else {
                setCameraError(`Camera error: ${error.message || error.name || 'Unknown'}`);
            }
        }
    }, [enabled]);

    const stopCamera = useCallback(() => {
        isRunningRef.current = false;

        if (videoRef.current) {
            videoRef.current.pause();
            videoRef.current.srcObject = null;
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach((t) => t.stop());
            streamRef.current = null;
        }
        if (animationRef.current) {
            cancelAnimationFrame(animationRef.current);
            animationRef.current = null;
        }
        setIsCameraActive(false);
    }, []);

    // ────────────────────────────────────────────────────────────
    // 3. Core detection loop (rAF, throttled to ~10 FPS)
    // ────────────────────────────────────────────────────────────

    const runDetection = useCallback(() => {
        if (!isRunningRef.current) return;

        const video = videoRef.current;
        const landmarker = landmarkerRef.current;

        if (!video || !landmarker || !streamRef.current || video.readyState < 2) {
            animationRef.current = requestAnimationFrame(runDetection);
            return;
        }

        // ── Throttle to TARGET_FPS ──
        const now = performance.now();
        if (now - lastFrameTimeRef.current < FRAME_INTERVAL_MS) {
            animationRef.current = requestAnimationFrame(runDetection);
            return;
        }
        lastFrameTimeRef.current = now;

        try {
            // ── Run FaceLandmarker ──
            const result = landmarker.detectForVideo(video, now);
            const hasFace = result?.faceLandmarks?.length > 0;

            // Track face-presence ratio
            recentFramesRef.current.push(hasFace);
            if (recentFramesRef.current.length > 100) recentFramesRef.current.shift();

            let rawState: FocusState;

            if (!hasFace) {
                // ── No face detected ──
                noFaceCountRef.current++;
                rawState = noFaceCountRef.current > NO_FACE_AWAY_FRAMES ? 'away' : 'focused';
            } else {
                noFaceCountRef.current = 0;
                const landmarks = result.faceLandmarks[0];

                // ── EAR → eye openness ──
                const ear = calculateAverageEAR(landmarks);
                const eyesClosed = ear < EAR_THRESHOLD;

                // ── Blink detection ──
                if (eyesClosed) {
                    closedEyeFramesRef.current++;
                    if (eyeClosedStartRef.current === null) {
                        eyeClosedStartRef.current = now;
                    }
                } else {
                    const closedFrames = closedEyeFramesRef.current;
                    if (closedFrames >= BLINK_MIN_FRAMES && closedFrames <= BLINK_MAX_FRAMES) {
                        // Valid blink
                        blinkCountRef.current++;
                        blinkTimestampsRef.current.push(now);
                    }
                    closedEyeFramesRef.current = 0;
                    eyeClosedStartRef.current = null;
                }

                // Prune old blink timestamps (keep last 60 s)
                const sixtySecsAgo = now - 60_000;
                blinkTimestampsRef.current = blinkTimestampsRef.current.filter((t) => t > sixtySecsAgo);
                const blinkRate = blinkTimestampsRef.current.length; // blinks in last 60 s = blinks/min

                // ── Eye closed duration (for fatigue) ──
                const eyeClosedDurationS =
                    eyeClosedStartRef.current !== null ? (now - eyeClosedStartRef.current) / 1000 : 0;

                // ── Gaze direction ──
                const gaze: GazeResult = estimateGaze(landmarks);

                // Track gaze switches for anti-cheat
                if (gaze.direction !== lastGazeDirectionRef.current) {
                    gazeSwitchCountRef.current++;
                    gazeSwitchTimestampsRef.current.push(now);
                    lastGazeDirectionRef.current = gaze.direction;
                }
                // Prune old gaze switch timestamps (keep last 60 s)
                gazeSwitchTimestampsRef.current = gazeSwitchTimestampsRef.current.filter(
                    (t) => t > sixtySecsAgo,
                );
                const gazeSwitchFreq = gazeSwitchTimestampsRef.current.length;

                // ── Track look-away duration ──
                const isLookingAway = gaze.direction !== 'focused' || eyesClosed;
                if (isLookingAway) {
                    if (lookAwayStartRef.current === null) lookAwayStartRef.current = now;
                } else {
                    if (lookAwayStartRef.current !== null) {
                        totalLookAwayMsRef.current += now - lookAwayStartRef.current;
                        lookAwayStartRef.current = null;
                    }
                }
                const lookAwayDurationS = totalLookAwayMsRef.current / 1000;

                // ── Fatigue classification ──
                const fatigue = classifyFatigue(eyeClosedDurationS, blinkRate);

                // ── Distraction score ──
                const noFaceRatio =
                    recentFramesRef.current.length > 0
                        ? recentFramesRef.current.filter((f) => !f).length / recentFramesRef.current.length
                        : 0;
                const distractionScore = computeDistractionScore(
                    gazeSwitchFreq,
                    lookAwayDurationS,
                    noFaceRatio,
                );

                // ── Determine raw focus state ──
                if (fatigue === 'drowsy') {
                    rawState = 'drowsy';
                } else if (eyesClosed) {
                    rawState = 'eyes_closed';
                } else {
                    rawState = gaze.direction; // 'focused' | 'looking_left' | 'looking_right' | 'looking_down'
                }

                // ── Update extended metrics (batch, avoids per-frame state sets) ──
                // We write to a local and set once via ref-comparison below.
                setMetrics({
                    blinkCount: blinkCountRef.current,
                    blinkRate,
                    fatigue,
                    distractionScore,
                    eyeClosedDurationS,
                    gazeSwitchFreq,
                    lookAwayDurationS,
                });
            }

            // ── Smoothing buffer ──
            focusBufferRef.current.push(rawState);
            if (focusBufferRef.current.length > FOCUS_BUFFER_SIZE) {
                focusBufferRef.current.shift();
            }
            const smoothed = getMostFrequent(focusBufferRef.current) ?? 'focused';

            // ── Only update React state when smoothed value changes ──
            if (smoothed !== lastEmittedStateRef.current) {
                lastEmittedStateRef.current = smoothed;
                setCurrentFocus(smoothed);

                const isFocused = smoothed === 'focused';
                if (isFocused !== lastFocusedRef.current) {
                    lastFocusedRef.current = isFocused;
                    onFocusChange?.(isFocused);

                    if (!isFocused) {
                        onDistraction?.();
                        attentionService.recordDistraction();
                        attentionService.recordLookAway();

                        setStats((prev) => ({
                            ...prev,
                            distractionCount: prev.distractionCount + 1,
                            lastDistractionTime: new Date(),
                            currentStreak: 0,
                        }));
                    }
                }
            }

            // ── Draw landmarks on canvas if preview enabled ──
            if (showPreview && canvasRef.current && hasFace) {
                drawLandmarks(canvasRef.current, result.faceLandmarks[0], smoothed);
            }
        } catch (error) {
            console.error('[FocusTracker] Detection error:', error);
        }

        animationRef.current = requestAnimationFrame(runDetection);
    }, [showPreview, onFocusChange, onDistraction]);

    // ────────────────────────────────────────────────────────────
    // 4. Canvas drawing helper
    // ────────────────────────────────────────────────────────────

    function drawLandmarks(
        canvas: HTMLCanvasElement,
        landmarks: any[],
        state: FocusState,
    ) {
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Choose colour by state
        const colours: Record<FocusState, string> = {
            focused: '#22c55e',
            looking_left: '#f59e0b',
            looking_right: '#f59e0b',
            looking_down: '#f59e0b',
            eyes_closed: '#ef4444',
            away: '#ef4444',
            drowsy: '#a855f7',
        };
        ctx.fillStyle = colours[state] ?? '#22c55e';

        for (const lm of landmarks) {
            const x = lm.x * canvas.width;
            const y = lm.y * canvas.height;
            ctx.beginPath();
            ctx.arc(x, y, 1.5, 0, 2 * Math.PI);
            ctx.fill();
        }
    }

    // ────────────────────────────────────────────────────────────
    // 5. Focused-time interval (1 Hz)
    // ────────────────────────────────────────────────────────────

    useEffect(() => {
        if (!isCameraActive) return;

        const interval = setInterval(() => {
            const state = lastEmittedStateRef.current;
            const isFocused = state === 'focused';

            if (isFocused) {
                setStats((prev) => ({
                    ...prev,
                    focusedTime: prev.focusedTime + 1,
                    currentStreak: prev.currentStreak + 1,
                    longestStreak: Math.max(prev.longestStreak, prev.currentStreak + 1),
                }));
                attentionService.incrementMetric('focused', 1);
            } else if (state === 'away') {
                attentionService.incrementMetric('away', 1);
            } else {
                attentionService.incrementMetric('distracted', 1);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [isCameraActive]);

    // ────────────────────────────────────────────────────────────
    // 6. Start detection loop when model + camera ready
    // ────────────────────────────────────────────────────────────

    useEffect(() => {
        if (isModelReady && isCameraActive && enabled) {
            console.log('[FocusTracker] Starting detection loop');
            isRunningRef.current = true;
            sessionStartRef.current = Date.now();
            runDetection();
        }

        return () => {
            isRunningRef.current = false;
            if (animationRef.current) cancelAnimationFrame(animationRef.current);
        };
    }, [isModelReady, isCameraActive, enabled, runDetection]);

    // ────────────────────────────────────────────────────────────
    // 7. Init / teardown when enabled changes
    // ────────────────────────────────────────────────────────────

    useEffect(() => {
        if (enabled) {
            loadModel();
            startCamera();
            attentionService.startSession();
        } else {
            stopCamera();
            attentionService.endSession();
        }

        return () => {
            stopCamera();
            attentionService.endSession();
        };
    }, [enabled, loadModel, startCamera, stopCamera]);

    // ────────────────────────────────────────────────────────────
    // UI helpers
    // ────────────────────────────────────────────────────────────

    const focusMeta: Record<
        FocusState,
        { label: string; colour: string; bg: string; icon: React.ReactNode; hint: string }
    > = {
        focused: {
            label: 'Focused',
            colour: 'text-green-500',
            bg: 'bg-green-500/20 border-green-500/50',
            icon: <Eye className="w-5 h-5" />,
            hint: 'Great work — keep it up!',
        },
        looking_left: {
            label: 'Looking Left',
            colour: 'text-yellow-500',
            bg: 'bg-yellow-500/20 border-yellow-500/50',
            icon: <AlertTriangle className="w-5 h-5" />,
            hint: 'Please look at the screen.',
        },
        looking_right: {
            label: 'Looking Right',
            colour: 'text-yellow-500',
            bg: 'bg-yellow-500/20 border-yellow-500/50',
            icon: <AlertTriangle className="w-5 h-5" />,
            hint: 'Please look at the screen.',
        },
        looking_down: {
            label: 'Looking Down',
            colour: 'text-orange-500',
            bg: 'bg-orange-500/20 border-orange-500/50',
            icon: <AlertTriangle className="w-5 h-5" />,
            hint: 'Head down — are you writing notes?',
        },
        eyes_closed: {
            label: 'Eyes Closed',
            colour: 'text-red-500',
            bg: 'bg-red-500/20 border-red-500/50',
            icon: <EyeOff className="w-5 h-5" />,
            hint: 'Open your eyes to continue.',
        },
        away: {
            label: 'Away',
            colour: 'text-red-500',
            bg: 'bg-red-500/20 border-red-500/50',
            icon: <EyeOff className="w-5 h-5" />,
            hint: 'No face detected — please return.',
        },
        drowsy: {
            label: 'Drowsy',
            colour: 'text-purple-500',
            bg: 'bg-purple-500/20 border-purple-500/50',
            icon: <ZapOff className="w-5 h-5" />,
            hint: 'You seem tired — take a short break!',
        },
    };

    const meta = focusMeta[currentFocus];

    const formatTime = (seconds: number) => {
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        return hrs > 0 ? `${hrs}h ${mins}m ${secs}s` : `${mins}m ${secs}s`;
    };

    const fatigueMeta: Record<FatigueState, { label: string; colour: string }> = {
        alert: { label: 'Alert', colour: 'text-green-400' },
        normal: { label: 'Normal', colour: 'text-yellow-400' },
        drowsy: { label: 'Drowsy', colour: 'text-red-400' },
    };

    // ────────────────────────────────────────────────────────────
    // Render
    // ────────────────────────────────────────────────────────────

    return (
        <div className="space-y-4">
            {/* ─── Status Indicator ─── */}
            <div className={`rounded-xl border p-4 transition-all duration-300 ${meta.bg}`}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-full ${meta.colour} bg-current/10`}>
                            {isModelLoading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : !isCameraActive ? (
                                <CameraOff className="w-5 h-5" />
                            ) : (
                                meta.icon
                            )}
                        </div>
                        <div>
                            <p className={`font-semibold ${meta.colour}`}>
                                {isModelLoading
                                    ? 'Loading AI Model…'
                                    : !isCameraActive
                                        ? 'Camera Off'
                                        : meta.label}
                            </p>
                            <p className="text-xs text-muted-foreground">
                                {isModelLoading
                                    ? 'Preparing FaceLandmarker…'
                                    : !isCameraActive
                                        ? 'Enable camera to track focus'
                                        : meta.hint}
                            </p>
                        </div>
                    </div>

                    {enabled && (
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => (isCameraActive ? stopCamera() : startCamera())}
                        >
                            {isCameraActive ? (
                                <>
                                    <CameraOff className="w-4 h-4 mr-2" />
                                    Stop
                                </>
                            ) : (
                                <>
                                    <Camera className="w-4 h-4 mr-2" />
                                    Start
                                </>
                            )}
                        </Button>
                    )}
                </div>
            </div>

            {/* ─── Camera Preview ─── */}
            <div className="relative">
                <video
                    ref={videoRef}
                    className={showPreview ? 'w-full rounded-lg' : 'absolute opacity-0 pointer-events-none'}
                    style={showPreview ? {} : { width: 1, height: 1 }}
                    muted
                    playsInline
                />
                {showPreview && (
                    <canvas
                        ref={canvasRef}
                        width={640}
                        height={480}
                        className="absolute top-0 left-0 w-full h-full rounded-lg"
                    />
                )}
            </div>

            {/* ─── Error Display ─── */}
            {cameraError && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    {cameraError}
                </div>
            )}

            {/* ─── Core Stats ─── */}
            {isCameraActive && (
                <div className="grid grid-cols-3 gap-3">
                    <div className="text-center p-3 rounded-lg bg-muted">
                        <p className="text-lg font-bold text-green-500">{formatTime(stats.focusedTime)}</p>
                        <p className="text-xs text-muted-foreground">Focus Time</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-muted">
                        <p className="text-lg font-bold text-yellow-500">{stats.distractionCount}</p>
                        <p className="text-xs text-muted-foreground">Distractions</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-muted">
                        <p className="text-lg font-bold text-blue-500">{formatTime(stats.longestStreak)}</p>
                        <p className="text-xs text-muted-foreground">Best Streak</p>
                    </div>
                </div>
            )}

            {/* ─── Extended AI Metrics ─── */}
            {isCameraActive && (
                <div className="grid grid-cols-2 gap-3">
                    {/* Blink */}
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-muted">
                        <Activity className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                        <div className="min-w-0">
                            <p className="text-sm font-semibold truncate">
                                {metrics.blinkCount} blinks
                            </p>
                            <p className="text-xs text-muted-foreground">
                                {metrics.blinkRate} / min
                            </p>
                        </div>
                    </div>

                    {/* Fatigue */}
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-muted">
                        <Brain className="w-4 h-4 text-purple-400 flex-shrink-0" />
                        <div className="min-w-0">
                            <p className={`text-sm font-semibold ${fatigueMeta[metrics.fatigue].colour}`}>
                                {fatigueMeta[metrics.fatigue].label}
                            </p>
                            <p className="text-xs text-muted-foreground">Fatigue Level</p>
                        </div>
                    </div>

                    {/* Anti-Cheat Score */}
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-muted">
                        <Shield className="w-4 h-4 text-amber-400 flex-shrink-0" />
                        <div className="min-w-0">
                            <p className="text-sm font-semibold">
                                {metrics.distractionScore}
                                <span className="text-xs font-normal text-muted-foreground"> / 100</span>
                            </p>
                            <p className="text-xs text-muted-foreground">Distraction Score</p>
                        </div>
                    </div>

                    {/* Gaze Switches */}
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-muted">
                        <Eye className="w-4 h-4 text-teal-400 flex-shrink-0" />
                        <div className="min-w-0">
                            <p className="text-sm font-semibold">
                                {metrics.gazeSwitchFreq}
                                <span className="text-xs font-normal text-muted-foreground"> / min</span>
                            </p>
                            <p className="text-xs text-muted-foreground">Gaze Switches</p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export type { FocusStats };
