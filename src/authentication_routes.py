"""Authentication endpoints - OpenAPI v3.4.7 spec compliance.

FILE PURPOSE:
Implements user registration and authentication endpoints per OpenAPI spec.
Provides JWT token-based authentication for API access.

SPEC COMPLIANCE:
Per OpenAPI v3.4.7:
- PUT /authenticate: Create access token (NON-BASELINE)
- POST /register: User registration (custom addition for user creation)

ENDPOINTS IMPLEMENTED:
1. PUT /authenticate - Authenticate user and return JWT token
2. POST /register - Register new user account
"""

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.crud.upload.artifacts import AuthenticationRequest, AuthenticationToken
from src.crud.upload.auth import create_access_token, hash_password, verify_password
from src.database import get_db
from src.database_models import User as DBUser

router = APIRouter(tags=["authentication"])


@router.post("/register", response_model=AuthenticationToken)
async def register_user(
    request: AuthenticationRequest,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Register a new user account.

    Creates a new user with hashed password and returns JWT authentication token.

    Args:
        request: AuthenticationRequest with user info and password
        db: Database session

    Returns:
        AuthenticationToken: JWT bearer token for authenticated access

    Raises:
        HTTPException:
            400: Missing fields or improperly formed request
            409: User already exists
    """
    # Validate request
    if not request.user or not request.secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is missing field(s) in the AuthenticationRequest or it is formed improperly.",
        )

    if not request.user.name or not request.secret.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is missing field(s) in the AuthenticationRequest or it is formed improperly.",
        )

    # Check if user already exists
    existing_user = (
        db.query(DBUser).filter(DBUser.username == request.user.name).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User {request.user.name} already exists.",
        )

    # Hash password
    hashed_password = hash_password(request.secret.password)

    # Create new user
    new_user = DBUser(
        username=request.user.name,
        email=request.user.name,  # Use name as email for now
        hashed_password=hashed_password,
        is_admin=request.user.is_admin,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate JWT token
    token_data = {
        "sub": str(new_user.id),
        "name": new_user.username,
        "is_admin": new_user.is_admin,
    }
    access_token = create_access_token(token_data)

    return AuthenticationToken(token=access_token)


@router.put("/authenticate", response_model=AuthenticationToken)
async def authenticate_user(
    request: AuthenticationRequest,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Authenticate user and return access token (NON-BASELINE per spec).

    Per OpenAPI v3.4.7 spec PUT /authenticate endpoint:
    - Takes AuthenticationRequest with user credentials
    - Returns AuthenticationToken with JWT bearer token
    - Token should be provided in X-Authorization header for other endpoints

    Args:
        request: AuthenticationRequest with username and password
        db: Database session

    Returns:
        AuthenticationToken: JWT bearer token in format "bearer <jwt>"

    Raises:
        HTTPException:
            400: Missing fields or improperly formed request
            401: Invalid user or password
            501: Authentication not supported (if not implemented)
    """
    # Validate request
    if not request.user or not request.secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is missing field(s) in the AuthenticationRequest or it is formed improperly.",
        )

    if not request.user.name or not request.secret.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is missing field(s) in the AuthenticationRequest or it is formed improperly.",
        )

    # Find user in database
    user = db.query(DBUser).filter(DBUser.username == request.user.name).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The user or password is invalid.",
        )

    # Verify password
    if not verify_password(request.secret.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The user or password is invalid.",
        )

    # Generate JWT token
    token_data = {
        "sub": str(user.id),
        "name": user.username,
        "is_admin": user.is_admin,
    }
    access_token = create_access_token(token_data)

    return AuthenticationToken(token=access_token)
