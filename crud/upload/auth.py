"""Authentication and authorization utilities for model upload endpoints.

This module provides functions to manage user authentication for API requests.
It handles JWT token generation, validation, and user authentication.

Key features:
- JWT token generation and validation for stateless authentication
- Extracts and validates user credentials from X-Authorization header
- Provides dependency injection for FastAPI route handlers
- Raises 401 Unauthorized if credentials are missing or invalid
"""

import os
from datetime import datetime, timedelta
from typing import Any, Optional

import jwt  # NEW: JWT library for token generation and validation
from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext  # NEW: Password hashing

from src.models import User

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")  # NEW: JWT secret
ALGORITHM = "HS256"  # NEW: JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # NEW: Token expiration time

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # NEW: Password hashing


def hash_password(password: str) -> str:  # NEW: Hash password for storage
    """Hash a plain text password using bcrypt."""
    return pwd_context.hash(password)  # type: ignore[no-any-return]


def verify_password(plain_password: str, hashed_password: str) -> bool:  # NEW: Verify password during login
    """Verify a plain text password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)  # type: ignore[no-any-return]


def create_access_token(
    data: dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:  # NEW: JWT token generation
    """Create a JWT access token.

    Args:
        data: Dictionary containing claims to encode
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:  # NEW: JWT token validation
    """Decode and validate a JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # type: ignore[no-any-return]
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# Mock for testing; in production, use JWT or session-based auth
_current_user: Optional[Any] = None


# db is a placeholder for a database session dependency
def get_current_user(  # UPDATED: Now validates JWT from X-Authorization header
    authorization: Optional[str] = None,
    db: Any = None
) -> User:
    """Get current authenticated user from X-Authorization header token.
    
    Expected header format: X-Authorization: bearer <token>
    
    Args:
        authorization: X-Authorization header value
        db: Database session dependency
        
    Returns:
        Authenticated User object
        
    Raises:
        HTTPException: If not authenticated or token invalid
    """
    # Check for test mode via environment variable
    if os.getenv("TEST_USER_ID"):
        user_id_str = os.getenv("TEST_USER_ID", "0")
        user = User(id=int(user_id_str), is_admin=False, username="test", email="test@test.com", hashed_password="")
        return user

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Authorization header"
        )

    try:
        # Extract token from "bearer <token>" format
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        token = authorization[7:]  # Remove "bearer " prefix
        payload = decode_access_token(token)
        token_user_id: Optional[str] = payload.get("sub")
        
        if token_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # In a real implementation, fetch from database
        # For now, create a minimal User object
        user = User(
            id=int(token_user_id),
            is_admin=bool(payload.get("is_admin", False)),
            username="",
            email="",
            hashed_password=""
        )
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )


def set_test_user(user: Any) -> None:
    """Set current user for testing"""
    global _current_user
    if isinstance(user, User):
        # Store just the ID to avoid session issues
        _current_user = user.id
    else:
        _current_user = user


def clear_test_user() -> None:
    """Clear current user"""
    global _current_user
    _current_user = None
