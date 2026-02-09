'use client';

import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
    Camera,
    CameraOff,
    Eye,
    EyeOff,
    AlertTriangle,
    CheckCircle,
    Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import attentionService from '@/services/attention';

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

export function FocusTracker({
    onFocusChange,
    onDistraction,
    enabled,
    showPreview = false
}: FocusTrackerProps) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const detectorRef = useRef<any>(null);
    const animationRef = useRef<number | null>(null);
    const lastFocusStateRef = useRef<boolean>(true);
    const noFaceCountRef = useRef<number>(0);
    const isRunningRef = useRef<boolean>(false);

    const [isModelLoading, setIsModelLoading] = useState(false);
    const [isModelReady, setIsModelReady] = useState(false);
    const [isCameraActive, setIsCameraActive] = useState(false);
    const [cameraError, setCameraError] = useState<string | null>(null);
    const [currentFocus, setCurrentFocus] = useState<'focused' | 'distracted' | 'away'>('focused');
    const [stats, setStats] = useState<FocusStats>({
        focusedTime: 0,
        distractionCount: 0,
        lastDistractionTime: null,
        currentStreak: 0,
        longestStreak: 0
    });

    // Load MediaPipe Face Detector
    const loadModel = useCallback(async () => {
        if (detectorRef.current) return;

        setIsModelLoading(true);
        try {
            // Dynamically import MediaPipe
            const vision = await import('@mediapipe/tasks-vision');
            const { FaceDetector, FilesetResolver } = vision;

            // Create the face detector
            const filesetResolver = await FilesetResolver.forVisionTasks(
                'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
            );

            const detector = await FaceDetector.createFromOptions(filesetResolver, {
                baseOptions: {
                    modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite',
                    delegate: 'GPU'
                },
                runningMode: 'VIDEO',
                minDetectionConfidence: 0.5
            });

            detectorRef.current = detector;
            setIsModelReady(true);
            console.log('[MediaPipe] Face detector loaded successfully');
        } catch (error) {
            console.error('Error loading MediaPipe face detector:', error);
            setCameraError('Failed to load AI model. Please refresh the page.');
        } finally {
            setIsModelLoading(false);
        }
    }, []);

    // Start camera
    const startCamera = useCallback(async () => {
        if (!enabled) return;

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setCameraError('Camera API not supported in this browser context (secure context required).');
            return;
        }

        try {
            setCameraError(null);

            // Try with ideal constraints first, fallback to basic if needed
            let stream;
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: { ideal: 640 },
                        height: { ideal: 480 },
                        facingMode: 'user'
                    }
                });
            } catch (e) {
                console.warn('Ideal constraints failed, trying basic video constraints');
                stream = await navigator.mediaDevices.getUserMedia({ video: true });
            }

            streamRef.current = stream;

            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                try {
                    await videoRef.current.play();
                    setIsCameraActive(true);
                    console.log('[Camera] Started successfully');
                } catch (e: any) {
                    // Ignore interruption errors explicitly (common in React Strict Mode or fast toggling)
                    if (e.name === 'AbortError' || e.message?.includes('interrupted')) {
                        console.log('Video playback interrupted (likely race condition), ignoring.');
                        return;
                    }
                    throw e;
                }
            }
        } catch (error: any) {
            console.error('Camera access error:', error);
            if (error.name === 'NotAllowedError') {
                setCameraError('Camera access denied. Please allow camera access in your browser settings.');
            } else if (error.name === 'NotFoundError') {
                setCameraError('No camera found. Please connect a camera.');
            } else if (error.name === 'NotReadableError') {
                setCameraError('Camera is in use by another application. Please close other apps using the camera.');
            } else {
                setCameraError(`Failed to access camera: ${error.message || error.name || 'Unknown error'}`);
            }
        }
    }, [enabled]);

    // Stop camera
    const stopCamera = useCallback(() => {
        isRunningRef.current = false;
        // Pause video first to prevent "interrupted" errors
        if (videoRef.current) {
            videoRef.current.pause();
            videoRef.current.srcObject = null;
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        if (animationRef.current) {
            cancelAnimationFrame(animationRef.current);
            animationRef.current = null;
        }
        setIsCameraActive(false);
    }, []);

    // Detection loop using requestAnimationFrame
    const runDetection = useCallback(() => {
        if (!isRunningRef.current) return;
        if (!detectorRef.current || !videoRef.current || !streamRef.current) {
            animationRef.current = requestAnimationFrame(runDetection);
            return;
        }

        // Check if video is actually playing and ready
        if (videoRef.current.readyState < 2) {
            animationRef.current = requestAnimationFrame(runDetection);
            return;
        }

        try {
            const startTimeMs = performance.now();
            const detections = detectorRef.current.detectForVideo(videoRef.current, startTimeMs);

            let focusState: 'focused' | 'away';

            if (!detections || detections.detections.length === 0) {
                noFaceCountRef.current++;
                // Very forgiving - wait 90 frames (~3 seconds at 30fps) before marking away
                if (noFaceCountRef.current > 90) {
                    focusState = 'away';
                } else {
                    focusState = 'focused';
                }
            } else {
                // Face detected! Always focused.
                noFaceCountRef.current = 0;
                focusState = 'focused';
            }

            // Update state
            setCurrentFocus(focusState);

            // Trigger events based on focus state change
            const isFocused = focusState === 'focused';
            if (isFocused !== lastFocusStateRef.current) {
                lastFocusStateRef.current = isFocused;
                onFocusChange?.(isFocused);

                if (!isFocused) {
                    onDistraction?.();
                    attentionService.recordDistraction();
                    attentionService.recordLookAway();

                    setStats(prev => ({
                        ...prev,
                        distractionCount: prev.distractionCount + 1,
                        lastDistractionTime: new Date(),
                        currentStreak: 0
                    }));
                }
            }

            // Draw on canvas if preview enabled
            if (showPreview && canvasRef.current && detections && detections.detections.length > 0) {
                const ctx = canvasRef.current.getContext('2d');
                if (ctx) {
                    ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);

                    // Draw bounding boxes
                    ctx.strokeStyle = focusState === 'focused' ? '#22c55e' : '#ef4444';
                    ctx.lineWidth = 3;

                    detections.detections.forEach((detection: any) => {
                        const box = detection.boundingBox;
                        if (box) {
                            ctx.strokeRect(box.originX, box.originY, box.width, box.height);
                        }
                    });
                }
            }

        } catch (error) {
            console.error('Face detection error:', error);
        }

        // Continue detection loop
        animationRef.current = requestAnimationFrame(runDetection);
    }, [showPreview, onFocusChange, onDistraction]);

    // Update focused time every second
    useEffect(() => {
        if (!isCameraActive) return;

        const interval = setInterval(() => {
            if (currentFocus === 'focused') {
                setStats(prev => ({
                    ...prev,
                    focusedTime: prev.focusedTime + 1,
                    currentStreak: prev.currentStreak + 1,
                    longestStreak: Math.max(prev.longestStreak, prev.currentStreak + 1)
                }));
                attentionService.incrementMetric('focused', 1);
            } else {
                attentionService.incrementMetric('away', 1);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [isCameraActive, currentFocus]);

    // Start detection when camera and model are ready
    useEffect(() => {
        if (isModelReady && isCameraActive && enabled) {
            console.log('[Detection] Starting detection loop');
            isRunningRef.current = true;
            runDetection();
        }

        return () => {
            isRunningRef.current = false;
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, [isModelReady, isCameraActive, enabled, runDetection]);

    // Initialize when enabled
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

    const getFocusStatusColor = () => {
        switch (currentFocus) {
            case 'focused': return 'text-green-500';
            case 'distracted': return 'text-yellow-500';
            case 'away': return 'text-red-500';
        }
    };

    const getFocusStatusBg = () => {
        switch (currentFocus) {
            case 'focused': return 'bg-green-500/20 border-green-500/50';
            case 'distracted': return 'bg-yellow-500/20 border-yellow-500/50';
            case 'away': return 'bg-red-500/20 border-red-500/50';
        }
    };

    const getFocusStatusIcon = () => {
        switch (currentFocus) {
            case 'focused': return <Eye className="w-5 h-5" />;
            case 'distracted': return <AlertTriangle className="w-5 h-5" />;
            case 'away': return <EyeOff className="w-5 h-5" />;
        }
    };

    const formatTime = (seconds: number) => {
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        if (hrs > 0) {
            return `${hrs}h ${mins}m ${secs}s`;
        }
        return `${mins}m ${secs}s`;
    };

    return (
        <div className="space-y-4">
            {/* Status Indicator */}
            <div className={`rounded-xl border p-4 transition-all duration-300 ${getFocusStatusBg()}`}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-full ${getFocusStatusColor()} bg-current/10`}>
                            {isModelLoading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : !isCameraActive ? (
                                <CameraOff className="w-5 h-5" />
                            ) : (
                                getFocusStatusIcon()
                            )}
                        </div>
                        <div>
                            <p className={`font-semibold ${getFocusStatusColor()}`}>
                                {isModelLoading ? 'Loading AI...' :
                                    !isCameraActive ? 'Camera Off' :
                                        currentFocus === 'focused' ? 'Focused' :
                                            currentFocus === 'distracted' ? 'Distracted' :
                                                'Looking Away'}
                            </p>
                            <p className="text-xs text-muted-foreground">
                                {isModelLoading ? 'Preparing face detection...' :
                                    !isCameraActive ? 'Enable camera to track focus' :
                                        currentFocus === 'focused' ? 'Keep it up!' :
                                            'Please look at the screen'}
                            </p>
                        </div>
                    </div>

                    {enabled && (
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => isCameraActive ? stopCamera() : startCamera()}
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

            {/* Camera Preview (Hidden by default) */}
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

            {/* Error Display */}
            {cameraError && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
                    <AlertTriangle className="w-4 h-4" />
                    {cameraError}
                </div>
            )}

            {/* Quick Stats */}
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
        </div>
    );
}

export type { FocusStats };
