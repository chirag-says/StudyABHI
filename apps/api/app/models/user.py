"""
User Model
SQLAlchemy ORM model for user authentication and profile
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text
)
import enum

from app.core.database import Base
from app.models.base import TimestampMixin


class UserRole(str, enum.Enum):
    """User role enumeration"""
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class ExamType(str, enum.Enum):
    """Supported exam types"""
    UPSC = "upsc"
    JEE = "jee"
    NEET = "neet"


class User(Base, TimestampMixin):
    """
    User model for authentication and profile management.
    
    Attributes:
        id: Unique identifier (UUID stored as string for SQLite compatibility)
        email: User's email address (unique)
        hashed_password: Bcrypt hashed password
        full_name: User's full name
        phone: Optional phone number
        role: User role (student, teacher, admin)
        exam_type: Primary exam the user is preparing for
        is_active: Whether the user account is active
        is_verified: Whether email is verified
        is_admin: Whether user has admin privileges
        last_login: Last login timestamp
        profile_image: URL to profile image
        bio: User biography/description
    """
    __tablename__ = "users"
    
    # Primary Key - using String for SQLite compatibility
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    
    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    
    # Role & Permissions - stored as string for SQLite compatibility
    role = Column(
        String(20),
        default=UserRole.STUDENT.value,
        nullable=False
    )
    exam_type = Column(
        String(20),
        default=ExamType.UPSC.value,
        nullable=False
    )
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    last_login = Column(DateTime, nullable=True)
    profile_image = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
    
    def update_last_login(self) -> None:
        """Update the last login timestamp"""
        self.last_login = datetime.now(timezone.utc)
