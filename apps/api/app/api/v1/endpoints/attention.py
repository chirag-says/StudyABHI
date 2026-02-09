"""
Attention Tracking API Endpoints
Record attention metrics and retrieve insights.

PRIVACY-FIRST: Only aggregated metrics are stored.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== Schemas ====================

class RecordMetricsRequest(BaseModel):
    """Record attention metrics from frontend tracker"""
    session_id: str
    total_seconds: int = Field(ge=0)
    focused_seconds: int = Field(ge=0)
    distracted_seconds: int = Field(ge=0)
    away_seconds: int = Field(ge=0)
    tab_switch_count: int = Field(ge=0)
    look_away_count: int = Field(ge=0)
    idle_count: int = Field(ge=0)
    focus_score: float = Field(ge=0, le=100)
    engagement_score: float = Field(ge=0, le=100)
    start_time: int
    study_session_id: Optional[str] = None
    gaze_tracking_used: bool = False


class SessionMetricsResponse(BaseModel):
    """Response after recording metrics"""
    session_id: str
    focus_score: float
    attention_level: str
    message: str


class PatternResponse(BaseModel):
    """Detected attention pattern"""
    pattern_type: str
    title: str
    description: str
    confidence: float


class InsightResponse(BaseModel):
    """Attention insight"""
    insight_type: str
    title: str
    description: str
    priority: int


class CorrelationResponse(BaseModel):
    """Topic-attention correlation"""
    topic_id: Optional[str] = None
    topic_name: Optional[str] = None
    avg_focus_score: float
    avg_quiz_accuracy: Optional[float] = None
    study_efficiency: float


class AnalyticsResponse(BaseModel):
    """Complete attention analytics"""
    total_tracked_hours: float
    avg_focus_score: float
    avg_engagement_score: float
    focus_trend: str
    peak_focus_hours: List[int]
    best_session_duration: int
    avg_distraction_interval: int
    patterns: List[PatternResponse]
    insights: List[InsightResponse]
    correlations: List[CorrelationResponse]


class PreferencesRequest(BaseModel):
    """Update tracking preferences"""
    tracking_enabled: Optional[bool] = None
    gaze_tracking_enabled: Optional[bool] = None
    tab_tracking_enabled: Optional[bool] = None
    idle_tracking_enabled: Optional[bool] = None
    data_retention_days: Optional[int] = Field(None, ge=7, le=365)
    show_focus_reminders: Optional[bool] = None
    show_break_reminders: Optional[bool] = None
    show_insights: Optional[bool] = None


class PreferencesResponse(BaseModel):
    """Tracking preferences"""
    tracking_enabled: bool
    gaze_tracking_enabled: bool
    tab_tracking_enabled: bool
    idle_tracking_enabled: bool
    data_retention_days: int
    show_focus_reminders: bool
    show_break_reminders: bool
    show_insights: bool


class DailySummaryResponse(BaseModel):
    """Daily attention summary"""
    date: str
    total_tracked_minutes: int
    avg_focus_score: Optional[float] = None
    session_count: int
    had_deep_focus: bool
    peak_hour: Optional[int] = None


# ==================== Endpoints ====================

@router.post("/metrics", response_model=SessionMetricsResponse)
async def record_attention_metrics(
    request: RecordMetricsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record attention metrics from a study session.
    
    Called by the frontend attention tracker periodically
    or at the end of a study session.
    """
    from app.services.attention_service import AttentionProcessor, AttentionMetricsInput
    from app.models.attention import AttentionLevel
    
    processor = AttentionProcessor(db)
    
    metrics = AttentionMetricsInput(
        session_id=request.session_id,
        total_seconds=request.total_seconds,
        focused_seconds=request.focused_seconds,
        distracted_seconds=request.distracted_seconds,
        away_seconds=request.away_seconds,
        tab_switch_count=request.tab_switch_count,
        look_away_count=request.look_away_count,
        idle_count=request.idle_count,
        focus_score=request.focus_score,
        engagement_score=request.engagement_score,
        start_time=request.start_time,
        gaze_tracking_used=request.gaze_tracking_used,
    )
    
    session_id = await processor.record_session_metrics(
        user_id=current_user.id,
        metrics=metrics,
        study_session_id=request.study_session_id,
    )
    
    await db.commit()
    
    # Generate encouraging message based on focus score
    if request.focus_score >= 80:
        message = "Excellent focus! You're in the zone! 🌟"
        level = AttentionLevel.HIGH
    elif request.focus_score >= 60:
        message = "Good focus session! Keep it up! 👍"
        level = AttentionLevel.MODERATE
    elif request.focus_score >= 40:
        message = "Solid effort! Every bit of progress counts. 💪"
        level = AttentionLevel.LOW
    else:
        message = "It's okay to have challenging sessions. Tomorrow is a new day! 🌱"
        level = AttentionLevel.MINIMAL
    
    return SessionMetricsResponse(
        session_id=session_id,
        focus_score=request.focus_score,
        attention_level=level.value,
        message=message,
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_attention_analytics(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get comprehensive attention analytics.
    
    Includes patterns, insights, and learning correlations.
    """
    from app.services.attention_service import AttentionProcessor
    
    processor = AttentionProcessor(db)
    analytics = await processor.get_user_analytics(current_user.id, days)
    
    # Convert to response
    patterns = await processor.detect_patterns(current_user.id, days)
    
    return AnalyticsResponse(
        total_tracked_hours=analytics.total_tracked_hours,
        avg_focus_score=analytics.avg_focus_score,
        avg_engagement_score=analytics.avg_engagement_score,
        focus_trend=analytics.focus_trend,
        peak_focus_hours=analytics.peak_focus_hours,
        best_session_duration=analytics.best_session_duration,
        avg_distraction_interval=analytics.avg_distraction_interval,
        patterns=[
            PatternResponse(
                pattern_type=p.pattern_type,
                title=p.title,
                description=p.description,
                confidence=p.confidence,
            )
            for p in patterns
        ],
        insights=[
            InsightResponse(
                insight_type=i.insight_type,
                title=i.title,
                description=i.description,
                priority=i.priority,
            )
            for i in analytics.insights
        ],
        correlations=[
            CorrelationResponse(
                topic_id=c.topic_id,
                topic_name=c.topic_name,
                avg_focus_score=c.avg_focus_score,
                avg_quiz_accuracy=c.avg_quiz_accuracy,
                study_efficiency=c.study_efficiency,
            )
            for c in analytics.topic_correlations
        ],
    )


@router.get("/insights", response_model=List[InsightResponse])
async def get_attention_insights(
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get personalized attention insights."""
    from app.services.attention_service import AttentionProcessor
    
    processor = AttentionProcessor(db)
    insights = await processor.generate_insights(current_user.id, days)
    
    return [
        InsightResponse(
            insight_type=i.insight_type,
            title=i.title,
            description=i.description,
            priority=i.priority,
        )
        for i in insights
    ]


@router.get("/patterns", response_model=List[PatternResponse])
async def get_attention_patterns(
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detected attention patterns."""
    from app.services.attention_service import AttentionProcessor
    
    processor = AttentionProcessor(db)
    patterns = await processor.detect_patterns(current_user.id, days)
    
    return [
        PatternResponse(
            pattern_type=p.pattern_type,
            title=p.title,
            description=p.description,
            confidence=p.confidence,
        )
        for p in patterns
    ]


@router.get("/daily-summary", response_model=List[DailySummaryResponse])
async def get_daily_summaries(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get daily attention summaries for trend visualization."""
    from app.models.attention import DailyAttentionSummary
    from sqlalchemy import select
    from datetime import timedelta
    
    since = date.today() - timedelta(days=days)
    
    result = await db.execute(
        select(DailyAttentionSummary)
        .where(DailyAttentionSummary.user_id == current_user.id)
        .where(DailyAttentionSummary.date >= since)
        .order_by(DailyAttentionSummary.date.desc())
    )
    summaries = list(result.scalars().all())
    
    return [
        DailySummaryResponse(
            date=s.date.isoformat(),
            total_tracked_minutes=s.total_tracked_seconds // 60,
            avg_focus_score=s.avg_focus_score,
            session_count=s.session_count,
            had_deep_focus=s.had_deep_focus_session,
            peak_hour=s.peak_focus_hour,
        )
        for s in summaries
    ]


@router.get("/preferences", response_model=PreferencesResponse)
async def get_tracking_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's attention tracking preferences."""
    from app.models.attention import UserAttentionPreferences
    from sqlalchemy import select
    
    result = await db.execute(
        select(UserAttentionPreferences)
        .where(UserAttentionPreferences.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()
    
    if not prefs:
        # Return defaults
        return PreferencesResponse(
            tracking_enabled=False,
            gaze_tracking_enabled=False,
            tab_tracking_enabled=True,
            idle_tracking_enabled=True,
            data_retention_days=90,
            show_focus_reminders=True,
            show_break_reminders=True,
            show_insights=True,
        )
    
    return PreferencesResponse(
        tracking_enabled=prefs.tracking_enabled,
        gaze_tracking_enabled=prefs.gaze_tracking_enabled,
        tab_tracking_enabled=prefs.tab_tracking_enabled,
        idle_tracking_enabled=prefs.idle_tracking_enabled,
        data_retention_days=prefs.data_retention_days,
        show_focus_reminders=prefs.show_focus_reminders,
        show_break_reminders=prefs.show_break_reminders,
        show_insights=prefs.show_insights,
    )


@router.put("/preferences", response_model=PreferencesResponse)
async def update_tracking_preferences(
    request: PreferencesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update attention tracking preferences."""
    from app.models.attention import UserAttentionPreferences
    from sqlalchemy import select
    
    result = await db.execute(
        select(UserAttentionPreferences)
        .where(UserAttentionPreferences.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()
    
    if not prefs:
        prefs = UserAttentionPreferences(user_id=current_user.id)
        db.add(prefs)
    
    # Update non-None fields
    if request.tracking_enabled is not None:
        prefs.tracking_enabled = request.tracking_enabled
    if request.gaze_tracking_enabled is not None:
        prefs.gaze_tracking_enabled = request.gaze_tracking_enabled
    if request.tab_tracking_enabled is not None:
        prefs.tab_tracking_enabled = request.tab_tracking_enabled
    if request.idle_tracking_enabled is not None:
        prefs.idle_tracking_enabled = request.idle_tracking_enabled
    if request.data_retention_days is not None:
        prefs.data_retention_days = request.data_retention_days
    if request.show_focus_reminders is not None:
        prefs.show_focus_reminders = request.show_focus_reminders
    if request.show_break_reminders is not None:
        prefs.show_break_reminders = request.show_break_reminders
    if request.show_insights is not None:
        prefs.show_insights = request.show_insights
    
    await db.commit()
    await db.refresh(prefs)
    
    return PreferencesResponse(
        tracking_enabled=prefs.tracking_enabled,
        gaze_tracking_enabled=prefs.gaze_tracking_enabled,
        tab_tracking_enabled=prefs.tab_tracking_enabled,
        idle_tracking_enabled=prefs.idle_tracking_enabled,
        data_retention_days=prefs.data_retention_days,
        show_focus_reminders=prefs.show_focus_reminders,
        show_break_reminders=prefs.show_break_reminders,
        show_insights=prefs.show_insights,
    )


@router.delete("/data")
async def delete_attention_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete all attention tracking data for the user.
    
    PRIVACY: Users have full control over their data.
    """
    from app.models.attention import (
        AttentionSession, DailyAttentionSummary, 
        AttentionInsight, UserAttentionPreferences
    )
    from sqlalchemy import delete
    
    # Delete all attention data
    await db.execute(
        delete(AttentionSession).where(AttentionSession.user_id == current_user.id)
    )
    await db.execute(
        delete(DailyAttentionSummary).where(DailyAttentionSummary.user_id == current_user.id)
    )
    await db.execute(
        delete(AttentionInsight).where(AttentionInsight.user_id == current_user.id)
    )
    
    await db.commit()
    
    return {"message": "All attention tracking data has been deleted."}
