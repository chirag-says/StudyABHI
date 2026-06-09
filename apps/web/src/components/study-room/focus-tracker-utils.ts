/**
 * focus-tracker-utils.ts
 *
 * Pure math / detection utilities for the FocusTracker component.
 * Every function is side-effect-free and fully typed.
 */

import type { NormalizedLandmark } from '@mediapipe/tasks-vision';

// ────────────────────────────────────────────────────────────
// Landmark indices (MediaPipe 478-landmark mesh)
// ────────────────────────────────────────────────────────────

export const LANDMARKS = {
    LEFT_EYE: { outer: 33, inner: 133, top: 159, bottom: 145 },
    RIGHT_EYE: { outer: 362, inner: 263, top: 386, bottom: 374 },
    NOSE_TIP: 1,
} as const;

// ────────────────────────────────────────────────────────────
// Tuning constants
// ────────────────────────────────────────────────────────────

/** Below this EAR the eyes are considered closed. */
export const EAR_THRESHOLD = 0.18;

/** Minimum consecutive closed-eye frames that count as a blink. */
export const BLINK_MIN_FRAMES = 2;

/** Maximum consecutive closed-eye frames that still count as a blink (vs. prolonged closure). */
export const BLINK_MAX_FRAMES = 8;

/** Eye closed longer than this (in seconds) triggers fatigue/drowsy. */
export const FATIGUE_CLOSURE_THRESHOLD_S = 1.5;

/** Blink rate (blinks/min) above this is considered fatigued. */
export const HIGH_BLINK_RATE = 25;

/** Size of the focus-state smoothing buffer. */
export const FOCUS_BUFFER_SIZE = 10;

/** Target detection FPS. */
export const TARGET_FPS = 10;

/** Minimum ms between two detection frames. */
export const FRAME_INTERVAL_MS = 1000 / TARGET_FPS;

/** Gaze horizontal threshold (nose-to-eye-center offset, normalised coords). */
export const GAZE_H_THRESHOLD = 0.035;

/** Gaze vertical threshold. */
export const GAZE_V_THRESHOLD = 0.03;

/** Number of "no-face" frames before marking `away` (at ~10 FPS → ~3 s). */
export const NO_FACE_AWAY_FRAMES = 30;

/** Grace frames before counting a new distraction after the last one. */
export const DISTRACTION_COOLDOWN_FRAMES = 15;

// ────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────

export type FocusState =
    | 'focused'
    | 'looking_left'
    | 'looking_right'
    | 'looking_down'
    | 'eyes_closed'
    | 'away'
    | 'drowsy';

export type FatigueState = 'alert' | 'normal' | 'drowsy';

export interface GazeResult {
    horizontalOffset: number;
    verticalOffset: number;
    direction: 'focused' | 'looking_left' | 'looking_right' | 'looking_down';
}

export interface BlinkSnapshot {
    blinkCount: number;
    /** Rolling blinks-per-minute. */
    blinkRate: number;
}

export interface FatigueSnapshot {
    state: FatigueState;
    /** Continuous eye-closed duration (seconds). */
    eyeClosedDuration: number;
    blinkRate: number;
}

export interface DistractionSnapshot {
    /** 0–100, higher = more distracted. */
    distractionScore: number;
    /** Gaze direction switches per minute. */
    gazeSwitchFrequency: number;
    /** Total seconds spent looking away this session. */
    lookAwayDuration: number;
}

// ────────────────────────────────────────────────────────────
// Math helpers
// ────────────────────────────────────────────────────────────

/** Euclidean distance between two normalised landmarks. */
function euclidean(a: NormalizedLandmark, b: NormalizedLandmark): number {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    return Math.sqrt(dx * dx + dy * dy);
}

// ────────────────────────────────────────────────────────────
// Eye Aspect Ratio (EAR)
// ────────────────────────────────────────────────────────────

/**
 * Compute the Eye Aspect Ratio for one eye.
 *
 *   EAR = vertical_dist / horizontal_dist
 *
 * A low EAR (< 0.18) means the eye is closed.
 */
export function calculateEAR(
    landmarks: NormalizedLandmark[],
    eye: { outer: number; inner: number; top: number; bottom: number },
): number {
    const vertical = euclidean(landmarks[eye.top], landmarks[eye.bottom]);
    const horizontal = euclidean(landmarks[eye.outer], landmarks[eye.inner]);
    if (horizontal === 0) return 0;
    return vertical / horizontal;
}

/** Average EAR across both eyes. */
export function calculateAverageEAR(landmarks: NormalizedLandmark[]): number {
    const left = calculateEAR(landmarks, LANDMARKS.LEFT_EYE);
    const right = calculateEAR(landmarks, LANDMARKS.RIGHT_EYE);
    return (left + right) / 2;
}

// ────────────────────────────────────────────────────────────
// Gaze / head direction
// ────────────────────────────────────────────────────────────

/**
 * Estimate attention direction from nose-tip ↔ eye-centre offset.
 *
 * Positive horizontalOffset → nose is right of eye centre → looking left  
 * Negative horizontalOffset → nose is left of eye centre  → looking right  
 * Positive verticalOffset   → nose is below eye centre    → looking down  
 */
export function estimateGaze(
    landmarks: NormalizedLandmark[],
    hThreshold = GAZE_H_THRESHOLD,
    vThreshold = GAZE_V_THRESHOLD,
): GazeResult {
    const nose = landmarks[LANDMARKS.NOSE_TIP];

    const lx = (landmarks[LANDMARKS.LEFT_EYE.outer].x + landmarks[LANDMARKS.LEFT_EYE.inner].x) / 2;
    const ly = (landmarks[LANDMARKS.LEFT_EYE.outer].y + landmarks[LANDMARKS.LEFT_EYE.inner].y) / 2;
    const rx = (landmarks[LANDMARKS.RIGHT_EYE.outer].x + landmarks[LANDMARKS.RIGHT_EYE.inner].x) / 2;
    const ry = (landmarks[LANDMARKS.RIGHT_EYE.outer].y + landmarks[LANDMARKS.RIGHT_EYE.inner].y) / 2;

    const eyeCenterX = (lx + rx) / 2;
    const eyeCenterY = (ly + ry) / 2;

    const horizontalOffset = nose.x - eyeCenterX;
    const verticalOffset = nose.y - eyeCenterY;

    let direction: GazeResult['direction'] = 'focused';
    if (verticalOffset > vThreshold) {
        direction = 'looking_down';
    } else if (horizontalOffset > hThreshold) {
        direction = 'looking_left';
    } else if (horizontalOffset < -hThreshold) {
        direction = 'looking_right';
    }

    return { horizontalOffset, verticalOffset, direction };
}

// ────────────────────────────────────────────────────────────
// Smoothing: mode of the last N states
// ────────────────────────────────────────────────────────────

/**
 * Return the most-frequent (mode) element of `buffer`.
 * Ties are broken by the most-recent occurrence.
 */
export function getMostFrequent<T>(buffer: T[]): T | null {
    if (buffer.length === 0) return null;

    const freq = new Map<T, number>();
    let maxCount = 0;
    let winner: T = buffer[0];

    for (const item of buffer) {
        const c = (freq.get(item) || 0) + 1;
        freq.set(item, c);
        if (c >= maxCount) {
            // >= so that later (more recent) items win ties
            maxCount = c;
            winner = item;
        }
    }
    return winner;
}

// ────────────────────────────────────────────────────────────
// Fatigue classification
// ────────────────────────────────────────────────────────────

/**
 * Derive a fatigue level from eye-closure duration and blink rate.
 *
 * - `drowsy`  → prolonged closure (> 1.5 s) **or** very high blink rate
 * - `normal`  → moderate blink rate, no prolonged closure
 * - `alert`   → everything normal
 */
export function classifyFatigue(
    eyeClosedDurationS: number,
    blinkRate: number,
): FatigueState {
    if (eyeClosedDurationS >= FATIGUE_CLOSURE_THRESHOLD_S) return 'drowsy';
    if (blinkRate >= HIGH_BLINK_RATE) return 'drowsy';
    if (blinkRate >= 18) return 'normal';
    return 'alert';
}

// ────────────────────────────────────────────────────────────
// Distraction scoring
// ────────────────────────────────────────────────────────────

/**
 * Produce a 0-100 distraction score from measurable signals.
 *
 * Weights (all out of 100):
 *   40 – gaze switch frequency (> 10 switches/min → max)
 *   30 – look-away duration    (> 30 s → max)
 *   30 – no-face ratio         (> 20 % of recent frames → max)
 */
export function computeDistractionScore(
    gazeSwitchFreq: number,
    lookAwayDurationS: number,
    noFaceRatio: number,
): number {
    const gazeScore = Math.min(gazeSwitchFreq / 10, 1) * 40;
    const awayScore = Math.min(lookAwayDurationS / 30, 1) * 30;
    const faceScore = Math.min(noFaceRatio / 0.2, 1) * 30;
    return Math.round(Math.min(gazeScore + awayScore + faceScore, 100));
}
