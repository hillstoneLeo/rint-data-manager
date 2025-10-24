#!/bin/bash
# Demo script to showcase the Rint Data Manager functionality

set -e

# Function to print timestamped messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "=== Rint Data Manager Demo ==="
echo ""

# Function to demonstrate user operations
demo_user_operations() {
    local username=$1
    local password=$2
    local container=$3
    
    log "--- Demo for user: $username ---"
    
    # Switch to user
    log "Switching to user $username..."
    
    # Show current directory and files
    log "Current workspace:"
    ls -la /home/$username/
    
    # Navigate to project
    cd "/home/$username/demo-project" 2>/dev/null || cd "/home/$username/data-analysis" 2>/dev/null || cd "/home/$username/ml-experiment"
    
    log "Current project directory: $(pwd)"
    log "Project files:"
    ls -la
    
    log "Data directory contents:"
    ls -la data/ 2>/dev/null || log "No data directory found"

    # Show data generation capabilities
    log "Data generation script available:"
    sudo -u "$username" python src/data_generator.py --help 2>/dev/null || log "Data generator not found"

    # Generate small sample dataset
    log "Generating small sample dataset (100 records)..."
    sudo -u "$username" python src/data_generator.py --records 100 --dataset customers --output-dir data/sample

    log "Sample dataset generated:"
    sudo -u "$username" ls -la data/sample/
    sudo -u "$username" head -5 data/sample/customers.csv
    
    # Show DVC status
    log "DVC status:"
    sudo -u "$username" dvc status
    
    # Show git log
    log "Git log:"
    sudo -u "$username" git log --oneline
    
    # Create new data file
    log "Creating new data file..."
    sudo -u "$username" cat > new_data.json << 'EOF'
{
    "experiment": "demo",
    "timestamp": "2025-01-01T00:00:00Z",
    "results": [1, 2, 3, 4, 5]
}
EOF
    
    # Add new file to DVC
    log "Adding new file to DVC..."
    sudo -u "$username" dvc add new_data.json
    
    # Commit changes
    log "Committing changes..."
    sudo -u "$username" git add .
    sudo -u "$username" git commit -m "Add new experimental data"
    
    log "✓ Demo completed for $username"
    echo ""
}

# Container A: Demo alice and bob
if [ "$CONTAINER_TYPE" = "client_a" ]; then
    demo_user_operations "alice" "alice123" "client_a"
    demo_user_operations "bob" "bob123" "client_a"
fi

# Container B: Demo cindy
if [ "$CONTAINER_TYPE" = "client_b" ]; then
    demo_user_operations "cindy" "cindy123" "client_b"
fi

log "=== Demo Complete ==="
echo ""
log "Web UI is available at: http://localhost:${SERVER_PORT:-8000}"
log "Users can register and login with the following credentials:"
log "  - alice / alice123"
log "  - bob / bob123" 
log "  - cindy / cindy123"
echo ""
log "DVC hooks are automatically installed and will upload metadata to the server."