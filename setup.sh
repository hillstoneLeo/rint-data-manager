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
    echo "DOCKER_SERVER_PORT=8383"
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
echo "  Docker Server Port: ${DOCKER_SERVER_PORT}"
echo "  Docker Client A SSH Port: ${DOCKER_CLIENT_A_SSH_PORT}"
echo "  Docker Client B SSH Port: ${DOCKER_CLIENT_B_SSH_PORT}"
echo ""

# Function to update file from template with specific replacements
update_file_from_template() {
    local template=$1
    local output=$2
    
    if [ -f "$template" ]; then
        echo "Generating $output from $template..."
        # Create backup if output exists
        if [ -f "$output" ]; then
            cp "$output" "$output.backup"
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
                sed -i "s|\${DOCKER_SERVER_PORT}|${DOCKER_SERVER_PORT}|g" "$output"
                sed -i "s|\${DOCKER_CLIENT_A_SSH_PORT}|${DOCKER_CLIENT_A_SSH_PORT}|g" "$output"
                sed -i "s|\${DOCKER_CLIENT_B_SSH_PORT}|${DOCKER_CLIENT_B_SSH_PORT}|g" "$output"
                sed -i "s|\${PROXY_IP}|${PROXY_IP}|g" "$output"
                sed -i "s|\${PROXY_PORT}|${PROXY_PORT}|g" "$output"
                ;;
            "deployment/setup-demo.sh")
                sed -i "s|http://server:7123|http://server:${DOCKER_SERVER_PORT}|g" "$output"
                ;;
            "deployment/demo.sh")
                sed -i "s|http://localhost:7123|http://localhost:${DOCKER_SERVER_PORT}|g" "$output"
                ;;
            "deployment/Dockerfile.server")
                sed -i "s|\${DOCKER_SERVER_PORT}|${DOCKER_SERVER_PORT}|g" "$output"
                ;;
            "deployment/Dockerfile.client")
                sed -i "s|http://server:7123|http://server:${DOCKER_SERVER_PORT}|g" "$output"
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
echo "Backup files created with .backup extension"
echo ""
echo "Next steps:"
echo "  1. Review the generated files"
echo "  2. Start the application: python main.py"
echo "  3. Or run Docker containers: cd deployment && docker-compose up -d"
echo ""
echo "Note: Generated files are ignored by git. Only templates are versioned."