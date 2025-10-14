#!/bin/bash
# RINT Data Manager Cleanup Script
# Removes all Docker resources, generated files, and directories
# Usage: ./deployment/cleanup.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/deployment/docker-compose.yml"

# Default options
DRY_RUN=false
DOCKER_ONLY=false
FILES_ONLY=false
FORCE=false
VERBOSE=false

# Template-generated files mapping (relative to project root)
GENERATED_FILES=(
    "config.yml"
    "deployment/docker-compose.yml"
    "deployment/setup-demo.sh"
    "deployment/demo.sh"
    "deployment/Dockerfile.server"
    "deployment/Dockerfile.client"
    "collect-metadata/pre-push"
    "collect-metadata/post-commit"
)

# Directories to clean (relative to project root)
CLEANUP_DIRECTORIES=(
    "dvc_storage"
)

# Backup directory
BACKUP_DIR="/tmp/rint-backups"

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "DRYRUN")
            echo -e "${BLUE}[DRY-RUN]${NC} $message"
            ;;
        "VERBOSE")
            if [ "$VERBOSE" = true ]; then
                echo -e "${BLUE}[VERBOSE]${NC} $message"
            fi
            ;;
    esac
}

# Show usage information
show_usage() {
    cat << EOF
RINT Data Manager Cleanup Script

USAGE:
    ./deployment/cleanup.sh [OPTIONS]

OPTIONS:
    --dry-run, -n       Show what would be deleted without actually deleting
    --docker-only       Only clean Docker resources (containers, images, volumes, networks)
    --files-only        Only delete generated files and directories
    --force, -f         Skip confirmation prompts
    --verbose, -v       Show detailed operations
    --help, -h          Show this help message

EXAMPLES:
    ./deployment/cleanup.sh                    # Full cleanup with confirmation
    ./deployment/cleanup.sh --dry-run          # Preview what would be deleted
    ./deployment/cleanup.sh --docker-only      # Only clean Docker resources
    ./deployment/cleanup.sh --force            # Full cleanup without confirmation

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run|-n)
                DRY_RUN=true
                shift
                ;;
            --docker-only)
                DOCKER_ONLY=true
                shift
                ;;
            --files-only)
                FILES_ONLY=true
                shift
                ;;
            --force|-f)
                FORCE=true
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Check if we're in the correct directory
check_directory() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        log "ERROR" "docker-compose.yml not found at $COMPOSE_FILE"
        log "ERROR" "Please run this script from the project root directory"
        exit 1
    fi
    
    log "VERBOSE" "Project root: $PROJECT_ROOT"
    log "VERBOSE" "Compose file: $COMPOSE_FILE"
}

# Confirm cleanup operation
confirm_cleanup() {
    if [ "$FORCE" = true ]; then
        return 0
    fi
    
    echo ""
    echo -e "${YELLOW}⚠️  WARNING: This will completely remove the following:${NC}"
    echo ""
    
    if [ "$FILES_ONLY" = false ]; then
        echo "🐳 Docker Resources:"
        echo "   • All RDM containers (rdm-server, rdm-client-a, rdm-client-b)"
        echo "   • All RDM Docker images"
        echo "   • All RDM Docker volumes and their data"
        echo "   • RDM Docker network"
        echo ""
    fi
    
    if [ "$DOCKER_ONLY" = false ]; then
        echo "📄 Generated Files:"
        for file in "${GENERATED_FILES[@]}"; do
            if [ -f "$PROJECT_ROOT/$file" ]; then
                echo "   • $file"
            fi
        done
        echo ""
        echo "📁 Directories:"
        for dir in "${CLEANUP_DIRECTORIES[@]}"; do
            if [ -d "$PROJECT_ROOT/$dir" ]; then
                echo "   • $dir/"
            fi
        done
        echo ""
        echo "🗂️  Backup files in $BACKUP_DIR/"
        echo ""
    fi
    
    echo -e "${RED}This action cannot be undone!${NC}"
    echo ""
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log "INFO" "Cleanup cancelled by user."
        exit 0
    fi
}

# Cleanup Docker resources
cleanup_docker_resources() {
    log "INFO" "Cleaning Docker resources..."
    
    cd "$PROJECT_ROOT"
    
    if [ "$DRY_RUN" = true ]; then
        log "DRYRUN" "Would stop and remove containers: docker compose -f deployment/docker-compose.yml down --volumes --remove-orphans"
        log "DRYRUN" "Would remove images: docker compose -f deployment/docker-compose.yml down --rmi all"
        return 0
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log "WARN" "Docker daemon is not running. Skipping Docker cleanup."
        return 0
    fi
    
    # Stop and remove containers, volumes, and orphans
    if [ -f "$COMPOSE_FILE" ]; then
        log "VERBOSE" "Stopping and removing containers, volumes, and orphans..."
        if docker compose -f deployment/docker-compose.yml down --volumes --remove-orphans 2>/dev/null; then
            log "INFO" "✓ Containers, volumes, and orphans removed"
        else
            log "WARN" "Some containers/volumes may not exist or couldn't be removed"
        fi
        
        # Remove images
        log "VERBOSE" "Removing Docker images..."
        if docker compose -f deployment/docker-compose.yml down --rmi all 2>/dev/null; then
            log "INFO" "✓ Docker images removed"
        else
            log "WARN" "Some images may not exist or couldn't be removed"
        fi
    fi
    
    # Clean up any remaining RDM resources
    log "VERBOSE" "Cleaning up remaining RDM resources..."
    
    # Remove any remaining RDM containers
    local remaining_containers=$(docker ps -aq --filter "name=rdm-" 2>/dev/null || true)
    if [ -n "$remaining_containers" ]; then
        log "VERBOSE" "Removing remaining containers: $remaining_containers"
        docker rm -f $remaining_containers 2>/dev/null || true
    fi
    
    # Remove RDM volumes
    local rdm_volumes=$(docker volume ls -q --filter "name=deployment_" 2>/dev/null || true)
    if [ -n "$rdm_volumes" ]; then
        log "VERBOSE" "Removing volumes: $rdm_volumes"
        docker volume rm $rdm_volumes 2>/dev/null || true
    fi
    
    # Remove RDM networks
    local rdm_networks=$(docker network ls -q --filter "name=deployment_" 2>/dev/null || true)
    if [ -n "$rdm_networks" ]; then
        log "VERBOSE" "Removing networks: $rdm_networks"
        docker network rm $rdm_networks 2>/dev/null || true
    fi
    
    log "INFO" "✓ Docker resources cleanup complete"
}

# Cleanup generated files
cleanup_generated_files() {
    log "INFO" "Removing generated files..."
    
    local files_removed=0
    
    for file in "${GENERATED_FILES[@]}"; do
        local full_path="$PROJECT_ROOT/$file"
        
        if [ -f "$full_path" ]; then
            if [ "$DRY_RUN" = true ]; then
                log "DRYRUN" "Would remove file: $file"
                files_removed=$((files_removed + 1))
            else
                log "VERBOSE" "Removing file: $file"
                if rm "$full_path"; then
                    files_removed=$((files_removed + 1))
                    log "INFO" "✓ Removed: $file"
                else
                    log "WARN" "Failed to remove: $file"
                fi
            fi
        else
            log "VERBOSE" "File not found, skipping: $file"
        fi
    done
    
    if [ "$DRY_RUN" = true ]; then
        log "DRYRUN" "Would remove $files_removed generated files"
    else
        log "INFO" "✓ Removed $files_removed generated files"
    fi
}

# Cleanup directories
cleanup_directories() {
    log "INFO" "Cleaning directories..."
    
    local dirs_removed=0
    
    for dir in "${CLEANUP_DIRECTORIES[@]}"; do
        local full_path="$PROJECT_ROOT/$dir"
        
        if [ -d "$full_path" ]; then
            if [ "$DRY_RUN" = true ]; then
                log "DRYRUN" "Would remove directory: $dir/"
                dirs_removed=$((dirs_removed + 1))
            else
                log "VERBOSE" "Removing directory: $dir/"
                # Some directories might be owned by root (Docker volumes)
                if rm -rf "$full_path" 2>/dev/null; then
                    ((dirs_removed++))
                    log "INFO" "✓ Removed directory: $dir/"
                else
                    log "WARN" "Directory $dir/ might need sudo. Trying with elevated permissions..."
                    if sudo rm -rf "$full_path" 2>/dev/null; then
                        dirs_removed=$((dirs_removed + 1))
                        log "INFO" "✓ Removed directory with sudo: $dir/"
                    else
                        log "WARN" "Failed to remove directory: $dir/"
                    fi
                fi
            fi
        else
            log "VERBOSE" "Directory not found, skipping: $dir/"
        fi
    done
    
    # Clean up backup directory
    if [ -d "$BACKUP_DIR" ]; then
        if [ "$DRY_RUN" = true ]; then
            log "DRYRUN" "Would remove backup directory: $BACKUP_DIR/"
        else
            log "VERBOSE" "Removing backup directory: $BACKUP_DIR/"
            if rm -rf "$BACKUP_DIR" 2>/dev/null; then
                log "INFO" "✓ Removed backup directory: $BACKUP_DIR/"
            else
                log "WARN" "Failed to remove backup directory: $BACKUP_DIR/"
            fi
        fi
    fi
    
    if [ "$DRY_RUN" = true ]; then
        log "DRYRUN" "Would remove $dirs_removed directories"
    else
        log "INFO" "✓ Removed $dirs_removed directories"
    fi
}

# Show cleanup summary
show_summary() {
    echo ""
    if [ "$DRY_RUN" = true ]; then
        log "INFO" "Dry run complete. No files were actually deleted."
        log "INFO" "Run without --dry-run to perform the actual cleanup."
    else
        log "INFO" "🎉 Cleanup complete!"
        echo ""
        log "INFO" "Next steps:"
        echo "   1. Run './setup.sh' to regenerate configuration files"
        echo "   2. Run 'docker compose -f deployment/docker-compose.yml up -d' to start services"
        echo ""
    fi
}

# Main execution function
main() {
    log "INFO" "RINT Data Manager Cleanup Script"
    log "INFO" "================================="
    
    parse_args "$@"
    check_directory
    
    # Validate options
    if [ "$DOCKER_ONLY" = true ] && [ "$FILES_ONLY" = true ]; then
        log "ERROR" "Cannot specify both --docker-only and --files-only"
        exit 1
    fi
    
    # Show what will be done
    if [ "$DRY_RUN" = true ]; then
        log "INFO" "DRY RUN MODE - No files will be deleted"
    fi
    
    if [ "$DOCKER_ONLY" = true ]; then
        log "INFO" "DOCKER ONLY MODE - Only Docker resources will be cleaned"
    elif [ "$FILES_ONLY" = true ]; then
        log "INFO" "FILES ONLY MODE - Only generated files and directories will be cleaned"
    else
        log "INFO" "FULL CLEANUP MODE - All resources will be cleaned"
    fi
    
    # Get confirmation unless in dry-run mode
    if [ "$DRY_RUN" = false ]; then
        confirm_cleanup
    fi
    
    echo ""
    
    # Perform cleanup
    if [ "$FILES_ONLY" = false ]; then
        cleanup_docker_resources
    fi
    
    if [ "$DOCKER_ONLY" = false ]; then
        cleanup_generated_files
        cleanup_directories
    fi
    
    show_summary
}

# Run main function with all arguments
main "$@"