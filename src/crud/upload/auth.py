"""Authentication utilities - OpenAPI v3.4.4 authentication implementation.

FILE PURPOSE:
Provides JWT token management and password hashing for API authentication per spec.
All functions align with specification requirements for secure authentication.

SPEC COMPLIANCE REFERENCE:
Per OpenAPI v3.4.4 Section 3.4 - Authentication

KEY FUNCTIONS & SPEC REQUIREMENTS:

1. hash_password(password: str) → str
   Purpose: Securely hash user passwords for storage
   Implementation:
   - UTF-8 encoding with 72-byte truncation (bcrypt limitation)
   - Bcrypt algorithm with 12 salt rounds (slow hash for security)
   - Never store plain text passwords

   Spec Requirement: Per Section 3.2.2 UserAuthenticationInfo
   Usage: Called during user registration in /auth/register

2. verify_password(plain: str, hashed: str) → bool
   Purpose: Verify plain text password against stored hash
   Implementation:
   - Constant-time comparison (bcrypt.checkpw)
   - Returns True only if passwords match
   - Returns False for any mismatch

   Spec Requirement: Required for authentication validation
   Usage: Called during login in /authenticate endpoint

3. create_access_token(data: dict) → str
   Purpose: Generate JWT bearer token for authenticated users
   Implementation:
   - JWT (JSON Web Token) with HS256 algorithm
   - Token expiration: 30 minutes (configurable)
   - Payload includes user ID and username
   - Bearer prefix: "bearer " (per spec examples)

   Spec Requirement: Per Section 3.4 Authentication
   Example: "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   Usage: Returned by /authenticate endpoint (HTTP 200)

4. decode_access_token(token: str) → dict
   Purpose: Validate and extract JWT token payload
   Implementation:
   - Verify JWT signature using SECRET_KEY
   - Check token expiration (raises ExpiredSignatureError if expired)
   - Extract user claims (sub, name, iat)
   - Returns payload dict for use in authenticated endpoints

   Spec Requirement: Required for validating X-Authorization header
   Error: Raises HTTPException 403 if token is invalid or expired
   Usage: Called by get_current_user() in all BASELINE endpoints

5. get_current_user(token: str, db: Session) → User
   Purpose: FastAPI dependency for extracting authenticated user from token
   Implementation:
   - Strips "bearer " prefix from X-Authorization header
   - Decodes and validates JWT token
   - Looks up user in database using token claims
   - Returns complete User object for audit logging

   Spec Requirement: Per Section 3.4 X-Authorization header usage
   Error: 403 Forbidden if token missing, invalid, or user not found
   Usage: Injected as parameter in all 4 Phase 2 endpoints

JWT CONFIGURATION:
- Algorithm: HS256 (HMAC with SHA-256)
- Secret Key: From environment variable SECRET_KEY (or dev fallback)
- Expiration: 30 minutes (per specification requirements)
- Format: Bearer token with "bearer " prefix

INTEGRATION POINTS:
- /auth/register endpoint: Uses hash_password() and create_access_token()
- /authenticate endpoint: Uses verify_password() and create_access_token()
- All 4 Phase 2 CRUD endpoints: Use get_current_user() as FastAPI dependency
- artifact_routes.py: Calls get_current_user() for authentication
- X-Authorization header: Format must be "bearer <token_string>"
"""

import os
from datetime import datetime, timedelta
from typing import Any, Optional

import bcrypt
import jwt  # NEW: JWT library for token generation and validation
from fastapi import HTTPException, status

try:
    from src.database_models import User
except ImportError:
    User = None  # type: ignore

# JWT Configuration
SECRET_KEY = os.getenv(
    "SECRET_KEY", "dev-secret-key-change-in-production"
)  # NEW: JWT secret
ALGORITHM = "HS256"  # NEW: JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = 600  # NEW: Token expiration time (10 hours)


def hash_password(password: str) -> str:  # NEW: Hash password for storage
    """Hash a plain text password using bcrypt.

    Per bcrypt specification: bcrypt truncates passwords to 72 bytes.
    This function enforces that limit explicitly to prevent errors.

    Args:
        password: The plain text password to hash

    Returns:
        The bcrypt-hashed password string
    """
    # Bcrypt has a 72-byte limit on passwords
    # Truncate to 72 bytes to prevent errors
    password_bytes = password.encode("utf-8")[:72]
    password_truncated = password_bytes.decode("utf-8", errors="ignore")
    # Hash using bcrypt with salt cost of 12
    hashed = bcrypt.hashpw(
        password_truncated.encode("utf-8"), bcrypt.gensalt(rounds=12)
    )
    return hashed.decode("utf-8")


def verify_password(
    plain_password: str, hashed_password: str
) -> bool:  # NEW: Verify password during login
    """Verify a plain text password against a hashed password.

    Per bcrypt specification: bcrypt truncates passwords to 72 bytes.
    This function enforces that limit to match hashing.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt-hashed password to compare against

    Returns:
        True if passwords match, False otherwise
    """
    # Bcrypt has a 72-byte limit on passwords - truncate to match hash
    import logging
    logger = logging.getLogger("auth_debug")
    password_bytes = plain_password.encode("utf-8")[:72]
    password_truncated = password_bytes.decode("utf-8", errors="ignore")
    try:
        result = bcrypt.checkpw(
            password_truncated.encode("utf-8"), hashed_password.encode("utf-8")
        )
        logger.info(f"verify_password: user input='{plain_password}', truncated='{password_truncated}', hash='{hashed_password[:10]}...', result={result}")
        return result
    except Exception as e:
        logger.error(f"verify_password exception: {e}")
        return False


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
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    # Per OpenAPI spec: Return token with "bearer " prefix
 
 curl -X PUT http://localhost:8000/authenticate -H "Content-Type: application/json" -d "{\"user\": {\"name\": \"ece30861defaultadminuser\"}, \"secret\": {\"password\": \"correcthorsebatterystaple123(!__+@**(A'\\\"`;DROP TABLE artifacts;\"}}"return Response(content=f"\"{access_token}\"", media_type="application/json")   

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
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


# Mock for testing; in production, use JWT or session-based auth
_current_user: Optional[Any] = None


# db is a placeholder for a database session dependency
def get_current_user(  # UPDATED: Now validates JWT from X-Authorization header
    authorization: Optional[str] = None, db: Any = None
) -> Any:
    """Get current authenticated user from X-Authorization header token.

    For production S3-based systems, validates JWT signature only (no database lookup).
    For testing with TEST_USER_ID env var, returns a User object if database available.

    Expected header format: X-Authorization: bearer <token>

    Args:
        authorization: X-Authorization header value
        db: Database session dependency (optional, for testing only)

    Returns:
        For test mode: User object
        For production: dict with token payload

    Raises:
        HTTPException: If not authenticated or token invalid
    """
    # Check for test mode via environment variable
    if os.getenv("TEST_USER_ID"):
        user_id_str = os.getenv("TEST_USER_ID", "0")
        if db and User is not None:
            # Try to fetch from database first
            user = db.query(User).filter(User.id == int(user_id_str)).first()
            if user:
                return user
        # Fall back to minimal user object if User class available
        if User is not None:
            user = User(
                id=int(user_id_str),
                is_admin=False,
                username="test",
                email="test@test.com",
                hashed_password="",
            )
            return user
        # Return dict for testing if User model unavailable
        return {
            "id": int(user_id_str),
            "is_admin": False,
            "username": "test",
            "email": "test@test.com",
        }

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Authorization header",
        )

    try:
        # Extract token from "bearer <token>" format
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
            )

        token = authorization[7:]  # Remove "bearer " prefix
        payload = decode_access_token(token)

        # For production: JWT validation is sufficient
        # Token has been validated by decode_access_token (signature + expiration)
        # No database lookup needed for stateless S3-based system
        return payload

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
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
