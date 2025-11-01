# auth.py

from fastapi import Depends, HTTPException, status

from models import User

# Mock for testing; in production, use JWT or session-based auth
_current_user = None


# db is a placeholder for a database session dependency
def get_current_user(db=None) -> User:
    """Get current authenticated user (mock for now)"""
    if _current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    # If _current_user is an int (just the ID), create a minimal User object
    if isinstance(_current_user, int):
        user = User(id=_current_user)
        user.is_admin = False
        return user
    return _current_user


def set_test_user(user):
    """Set current user for testing"""
    global _current_user
    if isinstance(user, User):
        # Store just the ID to avoid session issues
        _current_user = user.id
    else:
        _current_user = user


def clear_test_user():
    """Clear current user"""
    global _current_user
    _current_user = None
