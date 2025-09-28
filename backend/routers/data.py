from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db, ensure_tables_exist, UploadedMetadata, DataItem
from ..schemas import DataItemCreate, DataItemResponse, DataItemWithLineage, UploadResponse, UploadedMetadataResponse, MetadataUploadResponse
from ..auth import get_current_active_user
from ..database import User
from ..dvc_service import create_data_item, create_folder_data_item, get_data_item_with_lineage, get_user_data_items, get_all_data_items
import yaml

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

@router.post("/upload-metadata", response_model=MetadataUploadResponse)
async def upload_metadata(
    request: Request,
    dvc_file: UploadFile = File(...),
    username: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload DVC metadata file to store original filename and host information"""
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    try:
        # Read and parse the .dvc file
        content = await dvc_file.read()
        dvc_content = yaml.safe_load(content)
        
        if not dvc_content or 'outs' not in dvc_content or len(dvc_content['outs']) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid .dvc file format"
            )
        
        # Extract file hash and original filename from .dvc file
        dvc_out = dvc_content['outs'][0]
        file_hash = dvc_out.get('md5') or dvc_out.get('sha256')
        original_filename = dvc_out.get('path')
        
        if not file_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file hash found in .dvc file"
            )
        
        if not original_filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No original filename found in .dvc file"
            )
        
        # Get client IP from request
        host_ip = request.client.host if request.client else None
        
        # Check if metadata already exists for this file hash
        existing_metadata = db.query(UploadedMetadata).filter(
            UploadedMetadata.file_hash == file_hash
        ).first()
        
        if existing_metadata:
            # Update existing metadata
            existing_metadata.original_filename = original_filename  # type: ignore
            existing_metadata.host_ip = host_ip  # type: ignore
            existing_metadata.username = username  # type: ignore
            
            # Check if there's a matching DataItem and update name if it's hash-based
            data_item = db.query(DataItem).filter(DataItem.hash == file_hash).first()
            if data_item is not None:
                item_name = str(data_item.name) if data_item.name is not None else ""
                if item_name.startswith('dvc_file_') or item_name.startswith('dvc_dir_'):
                    # Update name only if it's a hash-based fallback
                    data_item.name = original_filename  # type: ignore
            
            db.commit()
            db.refresh(existing_metadata)
            
            metadata_id = int(existing_metadata.id) if existing_metadata.id else 0
            return MetadataUploadResponse(
                message="Metadata updated successfully",
                metadata_id=metadata_id,
                file_hash=file_hash,
                original_filename=original_filename
            )
        else:
            # Create new metadata record
            metadata_record = UploadedMetadata(
                file_hash=file_hash,
                original_filename=original_filename,
                host_ip=host_ip,
                username=username
            )
            db.add(metadata_record)
            
            # Check if there's a matching DataItem and update name if it's hash-based
            data_item = db.query(DataItem).filter(DataItem.hash == file_hash).first()
            if data_item is not None:
                item_name = str(data_item.name) if data_item.name is not None else ""
                if item_name.startswith('dvc_file_') or item_name.startswith('dvc_dir_'):
                    # Update name only if it's a hash-based fallback
                    data_item.name = original_filename  # type: ignore
            
            db.commit()
            db.refresh(metadata_record)
            
            metadata_id = int(metadata_record.id) if metadata_record.id else 0
            return MetadataUploadResponse(
                message="Metadata uploaded successfully",
                metadata_id=metadata_id,
                file_hash=file_hash,
                original_filename=original_filename
            )
            
    except yaml.YAMLError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YAML format in .dvc file"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process metadata: {str(e)}"
        )
