/**
 * Attention Tracking Module
 * Browser-based focus and attention monitoring for study sessions.
 * 
 * PRIVACY-FIRST DESIGN:
 * - NO raw video is stored or transmitted
 * - Only aggregated metrics are sent
 * - Processing happens entirely in the browser
 * - User has full control to enable/disable
 * 
 * Features:
 * - Eye gaze estimation using TensorFlow.js face-landmarks-detection
 * - Head pose detection (looking away detection)
 * - Tab visibility/switching detection
 * - Idle detection
 * - Focus scoring in real-time
 */

import { useEffect, useRef, useState, useCallback } from 'react';

// ==================== Types ====================

export interface AttentionMetrics {
    // Time-based metrics
    totalSeconds: number;
    focusedSeconds: number;
    distractedSeconds: number;
    awaySeconds: number;

    // Event counts
    tabSwitchCount: number;
    lookAwayCount: number;
    idleCount: number;

    // Derived scores (0-100)
    focusScore: number;
    engagementScore: number;

    // Session info
    sessionId: string;
    startTime: number;
    lastUpdate: number;
}


export interface AttentionEvent {
    type: 'focus_change' | 'tab_switch' | 'look_away' | 'idle' | 'return';
    timestamp: number;
    duration?: number;  // Duration of the state in ms
    details?: Record<string, any>;
}

export interface AttentionConfig {
    // Feature toggles
    enableGazeTracking: boolean;
    enableHeadPose: boolean;
    enableTabDetection: boolean;
    enableIdleDetection: boolean;

    // Thresholds
    lookAwayThresholdMs: number;     // Time before marking as "looking away"
    idleThresholdMs: number;         // Time before marking as "idle"
    tabSwitchGracePeriodMs: number;  // Grace period for quick tab switches

    // Reporting
    reportIntervalMs: number;        // How often to send metrics to backend

    // Privacy
    cameraPermission: boolean;
}

// Default configuration
export const DEFAULT_CONFIG: AttentionConfig = {
    enableGazeTracking: true,
    enableHeadPose: true,
    enableTabDetection: true,
    enableIdleDetection: true,

    lookAwayThresholdMs: 3000,      // 3 seconds
    idleThresholdMs: 60000,         // 1 minute
    tabSwitchGracePeriodMs: 5000,   // 5 seconds

    reportIntervalMs: 30000,        // Every 30 seconds

    cameraPermission: false,
};

// ==================== Attention State Machine ====================

type AttentionState = 'focused' | 'distracted' | 'away' | 'idle' | 'paused';

interface StateTransition {
    from: AttentionState;
    to: AttentionState;
    timestamp: number;
}

/**
 * State machine for attention tracking.
 * 
 * States:
 * - focused: User is actively engaged (looking at screen, interacting)
 * - distracted: User is present but not focused (looking away briefly)
 * - away: User has switched tabs or window
 * - idle: User is present but inactive for extended period
 * - paused: Tracking is paused by user
 */
class AttentionStateMachine {
    private currentState: AttentionState = 'focused';
    private stateStartTime: number = Date.now();
    private stateHistory: StateTransition[] = [];

    // Time accumulators
    private timeInState: Record<AttentionState, number> = {
        focused: 0,
        distracted: 0,
        away: 0,
        idle: 0,
        paused: 0,
    };

    // Event counters
    private eventCounts = {
        tabSwitches: 0,
        lookAways: 0,
        idles: 0,
    };

    getState(): AttentionState {
        return this.currentState;
    }

    transition(newState: AttentionState): AttentionEvent | null {
        if (newState === this.currentState) return null;

        const now = Date.now();
        const duration = now - this.stateStartTime;

        // Accumulate time in previous state
        this.timeInState[this.currentState] += duration;

        // Record transition
        this.stateHistory.push({
            from: this.currentState,
            to: newState,
            timestamp: now,
        });

        // Count events
        if (newState === 'away') this.eventCounts.tabSwitches++;
        if (newState === 'distracted') this.eventCounts.lookAways++;
        if (newState === 'idle') this.eventCounts.idles++;

        const event: AttentionEvent = {
            type: this.getEventType(this.currentState, newState),
            timestamp: now,
            duration,
        };

        this.currentState = newState;
        this.stateStartTime = now;

        return event;
    }

    private getEventType(from: AttentionState, to: AttentionState): AttentionEvent['type'] {
        if (to === 'focused') return 'return';
        if (to === 'away') return 'tab_switch';
        if (to === 'idle') return 'idle';
        if (to === 'distracted') return 'look_away';
        return 'focus_change';
    }

    getMetrics(): Partial<AttentionMetrics> {
        // Include current state time
        const now = Date.now();
        const currentDuration = now - this.stateStartTime;

        const totalFocused = this.timeInState.focused +
            (this.currentState === 'focused' ? currentDuration : 0);
        const totalDistracted = this.timeInState.distracted +
            (this.currentState === 'distracted' ? currentDuration : 0);
        const totalAway = this.timeInState.away +
            (this.currentState === 'away' ? currentDuration : 0);

        const totalActive = totalFocused + totalDistracted;
        const totalTime = totalActive + totalAway + this.timeInState.idle;

        return {
            totalSeconds: Math.floor(totalTime / 1000),
            focusedSeconds: Math.floor(totalFocused / 1000),
            distractedSeconds: Math.floor(totalDistracted / 1000),
            awaySeconds: Math.floor(totalAway / 1000),
            tabSwitchCount: this.eventCounts.tabSwitches,
            lookAwayCount: this.eventCounts.lookAways,
            idleCount: this.eventCounts.idles,
            focusScore: totalTime > 0 ? Math.round((totalFocused / totalTime) * 100) : 100,
            engagementScore: totalTime > 0 ? Math.round((totalActive / totalTime) * 100) : 100,
        };
    }

    reset() {
        this.currentState = 'focused';
        this.stateStartTime = Date.now();
        this.stateHistory = [];
        this.timeInState = { focused: 0, distracted: 0, away: 0, idle: 0, paused: 0 };
        this.eventCounts = { tabSwitches: 0, lookAways: 0, idles: 0 };
    }
}

// ==================== Eye Gaze Detector ====================

/**
 * Eye gaze estimation using TensorFlow.js.
 * 
 * PRIVACY: Video stream is processed locally.
 * Only boolean "looking at screen" is extracted.
 */
class GazeDetector {
    private video: HTMLVideoElement | null = null;
    private model: any = null;
    private isInitialized = false;
    private lastGazeState: 'looking' | 'away' = 'looking';
    private awayStartTime: number | null = null;

    async initialize(): Promise<boolean> {
        try {
            // Dynamic import to avoid loading TensorFlow if not needed
            const faceLandmarksDetection = await import('@tensorflow-models/face-landmarks-detection');
            await import('@tensorflow/tfjs-backend-webgl');

            // Create hidden video element
            this.video = document.createElement('video');
            this.video.setAttribute('playsinline', '');

            // Request camera access
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: 320, height: 240 },
                audio: false,
            });

            this.video.srcObject = stream;
            await this.video.play();

            // Load face detection model
            this.model = await faceLandmarksDetection.createDetector(
                faceLandmarksDetection.SupportedModels.MediaPipeFaceMesh,
                {
                    runtime: 'tfjs',
                    refineLandmarks: true,
                }
            );

            this.isInitialized = true;
            return true;
        } catch (error) {
            console.warn('Gaze detection initialization failed:', error);
            return false;
        }
    }

    async detectGaze(): Promise<{ looking: boolean; headPose: HeadPose | null }> {
        if (!this.isInitialized || !this.video || !this.model) {
            return { looking: true, headPose: null };
        }

        try {
            const faces = await this.model.estimateFaces(this.video);

            if (faces.length === 0) {
                // No face detected - user is away
                return { looking: false, headPose: null };
            }

            const face = faces[0];
            const keypoints = face.keypoints;

            // Extract eye landmarks
            const leftEye = this.getEyeCenter(keypoints, 'left');
            const rightEye = this.getEyeCenter(keypoints, 'right');
            const nose = keypoints.find((kp: any) => kp.name === 'noseTip');

            // Estimate head pose from face landmarks
            const headPose = this.estimateHeadPose(keypoints);

            // Determine if looking at screen based on head pose
            const isLooking = this.isLookingAtScreen(headPose);

            return { looking: isLooking, headPose };
        } catch (error) {
            console.warn('Gaze detection error:', error);
            return { looking: true, headPose: null };
        }
    }

    private getEyeCenter(keypoints: any[], side: 'left' | 'right') {
        const eyePoints = keypoints.filter((kp: any) =>
            kp.name?.includes(`${side}Eye`)
        );
        if (eyePoints.length === 0) return null;

        const x = eyePoints.reduce((sum: number, p: any) => sum + p.x, 0) / eyePoints.length;
        const y = eyePoints.reduce((sum: number, p: any) => sum + p.y, 0) / eyePoints.length;
        return { x, y };
    }

    private estimateHeadPose(keypoints: any[]): HeadPose {
        // Simplified head pose from key facial landmarks
        const noseTip = keypoints.find((kp: any) => kp.name === 'noseTip');
        const leftEar = keypoints.find((kp: any) => kp.name === 'leftEarTragion');
        const rightEar = keypoints.find((kp: any) => kp.name === 'rightEarTragion');
        const foreheadCenter = keypoints.find((kp: any) => kp.name === 'foreheadCenter');
        const chin = keypoints.find((kp: any) => kp.name === 'chin');

        // Estimate yaw (left-right rotation) from ear positions
        let yaw = 0;
        if (leftEar && rightEar && noseTip) {
            const earMidX = (leftEar.x + rightEar.x) / 2;
            yaw = (noseTip.x - earMidX) * 2; // Simplified
        }

        // Estimate pitch (up-down rotation)
        let pitch = 0;
        if (noseTip && chin) {
            pitch = (noseTip.y - chin.y) / 100; // Simplified
        }

        return { yaw, pitch, roll: 0 };
    }

    private isLookingAtScreen(headPose: HeadPose): boolean {
        // Threshold for "looking away"
        // Yaw > 30 degrees or pitch > 20 degrees = looking away
        const yawThreshold = 0.3;
        const pitchThreshold = 0.2;

        return Math.abs(headPose.yaw) < yawThreshold &&
            Math.abs(headPose.pitch) < pitchThreshold;
    }

    stop() {
        if (this.video?.srcObject) {
            const stream = this.video.srcObject as MediaStream;
            stream.getTracks().forEach(track => track.stop());
            this.video.srcObject = null;
        }
        this.isInitialized = false;
    }
}

interface HeadPose {
    yaw: number;   // Left-right rotation
    pitch: number; // Up-down rotation
    roll: number;  // Tilt
}

// ==================== Tab Visibility Detector ====================

/**
 * Detects tab switching and visibility changes.
 */
class TabVisibilityDetector {
    private listeners: ((visible: boolean) => void)[] = [];
    private isVisible = true;

    initialize() {
        // Page Visibility API
        document.addEventListener('visibilitychange', this.handleVisibilityChange);

        // Window blur/focus (catches more cases)
        window.addEventListener('blur', this.handleBlur);
        window.addEventListener('focus', this.handleFocus);

        this.isVisible = document.visibilityState === 'visible';
    }

    private handleVisibilityChange = () => {
        const visible = document.visibilityState === 'visible';
        if (visible !== this.isVisible) {
            this.isVisible = visible;
            this.notifyListeners(visible);
        }
    };

    private handleBlur = () => {
        if (this.isVisible) {
            this.isVisible = false;
            this.notifyListeners(false);
        }
    };

    private handleFocus = () => {
        if (!this.isVisible) {
            this.isVisible = true;
            this.notifyListeners(true);
        }
    };

    private notifyListeners(visible: boolean) {
        this.listeners.forEach(cb => cb(visible));
    }

    onVisibilityChange(callback: (visible: boolean) => void) {
        this.listeners.push(callback);
    }

    getVisibility(): boolean {
        return this.isVisible;
    }

    destroy() {
        document.removeEventListener('visibilitychange', this.handleVisibilityChange);
        window.removeEventListener('blur', this.handleBlur);
        window.removeEventListener('focus', this.handleFocus);
        this.listeners = [];
    }
}

// ==================== Idle Detector ====================

/**
 * Detects user inactivity.
 */
class IdleDetector {
    private lastActivity = Date.now();
    private idleThresholdMs: number;
    private isIdle = false;
    private checkInterval: any;
    private listeners: ((idle: boolean) => void)[] = [];

    constructor(thresholdMs: number = 60000) {
        this.idleThresholdMs = thresholdMs;
    }

    initialize() {
        // Track user activity
        const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
        activityEvents.forEach(event => {
            document.addEventListener(event, this.handleActivity, { passive: true });
        });

        // Periodically check for idle
        this.checkInterval = setInterval(this.checkIdle, 5000);
    }

    private handleActivity = () => {
        this.lastActivity = Date.now();
        if (this.isIdle) {
            this.isIdle = false;
            this.notifyListeners(false);
        }
    };

    private checkIdle = () => {
        const now = Date.now();
        const idleTime = now - this.lastActivity;

        if (idleTime >= this.idleThresholdMs && !this.isIdle) {
            this.isIdle = true;
            this.notifyListeners(true);
        }
    };

    private notifyListeners(idle: boolean) {
        this.listeners.forEach(cb => cb(idle));
    }

    onIdleChange(callback: (idle: boolean) => void) {
        this.listeners.push(callback);
    }

    getIdleState(): boolean {
        return this.isIdle;
    }

    destroy() {
        clearInterval(this.checkInterval);
        const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
        activityEvents.forEach(event => {
            document.removeEventListener(event, this.handleActivity);
        });
        this.listeners = [];
    }
}

// ==================== Main Attention Tracker ====================

/**
 * Main attention tracking class.
 * Coordinates all detection modules and produces unified metrics.
 */
export class AttentionTracker {
    private config: AttentionConfig;
    private stateMachine: AttentionStateMachine;
    private gazeDetector: GazeDetector | null = null;
    private tabDetector: TabVisibilityDetector;
    private idleDetector: IdleDetector;

    private sessionId: string;
    private startTime: number;
    private isRunning = false;
    private gazeCheckInterval: any;
    private reportInterval: any;

    private eventListeners: ((event: AttentionEvent) => void)[] = [];
    private metricsListeners: ((metrics: AttentionMetrics) => void)[] = [];

    constructor(config: Partial<AttentionConfig> = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.stateMachine = new AttentionStateMachine();
        this.tabDetector = new TabVisibilityDetector();
        this.idleDetector = new IdleDetector(this.config.idleThresholdMs);
        this.sessionId = this.generateSessionId();
        this.startTime = Date.now();
    }

    async start(): Promise<void> {
        if (this.isRunning) return;

        this.isRunning = true;
        this.startTime = Date.now();

        // Initialize tab detection
        if (this.config.enableTabDetection) {
            this.tabDetector.initialize();
            this.tabDetector.onVisibilityChange((visible) => {
                if (!visible) {
                    this.handleStateChange('away');
                } else {
                    this.handleStateChange('focused');
                }
            });
        }

        // Initialize idle detection
        if (this.config.enableIdleDetection) {
            this.idleDetector.initialize();
            this.idleDetector.onIdleChange((idle) => {
                if (idle && this.tabDetector.getVisibility()) {
                    this.handleStateChange('idle');
                } else if (!idle) {
                    this.handleStateChange('focused');
                }
            });
        }

        // Initialize gaze detection (if camera permission granted)
        if (this.config.enableGazeTracking && this.config.cameraPermission) {
            this.gazeDetector = new GazeDetector();
            const initialized = await this.gazeDetector.initialize();

            if (initialized) {
                // Check gaze every 500ms
                this.gazeCheckInterval = setInterval(async () => {
                    const { looking } = await this.gazeDetector!.detectGaze();
                    if (!looking && this.tabDetector.getVisibility()) {
                        this.handleStateChange('distracted');
                    } else if (looking && !this.idleDetector.getIdleState()) {
                        this.handleStateChange('focused');
                    }
                }, 500);
            }
        }

        // Set up periodic reporting
        this.reportInterval = setInterval(() => {
            this.reportMetrics();
        }, this.config.reportIntervalMs);
    }

    private handleStateChange(newState: AttentionState) {
        const event = this.stateMachine.transition(newState);
        if (event) {
            this.eventListeners.forEach(cb => cb(event));
        }
    }

    private reportMetrics() {
        const metrics = this.getMetrics();
        this.metricsListeners.forEach(cb => cb(metrics));
    }

    getMetrics(): AttentionMetrics {
        const stateMetrics = this.stateMachine.getMetrics();

        return {
            ...stateMetrics,
            sessionId: this.sessionId,
            startTime: this.startTime,
            lastUpdate: Date.now(),
        } as AttentionMetrics;
    }

    onEvent(callback: (event: AttentionEvent) => void) {
        this.eventListeners.push(callback);
    }

    onMetricsUpdate(callback: (metrics: AttentionMetrics) => void) {
        this.metricsListeners.push(callback);
    }

    pause() {
        this.handleStateChange('paused');
    }

    resume() {
        this.handleStateChange('focused');
    }

    stop() {
        this.isRunning = false;

        clearInterval(this.gazeCheckInterval);
        clearInterval(this.reportInterval);

        this.gazeDetector?.stop();
        this.tabDetector.destroy();
        this.idleDetector.destroy();

        // Final metrics report
        this.reportMetrics();
    }

    reset() {
        this.stateMachine.reset();
        this.startTime = Date.now();
        this.sessionId = this.generateSessionId();
    }

    private generateSessionId(): string {
        return `attn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}

// ==================== React Hook ====================

/**
 * React hook for attention tracking.
 * 
 * Usage:
 * ```tsx
 * const { metrics, isTracking, start, stop } = useAttentionTracking({
 *   onMetricsUpdate: (m) => sendToBackend(m)
 * });
 * ```
 */
export function useAttentionTracking(options: {
    config?: Partial<AttentionConfig>;
    onEvent?: (event: AttentionEvent) => void;
    onMetricsUpdate?: (metrics: AttentionMetrics) => void;
    autoStart?: boolean;
}) {
    const trackerRef = useRef<AttentionTracker | null>(null);
    const [isTracking, setIsTracking] = useState(false);
    const [metrics, setMetrics] = useState<AttentionMetrics | null>(null);
    const [currentState, setCurrentState] = useState<AttentionState>('focused');

    // Initialize tracker
    useEffect(() => {
        trackerRef.current = new AttentionTracker(options.config);

        trackerRef.current.onEvent((event) => {
            options.onEvent?.(event);
            // Update current state based on event
            if (event.type === 'focus_change' || event.type === 'return') {
                setCurrentState('focused');
            } else if (event.type === 'tab_switch') {
                setCurrentState('away');
            } else if (event.type === 'look_away') {
                setCurrentState('distracted');
            } else if (event.type === 'idle') {
                setCurrentState('idle');
            }
        });

        trackerRef.current.onMetricsUpdate((m) => {
            setMetrics(m);
            options.onMetricsUpdate?.(m);
        });

        if (options.autoStart) {
            trackerRef.current.start().then(() => setIsTracking(true));
        }

        return () => {
            trackerRef.current?.stop();
        };
    }, []);

    const start = useCallback(async () => {
        await trackerRef.current?.start();
        setIsTracking(true);
    }, []);

    const stop = useCallback(() => {
        trackerRef.current?.stop();
        setIsTracking(false);
    }, []);

    const pause = useCallback(() => {
        trackerRef.current?.pause();
    }, []);

    const resume = useCallback(() => {
        trackerRef.current?.resume();
    }, []);

    const getMetrics = useCallback(() => {
        return trackerRef.current?.getMetrics() || null;
    }, []);

    return {
        isTracking,
        metrics,
        currentState,
        start,
        stop,
        pause,
        resume,
        getMetrics,
    };
}

export default AttentionTracker;
