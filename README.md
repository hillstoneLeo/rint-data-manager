# RINT Data Sharing Platform

A DVC-based platform for data collection and sharing with naive lineage tracking visualization.

## Features

- **User Management**: Registration, login, and JWT-based authentication
- **Data Upload**: File/folder upload with metadata (name, source, description)
- **DVC Integration**: Automatic DVC tracking for uploaded files
- **DVC HTTP Remote**: Full DVC remote server with database authentication
- **Lineage Tracking**: Parent-child relationships between data items with visualization
- **Web Interface**: Clean, responsive UI for data management
- **Template-Based Configuration**: Easy deployment across different environments

## Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd rint-data-manager
```

### 2. Configure Environment
Edit `.env` file with your settings:
```bash
# Server Configuration
SERVER_IP=10.160.43.83
SERVER_PORT=8383

# Proxy Configuration
PROXY_IP=10.160.43.82
PROXY_PORT=7897

# Docker Configuration
DOCKER_SERVER_PORT=8383
DOCKER_CLIENT_A_SSH_PORT=2222
DOCKER_CLIENT_B_SSH_PORT=2223
```

### 3. Generate Configuration Files
```bash
./setup.sh
```

### 4. Start Application
```bash
# Option 1: Direct run
uv run main.py

# Option 2: Docker containers
cd deployment && docker-compose up -d
```

### 5. Access Application
Open http://localhost:8383 in your browser

## Configuration System

This project uses a template-based configuration system:

- **Templates** (version-controlled): `*.template` files
- **Generated files** (git-ignored): Actual configuration files
- **Single source**: Only `.env` file needs editing

### Moving to New Host

1. Edit `.env` with new IP/port values
2. Run `./setup.sh` to regenerate all files
3. Start services

No manual file editing required!

## DVC Remote Server

Full-featured DVC HTTP remote server with database authentication.

### Setup DVC Remote
```bash
# Add remote
dvc remote add -d myremote http://server:8383/dvc

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
├── .env                    # Environment configuration
├── setup.sh                # Configuration generator
├── config.yml.template     # Application config template
├── main.py                 # Application entry point
├── backend/               # FastAPI backend
├── templates/             # HTML templates
├── static/               # CSS/JS files
└── deployment/           # Docker configurations
    ├── docker-compose.yml.template
    ├── Dockerfile.server.template
    └── Dockerfile.client.template
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
- Verify template files exist in repository

### Port Conflicts
- Ensure specified ports are available on host
- Check firewall settings
- Verify no other services use same ports

### Docker Issues
- Ensure Docker is installed and running
- Check Docker daemon status
- Verify Docker Compose is installed

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVER_IP` | Server public IP | 10.160.43.83 |
| `SERVER_PORT` | Server port | 8383 |
| `PROXY_IP` | Proxy server IP | 10.160.43.82 |
| `PROXY_PORT` | Proxy server port | 7897 |
| `DOCKER_SERVER_PORT` | Docker server port | 8383 |
| `DOCKER_CLIENT_A_SSH_PORT` | Client A SSH port | 2222 |
| `DOCKER_CLIENT_B_SSH_PORT` | Client B SSH port | 2223 |
