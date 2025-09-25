#!/bin/bash
# Install DVC metadata upload hooks

echo "Installing DVC metadata upload hooks..."

# Get repository root
REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$REPO_ROOT/.git/hooks"

# Copy post-commit hook
cp "$(dirname "$0")/post-commit" "$HOOKS_DIR/post-commit"
chmod +x "$HOOKS_DIR/post-commit"

# Copy pre-push hook
cp "$(dirname "$0")/pre-push" "$HOOKS_DIR/pre-push"
chmod +x "$HOOKS_DIR/pre-push"

echo "✓ DVC metadata hooks installed successfully!"
echo ""
echo "Post-commit hook location: $HOOKS_DIR/post-commit"
echo "Pre-push hook location: $HOOKS_DIR/pre-push"
echo ""
echo "To configure, edit the SERVER_URL in the hook scripts."
echo ""
echo "Hook differences:"
echo "- post-commit: Uploads ALL .dvc files after every commit"
echo "- pre-push: Uploads only .dvc files being pushed (more efficient)"