"""
Authentication Service
Business logic for authentication operations
"""
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate
from app.schemas.auth import TokenResponse
from app.services.user_service import UserService
from app.core.security import (
    verify_password,
    create_token_pair,
    verify_token,
    hash_password
)


class AuthService:
    """Service class for authentication operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_service = UserService(db)
    
    async def register(self, user_data: UserCreate) -> Tuple[User, TokenResponse]:
        """
        Register a new user and return tokens.
        
        Args:
            user_data: User registration data
            
        Returns:
            Tuple of (User, TokenResponse)
            
        Raises:
            ValueError: If email already exists
        """
        # Check if email exists
        if await self.user_service.email_exists(user_data.email):
            raise ValueError("Email already registered")
        
        # Create user
        user = await self.user_service.create(user_data)
        
        # Generate tokens
        tokens = create_token_pair(str(user.id))
        token_response = TokenResponse(**tokens)
        
        return user, token_response
    
    async def login(self, email: str, password: str) -> Optional[Tuple[User, TokenResponse]]:
        """
        Authenticate user and return tokens.
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            Tuple of (User, TokenResponse) or None if authentication fails
        """
        # Get user by email
        user = await self.user_service.get_by_email(email)
        
        if not user:
            return None
        
        # Verify password
        if not verify_password(password, user.hashed_password):
            return None
        
        # Check if user is active
        if not user.is_active:
            return None
        
        # Update last login
        user.update_last_login()
        await self.db.flush()
        
        # Generate tokens
        tokens = create_token_pair(str(user.id))
        token_response = TokenResponse(**tokens)
        
        return user, token_response
    
    async def refresh_tokens(self, refresh_token: str) -> Optional[TokenResponse]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New TokenResponse or None if refresh token is invalid
        """
        # Verify refresh token
        payload = verify_token(refresh_token, token_type="refresh")
        
        if not payload:
            return None
        
        # Check if user still exists and is active
        user = await self.user_service.get_by_id(payload.user_id)
        
        if not user or not user.is_active:
            return None
        
        # Generate new tokens
        tokens = create_token_pair(str(user.id))
        return TokenResponse(**tokens)
    
    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user's password.
        
        Args:
            user: User instance
            current_password: Current password
            new_password: New password
            
        Returns:
            True if successful, False otherwise
        """
        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            return False
        
        # Hash and update new password
        user.hashed_password = hash_password(new_password)
        await self.db.flush()
        
        return True
    
    async def logout(self, user: User) -> bool:
        """
        Logout user (for future token blacklisting).
        
        Args:
            user: User instance
            
        Returns:
            True (always succeeds for now)
        """
        # TODO: Implement token blacklisting with Redis
        # For now, just return True
        return True
