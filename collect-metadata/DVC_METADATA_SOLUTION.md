# DVC Metadata Upload Solution

This solution enables the server to capture original filenames when users run `dvc push` from remote hosts, solving the problem where DVC-pushed files only have hash-based names.

## Problem

When users run `dvc push` to this HTTP server:
- Data files are stored with hash-based paths (`files/md5/47/3eee96816e270cfcbc2813602413b9`)
- `.dvc` metadata files (containing original filenames) stay on the client
- Server has no way to get the original filename

## Solution Overview

1. **New API Endpoint**: `/upload-metadata` to accept `.dvc` file uploads
2. **Database Schema**: Added `original_filename` column to `data_items` table
3. **Git Hooks**: Automatically upload `.dvc` files after git events
4. **Migration Script**: Update existing databases

## Implementation

### 1. Backend Changes

#### Added `upload_metadata` endpoint (`backend/routers/data.py`)
```python
@router.post("/upload-metadata")
async def upload_dvc_metadata(
    dvc_file: UploadFile = File(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
```

**Features:**
- Parses `.dvc` YAML files to extract original filename
- Creates or updates `DataItem` records with original filename
- Handles both new uploads and existing data items

#### Database Schema Update (`backend/database.py`)
```python
class DataItem(Base):
    # ... existing fields ...
    original_filename = Column(String, nullable=True)  # NEW
```

#### Schema Update (`backend/schemas.py`)
```python
class DataItemResponse(DataItemBase):
    # ... existing fields ...
    original_filename: Optional[str] = None  # NEW
```

### 2. Git Hooks

#### Recommended: `post-commit` hook
**Location:** `.git/hooks/post-commit`

**Why `post-commit`?**
- Runs after `.dvc` files are committed to git
- Ensures `.dvc` files are finalized and ready
- Captures both new and modified `.dvc` files
- Integrates naturally with DVC workflow

**Features:**
- Scans repository for all `.dvc` files
- Uploads each `.dvc` file to the server
- Configurable server URL and user ID
- Supports authentication tokens

#### Alternative: `pre-push` hook
**Location:** `.git/hooks/pre-push`

**Features:**
- Only uploads `.dvc` files that are being pushed
- More efficient for large repositories
- Can block push if upload fails

### 3. Installation Scripts

#### `install-dvc-hooks.sh`
Automated installation script that:
- Creates git hooks in the correct location
- Makes hooks executable
- Provides configuration instructions

## Usage

### 1. Install Git Hooks
```bash
./install-dvc-hooks.sh
```

### 2. Configure Hooks
Edit the hook scripts to set:
- `SERVER_URL`: Your server endpoint
- `USER_ID`: User ID for metadata uploads
- `AUTH_TOKEN`: Authentication token (if required)

### 4. User Workflow

#### For users uploading via web interface:
- No changes needed - works as before

#### For users using `dvc push` from remote hosts:
```bash
# User workflow remains the same
dvc add my_data.csv
git add my_data.csv.dvc
git commit -m "Add data file"
# Git hook automatically uploads .dvc file to server
dvc push
```

## API Endpoint Details

### `POST /api/v1/data/upload-metadata`

**Request:**
```http
POST /api/v1/data/upload-metadata
Content-Type: multipart/form-data

dvc_file=@my_data.csv.dvc
user_id=1
```

**Response:**
```json
{
  "message": "Metadata uploaded successfully",
  "data_item_id": 123
}
```

**Error Responses:**
- `400 Bad Request`: Invalid `.dvc` file format
- `500 Internal Server Error`: Failed to process metadata

## Benefits

1. **Preserves Original Filenames**: Server now displays original names instead of hashes
2. **Seamless Integration**: Users don't need to change their workflow
3. **Automatic**: Git hooks handle metadata upload automatically
4. **Backward Compatible**: Existing uploads continue to work
5. **Flexible**: Supports both `post-commit` and `pre-push` hooks

## Files Modified

- `backend/database.py`: Added `original_filename` column
- `backend/schemas.py`: Added `original_filename` to response schema
- `backend/routers/data.py`: Added `upload_metadata` endpoint
- `.git/hooks/post-commit`: Git hook for automatic upload
- `.git/hooks/pre-push`: Alternative git hook
- `install-dvc-hooks.sh`: Installation script

## Testing

1. **Test API Endpoint:**
```bash
curl -X POST http://localhost:8000/api/v1/data/upload-metadata \
     -F "dvc_file=@test.dvc" \
     -F "user_id=1"
```

2. **Test Git Hook:**
```bash
# Create a test .dvc file
echo "outs:
- md5: test123
  path: original_name.csv" > test.dvc

# Commit to trigger hook
git add test.dvc
git commit -m "Test hook"
```

3. **Verify Database:**
```bash
usql -c 'select name, original_filename from data_items;' rint_data_manager.db
```

## Troubleshooting

### Hook Not Running
- Ensure hook is executable: `chmod +x .git/hooks/post-commit`
- Check git hook directory exists
- Verify hook script has correct shebang

### Upload Failing
- Check server URL in hook configuration
- Verify server is running
- Check authentication if required
- Test endpoint manually with curl

### Database Issues
- Check database file permissions
- Verify table structure

## Future Enhancements

1. **Bulk Upload**: Support uploading multiple `.dvc` files at once
2. **User Mapping**: Automatic user detection based on git config
3. **Webhook Support**: Receive notifications from DVC directly
4. **Metadata API**: Endpoint to query and manage metadata
5. **Validation**: Enhanced `.dvc` file validation and error handling
