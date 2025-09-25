#!/bin/bash
# Demo script to showcase the Rint Data Manager functionality

set -e

echo "=== Rint Data Manager Demo ==="
echo ""

# Function to demonstrate user operations
demo_user_operations() {
    local username=$1
    local password=$2
    local container=$3
    
    echo "--- Demo for user: $username ---"
    
    # Switch to user
    echo "Switching to user $username..."
    
    # Show current directory and files
    echo "Current workspace:"
    ls -la /workspace/$username/
    
    # Navigate to project
    cd "/workspace/$username/demo-project" 2>/dev/null || cd "/workspace/$username/data-analysis" 2>/dev/null || cd "/workspace/$username/ml-experiment"
    
    echo "Current project directory: $(pwd)"
    echo "Project files:"
    ls -la
    
    # Show DVC status
    echo "DVC status:"
    sudo -u "$username" dvc status
    
    # Show git log
    echo "Git log:"
    sudo -u "$username" git log --oneline
    
    # Create new data file
    echo "Creating new data file..."
    sudo -u "$username" cat > new_data.json << 'EOF'
{
    "experiment": "demo",
    "timestamp": "2025-01-01T00:00:00Z",
    "results": [1, 2, 3, 4, 5]
}
EOF
    
    # Add new file to DVC
    echo "Adding new file to DVC..."
    sudo -u "$username" dvc add new_data.json
    
    # Commit changes
    echo "Committing changes..."
    sudo -u "$username" git add .
    sudo -u "$username" git commit -m "Add new experimental data"
    
    echo "✓ Demo completed for $username"
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

echo "=== Demo Complete ==="
echo ""
echo "Web UI is available at: http://localhost:7123"
echo "Users can register and login with the following credentials:"
echo "  - alice / alice123"
echo "  - bob / bob123" 
echo "  - cindy / cindy123"
echo ""
echo "DVC hooks are automatically installed and will upload metadata to the server."