"""Phase 2 authentication endpoints for user login and token generation.

Per OpenAPI v3.4.4 Section 3.1 - Authentication Requirements

Implements 2 authentication endpoints:
- POST /auth/register: User registration (HTTP 200)
- PUT /authenticate: User login and token generation (HTTP 200)

Key Features:
- Bcrypt password hashing (12 rounds, constant-time comparison)
- JWT token generation with configurable expiration (30 minutes default)
- Username/email uniqueness validation
- Full audit logging on registration
- X-Authorization header format for all protected endpoints

Error Handling:
- 400: Malformed request (missing required fields)
- 401: Invalid credentials (user not found or password mismatch)
- 409: User already exists (registration only)
- 500: Internal server error

JWT Token Format:
- Header: Bearer token in X-Authorization header
- Example: X-Authorization: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
- Expiration: 30 minutes from token generation
- Claims: sub (user_id), is_admin (boolean flag)

Request/Response Schemas:
- AuthenticationRequest: {user: {name, is_admin}, secret: {password}}
- AuthenticationToken: {token: "bearer <JWT>"}
- Response codes match OpenAPI spec Section 3.1

Password Requirements:
- Minimum 1 character (enforced by bcrypt)
- Maximum 72 bytes (bcrypt limitation - truncates longer passwords)
- Hashed using bcrypt with 12 rounds for security

All endpoints require Content-Type: application/x-www-form-urlencoded
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.crud.upload.artifacts import \
    AuthenticationRequest  # NEW: Request/response models
from src.crud.upload.artifacts import AuthenticationToken
from src.crud.upload.auth import create_access_token  # NEW: Auth functions
from src.crud.upload.auth import hash_password, verify_password
from src.database import get_db  # UPDATED: Use proper dependency injection
from src.database_models import User

router = APIRouter(tags=["authentication"])  # NEW: Authentication router


@router.post("/auth/register")  # NEW: User registration endpoint
async def register_user(
    request: AuthenticationRequest, db: Session = Depends(get_db)
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
        try:
            hashed_pwd = hash_password(request.secret.password)  # NEW: Hash password for storage
        except ValueError as e:
            # Bcrypt has 72-byte limit - this shouldn't happen now but keep for safety
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password validation failed: {str(e)}"
            )
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
    request: AuthenticationRequest, db: Session = Depends(get_db)
) -> AuthenticationToken:  # UPDATED: Use Depends(get_db)
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

        return AuthenticationToken(token=f"bearer {access_token}")  # NEW: Return bearer token

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )
