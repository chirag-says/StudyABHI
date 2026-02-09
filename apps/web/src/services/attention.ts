import api from './api';

export interface RecordMetricsRequest {
    session_id: string;
    total_seconds: number;
    focused_seconds: number;
    distracted_seconds: number;
    away_seconds: number;
    tab_switch_count: number;  // Backend expects this field name
    look_away_count: number;
    idle_count: number;
    focus_score: number;
    engagement_score: number;
    start_time: number;
    study_session_id?: string;
    gaze_tracking_used: boolean;
}

export interface SessionMetricsResponse {
    session_id: string;
    focus_score: number;
    attention_level: string;
    message: string;
}

export interface AttentionAnalytics {
    total_tracked_hours: number;
    avg_focus_score: number;
    avg_engagement_score: number;
    focus_trend: string;
    peak_focus_hours: number[];
    best_session_duration: number;
    avg_distraction_interval: number;
    patterns: AttentionPattern[];
    insights: AttentionInsight[];
    correlations: TopicCorrelation[];
}

export interface AttentionPattern {
    pattern_type: string;
    title: string;
    description: string;
    confidence: number;
}

export interface AttentionInsight {
    insight_type: string;
    title: string;
    description: string;
    priority: number;
}

export interface TopicCorrelation {
    topic_id?: string;
    topic_name?: string;
    avg_focus_score: number;
    avg_quiz_accuracy?: number;
    study_efficiency: number;
}

export interface DailySummary {
    date: string;
    total_tracked_minutes: number;
    avg_focus_score?: number;
    session_count: number;
    had_deep_focus: boolean;
    peak_hour?: number;
}

export interface TrackingPreferences {
    tracking_enabled: boolean;
    gaze_tracking_enabled: boolean;
    tab_tracking_enabled: boolean;
    idle_tracking_enabled: boolean;
    data_retention_days: number;
    show_focus_reminders: boolean;
    show_break_reminders: boolean;
    show_insights: boolean;
}

class AttentionService {
    private sessionId: string | null = null;
    private startTime: number | null = null;
    private metricsBuffer: Partial<RecordMetricsRequest> = {};

    // Start a new attention tracking session
    startSession(): string {
        this.sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        this.startTime = Math.floor(Date.now() / 1000);
        this.metricsBuffer = {
            session_id: this.sessionId,
            start_time: this.startTime,
            total_seconds: 0,
            focused_seconds: 0,
            distracted_seconds: 0,
            away_seconds: 0,
            tab_switch_count: 0,
            look_away_count: 0,
            idle_count: 0,
            gaze_tracking_used: true
        };
        return this.sessionId;
    }

    // Update metrics during session
    updateMetrics(updates: Partial<RecordMetricsRequest>) {
        this.metricsBuffer = { ...this.metricsBuffer, ...updates };
    }

    // Record a distraction event (tab switch)
    recordDistraction() {
        this.metricsBuffer.tab_switch_count = (this.metricsBuffer.tab_switch_count || 0) + 1;
    }

    // Record looking away
    recordLookAway() {
        this.metricsBuffer.look_away_count = (this.metricsBuffer.look_away_count || 0) + 1;
    }

    // Increment metric by seconds
    incrementMetric(type: 'focused' | 'distracted' | 'away', seconds: number) {
        if (type === 'focused') {
            this.metricsBuffer.focused_seconds = (this.metricsBuffer.focused_seconds || 0) + seconds;
        } else {
            this.metricsBuffer.distracted_seconds = (this.metricsBuffer.distracted_seconds || 0) + seconds;
            if (type === 'away') {
                this.metricsBuffer.away_seconds = (this.metricsBuffer.away_seconds || 0) + seconds;
            }
        }
    }

    // Calculate and set scores
    calculateScores() {
        const total = this.metricsBuffer.total_seconds || 1;
        const focused = this.metricsBuffer.focused_seconds || 0;
        const distractions = this.metricsBuffer.tab_switch_count || 0;

        // Focus score: percentage of focused time
        const focusScore = Math.round((focused / total) * 100);

        // Engagement score: considers distractions per minute
        const distractionsPerMinute = distractions / (total / 60);
        const engagementScore = Math.max(0, Math.round(100 - (distractionsPerMinute * 10)));

        this.metricsBuffer.focus_score = Math.min(100, Math.max(0, focusScore));
        this.metricsBuffer.engagement_score = Math.min(100, Math.max(0, engagementScore));
    }

    // End session and send to server
    async endSession(): Promise<SessionMetricsResponse | null> {
        if (!this.sessionId || !this.startTime) return null;

        this.metricsBuffer.total_seconds = Math.floor(Date.now() / 1000) - this.startTime;
        this.calculateScores();

        try {
            const response = await api.post<SessionMetricsResponse>(
                '/attention/metrics',
                this.metricsBuffer
            );
            return response.data;
        } catch (error) {
            console.error('Failed to record attention metrics:', error);
            return null;
        } finally {
            this.sessionId = null;
            this.startTime = null;
            this.metricsBuffer = {};
        }
    }

    // Periodic sync during long sessions
    async syncMetrics(): Promise<void> {
        if (!this.sessionId) return;

        this.metricsBuffer.total_seconds = Math.floor(Date.now() / 1000) - (this.startTime || 0);
        this.calculateScores();

        try {
            await api.post('/attention/metrics', this.metricsBuffer);
        } catch (error) {
            console.error('Failed to sync attention metrics:', error);
        }
    }

    // Get analytics
    async getAnalytics(days: number = 30): Promise<AttentionAnalytics | null> {
        try {
            const response = await api.get<AttentionAnalytics>('/attention/analytics', {
                params: { days }
            });
            return response.data;
        } catch (error) {
            console.error('Failed to get attention analytics:', error);
            return null;
        }
    }

    // Get daily summaries
    async getDailySummaries(days: number = 30): Promise<DailySummary[]> {
        try {
            const response = await api.get<DailySummary[]>('/attention/daily-summary', {
                params: { days }
            });
            return response.data;
        } catch (error) {
            console.error('Failed to get daily summaries:', error);
            return [];
        }
    }

    // Get and update preferences
    async getPreferences(): Promise<TrackingPreferences | null> {
        try {
            const response = await api.get<TrackingPreferences>('/attention/preferences');
            return response.data;
        } catch (error) {
            console.error('Failed to get tracking preferences:', error);
            return null;
        }
    }

    async updatePreferences(prefs: Partial<TrackingPreferences>): Promise<TrackingPreferences | null> {
        try {
            const response = await api.put<TrackingPreferences>('/attention/preferences', prefs);
            return response.data;
        } catch (error) {
            console.error('Failed to update tracking preferences:', error);
            return null;
        }
    }

    // Delete all attention data
    async deleteAllData(): Promise<boolean> {
        try {
            await api.delete('/attention');
            return true;
        } catch (error) {
            console.error('Failed to delete attention data:', error);
            return false;
        }
    }
}

// Export singleton instance
export const attentionService = new AttentionService();
export default attentionService;
