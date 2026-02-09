"""
Privacy Service
Business logic for privacy controls, data export, and account deletion
"""
import json
import os
import zipfile
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.privacy import UserPrivacySettings, DataExportRequest, AccountDeletionRequest
from app.models.user import User


class PrivacyService:
    """Service for handling user privacy operations"""
    
    DELETION_COOLING_OFF_DAYS = 14  # GDPR recommended cooling-off period
    EXPORT_EXPIRY_HOURS = 48
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== Privacy Settings ====================
    
    async def get_privacy_settings(self, user_id: str) -> Optional[UserPrivacySettings]:
        """Get user's privacy settings, create default if not exists"""
        result = await self.db.execute(
            select(UserPrivacySettings).where(UserPrivacySettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = await self.create_default_settings(user_id)
        
        return settings
    
    async def create_default_settings(self, user_id: str) -> UserPrivacySettings:
        """Create default privacy settings for new user"""
        settings = UserPrivacySettings(
            user_id=user_id,
            ai_features_enabled=True,
            webcam_enabled=False,
            analytics_enabled=True,
        )
        self.db.add(settings)
        await self.db.commit()
        await self.db.refresh(settings)
        return settings
    
    async def update_privacy_settings(
        self, 
        user_id: str, 
        updates: Dict[str, Any]
    ) -> UserPrivacySettings:
        """Update user's privacy settings"""
        settings = await self.get_privacy_settings(user_id)
        now = datetime.now(timezone.utc)
        
        for key, value in updates.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)
                
                # Track consent timestamps
                if key.startswith("ai_") and value:
                    settings.ai_consent_date = now
                elif key.startswith("webcam_") or key.startswith("attention_") or key.startswith("session_"):
                    if value:
                        settings.webcam_consent_date = now
                elif key.startswith("analytics_"):
                    if value:
                        settings.analytics_consent_date = now
        
        await self.db.commit()
        await self.db.refresh(settings)
        return settings
    
    # ==================== Data Export ====================
    
    async def request_data_export(
        self, 
        user_id: str,
        export_format: str = "json",
        include_quiz_history: bool = True,
        include_study_sessions: bool = True,
        include_ai_conversations: bool = True,
        include_documents: bool = True
    ) -> DataExportRequest:
        """Create a data export request"""
        export_request = DataExportRequest(
            user_id=user_id,
            status="pending",
            export_format=export_format,
            include_quiz_history=include_quiz_history,
            include_study_sessions=include_study_sessions,
            include_ai_conversations=include_ai_conversations,
            include_documents=include_documents,
        )
        self.db.add(export_request)
        await self.db.commit()
        await self.db.refresh(export_request)
        return export_request
    
    async def process_data_export(self, export_id: str) -> Dict[str, Any]:
        """
        Process a data export request.
        This should be called by a background worker.
        """
        result = await self.db.execute(
            select(DataExportRequest).where(DataExportRequest.id == export_id)
        )
        export_request = result.scalar_one_or_none()
        
        if not export_request:
            raise ValueError("Export request not found")
        
        # Update status
        export_request.status = "processing"
        await self.db.commit()
        
        try:
            # Collect user data
            user_data = await self._collect_user_data(
                export_request.user_id,
                include_quiz_history=export_request.include_quiz_history,
                include_study_sessions=export_request.include_study_sessions,
                include_ai_conversations=export_request.include_ai_conversations,
                include_documents=export_request.include_documents
            )
            
            # Generate export file
            file_path = await self._generate_export_file(
                export_request.id,
                export_request.user_id,
                user_data,
                export_request.export_format
            )
            
            # Update request with file info
            export_request.status = "completed"
            export_request.file_path = file_path
            export_request.completed_at = datetime.now(timezone.utc)
            export_request.expires_at = datetime.now(timezone.utc) + timedelta(hours=self.EXPORT_EXPIRY_HOURS)
            export_request.download_url = f"/api/v1/privacy/exports/{export_request.id}/download"
            
            await self.db.commit()
            
            return {"status": "completed", "download_url": export_request.download_url}
            
        except Exception as e:
            export_request.status = "failed"
            await self.db.commit()
            raise e
    
    async def _collect_user_data(
        self,
        user_id: str,
        include_quiz_history: bool,
        include_study_sessions: bool,
        include_ai_conversations: bool,
        include_documents: bool
    ) -> Dict[str, Any]:
        """Collect all user data for export"""
        data = {"user_id": user_id, "exported_at": datetime.now(timezone.utc).isoformat()}
        
        # Get user profile
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            data["profile"] = {
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "role": user.role,
                "exam_type": user.exam_type,
                "bio": user.bio,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        
        # Get privacy settings
        settings = await self.get_privacy_settings(user_id)
        if settings:
            data["privacy_settings"] = {
                "ai_features_enabled": settings.ai_features_enabled,
                "webcam_enabled": settings.webcam_enabled,
                "analytics_enabled": settings.analytics_enabled,
            }
        
        # TODO: Add actual data collection from other tables
        if include_quiz_history:
            data["quiz_history"] = []  # Placeholder
        if include_study_sessions:
            data["study_sessions"] = []  # Placeholder
        if include_ai_conversations:
            data["ai_conversations"] = []  # Placeholder
        if include_documents:
            data["documents"] = []  # Placeholder
        
        return data
    
    async def _generate_export_file(
        self,
        export_id: str,
        user_id: str,
        data: Dict[str, Any],
        export_format: str
    ) -> str:
        """Generate the export file"""
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)
        
        if export_format == "json":
            file_path = f"{export_dir}/{export_id}.json"
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        elif export_format == "zip":
            file_path = f"{export_dir}/{export_id}.zip"
            json_path = f"{export_dir}/{export_id}_data.json"
            with open(json_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            with zipfile.ZipFile(file_path, "w") as zf:
                zf.write(json_path, "user_data.json")
            os.remove(json_path)
        else:
            file_path = f"{export_dir}/{export_id}.json"
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        
        return file_path
    
    async def get_export_status(self, export_id: str, user_id: str) -> Optional[DataExportRequest]:
        """Get export request status"""
        result = await self.db.execute(
            select(DataExportRequest).where(
                DataExportRequest.id == export_id,
                DataExportRequest.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
    
    # ==================== Account Deletion ====================
    
    async def request_account_deletion(
        self, 
        user_id: str, 
        reason: Optional[str] = None
    ) -> AccountDeletionRequest:
        """Request account deletion with cooling-off period"""
        # Cancel any existing pending requests
        await self.db.execute(
            delete(AccountDeletionRequest).where(
                AccountDeletionRequest.user_id == user_id,
                AccountDeletionRequest.status == "pending"
            )
        )
        
        deletion_request = AccountDeletionRequest(
            user_id=user_id,
            reason=reason,
            status="pending",
            scheduled_deletion_date=datetime.now(timezone.utc) + timedelta(days=self.DELETION_COOLING_OFF_DAYS)
        )
        self.db.add(deletion_request)
        await self.db.commit()
        await self.db.refresh(deletion_request)
        return deletion_request
    
    async def cancel_account_deletion(self, user_id: str) -> bool:
        """Cancel pending account deletion"""
        result = await self.db.execute(
            select(AccountDeletionRequest).where(
                AccountDeletionRequest.user_id == user_id,
                AccountDeletionRequest.status == "pending"
            )
        )
        deletion_request = result.scalar_one_or_none()
        
        if deletion_request:
            deletion_request.status = "cancelled"
            deletion_request.cancelled_at = datetime.now(timezone.utc)
            await self.db.commit()
            return True
        return False
    
    async def process_account_deletion(self, user_id: str) -> bool:
        """
        Process account deletion after cooling-off period.
        Should be called by a scheduled job.
        """
        result = await self.db.execute(
            select(AccountDeletionRequest).where(
                AccountDeletionRequest.user_id == user_id,
                AccountDeletionRequest.status == "pending"
            )
        )
        deletion_request = result.scalar_one_or_none()
        
        if not deletion_request:
            return False
        
        if datetime.now(timezone.utc) < deletion_request.scheduled_deletion_date:
            return False  # Cooling-off period not over
        
        # Delete user data (cascade should handle related records)
        await self.db.execute(delete(User).where(User.id == user_id))
        
        deletion_request.status = "completed"
        deletion_request.completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        return True
    
    async def get_deletion_status(self, user_id: str) -> Optional[AccountDeletionRequest]:
        """Get pending deletion request status"""
        result = await self.db.execute(
            select(AccountDeletionRequest).where(
                AccountDeletionRequest.user_id == user_id,
                AccountDeletionRequest.status == "pending"
            )
        )
        return result.scalar_one_or_none()
