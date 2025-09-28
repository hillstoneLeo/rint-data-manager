# RINT Data Sharing Platform

A DVC-based platform for data collection and sharing with naive lineage tracking visualization.

## Features

- **User Management**: Registration, login, and JWT-based authentication
- **Data Upload**: File/folder upload with metadata (name, source, description)
- **DVC Integration**: Automatic DVC tracking for uploaded files
- **DVC HTTP Remote**: Full DVC remote server with database authentication
- **Unified Configuration**: Single DVC configuration for both internal and remote operations
- **Lineage Tracking**: Parent-child relationships between data items with naive visualization
- **Web Interface**: Clean, responsive UI for data management
- **SQLite Database**: User data and metadata storage
- **REST API**: Full backend API for all operations

## Usage

### Setup Server

Run the following commands on server host:

1. **Install dependencies**:
   ```bash
   uv sync
   ```

1. **Create DVC storage directory**:
    ```bash
    sudo mkdir /opt/dvc_storage
    sudo chown $USER:$USER /opt/dvc_storage
    mkdir /opt/dvc_storage/uploads  # defined in config.yml
    
    # Setup DVC remote storage structure
    python setup_dvc_storage.py
    ```

1. **Review and update configuration**:
   ```bash
   # Edit config.yml to customize settings as needed
   vi config.yml
   ```

1. Start up server: `uv run main.py`

### Client Setup: Admin

1. Install DVC client in system level:
    * Ubuntu: `sudo snap install --classic dvc`
    * Windows: download binary and install it as administrator

1. Install Git hooks in system level: update git template in systme level 

### Client Usage: Users

1. **Access the application**:
    - Open http://localhost:8000 in your browser
    - Register a new account
    - Upload data files with lineage information

## DVC HTTP Remote Server

This project now includes a full-featured DVC HTTP remote server that allows DVC clients to push, pull, and fetch data using registered users from the database.

### Features

- **Database Authentication**: Uses registered users and passwords from the database
- **User Isolation**: Each user gets a separate storage directory
- **Multiple Auth Methods**: Database, Basic, Custom header, or No authentication
- **DVC Protocol Support**: Full implementation of DVC's HTTP remote protocol
- **Security**: Path traversal protection, configurable access control

### Configuration

The DVC remote is now configured under unified `dvc` section in `config.yml`:

```yaml
dvc:
  # Common storage configuration
  storage_path: "/opt/dvc_storage"
  
  # Internal DVC operations (existing functionality)
  remote_name: "local_storage"
  uploads_dvc_project: "/opt/dvc_storage/uploads"
  
  # HTTP remote server (new functionality)
  remote_server:
    enabled: true
    auth:
      enabled: true
      method: "database"  # database, basic, custom, none
      database_auth:
        require_admin: false  # Whether only admin users can access DVC remote
        allowed_users: []  # Empty list means all registered users can access
      basic_auth:
        username: "dvc_user"
        password: "dvc_password"
      custom_auth:
        header_name: "X-DVC-Token"
        token: "your-custom-token-here"
    ssl_verify: true
    read_timeout: 300
    connect_timeout: 300
```

### Configuration Benefits

The unified configuration provides several advantages:

- **Single Storage Path**: One `storage_path` setting for all DVC operations
- **Logical Grouping**: All DVC-related settings under one section
- **Easier Maintenance**: Changes affect both internal and remote operations
- **Consistent Behavior**: Both systems use the same storage location
- **Backward Compatibility**: Existing configurations still work during transition

### Setup DVC Remote

1. **Configure DVC to use this server**:
    ```bash
    # Add the remote
    dvc remote add -d myremote http://localhost:7123/dvc
    
    # Configure authentication (for database auth)
    dvc remote modify myremote auth basic
    dvc remote modify myremote user your-email@example.com
    dvc remote modify myremote password your-password
    ```

2. **Test the connection**:
    ```bash
    dvc remote list
    dvc status
    ```

### Authentication Methods

#### Database Authentication (Recommended)

Uses registered users from the database:

```bash
dvc remote add -d myremote http://server:7123/dvc
dvc remote modify myremote auth basic
# DVC will prompt for email and password
```

#### Basic Authentication

Uses hardcoded credentials (for backward compatibility):

```bash
dvc remote add -d myremote http://server:7123/dvc
dvc remote modify myremote auth basic
dvc remote modify myremote user dvc_user
dvc remote modify myremote password dvc_password
```

#### Custom Header Authentication

Uses custom HTTP header:

```bash
dvc remote add -d myremote http://server:7123/dvc
dvc remote modify myremote auth custom
dvc remote modify myremote custom_auth_header X-DVC-Token
dvc remote modify myremote password your-custom-token
```

#### No Authentication

Open access (not recommended for production):

```bash
dvc remote add -d myremote http://server:7123/dvc
dvc remote modify myremote auth none
```

### DVC Remote API Endpoints

The DVC remote server provides the following endpoints under `/dvc/`:

- `GET /dvc/{file_path:path}` - Download DVC files
- `PUT /dvc/{file_path:path}` - Upload DVC files
- `POST /dvc/{file_path:path}` - Upload DVC files (alternative method)
- `HEAD /dvc/{file_path:path}` - Check file existence and metadata
- `GET /dvc/user/info` - Get current authenticated user information

### User Storage Isolation

When using database authentication, each user gets a dedicated storage directory:

```
/opt/dvc_storage/
├── users/
│   ├── a1b2c3d4/    # Hashed user directory 1
│   ├── e5f6g7h8/    # Hashed user directory 2
│   └── i9j0k1l2/    # Hashed user directory 3
└── .gitkeep
```

This ensures that users can only access their own data when using database authentication.

### Security Features

- **Path Traversal Protection**: Prevents access to files outside the storage directory
- **Database Authentication**: Leverages existing user management system
- **Access Control**: Configurable admin-only or specific user access
- **Password Verification**: Uses existing password hashing and verification
- **User Isolation**: Separate storage directories per user

### Usage Examples

#### Push Data to DVC Remote

```bash
# Track a file with DVC
dvc add data/my_dataset.csv

# Push to the remote
dvc push
```

#### Pull Data from DVC Remote

```bash
# Pull all data from remote
dvc pull

# Pull specific file
dvc pull data/my_dataset.csv.dvc
```

#### Check Remote Status

```bash
# Check what files need to be pushed/pulled
dvc status

# List remotes
dvc remote list
```

### Migration from Old Configuration

If you have an existing configuration with separate `dvc_remote` section, the system supports backward compatibility:

1. **Old configuration still works** during transition
2. **New unified configuration takes precedence** when both exist
3. **Migration is automatic** - no manual changes required
4. **Gradual transition** - update at your own pace

To migrate to new unified configuration:

1. **Backup your current config.yml**
2. **Update configuration** to use new unified structure
3. **Test both internal DVC operations** and **remote server functionality**
4. **Remove old `dvc_remote` section** once verified

### Troubleshooting

#### Configuration Issues

1. **Storage path conflicts**: Ensure `dvc.storage_path` is set correctly
2. **Remote server not enabled**: Check `dvc.remote_server.enabled: true`
3. **Authentication method**: Verify `dvc.remote_server.auth.method` is set correctly

#### Configuration Issues

1. **Storage path conflicts**: Ensure `dvc.storage_path` is set correctly
2. **Remote server not enabled**: Check `dvc.remote_server.enabled: true`
3. **Authentication method**: Verify `dvc.remote_server.auth.method` is set correctly

#### Authentication Issues

1. **Invalid credentials**: Ensure you're using the correct email and password
2. **User not authorized**: Check if the user is allowed to access DVC remote in configuration
3. **Admin access required**: If `require_admin` is true, only admin users can access

#### Connection Issues

1. **Server not running**: Ensure the application is running on the correct port
2. **Firewall blocking**: Check firewall settings for port 7123
3. **SSL issues**: If using HTTPS, ensure `ssl_verify` is configured correctly

#### Permission Issues

1. **Storage directory permissions**: Ensure the DVC storage directory is writable
2. **User directory creation**: The system automatically creates user directories on first access

## Project Structure

```
rint-data-manager/
├── config.yml              # Application configuration file (with unified DVC config)
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── database.py          # SQLAlchemy models and DB setup
│   ├── auth.py              # Authentication and JWT handling
│   ├── config.py            # Configuration management (with backward compatibility)
│   ├── dvc_auth.py         # DVC remote authentication (unified config)
│   ├── dvc_service.py      # DVC integration logic (unified config)
│   └── schemas.py           # Pydantic models
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # Authentication endpoints
│       ├── data.py          # Data management endpoints
│       ├── dvc_remote.py   # DVC remote endpoints (unified config)
│       └── admin.py        # Admin endpoints
├── templates/
│   ├── index.html           # Landing page
│   ├── login.html           # Login page
│   ├── register.html        # Registration page
│   └── dashboard.html       # Main dashboard with lineage visualization
├── static/
│   └── style.css            # Custom styles
├── uploads/                 # User upload directory
├── /opt/dvc_storage/        # DVC storage directory (unified)
├── setup_dvc_storage.py    # DVC storage setup script (unified config)
├── main.py                  # Application entry point
└── pyproject.toml           # Project configuration
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login (returns JWT token)

### Data Management
- `POST /api/data/upload` - Upload file with metadata and parent linkage
- `GET /api/data/` - List user's data items
- `GET /api/data/{id}` - Get data item with full lineage information

### Web Pages
- `GET /` - Landing page
- `GET /login` - Login form
- `GET /register` - Registration form
- `GET /dashboard` - Main dashboard with data management

## Lineage Tracking Implementation

The platform implements naive lineage tracking through parent-child relationships:

### How It Works
1. **Parent Link**: When uploading a file, users can specify a parent data item from a dropdown
2. **Database Schema**: `DataItem` model includes `parent_id` foreign key for lineage relationships
3. **Lineage Visualization**: Dashboard modal shows parent and children relationships
4. **DVC Integration**: Each file is tracked with DVC, providing version control alongside lineage

### Usage Example
1. **Register and login** to the platform
2. **Upload a dataset** with name, source, and description
3. **Upload a processed version** of the dataset, selecting the original as parent
4. **View lineage** by clicking "View Lineage" on any data item to see relationships

### Lineage Display
- **Parent Information**: Shows the parent data item if one exists
- **Children Information**: Lists all child data items that reference this item as parent
- **Visual Indication**: Clean modal interface with hierarchical display

## Technology Stack

- **Backend**: FastAPI for REST API
- **Database**: SQLAlchemy ORM with SQLite
- **Authentication**: JWT tokens with password hashing
- **Data Versioning**: DVC (Data Version Control)
- **Frontend**: Bootstrap 5 with custom JavaScript
- **File Storage**: Local filesystem with DVC tracking
- **Package Management**: uv for Python dependencies

## Key Components

### Database Models
- **User**: Email, password hash, admin status, avatar
- **DataItem**: Name, description, source, file path, DVC path, parent_id, user_id
- **UploadLog**: Action tracking for audit purposes

### DVC Integration
- Automatic DVC repository initialization
- File tracking with `dvc add` and `dvc push`
- Local storage backend configuration
- Error handling for DVC operations

### Security Features
- Password hashing with bcrypt
- JWT token authentication
- CORS middleware configuration
- User-specific data isolation

## Configuration

The application uses `config.yml` for centralized configuration management. All hardcoded values have been moved to this file for easy customization.

### Configuration Sections

#### Server Configuration
- **Host**: `0.0.0.0` (binds to all interfaces)
- **Port**: `8000` (default HTTP port)
- **Debug**: `true` (development mode)
- **Reload**: `true` (auto-reload on code changes)

#### Database Configuration
- **URL**: `sqlite:///rint_data_manager.db` (SQLite database file)
- **Echo**: `false` (SQL query logging)

#### DVC Configuration
- **Storage Path**: `/opt/dvc_storage` (DVC storage directory)
- **Remote Name**: `local_storage` (DVC remote identifier)

#### Upload Configuration
- **Directory**: `uploads/` (user upload directory)
- **Max File Size**: `100MB` (maximum upload size)
- **Allowed Extensions**: Common data file formats

#### Authentication Configuration
- **JWT Secret Key**: Change in production
- **JWT Algorithm**: `HS256`
- **JWT Expiration**: 24 hours
- **Password Min Length**: 8 characters

#### CORS Configuration
- **Allowed Origins**: Local development URLs
- **Allowed Methods**: Standard HTTP methods
- **Allowed Headers**: All headers

#### Logging Configuration
- **Level**: `INFO`
- **Format**: Standard logging format
- **File**: `app.log`

