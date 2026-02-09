"""
Authentication Endpoints
Login, Register, Token Refresh, Logout
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    MessageResponse
)
from app.services.auth_service import AuthService


router = APIRouter()


@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user"
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    
    - **email**: Valid email address (must be unique)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, number, special char)
    - **full_name**: User's full name
    - **phone**: Optional phone number
    - **exam_type**: Primary exam (upsc, jee, neet)
    
    Returns user data and JWT tokens.
    """
    auth_service = AuthService(db)
    
    try:
        user, tokens = await auth_service.register(user_data)
    except ValueError as e:
        print(f"REGISTER ERROR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return {
        "user": UserResponse.model_validate(user),
        "tokens": tokens
    }


@router.post(
    "/login",
    response_model=dict,
    summary="Login user"
)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and get access tokens.
    
    - **email**: Registered email address
    - **password**: Account password
    
    Returns user data and JWT tokens (access + refresh).
    """
    auth_service = AuthService(db)
    
    result = await auth_service.login(login_data.email, login_data.password)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user, tokens = result
    
    return {
        "user": UserResponse.model_validate(user),
        "tokens": tokens
    }


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token"
)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get new access token using refresh token.
    
    - **refresh_token**: Valid refresh token from login/register
    
    Returns new access and refresh tokens.
    """
    auth_service = AuthService(db)
    
    tokens = await auth_service.refresh_tokens(token_data.refresh_token)
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return tokens


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user"
)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout current user.
    
    Requires valid access token in Authorization header.
    Future: Will invalidate tokens via Redis blacklist.
    """
    auth_service = AuthService(db)
    await auth_service.logout(current_user)
    
    return MessageResponse(
        message="Successfully logged out",
        success=True
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user"
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get currently authenticated user's profile.
    
    Requires valid access token in Authorization header.
    """
    return UserResponse.model_validate(current_user)
