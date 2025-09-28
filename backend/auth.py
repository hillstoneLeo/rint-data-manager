from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db, User
from .config import config

SECRET_KEY = config.auth.get('jwt_secret_key', 'your-secret-key-here-change-in-production')
ALGORITHM = config.auth.get('jwt_algorithm', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = config.auth.get('jwt_expiration_minutes', 30)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def get_user_from_token(token: str, db: Session) -> Optional[User]:
    """Get user from JWT token for server-side rendering"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
    
    user = db.query(User).filter(User.email == email).first()
    return user

def get_current_user_for_template(request: Request, db: Session) -> Optional[User]:
    """Get current user from request for template rendering"""
    # Debug: print cookies
    print(f"Request cookies: {request.cookies}")
    
    # Try to get token from Authorization header
    auth_header = request.headers.get("Authorization")
    print(f"Authorization header: {auth_header}")
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        user = get_user_from_token(token, db)
        if user:
            return user
    
    # Try to get token from cookies
    token = request.cookies.get("access_token")
    print(f"Token from cookie: {token}")
    
    if token:
        user = get_user_from_token(token, db)
        if user:
            return user
    
    return None