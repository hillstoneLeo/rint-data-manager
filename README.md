# RINT Data Sharing Platform

A DVC-based platform for data collection and sharing with naive lineage tracking visualization.

## Features

- **User Management**: Registration, login, and JWT-based authentication
- **Data Upload**: File/folder upload with metadata (name, source, description)
- **DVC Integration**: Automatic DVC tracking for uploaded files
- **DVC HTTP Remote**: Full DVC remote server with database authentication
- **Lineage Tracking**: Parent-child relationships between data items with visualization
- **Web Interface**: Clean, responsive UI for data management
- **Environment-Based Configuration**: Runtime configuration with environment variable overrides

## Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd rint-data-manager
```

### 2. Configure Environment
Copy and edit the environment file:
```bash
cp .env.example .env
# Edit .env with your settings
```

Key environment variables:
```bash
# Server Configuration
RINT_SERVER_PORT=8000
RINT_SERVER_HOST=0.0.0.0

# Database Configuration
RINT_DATABASE_URL=sqlite:///rint_data_manager.db

# DVC Configuration
RINT_DVC_STORAGE_PATH=dvc_storage

# Docker/Deployment Configuration
SERVER_PORT=8000
SERVER_IP=127.0.0.1
PROXY_IP=
PROXY_PORT=
DOCKER_CLIENT_A_SSH_PORT=2222
DOCKER_CLIENT_B_SSH_PORT=2223
```

### 3. Create Required Directories
```bash
mkdir -p dvc_storage log
```

### 4. Storage Requirements

**Important**: DVC storage is always located in the `dvc_storage` folder within the project directory. 

#### Disk Space Considerations:
- **Location**: `./dvc_storage` (project root)
- **Growth**: Storage grows as users upload files through the application
- **Capacity**: Plan for future growth based on expected usage
- **Management**: Administrators are responsible for monitoring and managing disk space

#### Deployment Recommendations:
1. **Deploy on Large Partition**: Ensure the project is deployed on a disk partition with sufficient space (e.g., 10TB+ for production)
2. **Monitor Usage**: Regularly check disk usage in the `dvc_storage` directory
3. **Backup Strategy**: Implement regular backups of the `dvc_storage` folder
4. **Cleanup Policies**: Consider implementing automated cleanup for old/unused files

#### Example Large Storage Setup:
```bash
# Deploy to a large storage partition
sudo mount /dev/sdb1 /mnt/large-storage
cd /mnt/large-storage
git clone <repository-url> rint-data-manager
cd rint-data-manager
cp .env.example .env
# Edit .env with your settings
mkdir -p dvc_storage log
```

### 5. Start Application

#### In Python Virtual Environment

```bash
uv run main.py
```

#### In Docker containers

Setup demo environment and start containers:
```bash
docker compose -f deployment/docker-compose.yml up [-d]  # or:
podman-compose -f deployment/docker-compose.yml up [-d]
```

Clear demo environment:
```bash
docker compose -f deployment/docker-compose.yml down --rmi all --volumes --remove-orphans
sudo rm -rf dvc_storage/
```

### 4. Access Application
Open http://localhost:8000 in your browser (or your configured port)

## Configuration System

This project uses environment-based configuration with runtime overrides:

- **Base Configuration**: `config.yml` (version-controlled)
- **Environment Overrides**: `RINT_*` environment variables
- **Docker Variables**: Standard deployment variables

### Environment Variable Pattern

All configuration values can be overridden using environment variables:
- Pattern: `RINT_SECTION_KEY` (e.g., `RINT_SERVER_PORT`, `RINT_DATABASE_URL`)
- Priority: Environment variables > config.yml > defaults
- Types: Automatic conversion for strings, integers, booleans, lists

### Moving to New Host

1. Edit `.env` with new IP/port values
2. Set environment variables as needed
3. Start services

No template regeneration required!

## Storage Management

### Monitoring Disk Usage
```bash
# Check DVC storage size
du -sh dvc_storage/

# Monitor disk usage
df -h

# Find large files in DVC storage
find dvc_storage/ -type f -size +100M -exec ls -lh {} \;
```

### Backup Strategies
```bash
# Backup DVC storage
tar -czf dvc_storage_backup_$(date +%Y%m%d).tar.gz dvc_storage/

# Sync to remote storage
rsync -av dvc_storage/ user@backup-server:/backup/dvc_storage/
```

### Cleanup Operations
```bash
# DVC garbage collection (removes unused cache)
dvc gc -c

# Clean old files (example: files older than 30 days)
find dvc_storage/ -type f -mtime +30 -delete
```

## DVC Remote Server

Full-featured DVC HTTP remote server with database authentication.

### Setup DVC Remote
```bash
# Add remote (use your configured port)
dvc remote add -d myremote http://server:8000/dvc

# Configure authentication
dvc remote modify myremote auth basic
dvc remote modify myremote user your-email@example.com
dvc remote modify myremote password your-password
```

### Authentication Methods
- **Database**: Uses registered users (recommended)
- **Basic**: Hardcoded credentials
- **Custom**: HTTP header authentication
- **None**: Open access

## Project Structure

```
rint-data-manager/
├── .env.example           # Environment variables template
├── .env                   # Environment configuration (git-ignored)
├── config.yml             # Application configuration
├── main.py                # Application entry point
├── backend/              # FastAPI backend
├── templates/            # HTML templates
├── static/              # CSS/JS files
├── dvc_storage/          # DVC data storage (git-ignored)
├── log/                  # Application logs (git-ignored)
└── deployment/          # Docker configurations
    ├── docker-compose.yml
    ├── Dockerfile.server
    └── Dockerfile.client
```

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite
- **Authentication**: JWT tokens, bcrypt
- **Data Versioning**: DVC (Data Version Control)
- **Frontend**: Bootstrap 5, JavaScript
- **Package Management**: uv

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login

### Data Management
- `POST /api/data/upload` - Upload file with metadata
- `GET /api/data/` - List user's data items
- `GET /api/data/{id}` - Get data item with lineage

### DVC Remote
- `GET /dvc/{file_path}` - Download DVC files
- `PUT /dvc/{file_path}` - Upload DVC files
- `HEAD /dvc/{file_path}` - Check file existence

## Lineage Tracking

Track parent-child relationships between data items:

1. Upload a dataset with metadata
2. Upload processed version, selecting original as parent
3. View lineage relationships in dashboard

## Troubleshooting

### Setup Issues
- Ensure `.env` file exists and is properly formatted
- Check all required environment variables are set
- Verify `config.yml` exists in repository

### Port Conflicts
- Ensure specified ports are available on host
- Check firewall settings
- Verify no other services use same ports
- Use `RINT_SERVER_PORT` environment variable to change port

### Docker Issues
- Ensure Docker is installed and running
- Check Docker daemon status
- Verify Docker Compose is installed

## Environment Variables

### Application Configuration (RINT_*)
| Variable | Description | Default |
|----------|-------------|---------|
| `RINT_SERVER_HOST` | Server bind address | 0.0.0.0 |
| `RINT_SERVER_PORT` | Server port | 8000 |
| `RINT_SERVER_DEBUG` | Enable debug mode | true |
| `RINT_DATABASE_URL` | Database connection URL | sqlite:///rint_data_manager.db |
| `RINT_DVC_STORAGE_PATH` | DVC storage directory | dvc_storage |
| `RINT_AUTH_JWT_SECRET_KEY` | JWT signing secret | your-secret-key-here |
| `RINT_LOGGING_LEVEL` | Logging level | INFO |

### Docker/Deployment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `SERVER_PORT` | Docker exposed port | 8000 |
| `SERVER_IP` | Server IP for clients | 127.0.0.1 |
| `PROXY_IP` | Proxy server IP | (empty) |
| `PROXY_PORT` | Proxy server port | (empty) |
| `DOCKER_CLIENT_A_SSH_PORT` | Client A SSH port | 2222 |
| `DOCKER_CLIENT_B_SSH_PORT` | Client B SSH port | 2223 |

**Note**: See `.env.example` for the complete list of configurable variables. DVC storage is always located in `./dvc_storage` within the project directory. Ensure the project is deployed on a disk partition with sufficient space for your expected data volume.
