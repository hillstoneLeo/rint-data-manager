#!/bin/bash
# Install DVC metadata upload hooks

echo "Installing DVC metadata upload hooks..."

# Get repository root
REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$REPO_ROOT/.git/hooks"

# Create post-commit hook
cat > "$HOOKS_DIR/post-commit" << 'EOF'
#!/bin/bash
# DVC Metadata Upload Hook
set -e

SERVER_URL="http://localhost:8000/api/v1/data/upload-metadata"
USER_ID="1"
AUTH_TOKEN=""

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

find . -name "*.dvc" -type f | while read -r dvc_file; do
    if [[ "$dvc_file" == *".git"* ]]; then
        continue
    fi
    
    echo "Uploading metadata for: $dvc_file"
    
    if [ -n "$AUTH_TOKEN" ]; then
        curl -X POST "$SERVER_URL" \
             -H "Authorization: Bearer $AUTH_TOKEN" \
             -F "dvc_file=@$dvc_file" \
             -F "user_id=$USER_ID" \
             --silent --show-error --fail
    else
        curl -X POST "$SERVER_URL" \
             -F "dvc_file=@$dvc_file" \
             -F "user_id=$USER_ID" \
             --silent --show-error --fail
    fi
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully uploaded: $dvc_file"
    else
        echo "✗ Failed to upload: $dvc_file" >&2
    fi
done

echo "DVC metadata upload completed."
EOF

# Make hook executable
chmod +x "$HOOKS_DIR/post-commit"

echo "✓ DVC metadata hook installed successfully!"
echo "Hook location: $HOOKS_DIR/post-commit"
echo ""
echo "To configure, edit the SERVER_URL and USER_ID in the hook script."
echo ""
echo "You can also use the pre-push hook at: $HOOKS_DIR/pre-push"
echo "The pre-push hook only uploads .dvc files that are being pushed."