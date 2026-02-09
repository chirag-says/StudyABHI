"""
Attention Signal Processing Service
Aggregate focus metrics, correlate with study sessions, generate insights.

DESIGN PRINCIPLES:
1. Privacy-first: Only process aggregated metrics
2. Supportive: Generate insights, never judgments
3. Actionable: Focus on patterns and improvements
4. Correlative: Link attention data to learning outcomes
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import logging
import statistics

logger = logging.getLogger(__name__)


# ==================== Data Classes ====================

@dataclass
class AttentionMetricsInput:
    """Input metrics from frontend tracker"""
    session_id: str
    total_seconds: int
    focused_seconds: int
    distracted_seconds: int
    away_seconds: int
    tab_switch_count: int
    look_away_count: int
    idle_count: int
    focus_score: float
    engagement_score: float
    start_time: int
    gaze_tracking_used: bool = False


@dataclass
class AttentionPattern:
    """Detected attention pattern"""
    pattern_type: str       # peak_hour, focus_trend, distraction_pattern
    title: str
    description: str
    confidence: float       # 0-1
    supporting_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttentionInsightData:
    """Generated insight"""
    insight_type: str       # pattern, suggestion, achievement
    title: str
    description: str
    priority: int           # 1-10
    related_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttentionCorrelation:
    """Correlation between attention and learning"""
    topic_id: Optional[str]
    topic_name: Optional[str]
    avg_focus_score: float
    avg_quiz_accuracy: Optional[float]
    study_efficiency: float     # Higher accuracy per unit focus time
    sample_size: int


@dataclass
class AttentionAnalytics:
    """Complete attention analytics for a user"""
    user_id: str
    period_days: int
    
    # Aggregated metrics
    total_tracked_hours: float
    avg_focus_score: float
    avg_engagement_score: float
    focus_trend: str            # improving, stable, declining
    
    # Patterns
    peak_focus_hours: List[int]
    best_session_duration: int  # Optimal session length in minutes
    avg_distraction_interval: int  # Minutes between distractions
    
    # Correlations
    topic_correlations: List[AttentionCorrelation]
    
    # Insights
    insights: List[AttentionInsightData]


class AttentionProcessor:
    """
    Process and analyze attention signals.
    
    KEY RESPONSIBILITIES:
    1. Aggregate metrics from tracking sessions
    2. Detect patterns in attention data
    3. Correlate attention with learning outcomes
    4. Generate supportive insights (no judgments)
    5. Maintain daily/weekly summaries
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== Metric Ingestion ====================
    
    async def record_session_metrics(
        self,
        user_id: str,
        metrics: AttentionMetricsInput,
        study_session_id: Optional[str] = None,
    ) -> str:
        """
        Record attention metrics from a tracking session.
        
        This is called by the frontend at the end of a study session
        or periodically during long sessions.
        """
        from app.models.attention import AttentionSession, AttentionLevel
        
        # Calculate attention level
        attention_level = self._calculate_attention_level(metrics.focus_score)
        
        # Calculate consistency score
        consistency_score = self._calculate_consistency_score(metrics)
        
        # Check for existing session (for updates)
        result = await self.db.execute(
            select(AttentionSession)
            .where(AttentionSession.id == metrics.session_id)
        )
        session = result.scalar_one_or_none()
        
        if session:
            # Update existing session
            session.duration_seconds = metrics.total_seconds
            session.focused_seconds = metrics.focused_seconds
            session.distracted_seconds = metrics.distracted_seconds
            session.away_seconds = metrics.away_seconds
            session.tab_switch_count = metrics.tab_switch_count
            session.look_away_count = metrics.look_away_count
            session.idle_count = metrics.idle_count
            session.focus_score = metrics.focus_score
            session.engagement_score = metrics.engagement_score
            session.consistency_score = consistency_score
            session.attention_level = attention_level.value
            session.ended_at = datetime.now(timezone.utc)
        else:
            # Create new session
            session = AttentionSession(
                id=metrics.session_id,
                user_id=user_id,
                study_session_id=study_session_id,
                started_at=datetime.fromtimestamp(metrics.start_time / 1000, tz=timezone.utc),
                ended_at=datetime.now(timezone.utc),
                duration_seconds=metrics.total_seconds,
                focused_seconds=metrics.focused_seconds,
                distracted_seconds=metrics.distracted_seconds,
                away_seconds=metrics.away_seconds,
                tab_switch_count=metrics.tab_switch_count,
                look_away_count=metrics.look_away_count,
                idle_count=metrics.idle_count,
                focus_score=metrics.focus_score,
                engagement_score=metrics.engagement_score,
                consistency_score=consistency_score,
                attention_level=attention_level.value,
                gaze_tracking_enabled=metrics.gaze_tracking_used,
            )
            self.db.add(session)
        
        await self.db.flush()
        
        # Update daily summary
        await self._update_daily_summary(user_id, session)
        
        return session.id
    
    def _calculate_attention_level(self, focus_score: float) -> 'AttentionLevel':
        """Categorize attention level from focus score"""
        from app.models.attention import AttentionLevel
        
        if focus_score >= 80:
            return AttentionLevel.HIGH
        elif focus_score >= 60:
            return AttentionLevel.MODERATE
        elif focus_score >= 40:
            return AttentionLevel.LOW
        else:
            return AttentionLevel.MINIMAL
    
    def _calculate_consistency_score(self, metrics: AttentionMetricsInput) -> float:
        """
        Calculate consistency score.
        
        Higher score = more stable focus pattern
        Lower score = frequent alternation between focused/distracted
        """
        if metrics.total_seconds == 0:
            return 100.0
        
        # Calculate based on event frequency
        events_per_minute = (
            metrics.tab_switch_count + metrics.look_away_count
        ) / (metrics.total_seconds / 60)
        
        # Lower events = higher consistency
        # 0 events/min = 100, 10+ events/min = 0
        consistency = max(0, 100 - (events_per_minute * 10))
        
        return round(consistency, 2)
    
    async def _update_daily_summary(
        self,
        user_id: str,
        session: 'AttentionSession',
    ):
        """Update daily aggregated summary"""
        from app.models.attention import DailyAttentionSummary
        
        today = date.today()
        
        result = await self.db.execute(
            select(DailyAttentionSummary)
            .where(DailyAttentionSummary.user_id == user_id)
            .where(DailyAttentionSummary.date == today)
        )
        summary = result.scalar_one_or_none()
        
        if not summary:
            summary = DailyAttentionSummary(
                user_id=user_id,
                date=today,
            )
            self.db.add(summary)
        
        # Update aggregates
        summary.total_tracked_seconds += session.duration_seconds
        summary.total_focused_seconds += session.focused_seconds
        summary.total_distracted_seconds += session.distracted_seconds
        summary.total_away_seconds += session.away_seconds
        summary.total_tab_switches += session.tab_switch_count
        summary.total_look_aways += session.look_away_count
        summary.session_count += 1
        
        # Recalculate averages
        if summary.session_count > 0:
            summary.avg_session_duration = (
                summary.total_tracked_seconds / summary.session_count
            )
        
        # Get all today's focus scores for average
        result = await self.db.execute(
            select(func.avg(AttentionSession.focus_score))
            .where(AttentionSession.user_id == user_id)
            .where(func.date(AttentionSession.started_at) == today)
        )
        avg_focus = result.scalar()
        if avg_focus is not None:
            summary.avg_focus_score = round(avg_focus, 2)
        
        # Check for deep focus session
        if (session.duration_seconds >= 1800 and  # 30+ minutes
            session.focus_score >= 80):
            summary.had_deep_focus_session = True
        
        # Determine peak focus hour
        session_hour = session.started_at.hour
        if (summary.avg_focus_score is None or 
            session.focus_score > (summary.avg_focus_score or 0)):
            summary.peak_focus_hour = session_hour
        
        await self.db.flush()
    
    # ==================== Pattern Detection ====================
    
    async def detect_patterns(
        self,
        user_id: str,
        days: int = 14,
    ) -> List[AttentionPattern]:
        """
        Detect attention patterns from historical data.
        
        Patterns detected:
        - Peak focus hours (when user focuses best)
        - Optimal session duration
        - Distraction triggers (patterns before distractions)
        - Focus improvement trends
        """
        from app.models.attention import AttentionSession, DailyAttentionSummary
        
        patterns = []
        since = date.today() - timedelta(days=days)
        
        # Get session data
        result = await self.db.execute(
            select(AttentionSession)
            .where(AttentionSession.user_id == user_id)
            .where(AttentionSession.started_at >= datetime.combine(since, datetime.min.time()))
            .order_by(AttentionSession.started_at)
        )
        sessions = list(result.scalars().all())
        
        if not sessions:
            return patterns
        
        # === Pattern 1: Peak Focus Hours ===
        hourly_focus = {}
        for session in sessions:
            hour = session.started_at.hour
            if hour not in hourly_focus:
                hourly_focus[hour] = []
            if session.focus_score:
                hourly_focus[hour].append(session.focus_score)
        
        if hourly_focus:
            hourly_avg = {
                h: statistics.mean(scores) 
                for h, scores in hourly_focus.items() 
                if len(scores) >= 2
            }
            
            if hourly_avg:
                peak_hour = max(hourly_avg, key=hourly_avg.get)
                peak_score = hourly_avg[peak_hour]
                
                if peak_score > 70:  # Meaningful peak
                    patterns.append(AttentionPattern(
                        pattern_type="peak_hour",
                        title=f"Peak Focus at {peak_hour}:00",
                        description=f"Your focus is strongest around {peak_hour}:00, "
                                   f"averaging {peak_score:.0f}% focus score.",
                        confidence=min(len(hourly_focus.get(peak_hour, [])) / 5, 1.0),
                        supporting_data={"hour": peak_hour, "avg_score": peak_score}
                    ))
        
        # === Pattern 2: Optimal Session Duration ===
        duration_focus = []
        for session in sessions:
            if session.focus_score and session.duration_seconds > 300:  # >5 min
                duration_focus.append((session.duration_seconds / 60, session.focus_score))
        
        if len(duration_focus) >= 5:
            # Find duration range with best focus
            short = [f for d, f in duration_focus if d < 30]
            medium = [f for d, f in duration_focus if 30 <= d < 60]
            long = [f for d, f in duration_focus if d >= 60]
            
            ranges = []
            if len(short) >= 2:
                ranges.append(("15-30 minutes", statistics.mean(short)))
            if len(medium) >= 2:
                ranges.append(("30-60 minutes", statistics.mean(medium)))
            if len(long) >= 2:
                ranges.append(("60+ minutes", statistics.mean(long)))
            
            if ranges:
                best_range = max(ranges, key=lambda x: x[1])
                patterns.append(AttentionPattern(
                    pattern_type="optimal_duration",
                    title=f"Optimal Study Duration: {best_range[0]}",
                    description=f"You maintain best focus during {best_range[0]} sessions "
                               f"with {best_range[1]:.0f}% average focus.",
                    confidence=0.7,
                    supporting_data={"duration_range": best_range[0], "avg_focus": best_range[1]}
                ))
        
        # === Pattern 3: Focus Trend ===
        result = await self.db.execute(
            select(DailyAttentionSummary)
            .where(DailyAttentionSummary.user_id == user_id)
            .where(DailyAttentionSummary.date >= since)
            .order_by(DailyAttentionSummary.date)
        )
        daily_summaries = list(result.scalars().all())
        
        if len(daily_summaries) >= 7:
            recent_scores = [d.avg_focus_score for d in daily_summaries[-7:] if d.avg_focus_score]
            older_scores = [d.avg_focus_score for d in daily_summaries[:-7] if d.avg_focus_score]
            
            if recent_scores and older_scores:
                recent_avg = statistics.mean(recent_scores)
                older_avg = statistics.mean(older_scores)
                diff = recent_avg - older_avg
                
                if diff > 5:
                    patterns.append(AttentionPattern(
                        pattern_type="focus_trend",
                        title="Focus is Improving! 📈",
                        description=f"Your average focus has improved by {diff:.0f}% "
                                   f"over the past week. Great progress!",
                        confidence=0.8,
                        supporting_data={"improvement": diff}
                    ))
                elif diff < -5:
                    patterns.append(AttentionPattern(
                        pattern_type="focus_trend",
                        title="Focus Pattern Change Detected",
                        description="Your focus patterns have shifted recently. "
                                   "Consider reviewing your study environment.",
                        confidence=0.7,
                        supporting_data={"change": diff}
                    ))
        
        return patterns
    
    # ==================== Correlation Analysis ====================
    
    async def analyze_attention_learning_correlation(
        self,
        user_id: str,
        days: int = 30,
    ) -> List[AttentionCorrelation]:
        """
        Correlate attention metrics with learning outcomes.
        
        IMPORTANT: This is for insight generation, not judgment.
        We look for patterns like:
        - Topics where high focus correlates with better quiz scores
        - Optimal focus levels for different content types
        - Study efficiency patterns
        """
        from app.models.attention import AttentionSession
        from app.models.learning import StudySession, TopicProficiency
        from app.models.quiz import QuizAttempt
        
        correlations = []
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get study sessions with attention data
        result = await self.db.execute(
            select(AttentionSession)
            .options(selectinload(AttentionSession.user))
            .where(AttentionSession.user_id == user_id)
            .where(AttentionSession.started_at >= since)
            .where(AttentionSession.study_session_id.isnot(None))
        )
        attention_sessions = list(result.scalars().all())
        
        if not attention_sessions:
            return correlations
        
        # Get related study sessions with topic info
        study_session_ids = [a.study_session_id for a in attention_sessions]
        
        result = await self.db.execute(
            select(StudySession)
            .options(selectinload(StudySession.topic))
            .where(StudySession.id.in_(study_session_ids))
        )
        study_sessions = {s.id: s for s in result.scalars().all()}
        
        # Get topic proficiency data
        result = await self.db.execute(
            select(TopicProficiency)
            .where(TopicProficiency.user_id == user_id)
        )
        proficiencies = {p.topic_id: p for p in result.scalars().all()}
        
        # Group attention data by topic
        topic_attention: Dict[str, List[AttentionSession]] = {}
        
        for att_session in attention_sessions:
            study_session = study_sessions.get(att_session.study_session_id)
            if study_session and study_session.topic_id:
                topic_id = study_session.topic_id
                if topic_id not in topic_attention:
                    topic_attention[topic_id] = []
                topic_attention[topic_id].append(att_session)
        
        # Calculate correlations
        for topic_id, att_sessions in topic_attention.items():
            if len(att_sessions) < 2:
                continue
            
            study_session = next(
                (study_sessions[a.study_session_id] for a in att_sessions 
                 if a.study_session_id in study_sessions),
                None
            )
            topic_name = study_session.topic.name if study_session and study_session.topic else "Unknown"
            
            # Calculate average focus for topic
            focus_scores = [a.focus_score for a in att_sessions if a.focus_score]
            avg_focus = statistics.mean(focus_scores) if focus_scores else 0
            
            # Get topic accuracy
            proficiency = proficiencies.get(topic_id)
            avg_accuracy = proficiency.accuracy_percentage if proficiency else None
            
            # Calculate study efficiency
            total_focus_time = sum(a.focused_seconds for a in att_sessions)
            efficiency = 0.0
            if total_focus_time > 0 and avg_accuracy:
                # Higher accuracy per focus hour = higher efficiency
                efficiency = (avg_accuracy / 100) / (total_focus_time / 3600)
            
            correlations.append(AttentionCorrelation(
                topic_id=topic_id,
                topic_name=topic_name,
                avg_focus_score=round(avg_focus, 2),
                avg_quiz_accuracy=round(avg_accuracy, 2) if avg_accuracy else None,
                study_efficiency=round(efficiency, 4),
                sample_size=len(att_sessions),
            ))
        
        # Sort by sample size (most reliable first)
        correlations.sort(key=lambda c: c.sample_size, reverse=True)
        
        return correlations
    
    # ==================== Insight Generation ====================
    
    async def generate_insights(
        self,
        user_id: str,
        days: int = 14,
    ) -> List[AttentionInsightData]:
        """
        Generate supportive insights from attention data.
        
        DESIGN: Insights are:
        - Supportive and encouraging
        - Actionable with clear suggestions
        - Based on patterns, not individual sessions
        - Never judgmental or critical
        """
        insights = []
        
        # Detect patterns first
        patterns = await self.detect_patterns(user_id, days)
        
        # Get correlations
        correlations = await self.analyze_attention_learning_correlation(user_id, days)
        
        # === Insight 1: Peak Performance Times ===
        peak_pattern = next(
            (p for p in patterns if p.pattern_type == "peak_hour"),
            None
        )
        if peak_pattern:
            hour = peak_pattern.supporting_data.get("hour", 10)
            insights.append(AttentionInsightData(
                insight_type="pattern",
                title="🌟 Your Focus Superpower Hours",
                description=f"You're most focused around {hour}:00. "
                           f"Try scheduling challenging topics during this time!",
                priority=8,
                related_metrics=peak_pattern.supporting_data,
            ))
        
        # === Insight 2: Session Duration Recommendations ===
        duration_pattern = next(
            (p for p in patterns if p.pattern_type == "optimal_duration"),
            None
        )
        if duration_pattern:
            insights.append(AttentionInsightData(
                insight_type="suggestion",
                title="⏱️ Your Sweet Spot Session Length",
                description=duration_pattern.description,
                priority=7,
                related_metrics=duration_pattern.supporting_data,
            ))
        
        # === Insight 3: Topic-Focus Correlation ===
        high_efficiency_topics = [c for c in correlations if c.study_efficiency > 1.0]
        if high_efficiency_topics:
            best_topic = max(high_efficiency_topics, key=lambda c: c.study_efficiency)
            insights.append(AttentionInsightData(
                insight_type="pattern",
                title=f"🎯 High Efficiency in {best_topic.topic_name}",
                description=f"Your focused study time on {best_topic.topic_name} "
                           f"is paying off with strong retention!",
                priority=7,
                related_metrics={
                    "topic": best_topic.topic_name,
                    "efficiency": best_topic.study_efficiency,
                },
            ))
        
        # === Insight 4: Improvement Trend ===
        trend_pattern = next(
            (p for p in patterns if p.pattern_type == "focus_trend"),
            None
        )
        if trend_pattern and "improvement" in trend_pattern.supporting_data:
            insights.append(AttentionInsightData(
                insight_type="achievement",
                title="📈 Focus Improvement Detected!",
                description=trend_pattern.description,
                priority=9,
                related_metrics=trend_pattern.supporting_data,
            ))
        
        # === Insight 5: Break Reminder (if needed) ===
        from app.models.attention import DailyAttentionSummary
        
        today = date.today()
        result = await self.db.execute(
            select(DailyAttentionSummary)
            .where(DailyAttentionSummary.user_id == user_id)
            .where(DailyAttentionSummary.date == today)
        )
        today_summary = result.scalar_one_or_none()
        
        if today_summary and today_summary.total_tracked_seconds > 7200:  # >2 hours
            if (today_summary.avg_focus_score or 0) < 60:
                insights.append(AttentionInsightData(
                    insight_type="suggestion",
                    title="☕ Time for a Mindful Break",
                    description="You've been studying for a while. "
                               "A short break can help restore focus!",
                    priority=8,
                    related_metrics={
                        "hours_studied": today_summary.total_tracked_seconds / 3600,
                    },
                ))
        
        # Sort by priority
        insights.sort(key=lambda i: i.priority, reverse=True)
        
        return insights[:5]  # Return top 5 insights
    
    # ==================== Analytics Aggregation ====================
    
    async def get_user_analytics(
        self,
        user_id: str,
        days: int = 30,
    ) -> AttentionAnalytics:
        """Get comprehensive attention analytics for a user"""
        from app.models.attention import AttentionSession, DailyAttentionSummary
        
        since = date.today() - timedelta(days=days)
        
        # Get daily summaries
        result = await self.db.execute(
            select(DailyAttentionSummary)
            .where(DailyAttentionSummary.user_id == user_id)
            .where(DailyAttentionSummary.date >= since)
            .order_by(DailyAttentionSummary.date)
        )
        summaries = list(result.scalars().all())
        
        # Calculate aggregates
        total_seconds = sum(s.total_tracked_seconds for s in summaries)
        focus_scores = [s.avg_focus_score for s in summaries if s.avg_focus_score]
        engagement_scores = [s.avg_engagement_score for s in summaries if s.avg_engagement_score]
        
        avg_focus = statistics.mean(focus_scores) if focus_scores else 0
        avg_engagement = statistics.mean(engagement_scores) if engagement_scores else 0
        
        # Determine trend
        if len(focus_scores) >= 7:
            recent = statistics.mean(focus_scores[-7:])
            older = statistics.mean(focus_scores[:-7]) if len(focus_scores) > 7 else recent
            diff = recent - older
            trend = "improving" if diff > 3 else ("declining" if diff < -3 else "stable")
        else:
            trend = "stable"
        
        # Peak hours
        peak_hours = [s.peak_focus_hour for s in summaries if s.peak_focus_hour is not None]
        peak_hours_list = list(set(sorted(peak_hours)))[:3] if peak_hours else []
        
        # Get session data for detailed analysis
        result = await self.db.execute(
            select(AttentionSession)
            .where(AttentionSession.user_id == user_id)
            .where(AttentionSession.started_at >= datetime.combine(since, datetime.min.time()))
        )
        sessions = list(result.scalars().all())
        
        # Best session duration
        if sessions:
            duration_focus = [(s.duration_seconds / 60, s.focus_score or 0) for s in sessions]
            best_duration = max(duration_focus, key=lambda x: x[1], default=(30, 0))
            best_session_duration = int(best_duration[0])
        else:
            best_session_duration = 30
        
        # Average distraction interval
        if sessions:
            distraction_intervals = []
            for s in sessions:
                if s.duration_seconds > 0 and s.look_away_count > 0:
                    interval = s.duration_seconds / 60 / s.look_away_count
                    distraction_intervals.append(interval)
            avg_distraction = int(statistics.mean(distraction_intervals)) if distraction_intervals else 30
        else:
            avg_distraction = 30
        
        # Get patterns and insights
        patterns = await self.detect_patterns(user_id, days)
        correlations = await self.analyze_attention_learning_correlation(user_id, days)
        insights = await self.generate_insights(user_id, days)
        
        return AttentionAnalytics(
            user_id=user_id,
            period_days=days,
            total_tracked_hours=round(total_seconds / 3600, 2),
            avg_focus_score=round(avg_focus, 2),
            avg_engagement_score=round(avg_engagement, 2),
            focus_trend=trend,
            peak_focus_hours=peak_hours_list,
            best_session_duration=best_session_duration,
            avg_distraction_interval=avg_distraction,
            topic_correlations=correlations,
            insights=insights,
        )
