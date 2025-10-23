from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db, User, ensure_tables_exist, DataItem
from ..schemas import UserResponse, UserPasswordUpdate, DeleteResponse, GCResponse
from ..auth import get_current_admin_user, get_password_hash

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
def list_users(skip: int = 0,
               limit: int = 100,
               db: Session = Depends(get_db),
               current_admin: User = Depends(get_current_admin_user)):
    # Ensure tables exist before proceeding
    ensure_tables_exist()

    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int,
             db: Session = Depends(get_db),
             current_admin: User = Depends(get_current_admin_user)):
    # Ensure tables exist before proceeding
    ensure_tables_exist()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User not found")
    return user


@router.put("/users/{user_id}/admin", response_model=UserResponse)
def toggle_admin_status(user_id: int,
                        db: Session = Depends(get_db),
                        current_admin: User = Depends(get_current_admin_user)):
    # Ensure tables exist before proceeding
    ensure_tables_exist()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User not found")

    # Prevent admin from removing their own admin status
    if user.id == current_admin.id:  # type: ignore[comparison-overlap]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot modify your own admin status")

    user.is_admin = not user.is_admin  # type: ignore
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(user_id: int,
                db: Session = Depends(get_db),
                current_admin: User = Depends(get_current_admin_user)):
    # Ensure tables exist before proceeding
    ensure_tables_exist()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User not found")

    # Prevent admin from deleting themselves
    if user.id == current_admin.id:  # type: ignore[comparison-overlap]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot delete your own account")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.put("/users/{user_id}/password")
def reset_user_password(user_id: int,
                        password_data: UserPasswordUpdate,
                        db: Session = Depends(get_db),
                        current_admin: User = Depends(get_current_admin_user)):
    # Ensure tables exist before proceeding
    ensure_tables_exist()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User not found")

    # Prevent admin from resetting their own password through this endpoint
    if user.id == current_admin.id:  # type: ignore[comparison-overlap]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reset your own password through this endpoint")

    # Validate password length
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long")

    user.hashed_password = get_password_hash(
        password_data.new_password)  # type: ignore
    db.commit()
    db.refresh(user)
    return {"message": "Password reset successfully"}


@router.delete("/data/{item_id}", response_model=DeleteResponse)
def admin_delete_data_item(item_id: int,
                          db: Session = Depends(get_db),
                          current_admin: User = Depends(get_current_admin_user)):
    """Admin endpoint to delete any data item"""
    ensure_tables_exist()

    # Get the data item
    data_item = db.query(DataItem).filter(DataItem.id == item_id).first()
    if not data_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Data item not found")

    # Store item info for response
    item_name = str(data_item.name)

    # Delete the data item (this will cascade delete related records)
    db.delete(data_item)
    db.commit()

    return DeleteResponse(
        message=f"Data item '{item_name}' deleted successfully by admin",
        item_id=item_id,
        item_name=item_name
    )


@router.post("/gc", response_model=GCResponse)
def garbage_collect(db: Session = Depends(get_db),
                   current_admin: User = Depends(get_current_admin_user)):
    """Garbage collection - remove DVC storage files not referenced in database"""
    ensure_tables_exist()

    import os
    from pathlib import Path
    from ..config import config

    # Get DVC storage path
    storage_path = config.get_dvc_storage_path()
    files_dir = os.path.join(storage_path, "files", "md5")
    
    if not os.path.exists(files_dir):
        return GCResponse(
            message="DVC storage directory not found",
            files_deleted=0,
            space_freed=0
        )

    # Get all file hashes from database
    db_hashes = set()
    data_items = db.query(DataItem).filter(DataItem.hash.isnot(None)).all()
    for item in data_items:
        if item.hash:
            db_hashes.add(str(item.hash))

    files_deleted = 0
    space_freed = 0

    # Walk through DVC storage directory
    for root, dirs, files in os.walk(files_dir):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip .dir files for now, handle them separately if needed
            if file.endswith('.dir'):
                continue
                
            # Try to match file with database hash
            # DVC stores files as: files/md5/ab/abcdef...
            relative_path = os.path.relpath(file_path, files_dir)
            # Remove directory separators to reconstruct hash
            file_hash = relative_path.replace(os.sep, '')
            
            if file_hash not in db_hashes:
                try:
                    # Get file size before deletion
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    files_deleted += 1
                    space_freed += file_size
                except OSError as e:
                    # Log error but continue with other files
                    print(f"Error deleting file {file_path}: {e}")

    # Clean up empty directories
    for root, dirs, files in os.walk(files_dir, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            try:
                if not os.listdir(dir_path):  # Directory is empty
                    os.rmdir(dir_path)
            except OSError:
                pass  # Directory not empty or other error

    return GCResponse(
        message=f"Garbage collection completed. Deleted {files_deleted} orphaned files.",
        files_deleted=files_deleted,
        space_freed=space_freed
    )
