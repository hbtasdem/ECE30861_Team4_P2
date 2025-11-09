"""Authentication endpoints for user registration and login.

This module implements user registration and authentication per OpenAPI spec:
- POST /auth/register: Register new user
- PUT /authenticate: Login and get JWT token

Implements AuthenticationToken, AuthenticationRequest, and User schemas from spec.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from crud.upload.auth import (create_access_token,  # NEW: Auth functions
                              hash_password, verify_password)
from crud.upload.models import (AuthRequest,  # NEW: Request/response models
                                AuthResponse, UserRegistrationRequest)
from src.database import get_db  # UPDATED: Use proper dependency injection
from src.models import User

router = APIRouter(prefix="/auth", tags=["authentication"])  # NEW: Authentication router


@router.post("/register")  # NEW: User registration endpoint
async def register_user(
    request: UserRegistrationRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:  # UPDATED: Use Depends(get_db)
    """Register a new user.

    Creates a new user account with the provided credentials.
    Per OpenAPI spec: AuthenticationRequest schema.

    Args:
        request: User registration request with username, email, password
        db: Database session (dependency injection)
        
    Returns:
        dict with success message and authentication token
        
    Raises:
        HTTPException: If user already exists or registration fails
    """
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == request.user.name) | (User.email == request.user.name)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,  # NEW: 409 Conflict per spec
                detail="User already exists"
            )
        
        # Create new user with hashed password
        hashed_pwd = hash_password(request.secret.password)  # NEW: Hash password for storage
        new_user = User(
            username=request.user.name,
            email=request.user.name,  # Use email as username for now
            hashed_password=hashed_pwd,  # NEW: Store hashed password
            is_admin=request.user.is_admin or False
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Generate access token
        access_token = create_access_token(  # NEW: Generate JWT token
            data={"sub": str(new_user.id), "is_admin": new_user.is_admin}
        )
        
        return {  # NEW: Return token in bearer format per spec
            "token": f"bearer {access_token}",
            "user_id": new_user.id,
            "username": new_user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )


@router.put("/authenticate")  # NEW: User authentication endpoint (login)
async def authenticate_user(
    request: AuthRequest, db: Session = Depends(get_db)
) -> AuthResponse:  # UPDATED: Use Depends(get_db)
    """Authenticate user and return JWT token.

    Per OpenAPI spec: /authenticate endpoint
    Validates credentials and returns bearer token.
    
    Args:
        request: Authentication request with username and password
        db: Database session (dependency injection)
        
    Returns:
        AuthResponse with bearer token
        
    Raises:
        HTTPException: 401 if credentials invalid, 501 if auth not supported
    """
    
    try:
        # Find user by username or email
        user = db.query(User).filter(
            (User.username == request.user.name) | (User.email == request.user.name)
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,  # NEW: Per spec
                detail="Invalid username or password"
            )
        
        # Verify password
        if not verify_password(request.secret.password, str(user.hashed_password)):  # NEW: Cast to str and verify
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Generate access token
        access_token = create_access_token(  # NEW: Generate JWT token
            data={"sub": str(user.id), "is_admin": bool(user.is_admin)}  # NEW: Cast to bool
        )
        
        return AuthResponse(token=f"bearer {access_token}")  # NEW: Return bearer token
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )
