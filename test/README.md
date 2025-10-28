# Test Client Container

This directory contains a Docker Compose setup for creating a standalone client container that can connect to a development server running on the `10.160.43.0/24` network.

## Purpose

This test client allows you to:
- Test the rint-data-manager server functionality in a development environment
- Verify `git commit` and `dvc push` operations work correctly
- Simulate multiple users (alice, bob) working with the system
- Debug and validate server endpoints without affecting production

## Prerequisites

1. Development server running on `10.160.43.x` network (default: `10.160.43.82:8383`)
2. Docker and Docker Compose installed
3. Access to the development network
4. **sqlite3** installed (required for cleanup script)

### Installing sqlite3

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install sqlite3
```

**CentOS/RHEL:**
```bash
sudo yum install sqlite3
```

**macOS:**
```bash
brew install sqlite3
```

## Setup

1. **Update the development server IP** in `.env`:
   ```bash
   # Edit .env file
   vim .env
   
   # Set your actual dev server IP
   DEV_SERVER_IP=10.160.43.82
   
   # Optional: Skip DVC setup (default: yes)
   SETUP_DVC=no
   ```

2. **Build and start the container**:
   ```bash
   docker-compose up -d
   ```

## Usage

### Test as Alice

```bash
docker compose exec -w /home/alice/demo-project test_client sudo -u alice bash  # as the tester

# Generate test data (100 records)
python src/data_generator.py --records 100 --dataset customers

# Add data to DVC tracking
dvc add data/customers.csv

# Commit changes to Git
git add data/customers.csv.dvc .gitignore
git commit -m "Add customer dataset"

# Push to development server
dvc push
```

### Test as Bob

```bash
docker compose exec -w /home/bob/data-analysis test_client sudo -u bob bash

# Generate sales data
python src/data_generator.py --records 200 --dataset sales

# Track with DVC
dvc add data/sales.csv

# Commit and push
git add data/sales.csv.dvc .gitignore
git commit -m "Add sales dataset"
dvc push
```

### Verify Server Functionality

1. **Check data upload**: Verify that files appear in the development server's storage
2. **Check metadata**: Verify that metadata is properly recorded in the database
3. **Test authentication**: Verify that user authentication works correctly
4. **Test hooks**: Verify that git hooks properly communicate with the server

## Container Details

### Users

- **alice**: Password `alice123`, email `alice@hillstonenet.com`
- **bob**: Password `bob123`, email `bob@hillstonenet.com`

### Projects

- **alice/demo-project**: Contains data generation scripts
- **bob/data-analysis**: Data analysis project setup

### Network Configuration

- Uses `network_mode: host` for direct access to development network
- Can access servers on `10.160.43.0/24` network
- No proxy interference with local network access

### Environment Variables

- **DEV_SERVER_IP**: Development server IP address (default: `10.160.43.100`)
- **DEV_SERVER_PORT**: Development server port (default: `8383`)
- **SETUP_DVC**: Whether to run DVC setup automatically (default: `yes`, set to `no` to skip)

### DVC Configuration

Each user's DVC is configured to point to:
```
http://<DEV_SERVER_IP>:8383/dvc
```

With basic authentication using:
- Username: `<user>@hillstonenet.com`
- Password: `<user>123`

## Troubleshooting

### Connection Issues

1. **Verify server IP**: Ensure `DEV_SERVER_IP` in `.env` matches your development server
2. **Check network**: Ensure the container can reach the development server:
   ```bash
   docker exec rdm-test-client ping 10.160.43.82
   ```
3. **Check server status**: Verify the development server is running and accessible

### DVC Issues

1. **Reconfigure DVC**: If server IP changes, re-run the setup script
2. **Check DVC config**: Verify DVC remote configuration:
   ```bash
   su - alice
   cd demo-project
   dvc remote list
   dvc remote modify myremote url http://<NEW_IP>:8383/dvc
   ```

### Git Hook Issues

1. **Update hooks manually**: If hooks don't work, update them:
   ```bash
   # In each project directory
   sed -i 's|http://server:8383|http://<NEW_IP>:8383|g' .git/hooks/post-commit
   sed -i 's|http://server:8383|http://<NEW_IP>:8383|g' .git/hooks/pre-push
   ```

## Cleanup

### Quick Cleanup

```bash
# Stop and remove container
docker-compose down

# Remove volume (optional - deletes all user data)
docker volume rm rint-data-manager_test_client_data
```

### Full Environment Reset

For a complete clean slate (removes container, image, database data, and file storage except users):

```bash
# Full cleanup with confirmation
./cleanup.sh

# Preview what would be deleted
./cleanup.sh --dry-run

# Full cleanup without confirmation
./cleanup.sh --force
```

The cleanup script will:
- Remove the test client container and Docker image
- Clean the `test_client_data` volume
- Delete all records from database tables (`data_items`, `uploaded_metadata`, `upload_logs`)
- Remove file storage directories (`dvc_storage` and `/tmp/rdm/uploads`)
- **Preserve the `users` table** so you don't need to re-register

**Note**: The cleanup script requires `sqlite3` to be installed (see Prerequisites above).

## Development Workflow

1. Make changes to the server code
2. Restart the development server
3. Use this test client to verify functionality
4. Check logs and debug issues
5. Use `./cleanup.sh` to reset the test environment
6. Repeat until features work correctly

This isolated test environment ensures you can thoroughly test server functionality without affecting production data or configurations.
