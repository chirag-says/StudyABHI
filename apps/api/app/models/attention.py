"""
Attention Signal Models
Database models for storing and analyzing attention metrics.

DESIGN PRINCIPLES:
- Store aggregated metrics only, never raw video data
- Focus on insights, not judgment
- Enable correlation with study sessions
- Support privacy controls
"""
import uuid
from datetime import datetime, timezone, date
from sqlalchemy import (
    Column, String, Boolean, Integer, Text, ForeignKey, 
    DateTime, JSON, Float, Date, UniqueConstraint
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.base import TimestampMixin


class AttentionLevel(str, enum.Enum):
    """Attention level categories"""
    HIGH = "high"           # 80-100% focus
    MODERATE = "moderate"   # 60-80% focus
    LOW = "low"             # 40-60% focus
    MINIMAL = "minimal"     # <40% focus


class AttentionSession(Base, TimestampMixin):
    """
    Aggregated attention metrics for a study session.
    
    PRIVACY:
    - No raw video data
    - No screenshots
    - Only aggregated metrics
    - User can delete anytime
    """
    __tablename__ = "attention_sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Link to study session
    study_session_id = Column(String(36), ForeignKey("study_sessions.id", ondelete="SET NULL"), nullable=True)
    
    # Session timing
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)
    
    # Time distribution (in seconds)
    focused_seconds = Column(Integer, default=0)        # Actively looking at screen
    distracted_seconds = Column(Integer, default=0)     # Looking away briefly
    away_seconds = Column(Integer, default=0)           # Tab switched/window changed
    idle_seconds = Column(Integer, default=0)           # No interaction
    
    # Event counts
    tab_switch_count = Column(Integer, default=0)
    look_away_count = Column(Integer, default=0)
    idle_count = Column(Integer, default=0)
    return_count = Column(Integer, default=0)           # Times user refocused
    
    # Derived scores (0-100)
    focus_score = Column(Float, nullable=True)          # Focused / Total time
    engagement_score = Column(Float, nullable=True)     # (Focused + Distracted) / Total
    consistency_score = Column(Float, nullable=True)    # Based on focus pattern stability
    
    # Attention level category
    attention_level = Column(String(20), nullable=True)
    
    # Tracking configuration used
    gaze_tracking_enabled = Column(Boolean, default=False)
    tab_tracking_enabled = Column(Boolean, default=True)
    
    # Aggregation status
    is_processed = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", backref="attention_sessions")
    
    def __repr__(self):
        return f"<AttentionSession {self.id} - {self.focus_score}%>"


class DailyAttentionSummary(Base, TimestampMixin):
    """
    Daily aggregated attention metrics.
    Used for trend analysis and insights.
    """
    __tablename__ = "daily_attention_summaries"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    
    # Aggregated metrics
    total_tracked_seconds = Column(Integer, default=0)
    total_focused_seconds = Column(Integer, default=0)
    total_distracted_seconds = Column(Integer, default=0)
    total_away_seconds = Column(Integer, default=0)
    
    # Session counts
    session_count = Column(Integer, default=0)
    avg_session_duration = Column(Float, nullable=True)
    
    # Daily scores
    avg_focus_score = Column(Float, nullable=True)
    avg_engagement_score = Column(Float, nullable=True)
    peak_focus_hour = Column(Integer, nullable=True)    # Hour of day with best focus
    
    # Event summaries
    total_tab_switches = Column(Integer, default=0)
    total_look_aways = Column(Integer, default=0)
    
    # Insights flags
    had_deep_focus_session = Column(Boolean, default=False)  # >30min with >80% focus
    focus_improved = Column(Boolean, default=False)          # Better than yesterday
    
    # Relationships
    user = relationship("User", backref="daily_attention_summaries")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='unique_attention_user_date'),
    )
    
    def __repr__(self):
        return f"<DailyAttentionSummary {self.date} - {self.avg_focus_score}%>"


class AttentionInsight(Base, TimestampMixin):
    """
    Generated insights from attention data.
    
    DESIGN: Insights are supportive, never judgmental.
    Focus on patterns and actionable suggestions.
    """
    __tablename__ = "attention_insights"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Insight details
    insight_type = Column(String(50), nullable=False)   # pattern, suggestion, achievement
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    
    # Validity
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    valid_from = Column(Date, nullable=False)
    valid_until = Column(Date, nullable=True)
    
    # User interaction
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    is_helpful = Column(Boolean, nullable=True)         # User feedback
    
    # Context
    related_data = Column(JSON, nullable=True)          # Supporting metrics
    
    # Relationships
    user = relationship("User", backref="attention_insights")
    
    def __repr__(self):
        return f"<AttentionInsight {self.title}>"


class UserAttentionPreferences(Base, TimestampMixin):
    """
    User preferences for attention tracking.
    Full user control over privacy.
    """
    __tablename__ = "user_attention_preferences"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Feature toggles
    tracking_enabled = Column(Boolean, default=False)   # Master switch
    gaze_tracking_enabled = Column(Boolean, default=False)
    tab_tracking_enabled = Column(Boolean, default=True)
    idle_tracking_enabled = Column(Boolean, default=True)
    
    # Privacy settings
    data_retention_days = Column(Integer, default=90)   # Auto-delete after N days
    share_with_analytics = Column(Boolean, default=False)
    
    # Notification preferences
    show_focus_reminders = Column(Boolean, default=True)
    show_break_reminders = Column(Boolean, default=True)
    show_insights = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", backref="attention_preferences", uselist=False)
    
    def __repr__(self):
        return f"<UserAttentionPreferences {self.user_id}>"
