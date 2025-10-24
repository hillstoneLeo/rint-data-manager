import os
import subprocess
import yaml
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
import time
import logging

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from .config import config
from .database import User, DataItem
from .schemas import DataItemCreate, DataItemResponse
try:
    from .utils.timing import timing_logger, log_timing
except ImportError:
    # Fallback if utils module is not available
    def timing_logger(func):
        return func
    def log_timing(message, start_time=None):
        return time.time()

# Set up logging for timing
logger = logging.getLogger(__name__)

UPLOAD_DIR = config.dvc_config.get('upload_directory', '/tmp/rdm/uploads')
DVC_STORAGE_DIR = config.dvc_config.get('storage_path', '/opt/dvc_storage')
DVC_REMOTE_NAME = config.dvc_config.get('remote_name', 'local_storage')
DVC_UPLOADS_PROJECT = config.dvc_config.get('uploads_dvc_project',
                                            '/tmp/rdm/uploads')

def run_dvc_command(args, cwd=None, check=True, capture_output=False, text=False):
    """Run DVC command using uv run to ensure proper environment."""
    cmd = ['uv', 'run', 'dvc'] + args
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=capture_output, text=text)


def ensure_dvc_repo():
    # Ensure uploads DVC project exists
    if not os.path.exists(DVC_UPLOADS_PROJECT):
        os.makedirs(DVC_UPLOADS_PROJECT, exist_ok=True)

    # Initialize DVC in uploads project if not already initialized
    if not os.path.exists(os.path.join(DVC_UPLOADS_PROJECT, ".dvc")):
        Path(DVC_UPLOADS_PROJECT).mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], check=True, cwd=DVC_UPLOADS_PROJECT)
        run_dvc_command(["init", "-f", "-q"], cwd=DVC_UPLOADS_PROJECT)

    # Ensure storage directory exists
    if not os.path.exists(DVC_STORAGE_DIR):
        os.makedirs(DVC_STORAGE_DIR, exist_ok=True)

    # Check and add remote in uploads DVC project
    remote_check = run_dvc_command(["remote", "list"],
                                  capture_output=True,
                                  text=True,
                                  cwd=DVC_UPLOADS_PROJECT)
    if DVC_REMOTE_NAME not in remote_check.stdout:
        run_dvc_command([
            "remote", "add", "-d", DVC_REMOTE_NAME,
            os.path.abspath(DVC_STORAGE_DIR)
        ],
                       cwd=DVC_UPLOADS_PROJECT)


async def save_upload_file(upload_file: UploadFile, destination: Path):
    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Could not save file: {str(e)}")


def extract_common_folder_name(files: List[UploadFile]) -> str:
    """Extract the common folder path from all uploaded files using Strategy 2"""
    if not files:
        return 'unknown_folder'
    
    # Get all normalized file paths
    normalized_paths = []
    for file in files:
        file_name = file.filename or 'unknown_file'
        # Normalize path separators and split into components
        normalized_path = file_name.replace('\\', '/')
        path_parts = [part for part in normalized_path.split('/') if part]
        normalized_paths.append(path_parts)
    
    # Find the common prefix among all paths
    if not normalized_paths:
        return 'unknown_folder'
    
    # Start with the first path and find common parts
    common_parts = normalized_paths[0][:-1]  # Exclude the filename
    
    for path_parts in normalized_paths[1:]:
        # Compare up to the second-to-last part (excluding filename)
        current_parts = path_parts[:-1]
        
        # Find common prefix length
        common_length = 0
        max_length = min(len(common_parts), len(current_parts))
        
        for i in range(max_length):
            if common_parts[i] == current_parts[i]:
                common_length += 1
            else:
                break
        
        # Truncate common_parts to the common length
        common_parts = common_parts[:common_length]
        
        # If no common parts left, break early
        if not common_parts:
            break
    
    # If we have common folder parts, join them with underscores
    if common_parts:
        return '_'.join(common_parts)
    else:
        # No common folder path, fall back to first filename without extension
        first_file_name = files[0].filename or 'unknown_file'
        filename = first_file_name.split('/')[-1].split('\\')[-1]
        return filename.rsplit('.', 1)[0] if '.' in filename else filename


async def create_folder_data_item(files: List[UploadFile],
                                  data: DataItemCreate, user: User,
                                  db: Session) -> DataItemResponse:
    ensure_dvc_repo()

    user_upload_dir = Path(UPLOAD_DIR or '/tmp/rdm/uploads') / str(user.id)
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    # Extract the common folder path from all uploaded files
    folder_base_name = extract_common_folder_name(files)
    folder_name = folder_base_name.replace(' ', '_').lower()
    folder_path = user_upload_dir / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)

    file_types = set()

    # Save all files preserving their relative paths
    for file in files:
        file_name = file.filename or 'unknown_file'

        # Normalize path separators and create subdirectories
        normalized_path = file_name.replace('\\', '/')
        file_subdir = folder_path / normalized_path.rsplit(
            '/', 1)[0] if '/' in normalized_path else folder_path
        file_subdir.mkdir(parents=True, exist_ok=True)
        file_path = folder_path / normalized_path

        await save_upload_file(file, file_path)

        if '.' in file_name:
            file_types.add(file_name.split('.')[-1])

    # Create single data item for the folder (size and file_count will be updated after DVC add)
    db_data_item = DataItem(
        name=folder_base_name,
        description=data.description,
        project=data.project,
        source=data.source,
        file_path=str(folder_path),
        file_size=0,  # Will be updated from DVC file
        file_type=', '.join(sorted(file_types)) if file_types else 'folder',
        is_folder=True,
        file_count=0,  # Will be updated from DVC file
        user_id=user.id,
        parent_id=data.parent_id)
    db.add(db_data_item)
    db.commit()
    db.refresh(db_data_item)

    try:
        # Run DVC commands from the uploads DVC project directory
        relative_folder_path = os.path.relpath(str(folder_path),
                                               DVC_UPLOADS_PROJECT)
        run_dvc_command(["add", relative_folder_path],
                        capture_output=True,
                        cwd=DVC_UPLOADS_PROJECT)
        run_dvc_command(["push"],
                        capture_output=True,
                        cwd=DVC_UPLOADS_PROJECT)

        dvc_file_path = str(folder_path) + ".dvc"
        if os.path.exists(dvc_file_path):
            # Read DVC file to get size and file count
            with open(dvc_file_path, 'r') as f:
                dvc_content = yaml.safe_load(f)

            if dvc_content and 'outs' in dvc_content and len(
                    dvc_content['outs']) > 0:
                dvc_out = dvc_content['outs'][0]
                db_data_item.file_size = dvc_out.get('size', 0)
                db_data_item.file_count = dvc_out.get('nfiles', len(files))
                db_data_item.hash = dvc_out.get('md5', '')

            db.commit()
            db.refresh(db_data_item)

    except subprocess.CalledProcessError as e:
        # Clean up the folder if DVC fails
        import shutil
        shutil.rmtree(folder_path, ignore_errors=True)
        db.delete(db_data_item)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=
            f"DVC operation failed: {e.stderr.decode() if e.stderr else str(e)}"
        )

    return db_data_item


async def create_data_item(file: UploadFile, data: DataItemCreate, user: User,
                           db: Session) -> DataItemResponse:
    ensure_dvc_repo()

    user_upload_dir = Path(UPLOAD_DIR or '/tmp/rdm/uploads') / str(user.id)
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    # Handle folder structure by preserving relative paths
    file_name = file.filename or 'unknown_file'

    # If the filename contains path separators (from folder upload), preserve the structure
    if '/' in file_name or '\\' in file_name:
        # Normalize path separators and create subdirectories
        normalized_path = file_name.replace('\\', '/')
        file_subdir = user_upload_dir / normalized_path.rsplit(
            '/', 1)[0] if '/' in normalized_path else user_upload_dir
        file_subdir.mkdir(parents=True, exist_ok=True)
        file_path = user_upload_dir / normalized_path
    else:
        file_path = user_upload_dir / file_name

    await save_upload_file(file, file_path)

    file_size = file_path.stat().st_size
    file_type = file_name.split('.')[-1] if '.' in file_name else None

    # Use the actual filename as the display name
    display_name = file_name.split('/')[-1].split('\\')[
        -1]  # Get just the filename without path

    db_data_item = DataItem(name=display_name,
                            description=data.description,
                            project=data.project,
                            source=data.source,
                            file_path=str(file_path),
                            file_size=file_size,
                            file_type=file_type,
                            user_id=user.id,
                            parent_id=data.parent_id)
    db.add(db_data_item)
    db.commit()
    db.refresh(db_data_item)

    try:
        # Run DVC commands from the uploads DVC project directory
        relative_file_path = os.path.relpath(str(file_path),
                                             DVC_UPLOADS_PROJECT)
        run_dvc_command(["add", relative_file_path],
                        capture_output=True,
                        cwd=DVC_UPLOADS_PROJECT)
        run_dvc_command(["push"],
                        capture_output=True,
                        cwd=DVC_UPLOADS_PROJECT)

        dvc_file_path = str(file_path) + ".dvc"
        if os.path.exists(dvc_file_path):
            with open(dvc_file_path, 'r') as f:
                dvc_content = yaml.safe_load(f)

            if dvc_content and 'outs' in dvc_content and len(
                    dvc_content['outs']) > 0:
                dvc_out = dvc_content['outs'][0]
                db_data_item.hash = dvc_out.get('md5', '')
                db_data_item.file_size = dvc_out.get(
                    'size',
                    db_data_item.file_size)  # Update file_size from DVC file

            db.commit()
            db.refresh(db_data_item)

    except subprocess.CalledProcessError as e:
        db.delete(db_data_item)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=
            f"DVC operation failed: {e.stderr.decode() if e.stderr else str(e)}"
        )

    return db_data_item


def get_data_item_with_lineage(db: Session, item_id: int,
                               user: User) -> Optional[DataItem]:
    return db.query(DataItem).filter(DataItem.id == item_id,
                                     DataItem.user_id == user.id).first()


@timing_logger
def get_user_data_items(db: Session,
                        user: User,
                        skip: int = 0,
                        limit: int = 100):
    log_timing(f"get_user_data_items - starting query for user {user.id}")
    start_time = log_timing("get_user_data_items - executing query")
    result = db.query(DataItem).filter(
        DataItem.user_id == user.id).offset(skip).limit(limit).all()
    log_timing(f"get_user_data_items - query completed, returned {len(result)} items", start_time)
    return result


@timing_logger
def get_all_data_items(db: Session, skip: int = 0, limit: int = 100):
    log_timing("get_all_data_items - starting query")
    start_time = log_timing("get_all_data_items - executing query")
    result = db.query(DataItem).offset(skip).limit(limit).all()
    log_timing(f"get_all_data_items - query completed, returned {len(result)} items", start_time)
    return result
