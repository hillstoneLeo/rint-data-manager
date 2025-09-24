from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db, ensure_tables_exist
from ..schemas import DataItemCreate, DataItemResponse, DataItemWithLineage, UploadResponse
from ..auth import get_current_active_user
from ..database import User
from ..dvc_service import create_data_item, create_folder_data_item, get_data_item_with_lineage, get_user_data_items, get_all_data_items

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_data(
    files: List[UploadFile] = File(...),
    source: str = Form(...),
    description: Optional[str] = Form(None),
    parent_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    data_item_data = DataItemCreate(
        source=source,
        description=description,
        parent_id=parent_id
    )
    
    # Check if this is a folder upload (multiple files with path separators)
    is_folder_upload = len(files) > 1 or any('/' in (file.filename or '') or '\\' in (file.filename or '') for file in files)
    
    if is_folder_upload:
        data_item = await create_folder_data_item(files, data_item_data, current_user, db)
        message = f"Folder uploaded successfully with {len(files)} files"
    else:
        # Single file upload
        data_item = await create_data_item(files[0], data_item_data, current_user, db)
        message = "File uploaded successfully"
    
    return UploadResponse(
        message=message,
        data_item=data_item
    )

@router.get("/", response_model=List[DataItemResponse])
def list_data_items(
    skip: int = 0,
    limit: int = 100,
    user_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    if user_only:
        return get_user_data_items(db, current_user, skip, limit)
    else:
        return get_all_data_items(db, skip, limit)

@router.get("/{item_id}", response_model=DataItemWithLineage)
def get_data_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    data_item = get_data_item_with_lineage(db, item_id, current_user)
    if not data_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data item not found"
        )
    return data_item