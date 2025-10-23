# Rint Data Manager - Deployment Options

This document provides multiple deployment options for the Rint Data Manager platform.

## Option 1: Docker Demo Environment

This demo environment showcases the Rint Data Manager platform using Docker containers. It includes a server container running the Rint Data Manager application and two client containers with pre-configured users and DVC setup.

## Architecture

The demo environment consists of three containers:

1. **Server Container** (`rint-server`): Runs the Rint Data Manager web application
2. **Client A Container** (`rint-client-a`): Contains users `alice` and `bob`
3. **Client B Container** (`rint-client-b`): Contains user `cindy`

All containers share a common network and DVC storage volume for seamless data management.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- At least 4GB of available memory
- Port 8383 available on host machine

### Setup

1. Navigate to the test directory:
   ```bash
   cd test
   ```

2. Build and start all containers:
   ```bash
   docker-compose up --build
   ```

3. Wait for all containers to start (this may take a few minutes)

### Access the Application

- **Web UI**: Open http://localhost:8383 in your browser
- **Client A SSH**: `ssh alice@localhost -p 2222` (password: `alice123`)
- **Client B SSH**: `ssh cindy@localhost -p 2223` (password: `cindy123`)

## User Accounts

### Web UI Users
Register and login with these credentials:

| Username | Password | Container |
|----------|----------|-----------|
| alice    | alice123 | Client A  |
| bob      | bob123   | Client A  |
| cindy    | cindy123 | Client B  |

### System Users (SSH Access)
| Username | Password | Container | SSH Port |
|----------|----------|-----------|----------|
| alice    | alice123 | Client A  | 2222     |
| bob      | bob123   | Client A  | 2222     |
| cindy    | cindy123 | Client B  | 2223     |

## Features Demonstrated

### 1. Web Interface
- User registration and authentication
- File upload and management
- Data visualization dashboard
- Admin interface for data management

### 2. DVC Integration
- Pre-installed DVC client in all containers
- Automatic git hooks for metadata upload
- HTTP remote storage pointing to Rint Data Manager server
- Sample projects with DVC tracking

### 3. Automated Workflows
- Git hooks automatically upload DVC metadata to the server
- Post-commit hook: Uploads all .dvc files after every commit
- Pre-push hook: Uploads only .dvc files being pushed (more efficient)

## Demo Workflow

### Step 1: Web Interface Demo
1. Open http://localhost:8383
2. Register as `alice` with password `alice123`
3. Login and upload some data files
4. Explore the dashboard and admin interface

### Step 2: Client Container Demo
1. Access Client A container:
   ```bash
   cd test && docker compose exec client_a sudo -u alice bash
   ```

2. Navigate to alice's demo project:
   ```bash
   cd /home/alice/demo-project
   ```

3. Explore the existing DVC project:
   ```bash
   ls -la
   dvc status
   git log --oneline
   ```

4. Create new data and add to DVC:
   ```bash
   echo "new data content" > new_file.txt
   dvc add new_file.txt
   git add .
   git commit -m "Add new data file"
   ```
   *The git hook will automatically upload metadata to the server*

### Step 3: Multi-User Collaboration
1. SSH as `bob` in Client A:
   ```bash
   ssh bob@localhost -p 2222
   # Password: bob123
   ```

2. Navigate to bob's project:
   ```bash
   cd /home/bob/data-analysis
   ```

3. Create and track data:
   ```bash
   echo "bob's analysis data" > analysis_results.csv
   dvc add analysis_results.csv
   git add .
   git commit -m "Add analysis results"
   ```

4. SSH as `cindy` in Client B:
   ```bash
   ssh cindy@localhost -p 2223
   # Password: cindy123
   ```

5. Work on ML experiment:
   ```bash
   cd /home/cindy/ml-experiment
   echo "ml experiment data" > experiment.json
   dvc add experiment.json
   git add .
   git commit -m "Add ML experiment data"
   ```

### Step 4: Verify Integration
1. Check the web UI to see all uploaded metadata
2. Verify that DVC files from all users are tracked
3. Check the admin interface for data management

## Container Details

### Server Container
- **Image**: Built from `Dockerfile.server`
- **Port**: 8383 (mapped to host)
- **Volumes**: 
  - `server_data`: Upload directory
  - `dvc_storage`: Shared DVC storage
- **Environment**: Database configuration

### Client Containers
- **Image**: Built from `Dockerfile.client`
- **Features**:
  - Pre-installed DVC with all dependencies
  - Git hooks automatically configured
  - System users with sudo access
  - SSH service for remote access
  - Shared DVC storage mount

### Volume Structure
```
dvc_storage/          # Server DVC storage (managed by Rint Data Manager)
├── cache/             # DVC cache directory
│   └── files/         # Actual data files stored by MD5 hash
│       └── md5/       # Files organized by content hash
├── config             # DVC configuration files
└── .dvc               # DVC metadata

server_data/          # Server upload directory
└── uploads/          # User file uploads

client_a_data/        # Client A workspace
├── alice/            # Alice's projects (with .dvc files)
└── bob/              # Bob's projects (with .dvc files)

client_b_data/        # Client B workspace
└── cindy/            # Cindy's projects (with .dvc files)
```

**Note**: DVC uses HTTP remote storage pointing to `http://server:8383/dvc`. This means:
- All DVC data is stored and managed by the Rint Data Manager server in `/opt/dvc_storage`
- User separation is maintained through DVC metadata (.dvc files) in each project
- No shared storage volume is needed between containers - clients communicate with server via HTTP
- The server maintains its own DVC storage for handling client uploads and data management
- DVC hooks automatically upload .dvc metadata files to the server after git commits

## Development and Testing

### Running the Demo
```bash
# Start all containers
docker-compose up --build

# Wait for containers to fully start (check logs with: docker-compose logs -f server)

# Setup demo environment (creates sample projects and configures DVC)
docker-compose exec client_a bash -c "CONTAINER_TYPE=client_a sudo -u alice /home/alice/setup-demo.sh"
docker-compose exec client_a bash -c "CONTAINER_TYPE=client_a sudo -u bob /home/bob/setup-demo.sh"
docker-compose exec client_b bash -c "CONTAINER_TYPE=client_b sudo -u cindy /home/cindy/setup-demo.sh"

# Run demo script in client containers
docker-compose exec client_a sudo -u alice bash /home/alice/demo.sh
docker-compose exec client_a sudo -u bob bash /home/bob/demo.sh
docker-compose exec client_b sudo -u cindy bash /home/cindy/demo.sh

# View logs
docker-compose logs -f server
docker-compose logs -f client_a
docker-compose logs -f client_b
```

**Note**: The `setup-demo.sh` script must be run before `demo.sh` as it:
- Creates user workspaces and sample projects
- Initializes git repositories and DVC configuration
- Sets up DVC remote storage pointing to shared `/opt/dvc_storage`
- Installs git hooks for automatic metadata upload
- Creates sample data files and adds them to DVC

### Customization
- Modify `docker-compose.yml` to change port mappings
- Update `Dockerfile.client` to add additional tools
- Edit `setup-demo.sh` to create different sample projects or users
- Modify `demo.sh` to change the demo workflow
- Modify git hooks in `collect-metadata/` directory

### Troubleshooting
1. **Port conflicts**: Ensure ports 8383, 2222, and 2223 are available
2. **Permission issues**: Check volume permissions if containers fail to start
3. **Network issues**: Verify all containers are on the same network
4. **DVC storage**: Ensure shared volume has proper permissions

## File Structure

```
test/
├── Dockerfile.server          # Server container build file
├── Dockerfile.client          # Client container build file
├── docker-compose.yml         # Container orchestration
├── setup-demo.sh             # Demo environment setup script
├── demo.sh                   # Demo execution script
└── README.md                 # This file
```

**Script Overview:**
- `setup-demo.sh`: Creates sample projects, initializes DVC, and configures shared storage
- `demo.sh`: Demonstrates the complete workflow with sample operations

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite
- **Frontend**: HTML, CSS, JavaScript
- **Data Management**: DVC (Data Version Control)
- **Containerization**: Docker, Docker Compose
- **Version Control**: Git with custom hooks
- **Authentication**: JWT tokens, bcrypt passwords

## Security Notes

This demo environment uses default credentials for demonstration purposes. In production:

- Change all default passwords
- Use environment variables for sensitive configuration
- Implement proper SSL/TLS encryption
- Restrict network access as needed
- Use proper user authentication and authorization

## Support

For issues or questions about this demo environment, please refer to the main project documentation or create an issue in the project repository.

---

## Option 2: Systemd Service Deployment

This deployment method runs the Rint Data Manager as a systemd service, providing automatic startup on boot and process restart capabilities.

### Prerequisites

- Python 3.13+ with uv installed
- systemd (available on most Linux distributions)
- Appropriate system permissions to create and manage services

### Setup

1. **Copy the service file**:
   ```bash
   sudo cp deployment/rint-data-manager.service /etc/systemd/system/
   ```

2. **Customize the service file** (if needed):
   Edit `/etc/systemd/system/rint-data-manager.service` to modify:
   - `User`: Change to the user that should run the service
   - `WorkingDirectory`: Update to your project path
   - `Environment`: Adjust PATH if uv is installed elsewhere
   - `ExecStart`: Modify if using different startup command

3. **Reload systemd and enable the service**:
   ```bash
   # Reload systemd to recognize the new service
   sudo systemctl daemon-reload
   
   # Enable the service to start on boot
   sudo systemctl enable rint-data-manager
   
   # Start the service now
   sudo systemctl start rint-data-manager
   ```

### Service Management

```bash
# Check service status
sudo systemctl status rint-data-manager

# View real-time logs (recommended)
sudo journalctl -u rint-data-manager -f

# View recent logs (last 100 lines)
sudo journalctl -u rint-data-manager -n 100

# View logs since service start
sudo journalctl -u rint-data-manager -b

# View logs with timestamps
sudo journalctl -u rint-data-manager -o short-iso

# Restart the service
sudo systemctl restart rint-data-manager

# Stop the service
sudo systemctl stop rint-data-manager

# Disable automatic startup on boot
sudo systemctl disable rint-data-manager
```

### Log Monitoring

**Recommended: Use `journalctl`**

For systemd services, `journalctl` is the recommended way to watch logs:

```bash
# Follow real-time logs
sudo journalctl -u rint-data-manager -f

# View logs with specific priority
sudo journalctl -u rint-data-manager -p err -f  # Errors only
sudo journalctl -u rint-data-manager -p warning -f  # Warnings and above

# View logs from specific time
sudo journalctl -u rint-data-manager --since "1 hour ago"
sudo journalctl -u rint-data-manager --since "2025-01-01" --until "2025-01-02"
```

**Why `journalctl` over `tail -f ./log/xxx`:**

- **Centralized**: All service logs in one place
- **Structured**: Proper log levels and metadata
- **Persistent**: Survives service restarts
- **Searchable**: Filter by time, priority, etc.
- **Standard**: Works consistently across all systemd services

**Note**: The service is configured to send both stdout and stderr to the systemd journal. While your application may also write to log files, `journalctl` provides the most reliable and complete view of service activity.

### Service Features

- **Automatic Restart**: The service will automatically restart if the process is killed or crashes
- **Boot Startup**: Configured to start automatically when the system boots
- **Logging**: Uses systemd journal for centralized logging
- **Process Management**: Managed by systemd with proper resource limits

### Configuration

The service file includes these key settings:

- `Type=simple`: Standard service type
- `Restart=always`: Always restart on failure
- `RestartSec=10`: Wait 10 seconds before restarting
- `StandardOutput=journal`: Send output to systemd journal
- `StandardError=journal`: Send errors to systemd journal

### Troubleshooting

1. **Service fails to start**:
   ```bash
   sudo journalctl -u rint-data-manager -n 50
   ```

2. **Permission issues**:
   - Ensure the specified user has read/write access to the project directory
   - Check that uv is accessible in the specified PATH

3. **Port conflicts**:
   - The service defaults to port 8000 (configurable in your application config)
   - Ensure the port is not already in use

4. **Environment variables**:
   - Add any required environment variables to the service file using `Environment=` lines

### Advantages of Systemd Deployment

- **Production Ready**: Suitable for production environments
- **Resource Management**: systemd handles process limits and resource allocation
- **Integration**: Integrates well with system monitoring and logging tools
- **Reliability**: Automatic restart and health monitoring
- **Performance**: Direct execution without container overhead

### Migration from Docker

If you're migrating from the Docker deployment:

1. Ensure all dependencies are installed on the host system
2. Copy any configuration files from the Docker container
3. Update database connection strings if needed
4. Verify file permissions and paths
5. Test the service before switching production traffic