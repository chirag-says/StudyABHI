"""
User Privacy Preferences Model
Stores user consent and privacy settings
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class UserPrivacySettings(Base, TimestampMixin):
    """
    User privacy and consent settings.
    GDPR-compliant storage of user preferences.
    """
    __tablename__ = "user_privacy_settings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # AI Features Consent
    ai_features_enabled = Column(Boolean, default=True, nullable=False)
    ai_tutoring_enabled = Column(Boolean, default=True, nullable=False)
    ai_quiz_generation_enabled = Column(Boolean, default=True, nullable=False)
    ai_study_recommendations_enabled = Column(Boolean, default=True, nullable=False)
    
    # Webcam/Proctoring Features
    webcam_enabled = Column(Boolean, default=False, nullable=False)
    attention_tracking_enabled = Column(Boolean, default=False, nullable=False)
    session_recording_enabled = Column(Boolean, default=False, nullable=False)
    
    # Data Collection Consent
    analytics_enabled = Column(Boolean, default=True, nullable=False)
    personalization_enabled = Column(Boolean, default=True, nullable=False)
    marketing_emails_enabled = Column(Boolean, default=False, nullable=False)
    
    # Data Retention
    data_retention_days = Column(String(20), default="365", nullable=False)  # "30", "90", "365", "forever"
    
    # Consent timestamps (for audit trail)
    ai_consent_date = Column(DateTime, nullable=True)
    webcam_consent_date = Column(DateTime, nullable=True)
    analytics_consent_date = Column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<UserPrivacySettings user_id={self.user_id}>"


class DataExportRequest(Base, TimestampMixin):
    """
    Track data export requests for GDPR compliance.
    """
    __tablename__ = "data_export_requests"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Request status
    status = Column(String(20), default="pending", nullable=False)  # pending, processing, completed, failed
    
    # Export details
    export_format = Column(String(20), default="json", nullable=False)  # json, csv, zip
    include_quiz_history = Column(Boolean, default=True)
    include_study_sessions = Column(Boolean, default=True)
    include_ai_conversations = Column(Boolean, default=True)
    include_documents = Column(Boolean, default=True)
    
    # File info
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(String(20), nullable=True)
    download_url = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    requested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<DataExportRequest id={self.id} status={self.status}>"


class AccountDeletionRequest(Base, TimestampMixin):
    """
    Track account deletion requests with cooling-off period.
    """
    __tablename__ = "account_deletion_requests"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Request details
    reason = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, cancelled, completed
    
    # Cooling off period (14 days default for GDPR)
    scheduled_deletion_date = Column(DateTime, nullable=False)
    
    # Confirmation
    confirmed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<AccountDeletionRequest id={self.id} status={self.status}>"
