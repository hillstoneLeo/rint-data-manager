#!/bin/bash
# Setup script for client containers - creates demo projects and configures DVC

set -e

echo "Setting up demo environment..."

# Function to setup user workspace
setup_user_workspace() {
    local username=$1
    local project_name=$2
    
    echo "Setting up workspace for $username..."
    
    # Create project directory
    sudo -u "$username" mkdir -p "/workspace/$username/$project_name"
    cd "/workspace/$username/$project_name"
    
    # Initialize git repository
    sudo -u "$username" git init
    
    # Initialize DVC
    sudo -u "$username" dvc init
    
    # Configure DVC remote to use shared storage
    sudo -u "$username" dvc remote add -d myremote /opt/dvc_storage
    
    # Install DVC hooks
    setup-dvc-hooks "/workspace/$username/$project_name"
    
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
    
    echo "✓ Workspace setup complete for $username"
}

# Container A: Setup alice and bob workspaces
if [ "$CONTAINER_TYPE" = "client_a" ]; then
    setup_user_workspace "alice" "demo-project"
    setup_user_workspace "bob" "data-analysis"
fi

# Container B: Setup cindy workspace
if [ "$CONTAINER_TYPE" = "client_b" ]; then
    setup_user_workspace "cindy" "ml-experiment"
fi

echo "Demo environment setup complete!"