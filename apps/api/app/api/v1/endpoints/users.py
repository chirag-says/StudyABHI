"""
User Management Endpoints
Profile management and user operations
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserUpdate, UserResponse, PasswordChange
from app.schemas.auth import MessageResponse
from app.services.user_service import UserService
from app.services.auth_service import AuthService


router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile"
)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get the authenticated user's profile.
    
    Requires valid access token in Authorization header.
    """
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile"
)
async def update_my_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the authenticated user's profile.
    
    Updatable fields:
    - **full_name**: User's full name
    - **phone**: Phone number
    - **exam_type**: Primary exam type
    - **bio**: User biography
    - **profile_image**: Profile image URL
    
    Requires valid access token in Authorization header.
    """
    user_service = UserService(db)
    
    updated_user = await user_service.update(current_user.id, user_data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.model_validate(updated_user)


@router.post(
    "/me/change-password",
    response_model=MessageResponse,
    summary="Change password"
)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change the authenticated user's password.
    
    - **current_password**: Current account password
    - **new_password**: New password (min 8 chars, strong)
    - **confirm_password**: Confirmation of new password
    
    Requires valid access token in Authorization header.
    """
    auth_service = AuthService(db)
    
    success = await auth_service.change_password(
        current_user,
        password_data.current_password,
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    return MessageResponse(
        message="Password changed successfully",
        success=True
    )


@router.delete(
    "/me",
    response_model=MessageResponse,
    summary="Deactivate account"
)
async def deactivate_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate the authenticated user's account.
    
    This is a soft delete - the account can be reactivated by admin.
    Requires valid access token in Authorization header.
    """
    user_service = UserService(db)
    
    await user_service.deactivate(current_user.id)
    
    return MessageResponse(
        message="Account deactivated successfully",
        success=True
    )
