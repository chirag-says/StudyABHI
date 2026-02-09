"""
Privacy API Endpoints
User privacy controls, data export, and account deletion
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.privacy import (
    PrivacySettingsUpdate,
    PrivacySettingsResponse,
    DataExportRequest,
    DataExportResponse,
    AccountDeletionRequest,
    AccountDeletionResponse,
    AccountDeletionCancel,
    UserDataSummary,
)
from app.services.privacy_service import PrivacyService


router = APIRouter(prefix="/privacy", tags=["Privacy"])


# ==================== Privacy Settings ====================

@router.get("/settings", response_model=PrivacySettingsResponse)
async def get_privacy_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's privacy settings.
    Returns default settings if none exist.
    """
    service = PrivacyService(db)
    settings = await service.get_privacy_settings(current_user.id)
    return settings


@router.patch("/settings", response_model=PrivacySettingsResponse)
async def update_privacy_settings(
    updates: PrivacySettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user's privacy settings.
    
    **AI Features:**
    - `ai_features_enabled`: Master toggle for all AI features
    - `ai_tutoring_enabled`: AI tutor conversations
    - `ai_quiz_generation_enabled`: AI-generated quizzes
    - `ai_study_recommendations_enabled`: Personalized study plans
    
    **Webcam Features:**
    - `webcam_enabled`: Master toggle for webcam
    - `attention_tracking_enabled`: Focus/attention monitoring
    - `session_recording_enabled`: Record study sessions
    
    **Data Collection:**
    - `analytics_enabled`: Usage analytics
    - `personalization_enabled`: Personalized content
    - `marketing_emails_enabled`: Marketing communications
    """
    service = PrivacyService(db)
    settings = await service.update_privacy_settings(
        current_user.id,
        updates.model_dump(exclude_unset=True)
    )
    return settings


@router.post("/settings/ai/enable")
async def enable_ai_features(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable all AI features with timestamp consent"""
    service = PrivacyService(db)
    settings = await service.update_privacy_settings(
        current_user.id,
        {
            "ai_features_enabled": True,
            "ai_tutoring_enabled": True,
            "ai_quiz_generation_enabled": True,
            "ai_study_recommendations_enabled": True,
        }
    )
    return {"message": "AI features enabled", "consent_date": settings.ai_consent_date}


@router.post("/settings/ai/disable")
async def disable_ai_features(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disable all AI features"""
    service = PrivacyService(db)
    await service.update_privacy_settings(
        current_user.id,
        {
            "ai_features_enabled": False,
            "ai_tutoring_enabled": False,
            "ai_quiz_generation_enabled": False,
            "ai_study_recommendations_enabled": False,
        }
    )
    return {"message": "AI features disabled"}


@router.post("/settings/webcam/enable")
async def enable_webcam_features(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable webcam features with explicit consent"""
    service = PrivacyService(db)
    settings = await service.update_privacy_settings(
        current_user.id,
        {
            "webcam_enabled": True,
            "attention_tracking_enabled": True,
        }
    )
    return {"message": "Webcam features enabled", "consent_date": settings.webcam_consent_date}


@router.post("/settings/webcam/disable")
async def disable_webcam_features(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disable all webcam features"""
    service = PrivacyService(db)
    await service.update_privacy_settings(
        current_user.id,
        {
            "webcam_enabled": False,
            "attention_tracking_enabled": False,
            "session_recording_enabled": False,
        }
    )
    return {"message": "Webcam features disabled"}


# ==================== Data Export ====================

@router.post("/export", response_model=DataExportResponse)
async def request_data_export(
    request: DataExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Request a full export of your data.
    
    **Includes:**
    - Profile information
    - Quiz history and scores
    - Study session data
    - AI conversation history
    - Uploaded documents
    
    Export will be processed in the background.
    Download link valid for 48 hours.
    """
    service = PrivacyService(db)
    export_request = await service.request_data_export(
        user_id=current_user.id,
        export_format=request.export_format.value,
        include_quiz_history=request.include_quiz_history,
        include_study_sessions=request.include_study_sessions,
        include_ai_conversations=request.include_ai_conversations,
        include_documents=request.include_documents
    )
    
    # Process export in background
    background_tasks.add_task(service.process_data_export, export_request.id)
    
    return export_request


@router.get("/export/{export_id}", response_model=DataExportResponse)
async def get_export_status(
    export_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the status of a data export request"""
    service = PrivacyService(db)
    export_request = await service.get_export_status(export_id, current_user.id)
    
    if not export_request:
        raise HTTPException(status_code=404, detail="Export request not found")
    
    return export_request


@router.get("/export/{export_id}/download")
async def download_export(
    export_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download the exported data file"""
    service = PrivacyService(db)
    export_request = await service.get_export_status(export_id, current_user.id)
    
    if not export_request:
        raise HTTPException(status_code=404, detail="Export request not found")
    
    if export_request.status != "completed":
        raise HTTPException(status_code=400, detail=f"Export not ready. Status: {export_request.status}")
    
    if export_request.expires_at and datetime.now(timezone.utc) > export_request.expires_at:
        raise HTTPException(status_code=410, detail="Export link has expired")
    
    if not export_request.file_path:
        raise HTTPException(status_code=500, detail="Export file not found")
    
    return FileResponse(
        export_request.file_path,
        filename=f"upsc_data_export_{current_user.id[:8]}.{export_request.export_format}",
        media_type="application/octet-stream"
    )


# ==================== Account Deletion ====================

@router.post("/delete-account", response_model=AccountDeletionResponse)
async def request_account_deletion(
    request: AccountDeletionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Request account deletion.
    
    **Important:**
    - 14-day cooling-off period before deletion
    - You can cancel anytime during this period
    - All data will be permanently deleted
    - This action cannot be undone after the cooling-off period
    
    You must confirm by entering your email address.
    """
    if request.confirm_email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=400,
            detail="Email confirmation does not match your account email"
        )
    
    service = PrivacyService(db)
    deletion_request = await service.request_account_deletion(
        user_id=current_user.id,
        reason=request.reason
    )
    
    return AccountDeletionResponse(
        id=deletion_request.id,
        status=deletion_request.status,
        scheduled_deletion_date=deletion_request.scheduled_deletion_date,
        message=f"Account scheduled for deletion on {deletion_request.scheduled_deletion_date.strftime('%Y-%m-%d')}. You can cancel anytime before this date."
    )


@router.get("/delete-account/status")
async def get_deletion_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if there's a pending account deletion request"""
    service = PrivacyService(db)
    deletion_request = await service.get_deletion_status(current_user.id)
    
    if not deletion_request:
        return {"pending_deletion": False}
    
    return {
        "pending_deletion": True,
        "scheduled_date": deletion_request.scheduled_deletion_date,
        "days_remaining": (deletion_request.scheduled_deletion_date - datetime.now(timezone.utc)).days
    }


@router.post("/delete-account/cancel")
async def cancel_account_deletion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a pending account deletion request"""
    service = PrivacyService(db)
    cancelled = await service.cancel_account_deletion(current_user.id)
    
    if not cancelled:
        raise HTTPException(
            status_code=404,
            detail="No pending deletion request found"
        )
    
    return {"message": "Account deletion cancelled successfully"}


# ==================== Data Summary ====================

@router.get("/data-summary", response_model=UserDataSummary)
async def get_data_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a summary of all data stored for your account.
    Useful for understanding what will be exported or deleted.
    """
    # Calculate account age
    account_age = (datetime.now(timezone.utc) - current_user.created_at).days if current_user.created_at else 0
    
    # TODO: Query actual counts from database
    return UserDataSummary(
        total_quiz_attempts=0,
        total_study_sessions=0,
        total_ai_conversations=0,
        total_documents=0,
        total_notes=0,
        account_age_days=account_age,
        storage_used_mb=0.0
    )
