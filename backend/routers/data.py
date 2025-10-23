from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db, ensure_tables_exist, UploadedMetadata, DataItem
from ..schemas import DataItemCreate, DataItemResponse, DataItemWithLineage, UploadResponse, UploadedMetadataResponse, MetadataUploadResponse, DeleteResponse
from ..auth import get_current_active_user
from ..database import User
from ..dvc_service import create_data_item, create_folder_data_item, get_data_item_with_lineage, get_user_data_items, get_all_data_items
import yaml
import os
import json
import zipfile
import tempfile
import time
import logging
from pathlib import Path
from fastapi.responses import FileResponse, Response
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


@router.post("/upload", response_model=UploadResponse)
async def upload_data(files: List[UploadFile] = File(...),
                      source: str = Form(...),
                      description: Optional[str] = Form(None),
                      project: Optional[str] = Form(None),
                      parent_id: Optional[int] = Form(None),
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_active_user)):
    # Ensure tables exist before proceeding
    ensure_tables_exist()

    data_item_data = DataItemCreate(source=source,
                                    description=description,
                                    project=project,
                                    parent_id=parent_id)

    # Check if this is a folder upload (multiple files with path separators)
    is_folder_upload = len(files) > 1 or any(
        '/' in (file.filename or '') or '\\' in (file.filename or '')
        for file in files)

    if is_folder_upload:
        data_item = await create_folder_data_item(files, data_item_data,
                                                  current_user, db)
        message = f"Folder uploaded successfully with {len(files)} files"
    else:
        # Single file upload
        data_item = await create_data_item(files[0], data_item_data,
                                           current_user, db)
        message = "File uploaded successfully"

    return UploadResponse(message=message, data_item=data_item)


@router.get("/", response_model=List[DataItemResponse])
@timing_logger
def list_data_items(skip: int = 0,
                    limit: int = 100,
                    user_only: bool = True,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_active_user)):
    log_timing(f"list_data_items - starting with user_only={user_only}")
    
    # Ensure tables exist before proceeding
    start_time = log_timing("list_data_items - calling ensure_tables_exist")
    ensure_tables_exist()
    log_timing("list_data_items - ensure_tables_exist completed", start_time)

    if user_only:
        query_start = log_timing("list_data_items - calling get_user_data_items")
        result = get_user_data_items(db, current_user, skip, limit)
        log_timing("list_data_items - get_user_data_items completed", query_start)
        return result
    else:
        query_start = log_timing("list_data_items - calling get_all_data_items")
        result = get_all_data_items(db, skip, limit)
        log_timing("list_data_items - get_all_data_items completed", query_start)
        return result


@router.get("/public", response_model=List[DataItemResponse])
def list_public_data_items(skip: int = 0,
                           limit: int = 100,
                           db: Session = Depends(get_db)):
    """Public endpoint that doesn't require authentication"""
    # Ensure tables exist before proceeding
    ensure_tables_exist()

    return get_all_data_items(db, skip, limit)


@router.get("/{item_id}", response_model=DataItemWithLineage)
def get_data_item(item_id: int,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_active_user)):
    # Ensure tables exist before proceeding
    ensure_tables_exist()

    data_item = get_data_item_with_lineage(db, item_id, current_user)
    if not data_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Data item not found")
    return data_item


@router.post("/upload-metadata", response_model=MetadataUploadResponse)
async def upload_metadata(request: Request,
                          dvc_file: UploadFile = File(...),
                          username: Optional[str] = Form(None),
                          db: Session = Depends(get_db)):
    """Upload DVC metadata file to store original filename and host information"""
    # Ensure tables exist before proceeding
    ensure_tables_exist()

    try:
        # Read and parse the .dvc file
        content = await dvc_file.read()
        dvc_content = yaml.safe_load(content)

        if not dvc_content or 'outs' not in dvc_content or len(
                dvc_content['outs']) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid .dvc file format")

        # Extract file hash and original filename from .dvc file
        dvc_out = dvc_content['outs'][0]
        file_hash = dvc_out.get('md5') or dvc_out.get('sha256')
        original_filename = dvc_out.get('path')

        if not file_hash:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="No file hash found in .dvc file")

        if not original_filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No original filename found in .dvc file")

        # Get client IP from request
        host_ip = request.client.host if request.client else None

        # Check if metadata already exists for this file hash
        existing_metadata = db.query(UploadedMetadata).filter(
            UploadedMetadata.file_hash == file_hash).first()

        if existing_metadata:
            # Update existing metadata
            existing_metadata.original_filename = original_filename  # type: ignore
            existing_metadata.host_ip = host_ip  # type: ignore
            existing_metadata.username = username  # type: ignore

            # Check if there's a matching DataItem and update name if it's hash-based
            data_item = db.query(DataItem).filter(
                DataItem.hash == file_hash).first()
            if data_item is not None:
                item_name = str(
                    data_item.name) if data_item.name is not None else ""
                if item_name.startswith('dvc_file_') or item_name.startswith(
                        'dvc_dir_'):
                    # Update name only if it's a hash-based fallback
                    data_item.name = original_filename  # type: ignore

            db.commit()
            db.refresh(existing_metadata)

            metadata_id = int(
                existing_metadata.id) if existing_metadata.id else 0
            return MetadataUploadResponse(
                message="Metadata updated successfully",
                metadata_id=metadata_id,
                file_hash=file_hash,
                original_filename=original_filename)
        else:
            # Create new metadata record
            metadata_record = UploadedMetadata(
                file_hash=file_hash,
                original_filename=original_filename,
                host_ip=host_ip,
                username=username)
            db.add(metadata_record)

            # Check if there's a matching DataItem and update name if it's hash-based
            data_item = db.query(DataItem).filter(
                DataItem.hash == file_hash).first()
            if data_item is not None:
                item_name = str(
                    data_item.name) if data_item.name is not None else ""
                if item_name.startswith('dvc_file_') or item_name.startswith(
                        'dvc_dir_'):
                    # Update name only if it's a hash-based fallback
                    data_item.name = original_filename  # type: ignore

            db.commit()
            db.refresh(metadata_record)

            metadata_id = int(metadata_record.id) if metadata_record.id else 0
            return MetadataUploadResponse(
                message="Metadata uploaded successfully",
                metadata_id=metadata_id,
                file_hash=file_hash,
                original_filename=original_filename)

    except yaml.YAMLError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid YAML format in .dvc file")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to process metadata: {str(e)}")


def get_dvc_file_path_from_hash(file_hash: str, storage_path: str) -> str:
    """Get DVC file path from hash"""
    if len(file_hash) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid file hash")
    
    hash_prefix = file_hash[:2]
    hash_suffix = file_hash[2:]
    return os.path.join(storage_path, "files", "md5", hash_prefix, hash_suffix)


def read_dir_metadata(dir_file_path: str) -> list:
    """Read DVC .dir metadata file and return list of files"""
    try:
        with open(dir_file_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Cannot read folder metadata: {str(e)}")


def create_folder_zip(folder_name: str, file_list: list, storage_path: str) -> str:
    """Create a ZIP file containing all files from the folder"""
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, f"{folder_name}.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_info in file_list:
            file_hash = file_info['md5']
            rel_path = file_info['relpath']
            
            # Get the actual file path from hash
            try:
                actual_file_path = get_dvc_file_path_from_hash(file_hash, storage_path)
                
                if os.path.exists(actual_file_path):
                    # Add file to ZIP with its relative path
                    zipf.write(actual_file_path, rel_path)
                else:
                    print(f"Warning: File {rel_path} (hash: {file_hash}) not found in storage")
            except Exception as e:
                print(f"Warning: Error processing file {rel_path}: {str(e)}")
                continue
    
    return zip_path


@router.get("/{item_id}/download")
def download_data_file(item_id: int,
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_active_user)):
    """Download the actual data file"""
    ensure_tables_exist()

    # Allow all users to download any data item (no user restriction)
    data_item = db.query(DataItem).filter(DataItem.id == item_id).first()

    if not data_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Data item not found")

    # Check if we have the hash to locate file in DVC storage
    if not data_item.hash:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="File hash not found")

    # Construct DVC storage path using hash
    from ..config import config
    storage_path = config.get_dvc_storage_path()
    
    # Check if this is a folder
    if data_item.is_folder and str(data_item.hash).endswith('.dir'):
        # Handle folder download - create ZIP file
        dir_file_path = get_dvc_file_path_from_hash(str(data_item.hash), storage_path)
        
        if not os.path.exists(dir_file_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Folder metadata not found in DVC storage")
        
        # Read folder metadata
        file_list = read_dir_metadata(dir_file_path)
        
        # Create ZIP file
        zip_path = create_folder_zip(str(data_item.name), file_list, storage_path)
        
        try:
            return FileResponse(
                path=zip_path,
                filename=f"{str(data_item.name)}.zip",
                media_type='application/zip'
            )
        except Exception as e:
            # Clean up temp file if something goes wrong
            import shutil
            if os.path.exists(zip_path):
                os.unlink(zip_path)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Failed to create folder download: {str(e)}")
    else:
        # Handle single file download (original logic)
        if len(str(data_item.hash)) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid file hash")

        # Build path: /opt/dvc_storage/files/md5/{first_two_chars}/{remaining_hash}
        dvc_file_path = get_dvc_file_path_from_hash(str(data_item.hash), storage_path)

        # Verify file exists in DVC storage
        if not os.path.exists(dvc_file_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="File not found in DVC storage")

        # Determine media type based on file extension
        from pathlib import Path
        file_extension = Path(str(data_item.name)).suffix.lower()
        media_type = {
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.txt': 'text/plain',
            '.xlsx':
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.parquet': 'application/octet-stream',
            '.h5': 'application/octet-stream',
            '.pkl': 'application/octet-stream',
            '.py': 'text/plain',
            '.ipynb': 'application/json',
            '.zip': 'application/zip',
        }.get(file_extension, 'application/octet-stream')

        # Serve file with original filename from database
        return FileResponse(
            path=dvc_file_path,
            filename=str(data_item.name),  # Use original name from database
            media_type=media_type)


@router.get("/{item_id}/dvc-file")
def download_dvc_file(item_id: int,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_active_user)):
    """Download .dvc file (generated from database)"""
    ensure_tables_exist()

    # Allow all users to download any DVC file (no user restriction)
    data_item = db.query(DataItem).filter(DataItem.id == item_id).first()

    if not data_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Data item not found")

    if not data_item.hash:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="File hash not found in database")

    # Generate .dvc content dynamically from database
    import yaml
    from io import StringIO

    # Build DVC content structure
    dvc_content = {
        'outs': [{
            'md5': data_item.hash,
            'size': data_item.file_size,
            'hash': 'md5',
            'path': data_item.name
        }]
    }

    # Add folder-specific fields if it's a folder
    if data_item.is_folder:
        dvc_content['outs'][0]['nfiles'] = data_item.file_count or 1

    # Convert to YAML string
    yaml_content = yaml.dump(dvc_content,
                             default_flow_style=False,
                             sort_keys=False)

    # Create a temporary file-like object to serve
    from tempfile import NamedTemporaryFile
    import tempfile

    with NamedTemporaryFile(mode='w',
                            suffix='.dvc',
                            delete=False,
                            encoding='utf-8') as temp_file:
        temp_file.write(yaml_content)
        temp_file_path = temp_file.name

    try:
        return FileResponse(path=temp_file_path,
                            filename=data_item.name + ".dvc",
                            media_type='text/yaml')
    except Exception as e:
        # Clean up temp file if something goes wrong
        import os
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to serve DVC file: {str(e)}")


@router.get("/{item_id}/dvc-content")
def get_dvc_content(item_id: int,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_active_user)):
    """Get .dvc file content as text (generated from database)"""
    ensure_tables_exist()

    # Allow all users to access any DVC content (no user restriction)
    data_item = db.query(DataItem).filter(DataItem.id == item_id).first()

    if not data_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Data item not found")

    if not data_item.hash:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="File hash not found in database")

    # Generate .dvc content dynamically from database
    import yaml

    # Build DVC content structure
    dvc_content = {
        'outs': [{
            'md5': data_item.hash,
            'size': data_item.file_size,
            'hash': 'md5',
            'path': data_item.name
        }]
    }

    # Add folder-specific fields if it's a folder
    if data_item.is_folder:
        dvc_content['outs'][0]['nfiles'] = data_item.file_count or 1

    # Convert to YAML string
    yaml_content = yaml.dump(dvc_content,
                             default_flow_style=False,
                             sort_keys=False)

    return Response(content=yaml_content, media_type='text/plain')


@router.delete("/{item_id}", response_model=DeleteResponse)
def delete_data_item(item_id: int,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_active_user)):
    """Delete a data item (only if owned by the current user)"""
    ensure_tables_exist()

    # Get the data item
    data_item = db.query(DataItem).filter(DataItem.id == item_id).first()
    if not data_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Data item not found")

    # Check if user owns this item
    if data_item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can only delete your own data items")

    # Store item info for response
    item_name = str(data_item.name)

    # Delete the data item (this will cascade delete related records)
    db.delete(data_item)
    db.commit()

    return DeleteResponse(
        message=f"Data item '{item_name}' deleted successfully",
        item_id=item_id,
        item_name=item_name
    )
