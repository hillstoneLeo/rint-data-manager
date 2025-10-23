from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta
import re
import time
import logging
from ..database import get_db, User, ensure_tables_exist
from ..schemas import UserCreate, UserLogin, Token, UserResponse
from ..auth import authenticate_user, create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_active_user, get_current_user_for_template
from ..config import config
try:
    from ..utils.timing import timing_logger, log_timing
except ImportError:
    # Fallback if utils module is not available
    def timing_logger(func):
        return func
    def log_timing(message, start_time=None):
        return time.time()

# Set up logging for timing
logger = logging.getLogger(__name__)

router = APIRouter()


def validate_email_domain(email: str) -> bool:
    email_suffix_regex = config.auth.get('email_suffix_regex')
    if not email_suffix_regex:
        return True  # Allow all emails if no regex is configured

    try:
        return bool(re.match(email_suffix_regex, email))
    except re.error:
        return True  # If regex is invalid, allow all emails (fail-safe)


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    from ..database import User

    # Ensure tables exist before proceeding
    ensure_tables_exist()

    # Validate email domain
    if not validate_email_domain(user.email):
        raise HTTPException(status_code=400,
                            detail="Email domain not allowed for registration")

    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/register-admin", response_model=UserResponse)
def register_admin(user: UserCreate, db: Session = Depends(get_db)):
    from ..database import User

    # Ensure tables exist before proceeding
    ensure_tables_exist()

    # Check if any admin users already exist
    existing_admin = db.query(User).filter(User.is_admin == True).first()
    if existing_admin:
        raise HTTPException(status_code=400,
                            detail="Admin user already exists")

    # Skip email domain validation for admin registration
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email,
                   hashed_password=hashed_password,
                   is_admin=True)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    from ..database import User

    # Ensure tables exist before proceeding
    ensure_tables_exist()

    user = authenticate_user(db, user_credentials.email,
                             user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email},
                                       expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
@timing_logger
def get_current_user_info(
        current_user: User = Depends(get_current_active_user)):
    log_timing("get_current_user_info - starting endpoint")
    return current_user


@router.get("/me-server", response_model=UserResponse)
@timing_logger
def get_current_user_info_server_side(
        request: Request,
        db: Session = Depends(get_db)):
    """Get current user info using server-side authentication (cookies/headers)"""
    log_timing("get_current_user_info_server_side - starting endpoint")
    
    start_time = log_timing("get_current_user_info_server_side - calling get_current_user_for_template")
    current_user = get_current_user_for_template(request, db)
    log_timing("get_current_user_info_server_side - get_current_user_for_template completed", start_time)
    
    if not current_user:
        log_timing("get_current_user_info_server_side - no user found, raising 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    log_timing("get_current_user_info_server_side - user found, returning response")
    return current_user
