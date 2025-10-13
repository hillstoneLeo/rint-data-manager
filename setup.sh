#!/bin/bash
# Setup script to generate configuration files from templates

set -e

echo "=== RINT Data Manager Configuration Setup ==="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please create it first."
    echo "Example .env file:"
    echo "SERVER_IP=10.160.43.83"
    echo "SERVER_PORT=8383"
    echo "PROXY_IP=10.160.43.82"
    echo "PROXY_PORT=7897"
    echo "DOCKER_CLIENT_A_SSH_PORT=2222"
    echo "DOCKER_CLIENT_B_SSH_PORT=2223"
    exit 1
fi

# Source environment variables
source .env

echo "Using configuration:"
echo "  Server IP: ${SERVER_IP}"
echo "  Server Port: ${SERVER_PORT}"
echo "  Proxy IP: ${PROXY_IP}"
echo "  Proxy Port: ${PROXY_PORT}"
echo "  Docker Client A SSH Port: ${DOCKER_CLIENT_A_SSH_PORT}"
echo "  Docker Client B SSH Port: ${DOCKER_CLIENT_B_SSH_PORT}"
echo ""

# Copy UV binary to data directory
echo "--- Preparing UV binary ---"
UV_SOURCE_PATH="${HOME}/.local/bin/uv"
UV_DEST_PATH="data/uv"

# Create data directory if it doesn't exist
mkdir -p data

if [ ! -f "$UV_SOURCE_PATH" ]; then
    echo "Error: UV binary not found at $UV_SOURCE_PATH"
    echo "Please install UV first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "Copying UV binary from $UV_SOURCE_PATH to $UV_DEST_PATH..."
if ! cp "$UV_SOURCE_PATH" "$UV_DEST_PATH"; then
    echo "Error: Failed to copy UV binary to data directory"
    exit 1
fi

echo "✓ UV binary copied successfully"
echo ""

# Create DVC storage directory
echo "--- Preparing DVC Storage Directory ---"
DVC_STORAGE_DIR="./dvc_storage"

# Create directory if it doesn't exist
mkdir -p "$DVC_STORAGE_DIR"

if [ ! -d "$DVC_STORAGE_DIR" ]; then
    echo "Error: Failed to create DVC storage directory at $DVC_STORAGE_DIR"
    exit 1
fi

echo "✓ DVC storage directory created/verified at $DVC_STORAGE_DIR"
echo ""

# Function to check Python version compatibility
check_python_version_compatibility() {
    echo "--- Checking Python Version Compatibility ---"
    
    # Extract Python version from pyproject.toml
    local pyproject_python=$(grep "requires-python" pyproject.toml | sed 's/.*"\(.*\)".*/\1/' | sed 's/>=//')
    
    # Extract Python version from Dockerfile.server.template
    local server_python=$(grep "FROM python:" deployment/Dockerfile.server.template | sed 's/.*python:\([0-9.]*\)-.*/\1/')
    
    # Extract Python version from Dockerfile.client.template  
    local client_python=$(grep "FROM python:" deployment/Dockerfile.client.template | sed 's/.*python:\([0-9.]*\)-.*/\1/')
    
    echo "  pyproject.toml requires Python: $pyproject_python"
    echo "  Dockerfile.server uses Python: $server_python"
    echo "  Dockerfile.client uses Python: $client_python"
    
    # Check compatibility using version comparison
    if ! printf '%s\n' "$pyproject_python" "$server_python" | sort -V | head -n1 | grep -q "^$pyproject_python$"; then
        echo "Error: Python version mismatch detected!"
        echo "Dockerfile.server uses Python $server_python but pyproject.toml requires >= $pyproject_python"
        echo "Please update either:"
        echo "  - pyproject.toml: requires-python = \">=$server_python\""
        echo "  - deployment/Dockerfile.server.template: FROM python:$pyproject_python-slim"
        exit 1
    fi
    
    if ! printf '%s\n' "$pyproject_python" "$client_python" | sort -V | head -n1 | grep -q "^$pyproject_python$"; then
        echo "Error: Python version mismatch detected!"
        echo "Dockerfile.client uses Python $client_python but pyproject.toml requires >= $pyproject_python"
        echo "Please update either:"
        echo "  - pyproject.toml: requires-python = \">=$client_python\""
        echo "  - deployment/Dockerfile.client.template: FROM python:$pyproject_python-slim"
        exit 1
    fi
    
    echo "✓ Python versions are compatible"
    echo ""
}

# Check Python version compatibility
check_python_version_compatibility

# Function to update file from template with specific replacements
update_file_from_template() {
    local template=$1
    local output=$2
    
    if [ -f "$template" ]; then
        echo "Generating $output from $template..."
        # Create backup if output exists
        if [ -f "$output" ]; then
            mkdir -p /tmp/rint-backups
            cp "$output" "/tmp/rint-backups/$(basename "$output").backup"
        fi
        
        # Copy template to output
        cp "$template" "$output"
        
        # Apply specific replacements based on file type
        case "$output" in
            "config.yml")
                sed -i "s|\${SERVER_PORT}|${SERVER_PORT}|g" "$output"
                sed -i "s|\${SERVER_IP}|${SERVER_IP}|g" "$output"
                ;;
            "deployment/docker-compose.yml")
                sed -i "s|\${SERVER_PORT}|${SERVER_PORT}|g" "$output"
                sed -i "s|\${DOCKER_CLIENT_A_SSH_PORT}|${DOCKER_CLIENT_A_SSH_PORT}|g" "$output"
                sed -i "s|\${DOCKER_CLIENT_B_SSH_PORT}|${DOCKER_CLIENT_B_SSH_PORT}|g" "$output"
                sed -i "s|\${PROXY_IP}|${PROXY_IP}|g" "$output"
                sed -i "s|\${PROXY_PORT}|${PROXY_PORT}|g" "$output"
                # Update dockerfile paths for root execution
                sed -i 's|dockerfile: deployment/|dockerfile: \./deployment/|g' "$output"
                ;;
            "deployment/setup-demo.sh")
                sed -i "s|\${SERVER_PORT:-7123}|${SERVER_PORT}|g" "$output"
                ;;
            "deployment/demo.sh")
                sed -i "s|http://localhost:7123|http://localhost:${SERVER_PORT}|g" "$output"
                ;;
            "deployment/Dockerfile.server")
                sed -i "s|\${SERVER_PORT}|${SERVER_PORT}|g" "$output"
                ;;
            "deployment/Dockerfile.client")
                sed -i "s|http://server:7123|http://server:${SERVER_PORT}|g" "$output"
                ;;
            "collect-metadata/pre-push")
                sed -i "s|\${SERVER_PORT}|${SERVER_PORT}|g" "$output"
                ;;
            "collect-metadata/post-commit")
                sed -i "s|\${SERVER_PORT}|${SERVER_PORT}|g" "$output"
                ;;
        esac
        
        echo "✓ Generated $output"
    else
        echo "Warning: Template $template not found, skipping..."
    fi
}

# Generate config.yml
echo "--- Generating config.yml ---"
update_file_from_template "config.yml.template" "config.yml"

# Generate deployment files
echo "--- Generating deployment files ---"
update_file_from_template "deployment/docker-compose.yml.template" "deployment/docker-compose.yml"
update_file_from_template "deployment/setup-demo.sh.template" "deployment/setup-demo.sh"
update_file_from_template "deployment/demo.sh.template" "deployment/demo.sh"
update_file_from_template "deployment/Dockerfile.server.template" "deployment/Dockerfile.server"
update_file_from_template "deployment/Dockerfile.client.template" "deployment/Dockerfile.client"

# Generate collect-metadata files
echo "--- Generating collect-metadata files ---"
update_file_from_template "collect-metadata/pre-push.template" "collect-metadata/pre-push"
update_file_from_template "collect-metadata/post-commit.template" "collect-metadata/post-commit"

# Make generated scripts executable
echo "--- Making scripts executable ---"
chmod +x deployment/setup-demo.sh
chmod +x deployment/demo.sh
chmod +x collect-metadata/pre-push
chmod +x collect-metadata/post-commit

echo ""
echo "=== Configuration Generation Complete ==="
echo ""
echo "Generated files:"
echo "  - config.yml"
echo "  - deployment/docker-compose.yml"
echo "  - deployment/setup-demo.sh"
echo "  - deployment/demo.sh"
echo "  - deployment/Dockerfile.server"
echo "  - deployment/Dockerfile.client"
echo "  - collect-metadata/pre-push"
echo "  - collect-metadata/post-commit"
echo ""
echo "Backup files created in /tmp/rint-backups/"
echo ""
echo "Next steps:"
echo "  1. Review the generated files"
echo "  2. Start the application: python main.py"
echo "  3. Or run Docker containers: docker compose -f deployment/docker-compose.yml up -d"
echo ""
echo "Note: Generated files are ignored by git. Only templates are versioned."