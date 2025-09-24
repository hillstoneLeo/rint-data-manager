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

router = APIRouter()

DVC_STORAGE_PATH = Path(config.dvc_config.get('storage_path', '/opt/dvc_storage'))

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