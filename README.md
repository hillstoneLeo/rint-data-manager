# RINT Data Manager

A DVC-based platform for data collection and sharing with naive lineage tracking visualization.

## Features

- **User Management**: Registration, login, and JWT-based authentication
- **Data Upload**: File/folder upload with metadata (name, source, description)
- **DVC Integration**: Automatic DVC tracking for uploaded files
- **Lineage Tracking**: Parent-child relationships between data items with naive visualization
- **Web Interface**: Clean, responsive UI for data management
- **SQLite Database**: User data and metadata storage
- **REST API**: Full backend API for all operations

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Create DVC storage directory**:
   ```bash
   sudo mkdir /opt/dvc_storage
   sudo chown $USER:$USER /opt/dvc_storage
   mkdir /opt/dvc_storage/uploads  # defined in config.yml
   cd /opt/dvc_storage/uploads
   git init
   dvc init
   ```

3. **Review and update configuration**:
   ```bash
   # Edit config.yml to customize settings as needed
   nano config.yml
   ```

4. **Run the application**:
   ```bash
   uv run main.py
   ```

5. **Access the application**:
   - Open http://localhost:8000 in your browser
   - Register a new account
   - Upload data files with lineage information

## Project Structure

```
rint-data-manager/
├── config.yml              # Application configuration file
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── database.py          # SQLAlchemy models and DB setup
│   ├── auth.py              # Authentication and JWT handling
│   ├── schemas.py           # Pydantic models
│   ├── dvc_service.py       # DVC integration logic
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # Authentication endpoints
│       └── data.py          # Data management endpoints
├── templates/
│   ├── index.html           # Landing page
│   ├── login.html           # Login page
│   ├── register.html        # Registration page
│   └── dashboard.html       # Main dashboard with lineage visualization
├── static/
│   └── style.css            # Custom styles
├── uploads/                 # User upload directory
├── /opt/dvc_storage/        # DVC storage directory
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

### Benefits of Centralized Configuration

- **Easy Customization**: All settings in one file
- **Environment-Specific Settings**: Different configs for dev/prod
- **No Hardcoded Values**: All configuration values are externalized
- **Version Control Friendly**: Config can be committed or excluded as needed
- **Runtime Changes**: Configuration can be changed without code modifications

## Development Notes

- Import errors in IDE are expected (virtual environment not activated in current shell)
- Application runs correctly when executed with proper Python environment
- DVC operations are handled automatically during file upload
- Lineage tracking is implemented as requested with naive parent-child relationships
- Ready for production deployment with proper secret key configuration
