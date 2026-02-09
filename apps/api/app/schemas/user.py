"""
User Schemas
Pydantic models for user-related request/response validation
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

from app.models.user import UserRole, ExamType


class UserBase(BaseModel):
    """Base user schema with shared fields"""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    exam_type: ExamType = ExamType.UPSC


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate password strength:
        - At least 8 characters
        - Contains uppercase and lowercase letters
        - Contains at least one number
        - Contains at least one special character
        """
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate that passwords match"""
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format"""
        if v is None:
            return v
        # Remove spaces and dashes
        cleaned = re.sub(r'[\s\-]', '', v)
        if not re.match(r'^\+?[\d]{10,15}$', cleaned):
            raise ValueError('Invalid phone number format')
        return cleaned


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    exam_type: Optional[ExamType] = None
    bio: Optional[str] = Field(None, max_length=500)
    profile_image: Optional[str] = Field(None, max_length=500)
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Schema for user response (public data)"""
    id: str
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str
    exam_type: str
    is_active: bool
    is_verified: bool
    profile_image: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """Schema for user with hashed password (internal use)"""
    hashed_password: str
    is_admin: bool
    
    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    """Schema for password change request"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate that passwords match"""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v
