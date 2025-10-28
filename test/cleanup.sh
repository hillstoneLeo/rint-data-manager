#!/bin/bash
# Test Environment Cleanup Script
# Removes test client container/image, cleans database tables (except users), and removes file storage

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
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
DB_FILE="$PROJECT_ROOT/rint_data_manager.db"

# Default options
DRY_RUN=false
FORCE=false

# Tables to clean (keeping users)
TABLES_TO_CLEAN=("data_items" "uploaded_metadata" "upload_logs")

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    
    case $level in
        "INFO")  echo -e "${GREEN}[INFO]${NC} $message" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC} $message" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} $message" ;;
        "DRYRUN") echo -e "${BLUE}[DRY-RUN]${NC} $message" ;;
    esac
}

# Show usage information
show_usage() {
    cat << USAGE_EOF
Test Environment Cleanup Script

USAGE:
    ./test/cleanup.sh [OPTIONS]

OPTIONS:
    --dry-run, -n       Show what would be deleted without actually deleting
    --force, -f         Skip confirmation prompts
    --help, -h          Show this help message

REQUIREMENTS:
    - sqlite3 (for database cleanup)
    - yq (for reading config.yml)
    - docker compose (for container management)

EXAMPLES:
    ./test/cleanup.sh                    # Full cleanup with confirmation
    ./test/cleanup.sh --dry-run          # Preview what would be deleted
    ./test/cleanup.sh --force            # Full cleanup without confirmation

USAGE_EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run|-n)
                DRY_RUN=true
                shift
                ;;
            --force|-f)
                FORCE=true
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

# Load cleanup directories from config.yml
load_cleanup_directories() {
    local config_file="$PROJECT_ROOT/config.yml"
    
    if [ ! -f "$config_file" ]; then
        log "ERROR" "config.yml not found at $config_file"
        exit 1
    fi
    
    log "INFO" "Loading cleanup directories from config.yml..."
    
    # Extract paths using yq
    local storage_path=$(yq eval '.dvc.storage_path' "$config_file" 2>/dev/null)
    local uploads_path=$(yq eval '.dvc.uploads_dvc_project' "$config_file" 2>/dev/null)
    
    # Validate paths were extracted
    if [ -z "$storage_path" ] || [ "$storage_path" = "null" ]; then
        log "ERROR" "Could not extract dvc.storage_path from config.yml"
        exit 1
    fi
    
    if [ -z "$uploads_path" ] || [ "$uploads_path" = "null" ]; then
        log "ERROR" "Could not extract dvc.uploads_dvc_project from config.yml"
        exit 1
    fi
    
    # Build CLEANUP_DIRECTORIES array
    CLEANUP_DIRECTORIES=()
    
    # Handle storage_path
    if [[ "$storage_path" == "$PROJECT_ROOT"* ]]; then
        # Convert absolute path within project to relative
        local rel_path="${storage_path#$PROJECT_ROOT/}"
        CLEANUP_DIRECTORIES+=("$rel_path")
    else
        # Keep absolute paths as-is
        CLEANUP_DIRECTORIES+=("$storage_path")
    fi
    
    # Handle uploads_path
    if [[ "$uploads_path" == "$PROJECT_ROOT"* ]]; then
        # Convert absolute path within project to relative
        local rel_path="${uploads_path#$PROJECT_ROOT/}"
        CLEANUP_DIRECTORIES+=("$rel_path")
    else
        # Keep absolute paths as-is
        CLEANUP_DIRECTORIES+=("$uploads_path")
    fi
    
    # Remove duplicates while preserving order
    local temp_array=()
    local seen_paths=""
    for dir in "${CLEANUP_DIRECTORIES[@]}"; do
        if [[ "$seen_paths" != *"$dir"* ]]; then
            temp_array+=("$dir")
            seen_paths="$seen_paths $dir"
        fi
    done
    CLEANUP_DIRECTORIES=("${temp_array[@]}")
    
    log "INFO" "Cleanup directories loaded: ${CLEANUP_DIRECTORIES[*]}"
}

# Check if we're in the correct directory
check_prerequisites() {
    # Check if sqlite3 is available
    if ! command -v sqlite3 >/dev/null 2>&1; then
        log "ERROR" "sqlite3 is not installed. Please install sqlite3 to use this script."
        exit 1
    fi
    
    # Check if yq is available
    if ! command -v yq >/dev/null 2>&1; then
        log "ERROR" "yq is not installed. Please install yq to use this script."
        exit 1
    fi
    
    # Check if docker compose is available
    if ! command -v docker >/dev/null 2>&1; then
        log "ERROR" "docker is not installed. Please install docker to use this script."
        exit 1
    fi
    
    if ! docker compose version >/dev/null 2>&1; then
        log "ERROR" "docker compose is not available. Please ensure you have docker compose plugin installed."
        exit 1
    fi
    
    # Check if docker-compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        log "ERROR" "docker-compose.yml not found at $COMPOSE_FILE"
        exit 1
    fi
    
    # Check if config.yml exists
    if [ ! -f "$PROJECT_ROOT/config.yml" ]; then
        log "ERROR" "config.yml not found at $PROJECT_ROOT/config.yml"
        exit 1
    fi
    
    log "INFO" "Project root: $PROJECT_ROOT"
    log "INFO" "Database file: $DB_FILE"
    log "INFO" "Config file: $PROJECT_ROOT/config.yml"
}

# Confirm cleanup operation
confirm_cleanup() {
    if [ "$FORCE" = true ]; then
        return 0
    fi
    
    echo ""
    echo -e "${YELLOW}WARNING: This will completely remove the following:${NC}"
    echo ""
    echo "Docker Resources:"
    echo "   • Test client container (rdm-test-client)"
    echo "   • Test client Docker image"
    echo "   • Test client volume (test_client_data)"
    echo ""
    echo "Database Tables to Clean:"
    for table in "${TABLES_TO_CLEAN[@]}"; do
        echo "   • $table (all records)"
    done
    echo "   • users table will be preserved"
    echo ""
    echo "File Storage Directories (contents will be removed, directories kept):"
    for dir in "${CLEANUP_DIRECTORIES[@]}"; do
        echo "   • $dir"
    done
    echo ""
    echo -e "${RED}This action cannot be undone!${NC}"
    echo ""
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log "INFO" "Cleanup cancelled by user."
        exit 0
    fi
}

# Cleanup Docker resources
cleanup_docker() {
    log "INFO" "Cleaning Docker resources..."
    
    if [ "$DRY_RUN" = true ]; then
        log "DRYRUN" "Would stop and remove containers: docker compose -f \"$COMPOSE_FILE\" down --volumes --remove-orphans"
        log "DRYRUN" "Would remove images: docker compose -f \"$COMPOSE_FILE\" down --rmi all"
        return 0
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log "WARN" "Docker daemon is not running. Skipping Docker cleanup."
        return 0
    fi
    
    # Stop and remove containers, volumes, and orphans
    log "INFO" "Stopping and removing containers, volumes, and orphans..."
    if docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans 2>/dev/null; then
        log "INFO" "✓ Containers, volumes, and orphans removed"
    else
        log "WARN" "Some containers/volumes may not exist or couldn't be removed"
    fi
    
    # Remove images
    log "INFO" "Removing Docker images..."
    if docker compose -f "$COMPOSE_FILE" down --rmi all 2>/dev/null; then
        log "INFO" "✓ Docker images removed"
    else
        log "WARN" "Some images may not exist or couldn't be removed"
    fi
    
    log "INFO" "✓ Docker resources cleanup complete"
}

# Cleanup database tables
cleanup_database() {
    log "INFO" "Cleaning database tables..."
    
    if [ ! -f "$DB_FILE" ]; then
        log "WARN" "Database file not found at $DB_FILE. Skipping database cleanup."
        return 0
    fi
    
    if [ "$DRY_RUN" = true ]; then
        log "DRYRUN" "Would clean tables: ${TABLES_TO_CLEAN[*]}"
        return 0
    fi
    
    # Check if database is accessible
    if ! sqlite3 "$DB_FILE" "SELECT 1;" >/dev/null 2>&1; then
        log "ERROR" "Cannot access database at $DB_FILE"
        return 1
    fi
    
    # Clean each table
    for table in "${TABLES_TO_CLEAN[@]}"; do
        log "INFO" "Cleaning table: $table"
        
        # Get record count before deletion
        count=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "0")
        
        if [ "$count" -gt 0 ]; then
            # Delete all records from the table
            if sqlite3 "$DB_FILE" "DELETE FROM $table;" 2>/dev/null; then
                log "INFO" "✓ Deleted $count records from $table"
            else
                log "WARN" "Failed to clean table: $table"
            fi
        else
            log "INFO" "✓ Table $table is already empty"
        fi
    done
    
    log "INFO" "✓ Database cleanup complete"
}

# Cleanup directories
cleanup_directories() {
    log "INFO" "Cleaning directories..."
    
    local dirs_cleaned=0
    
    for dir in "${CLEANUP_DIRECTORIES[@]}"; do
        # Handle relative vs absolute paths
        if [[ "$dir" == /* ]]; then
            local full_path="$dir"
        else
            local full_path="$PROJECT_ROOT/$dir"
        fi
        
        if [ -d "$full_path" ]; then
            if [ "$DRY_RUN" = true ]; then
                log "DRYRUN" "Would clean contents of directory: $dir"
                dirs_cleaned=$((dirs_cleaned + 1))
            else
                log "INFO" "Cleaning contents of directory: $dir"
                
                # Check if directory has contents
                local has_contents=false
                if [ -n "$(ls -A "$full_path" 2>/dev/null)" ]; then
                    has_contents=true
                fi
                
                if [ "$has_contents" = true ]; then
                    # Remove all contents but keep the directory
                    if rm -rf "$full_path"/* "$full_path"/.[^.] 2>/dev/null; then
                        dirs_cleaned=$((dirs_cleaned + 1))
                        log "INFO" "✓ Cleaned contents of directory: $dir"
                    else
                        log "WARN" "Directory $dir might need elevated permissions. Trying with sudo..."
                        if sudo rm -rf "$full_path"/* "$full_path"/.[^.] 2>/dev/null; then
                            dirs_cleaned=$((dirs_cleaned + 1))
                            log "INFO" "✓ Cleaned contents with sudo: $dir"
                        else
                            log "WARN" "Failed to clean directory: $dir"
                        fi
                    fi
                else
                    dirs_cleaned=$((dirs_cleaned + 1))
                    log "INFO" "✓ Directory $dir is already empty"
                fi
            fi
        else
            log "INFO" "Directory not found, skipping: $dir"
        fi
    done
    
    if [ "$DRY_RUN" = true ]; then
        log "DRYRUN" "Would clean $dirs_cleaned directories"
    else
        log "INFO" "✓ Cleaned $dirs_cleaned directories"
    fi
}

# Show cleanup summary
show_summary() {
    echo ""
    if [ "$DRY_RUN" = true ]; then
        log "INFO" "Dry run complete. No files were actually deleted."
        log "INFO" "Run without --dry-run to perform the actual cleanup."
    else
        log "INFO" "Test environment cleanup complete!"
        echo ""
        log "INFO" "Next steps:"
        echo "Run 'docker compose -f test/docker-compose.yml up -d' to start the test client"
        echo ""
    fi
}

# Main execution function
main() {
    log "INFO" "Test Environment Cleanup Script"
    log "INFO" "==============================="
    
    parse_args "$@"
    check_prerequisites
    load_cleanup_directories
    
    # Show what will be done
    if [ "$DRY_RUN" = true ]; then
        log "INFO" "DRY RUN MODE - No files will be deleted"
    fi
    
    # Get confirmation unless in dry-run mode
    if [ "$DRY_RUN" = false ]; then
        confirm_cleanup
    fi
    
    echo ""
    
    # Perform cleanup
    cleanup_docker
    cleanup_database
    cleanup_directories
    
    show_summary
}

# Run main function with all arguments
main "$@"
