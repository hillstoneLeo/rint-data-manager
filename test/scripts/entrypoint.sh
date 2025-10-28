#!/bin/bash
# Custom entrypoint script for test client containers

set -e

# Function to print timestamped messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Check if setup has already been completed
SETUP_MARKER="/tmp/client-setup-complete"
if [ -f "$SETUP_MARKER" ]; then
    log "Client setup already completed. Skipping setup..."
else
    log "Running client setup..."
    
    # Setup users based on container type using enhanced script
    export CONTAINER_NAME=${CONTAINER_NAME:-test_client}
    setup-users-enhanced

    setup-project-git

    if [ "${SETUP_DVC:-yes}" = "no" ]; then
      log "Env SETUP_DVC set to 'no', please do it manually"
    else
      setup-project-dvc
    fi
    
    # Mark setup as complete
    touch "$SETUP_MARKER"
    log "Client setup completed successfully!"
fi

# SSH service disabled for demo - containers work without SSH
log "SSH service disabled for demo"
log "UV projects with data generation capabilities ready!"
log "Test client container ready for development server testing!"

# Keep container running for demo
log "Starting container and keeping it alive..."
tail -f /dev/null
