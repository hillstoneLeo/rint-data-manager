from fastapi import APIRouter, Request, Response, HTTPException, status, Depends, Header
from fastapi.responses import FileResponse
from typing import Optional, List
import os
import hashlib
import base64
from pathlib import Path
from sqlalchemy.orm import Session
from ..config import config
from ..database import get_db, ensure_tables_exist
from ..dvc_auth import verify_dvc_auth
from ..schemas import DVCFileResponse, DVCUploadResponse, DVCUserInfo
import yaml
from datetime import datetime
from ..database import DataItem, User

router = APIRouter()

DVC_STORAGE_PATH = Path(config.dvc_config.get('storage_path', '/opt/dvc_storage'))

def create_data_item_from_dvc_upload(
    file_path: str, 
    file_hash: str, 
    user: User, 
    db: Session,
    is_directory: bool = False,
    file_size: Optional[int] = None,
    file_count: Optional[int] = None,
    original_filename: Optional[str] = None
) -> DataItem:
    """Create a DataItem record from DVC upload"""
    
    # Use original filename if available, otherwise fallback to hash-based name
    if original_filename:
        name = original_filename
        # Extract file type from original filename
        file_type = Path(original_filename).suffix.lower().lstrip('.') or 'unknown'
    else:
        if is_directory:
            name = f"dvc_dir_{file_hash[:8]}"
            file_type = "directory"
        else:
            name = f"dvc_file_{file_hash[:8]}"
            file_type = "unknown"
    
    # Create DataItem record
    data_item = DataItem(
        name=name,
        description=f"Uploaded via DVC push",
        source="DVC Remote",
        file_path=file_path,
        hash=file_hash,
        file_size=file_size,
        file_type=file_type,
        is_folder=is_directory,
        file_count=file_count,
        user_id=user.id,
        parent_id=None
    )
    
    db.add(data_item)
    db.commit()
    db.refresh(data_item)
    
    return data_item

def extract_original_filename_from_dvc_file(dvc_file_path: Path) -> Optional[str]:
    """Extract original filename from DVC metadata file"""
    try:
        if dvc_file_path.exists():
            with open(dvc_file_path, 'r') as f:
                dvc_content = yaml.safe_load(f)
            
            if dvc_content and 'outs' in dvc_content and len(dvc_content['outs']) > 0:
                dvc_out = dvc_content['outs'][0]
                # The 'path' field contains the original filename
                original_path = dvc_out.get('path')
                if original_path:
                    # Extract just the filename from the path
                    return Path(original_path).name
    except Exception:
        pass
    return None

def extract_metadata_from_dvc_file(file_path: Path, user: User) -> dict:
    """Extract metadata from a DVC file (.dvc or .dir file)"""
    metadata = {
        'is_directory': False,
        'file_size': None,
        'file_count': None
    }
    
    try:
        if file_path.exists():
            with open(file_path, 'r') as f:
                dvc_content = yaml.safe_load(f)
            
            if dvc_content and 'outs' in dvc_content and len(dvc_content['outs']) > 0:
                dvc_out = dvc_content['outs'][0]
                metadata['file_size'] = dvc_out.get('size')
                metadata['file_count'] = dvc_out.get('nfiles', 1)
                
                # Check if this is a directory by looking for .dir extension
                if str(file_path).endswith('.dir'):
                    metadata['is_directory'] = True
    except Exception:
        # If we can't parse the DVC file, use defaults
        pass
    
    return metadata

def handle_dvc_upload_data_item_creation(
    file_path: str, 
    full_path: Path, 
    user: User, 
    db: Session
) -> Optional[DataItem]:
    """Handle creation of DataItem record for DVC uploads"""
    
    try:
        # Check if this is a DVC hash path
        if is_dvc_hash_path(file_path):
            file_hash = extract_hash_from_path(file_path)
            
            # Check if there's a corresponding .dvc or .dir file
            dvc_file_path = full_path.parent / f"{full_path.name}.dvc"
            dir_file_path = full_path.parent / f"{full_path.name}.dir"
            
            metadata = {}
            original_filename = None
            
            if dir_file_path.exists():
                # This is a directory
                metadata = extract_metadata_from_dvc_file(dir_file_path, user)
                metadata['is_directory'] = True
                original_filename = extract_original_filename_from_dvc_file(dir_file_path)
            elif dvc_file_path.exists():
                # This is a file
                metadata = extract_metadata_from_dvc_file(dvc_file_path, user)
                metadata['is_directory'] = False
                original_filename = extract_original_filename_from_dvc_file(dvc_file_path)
            else:
                # No DVC metadata file, use file stat
                if full_path.exists():
                    stat = full_path.stat()
                    metadata['file_size'] = stat.st_size
                    metadata['file_count'] = 1
                    metadata['is_directory'] = False
            
            # Create DataItem record
            return create_data_item_from_dvc_upload(
                file_path=file_path,
                file_hash=file_hash,
                user=user,
                db=db,
                is_directory=metadata.get('is_directory', False),
                file_size=metadata.get('file_size'),
                file_count=metadata.get('file_count'),
                original_filename=original_filename
            )
    
    except Exception as e:
        # Log error but don't fail the upload
        print(f"Error creating DataItem record: {e}")
    
    return None

def get_user_storage_path(user_email: str) -> Path:
    """Get user-specific storage path to isolate user data"""
    # Create user-specific directory structure
    user_dir = hashlib.md5(user_email.encode()).hexdigest()[:8]
    return DVC_STORAGE_PATH / "users" / user_dir

def get_file_path_from_hash(file_hash: str, user_email: Optional[str] = None) -> Path:
    """Convert DVC file hash to actual file path in storage"""
    # DVC stores files in subdirectories based on first 2 characters of hash
    if len(file_hash) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file hash"
        )
    
    # Use shared storage path for all users (no user isolation)
    storage_path = DVC_STORAGE_PATH
    
    # DVC stores files as hash files in subdirectories: files/md5/ab/cdef123...
    file_path = storage_path / "files" / "md5" / file_hash[:2] / file_hash[2:]
    
    return file_path

def is_dvc_hash_path(file_path: str) -> bool:
    """Check if path follows DVC's hash pattern"""
    # DVC hash paths look like: files/md5/ab/cdef123...
    parts = file_path.split('/')
    if len(parts) >= 4 and parts[0] == 'files':
        if parts[1] in ['md5', 'sha256']:
            if len(parts) == 4:  # files/md5/ab/cdef123...
                return True
    return False

def extract_hash_from_path(file_path: str) -> str:
    """Extract full hash from DVC path like: files/md5/3d/c179a06d7ed78aa2b20d16619cebb4.dir"""
    parts = file_path.split('/')
    if len(parts) >= 4:
        # Combine the hash prefix (parts[2]) and hash suffix (parts[3])
        hash_prefix = parts[2]  # '3d'
        hash_suffix = parts[3]  # 'c179a06d7ed78aa2b20d16619cebb4.dir'
        return hash_prefix + hash_suffix  # '3dc179a06d7ed78aa2b20d16619cebb4.dir'
    raise ValueError("Invalid DVC hash path format")

@router.get("/{file_path:path}")
async def get_dvc_file(
    file_path: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    x_dvc_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Serve DVC files for download"""
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    # Verify authentication and get user
    user = verify_dvc_auth(authorization, x_dvc_token, db)
    
    # Check if this is a DVC hash path or regular file path
    if is_dvc_hash_path(file_path):
        try:
            file_hash = extract_hash_from_path(file_path)
            user_email = str(user.email) if user else None
            full_path = get_file_path_from_hash(file_hash, user_email)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid DVC hash path format"
            )
    else:
        # Regular file path - Security: Prevent path traversal
        safe_path = Path(file_path).resolve()
        if safe_path.is_absolute() or '..' in str(safe_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path"
            )
        
        # Get user-specific storage path
        if user:
            storage_path = get_user_storage_path(str(user.email))
        else:
            storage_path = DVC_STORAGE_PATH
        
        full_path = storage_path / safe_path
    
    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    if not full_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a file"
        )
    
    return FileResponse(
        path=str(full_path),
        filename=full_path.name,
        headers={
            'Content-Disposition': f'attachment; filename="{full_path.name}"'
        }
    )

@router.put("/{file_path:path}")
async def upload_dvc_file(
    file_path: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    x_dvc_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Handle DVC file uploads"""
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    # Verify authentication and get user
    user = verify_dvc_auth(authorization, x_dvc_token, db)
    
    # Check if this is a DVC hash path or regular file path
    if is_dvc_hash_path(file_path):
        try:
            file_hash = extract_hash_from_path(file_path)
            user_email = str(user.email) if user else None
            full_path = get_file_path_from_hash(file_hash, user_email)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid DVC hash path format"
            )
    else:
        # Regular file path - Security: Prevent path traversal
        safe_path = Path(file_path).resolve()
        if safe_path.is_absolute() or '..' in str(safe_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path"
            )
        
        # Get user-specific storage path
        if user:
            storage_path = get_user_storage_path(str(user.email))
        else:
            storage_path = DVC_STORAGE_PATH
        
        full_path = storage_path / safe_path
    
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read file content from request body
    content = await request.body()
    
    with open(full_path, 'wb') as f:
        f.write(content)
    
    # Create DataItem record for DVC upload
    if user:
        try:
            handle_dvc_upload_data_item_creation(file_path, full_path, user, db)
        except Exception as e:
            # Log error but don't fail the upload
            print(f"Error creating DataItem record: {e}")
    
    return DVCUploadResponse(
        status="success",
        path=file_path,
        user_email=str(user.email) if user else None
    )

@router.post("/{file_path:path}")
async def post_dvc_file(
    file_path: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    x_dvc_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Handle DVC file uploads via POST"""
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    return await upload_dvc_file(file_path, request, authorization, x_dvc_token, db)

@router.head("/{file_path:path}")
async def head_dvc_file(
    file_path: str,
    authorization: Optional[str] = Header(None),
    x_dvc_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Check if DVC file exists and return metadata"""
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    # Verify authentication and get user
    user = verify_dvc_auth(authorization, x_dvc_token, db)
    
    # Check if this is a DVC hash path or regular file path
    if is_dvc_hash_path(file_path):
        try:
            file_hash = extract_hash_from_path(file_path)
            user_email = str(user.email) if user else None
            full_path = get_file_path_from_hash(file_hash, user_email)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid DVC hash path format"
            )
    else:
        # Regular file path - Security: Prevent path traversal
        safe_path = Path(file_path).resolve()
        if safe_path.is_absolute() or '..' in str(safe_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path"
            )
        
        # Get user-specific storage path
        if user:
            storage_path = get_user_storage_path(str(user.email))
        else:
            storage_path = DVC_STORAGE_PATH
        
        full_path = storage_path / safe_path
    
    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    if not full_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a file"
        )
    
    stat = full_path.stat()
    return DVCFileResponse(
        path=file_path,
        size=stat.st_size,
        modified=stat.st_mtime,
        exists=True,
        user_email=str(user.email) if user else None
    )

@router.get("/user/info")
async def get_user_info(
    authorization: Optional[str] = Header(None),
    x_dvc_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Get current authenticated user information"""
    # Ensure tables exist before proceeding
    ensure_tables_exist()
    
    user = verify_dvc_auth(authorization, x_dvc_token, db)
    
    if not user:
        return DVCUserInfo(authenticated=False)
    
    return DVCUserInfo(
        authenticated=True,
        user_id=int(user.id),  # type: ignore
        email=str(user.email),  # type: ignore
        is_admin=bool(user.is_admin),  # type: ignore
        created_at=user.created_at  # type: ignore
    )