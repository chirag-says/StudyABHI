"""
Authentication Schemas
Pydantic models for auth-related request/response validation
"""
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request"""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True
