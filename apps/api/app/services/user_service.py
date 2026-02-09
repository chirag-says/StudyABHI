"""
User Service
Business logic for user management
"""
from typing import Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import hash_password


class UserService:
    """Service class for user-related operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User's UUID
            
        Returns:
            User instance or None
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: User's email address
            
        Returns:
            User instance or None
        """
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
    
    async def create(self, user_data: UserCreate) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created User instance
        """
        # Hash the password
        hashed_password = hash_password(user_data.password)
        
        # Create user instance
        user = User(
            email=user_data.email.lower(),
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            phone=user_data.phone,
            exam_type=user_data.exam_type.value if hasattr(user_data.exam_type, 'value') else user_data.exam_type
        )
        
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        
        return user
    
    async def update(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """
        Update user profile.
        
        Args:
            user_id: User's UUID
            user_data: Update data
            
        Returns:
            Updated User instance or None
        """
        # Get existing user
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        # Update fields
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await self.db.flush()
        await self.db.refresh(user)
        
        return user
    
    async def email_exists(self, email: str) -> bool:
        """
        Check if email is already registered.
        
        Args:
            email: Email to check
            
        Returns:
            True if email exists, False otherwise
        """
        user = await self.get_by_email(email)
        return user is not None
    
    async def deactivate(self, user_id: str) -> bool:
        """
        Deactivate a user account.
        
        Args:
            user_id: User's UUID
            
        Returns:
            True if successful, False otherwise
        """
        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False)
        )
        return result.rowcount > 0
    
    async def verify_email(self, user_id: str) -> bool:
        """
        Mark user's email as verified.
        
        Args:
            user_id: User's UUID
            
        Returns:
            True if successful, False otherwise
        """
        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_verified=True)
        )
        return result.rowcount > 0
