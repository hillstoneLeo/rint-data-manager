import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import DataItem, User
from backend.schemas import DataItemCreate, DataItemResponse
from backend.config import config

UPLOAD_DIR = config.upload.get('directory', 'uploads')
DVC_STORAGE_DIR = config.dvc.get('storage_path', '/opt/dvc_storage')
DVC_REMOTE_NAME = config.dvc.get('remote_name', 'local_storage')

def ensure_dvc_repo():
    if not os.path.exists(".dvc"):
        subprocess.run(["dvc", "init"], check=True)
    
    if not os.path.exists(DVC_STORAGE_DIR):
        os.makedirs(DVC_STORAGE_DIR, exist_ok=True)
    
    remote_check = subprocess.run(["dvc", "remote", "list"], capture_output=True, text=True)
    if DVC_REMOTE_NAME not in remote_check.stdout:
        subprocess.run([
            "dvc", "remote", "add", "-d", DVC_REMOTE_NAME, 
            os.path.abspath(DVC_STORAGE_DIR)
        ], check=True)

async def save_upload_file(upload_file: UploadFile, destination: Path):
    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {str(e)}"
        )

async def create_data_item(
    file: UploadFile,
    data: DataItemCreate,
    user: User,
    db: Session
) -> DataItemResponse:
    ensure_dvc_repo()
    
    user_upload_dir = Path(UPLOAD_DIR) / str(user.id)
    user_upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = user_upload_dir / file.filename
    await save_upload_file(file, file_path)
    
    file_size = file_path.stat().st_size
    file_type = file.filename.split('.')[-1] if '.' in file.filename else None
    
    db_data_item = DataItem(
        name=data.name,
        description=data.description,
        source=data.source,
        file_path=str(file_path),
        file_size=file_size,
        file_type=file_type,
        user_id=user.id,
        parent_id=data.parent_id
    )
    db.add(db_data_item)
    db.commit()
    db.refresh(db_data_item)
    
    try:
        subprocess.run(["dvc", "add", str(file_path)], check=True, capture_output=True)
        subprocess.run(["dvc", "push"], check=True, capture_output=True)
        
        dvc_file_path = str(file_path) + ".dvc"
        if os.path.exists(dvc_file_path):
            with open(dvc_file_path, 'r') as f:
                dvc_content = f.read()
                db_data_item.dvc_path = dvc_file_path
            
            db.commit()
            db.refresh(db_data_item)
    
    except subprocess.CalledProcessError as e:
        db.delete(db_data_item)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DVC operation failed: {e.stderr.decode() if e.stderr else str(e)}"
        )
    
    return db_data_item

def get_data_item_with_lineage(db: Session, item_id: int, user: User) -> Optional[DataItem]:
    return db.query(DataItem).filter(
        DataItem.id == item_id,
        DataItem.user_id == user.id
    ).first()

def get_user_data_items(db: Session, user: User, skip: int = 0, limit: int = 100):
    return db.query(DataItem).filter(
        DataItem.user_id == user.id
    ).offset(skip).limit(limit).all()