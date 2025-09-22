from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..schemas import DataItemCreate, DataItemResponse, DataItemWithLineage, UploadResponse
from ..auth import get_current_active_user
from ..database import User
from ..dvc_service import create_data_item, get_data_item_with_lineage, get_user_data_items

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_data(
    file: UploadFile = File(...),
    name: str = Form(...),
    source: str = Form(...),
    description: Optional[str] = Form(None),
    parent_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    data_item_data = DataItemCreate(
        name=name,
        source=source,
        description=description,
        parent_id=parent_id
    )
    
    data_item = await create_data_item(file, data_item_data, current_user, db)
    
    return UploadResponse(
        message="File uploaded successfully",
        data_item=data_item
    )

@router.get("/", response_model=List[DataItemResponse])
def list_data_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return get_user_data_items(db, current_user, skip, limit)

@router.get("/{item_id}", response_model=DataItemWithLineage)
def get_data_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    data_item = get_data_item_with_lineage(db, item_id, current_user)
    if not data_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data item not found"
        )
    return data_item