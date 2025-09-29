# DVC Metadata Upload Solution

Enables the server to capture original filenames when users run `dvc push` from remote hosts.

## Problem

When users run `dvc push` to this HTTP server:
- Data files are stored with hash-based paths (`files/md5/47/3eee96816e270cfcbc2813602413b9`)
- `.dvc` metadata files (containing original filenames) stay on the client
- Server has no way to get the original filename

## Solution

1. **API Endpoint**: `/upload-metadata` to accept `.dvc` file uploads
2. **Database Schema**: Added `original_filename` column to `data_items` table
3. **Git Hooks**: Automatically upload `.dvc` files after git events
4. **Fabric Method**: System-wide hook installation

## Implementation

### Backend Changes
- Added `upload_metadata` endpoint in `backend/routers/data.py`
- Added `original_filename` column to `DataItem` model in `backend/database.py`
- Updated response schema in `backend/schemas.py`

### Git Hooks
- `post-commit`: Uploads all `.dvc` files after commit
- `pre-push`: Uploads only `.dvc` files being pushed
- Both check for DVC installation and exit gracefully if not found

### Fabric Method
```bash
# Install system-wide git templates
uv run fab -r ./collect-metadata -H <dvc-client-ip> install-git-template  # for example:
uv run fab -r ./collect-metadata -H 10.160.43.66 install-git-template
```

The `install-git_template` task:
- Reads server URL from `config.yml`
- Installs hooks as system-wide git templates
- Configures git to use system template directory
- Requires sudo access for system-wide installation

## Usage

### Install Git Hooks
```bash
# System-wide installation (recommended)
fab install-git-template

# Or manual installation
./install-dvc-hooks.sh
```

### User Workflow
```bash
dvc add my_data.csv
git add my_data.csv.dvc
git commit -m "Add data file"
# Git hook automatically uploads .dvc file to server
dvc push
```

## API Endpoint

### `POST /api/data/upload-metadata`

**Request:**
```http
POST /api/data/upload-metadata
Content-Type: multipart/form-data

dvc_file=@my_data.csv.dvc
username=dvc_user_name
```

**Response:**
```json
{
  "message": "Metadata uploaded successfully",
  "data_item_id": 123
}
```

## Benefits

1. **Preserves Original Filenames**: Server displays original names instead of hashes
2. **Seamless Integration**: Users don't need to change their workflow
3. **Automatic**: Git hooks handle metadata upload automatically
4. **System-wide**: Fabric method enables organization-wide deployment
5. **Backward Compatible**: Existing uploads continue to work

## Files Modified

- `backend/database.py`: Added `original_filename` column
- `backend/schemas.py`: Added `original_filename` to response schema
- `backend/routers/data.py`: Added `upload_metadata` endpoint
- `collect-metadata/post-commit`: Git hook for automatic upload
- `collect-metadata/pre-push`: Alternative git hook
- `collect-metadata/fabfile.py`: Fabric task for system-wide installation
- `collect-metadata/install-dvc-hooks.sh`: Manual installation script
