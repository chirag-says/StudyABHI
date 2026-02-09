"""
Security Utilities
JWT token creation/verification and password hashing
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from jose import jwt, JWTError
import bcrypt
from pydantic import BaseModel

from app.core.config import settings


class TokenData(BaseModel):
    """Token payload data model"""
    sub: str  # Subject (user_id)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    type: str  # Token type: "access" or "refresh"


class TokenPayload(BaseModel):
    """Decoded token payload"""
    user_id: str
    token_type: str


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    # bcrypt requires bytes
    pwd_bytes = password.encode('utf-8')
    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    # Return as string for database storage
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        pwd_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: Token subject (usually user_id)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access"
    }
    
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        subject: Token subject (usually user_id)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "refresh"
    }
    
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Optional[TokenPayload]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Validate token type
        if payload.get("type") != token_type:
            return None
        
        user_id = payload.get("sub")
        if user_id is None:
            return None
            
        return TokenPayload(user_id=user_id, token_type=token_type)
        
    except JWTError:
        return None


def create_token_pair(subject: Union[str, int]) -> dict:
    """
    Create both access and refresh tokens.
    
    Args:
        subject: Token subject (usually user_id)
        
    Returns:
        Dictionary with access_token and refresh_token
    """
    return {
        "access_token": create_access_token(subject),
        "refresh_token": create_refresh_token(subject),
        "token_type": "Bearer"
    }
