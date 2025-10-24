#!/bin/bash
# Setup script for client containers - creates demo projects and configures DVC

set -e

# Function to print timestamped messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Setting up demo environment..."

# Function to setup user workspace
setup_user_workspace() {
    local username=$1
    local project_name=$2
    
    log "Setting up workspace for $username..."
    
    # Create project directory in user's home directory
    sudo -u "$username" mkdir -p "/home/$username/$project_name"
    cd "/home/$username/$project_name"
    
    # Initialize git repository
    sudo -u "$username" git init
    
    # Initialize DVC
    sudo -u "$username" dvc init
    
    # Configure DVC remote to use HTTP server
    sudo -u "$username" dvc remote add -d myremote http://server:${SERVER_PORT:-8000}/dvc
    sudo -u "$username" dvc remote modify myremote auth basic
    sudo -u "$username" dvc remote modify myremote user $username@hillstonenet.com
    sudo -u "$username" dvc remote modify myremote password ${username}123
    
    # Install DVC hooks
    setup-dvc-hooks "/home/$username/$project_name"
    
    # Create sample data file
    sudo -u "$username" cat > sample_data.csv << 'EOF'
name,age,city
Alice,25,New York
Bob,30,San Francisco
Charlie,35,Chicago
EOF
    
    # Add sample data to DVC
    sudo -u "$username" dvc add sample_data.csv
    
    # Add .dvc file to git
    sudo -u "$username" git add .
    sudo -u "$username" git commit -m "Initial commit with sample data"
    
    # Generate sample data using the new data generator
    log "Generating sample demo data..."
    cd "/home/$username/$project_name"

    # Generate a smaller dataset for demo (500 records)
    sudo -u "$username" python src/data_generator.py --records 500 --dataset all

    log "✓ Sample data generated in data/ directory"
    log "Data files created:"
    sudo -u "$username" ls -la data/

    # Add generated data to DVC
    log "Adding generated data to DVC..."
    sudo -u "$username" dvc add data/customers.csv
    sudo -u "$username" dvc add data/sales.csv

    # Commit the new data and project structure
    sudo -u "$username" git add .
    sudo -u "$username" git commit -m "Add UV project structure and generated demo data"

    log "✓ Enhanced workspace setup complete for $username"
}

# Container A: Setup alice and bob workspaces
if [ "$CONTAINER_NAME" = "client_a" ]; then
    setup_user_workspace "alice" "demo-project"
    setup_user_workspace "bob" "data-analysis"
fi

# Container B: Setup cindy workspace
if [ "$CONTAINER_NAME" = "client_b" ]; then
    setup_user_workspace "cindy" "ml-experiment"
fi

log "Demo environment setup complete!"