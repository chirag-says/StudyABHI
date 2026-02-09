"""
Privacy Schemas
Pydantic models for privacy-related requests/responses
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class DataRetentionPeriod(str, Enum):
    DAYS_30 = "30"
    DAYS_90 = "90"
    DAYS_365 = "365"
    FOREVER = "forever"


class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    ZIP = "zip"


class ExportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Privacy Settings Schemas
class PrivacySettingsBase(BaseModel):
    """Base privacy settings"""
    ai_features_enabled: bool = True
    ai_tutoring_enabled: bool = True
    ai_quiz_generation_enabled: bool = True
    ai_study_recommendations_enabled: bool = True
    webcam_enabled: bool = False
    attention_tracking_enabled: bool = False
    session_recording_enabled: bool = False
    analytics_enabled: bool = True
    personalization_enabled: bool = True
    marketing_emails_enabled: bool = False
    data_retention_days: DataRetentionPeriod = DataRetentionPeriod.DAYS_365


class PrivacySettingsUpdate(BaseModel):
    """Schema for updating privacy settings"""
    ai_features_enabled: Optional[bool] = None
    ai_tutoring_enabled: Optional[bool] = None
    ai_quiz_generation_enabled: Optional[bool] = None
    ai_study_recommendations_enabled: Optional[bool] = None
    webcam_enabled: Optional[bool] = None
    attention_tracking_enabled: Optional[bool] = None
    session_recording_enabled: Optional[bool] = None
    analytics_enabled: Optional[bool] = None
    personalization_enabled: Optional[bool] = None
    marketing_emails_enabled: Optional[bool] = None
    data_retention_days: Optional[DataRetentionPeriod] = None


class PrivacySettingsResponse(PrivacySettingsBase):
    """Response schema for privacy settings"""
    id: str
    user_id: str
    ai_consent_date: Optional[datetime] = None
    webcam_consent_date: Optional[datetime] = None
    analytics_consent_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Data Export Schemas
class DataExportRequest(BaseModel):
    """Request schema for data export"""
    export_format: ExportFormat = ExportFormat.JSON
    include_quiz_history: bool = True
    include_study_sessions: bool = True
    include_ai_conversations: bool = True
    include_documents: bool = True


class DataExportResponse(BaseModel):
    """Response schema for data export request"""
    id: str
    user_id: str
    status: ExportStatus
    export_format: ExportFormat
    include_quiz_history: bool
    include_study_sessions: bool
    include_ai_conversations: bool
    include_documents: bool
    download_url: Optional[str] = None
    file_size_bytes: Optional[str] = None
    expires_at: Optional[datetime] = None
    requested_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Account Deletion Schemas
class AccountDeletionRequest(BaseModel):
    """Request schema for account deletion"""
    reason: Optional[str] = Field(None, max_length=500)
    confirm_email: str  # User must enter email to confirm


class AccountDeletionResponse(BaseModel):
    """Response schema for account deletion request"""
    id: str
    status: str
    scheduled_deletion_date: datetime
    message: str

    class Config:
        from_attributes = True


class AccountDeletionCancel(BaseModel):
    """Request to cancel account deletion"""
    confirm: bool = True


# Consent Schemas
class ConsentUpdate(BaseModel):
    """Update specific consent"""
    consent_type: str  # "ai", "webcam", "analytics"
    granted: bool


class ConsentHistoryItem(BaseModel):
    """Single consent history entry"""
    consent_type: str
    granted: bool
    timestamp: datetime


class UserDataSummary(BaseModel):
    """Summary of user's stored data"""
    total_quiz_attempts: int
    total_study_sessions: int
    total_ai_conversations: int
    total_documents: int
    total_notes: int
    account_age_days: int
    storage_used_mb: float
