import base64
from typing import Optional, List, Union, Dict, Any
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from .database import get_db, User
from .auth import verify_password
from .config import config


def verify_dvc_auth(authorization: Optional[str], x_dvc_token: Optional[str],
                    db: Session) -> Optional[User]:
    """Verify DVC remote authentication using database users"""
    # Get auth config from unified structure
    dvc_config = config.dvc_config
    remote_server_config = dvc_config.get('remote_server', {})
    auth_config = remote_server_config.get('auth', {})

    if not auth_config.get('enabled', True):
        # If auth disabled, return a dummy user or allow anonymous
        return None

    auth_method = auth_config.get('method', 'database')

    if auth_method == 'database':
        return verify_database_auth(authorization, db, auth_config)
    elif auth_method == 'basic':
        verify_basic_auth(authorization, auth_config)
        return None  # Basic auth doesn't return a specific user
    elif auth_method == 'custom':
        verify_custom_auth(x_dvc_token, auth_config)
        return None  # Custom auth doesn't return a specific user
    elif auth_method == 'none':
        return None
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid authentication method")


def verify_database_auth(authorization: Optional[str], db: Session,
                         auth_config: Dict[str, Any]) -> User:
    """Verify authentication using database users"""
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Authorization header required")

    try:
        scheme, credentials = authorization.split()
        if scheme.lower() != 'basic':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Only Basic authentication supported for database auth")

        decoded = base64.b64decode(credentials).decode('utf-8')
        email, password = decoded.split(':', 1)

        # Find user in database
        user = db.query(User).filter(User.email == email).first()

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid credentials")

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid credentials")

        # Check if user is allowed to access DVC remote
        if not is_user_allowed_for_dvc(user, auth_config):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not authorized for DVC remote access")

        return user

    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid authorization header format")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Authentication failed")


def is_user_allowed_for_dvc(user: User, auth_config: Dict[str, Any]) -> bool:
    """Check if user is allowed to access DVC remote"""
    database_config = auth_config.get('database_auth', {})

    # Check if admin access is required
    if database_config.get('require_admin', False):
        return bool(user.is_admin)

    # Check if user is in allowed users list
    allowed_users = database_config.get('allowed_users', [])
    if allowed_users:
        return user.email in allowed_users

    # If no restrictions, all registered users can access
    return True


def verify_basic_auth(authorization: Optional[str],
                      auth_config: Dict[str, Any]) -> bool:
    """Verify Basic Authentication (for backward compatibility)"""
    if not authorization:
        return False

    try:
        scheme, credentials = authorization.split()
        if scheme.lower() != 'basic':
            return False

        decoded = base64.b64decode(credentials).decode('utf-8')
        username, password = decoded.split(':', 1)

        basic_config = auth_config.get('basic_auth', {})

        expected_username = basic_config.get('username')
        expected_password = basic_config.get('password')

        return username == expected_username and password == expected_password

    except Exception:
        return False


def verify_custom_auth(x_dvc_token: Optional[str],
                       auth_config: Dict[str, Any]) -> bool:
    """Verify Custom Header Authentication"""
    if not x_dvc_token:
        return False

    custom_config = auth_config.get('custom_auth', {})

    expected_token = custom_config.get('token')
    return x_dvc_token == expected_token
