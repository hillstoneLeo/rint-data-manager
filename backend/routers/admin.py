from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db, User, ensure_tables_exist
from ..schemas import UserResponse, UserPasswordUpdate
from ..auth import get_current_admin_user, get_password_hash

router = APIRouter()

@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/users/{user_id}/admin", response_model=UserResponse)
def toggle_admin_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from removing their own admin status
    if user.id == current_admin.id:  # type: ignore[comparison-overlap]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own admin status"
        )
    
    user.is_admin = not user.is_admin  # type: ignore
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from deleting themselves
    if user.id == current_admin.id:  # type: ignore[comparison-overlap]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

@router.put("/users/{user_id}/password")
def reset_user_password(
    user_id: int,
    password_data: UserPasswordUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from resetting their own password through this endpoint
    if user.id == current_admin.id:  # type: ignore[comparison-overlap]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reset your own password through this endpoint"
        )
    
    # Validate password length
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    user.hashed_password = get_password_hash(password_data.new_password)  # type: ignore
    db.commit()
    db.refresh(user)
    return {"message": "Password reset successfully"}