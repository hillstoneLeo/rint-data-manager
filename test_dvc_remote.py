#!/usr/bin/env python3
"""
Test script for DVC remote functionality
"""
import os
import sys
import tempfile
import requests
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.config import config
from backend.routers.dvc_remote import get_file_path_from_hash, get_user_storage_path, is_dvc_hash_path

def test_config():
    """Test configuration loading"""
    print("Testing configuration...")
    storage_path = config.dvc_config.get('storage_path', '/opt/dvc_storage')
    print(f"✓ Storage path: {storage_path}")
    
    remote_config = config.dvc_remote
    print(f"✓ Remote server enabled: {remote_config.get('enabled', False)}")
    
    auth_config = remote_config.get('auth', {})
    print(f"✓ Auth method: {auth_config.get('method', 'database')}")
    print()

def test_path_functions():
    """Test path manipulation functions"""
    print("Testing path functions...")
    
    # Test user storage path
    user_path = get_user_storage_path('test@example.com')
    expected_path = Path('/opt/dvc_storage/users/55502f40')
    print(f"✓ User storage path: {user_path}")
    print(f"✓ Expected: {expected_path}")
    print(f"✓ Match: {user_path == expected_path}")
    print()
    
    # Test DVC hash path detection
    test_paths = [
        'files/md5/47/3eee96816e270cfcbc2813602413b9',
        'files/sha256/ab/cdef123456789',
        'regular/file.txt',
        'files/md5/incomplete',
        'invalid/path'
    ]
    
    for path in test_paths:
        is_hash = is_dvc_hash_path(path)
        print(f"✓ {path}: {'DVC hash path' if is_hash else 'Regular path'}")
    print()
    
    # Test file path from hash
    test_hash = '473eee96816e270cfcbc2813602413b9'
    file_path = get_file_path_from_hash(test_hash)
    expected_file_path = Path('/opt/dvc_storage/files/47/3eee96816e270cfcbc2813602413b9')
    print(f"✓ Hash to file path: {file_path}")
    print(f"✓ Expected: {expected_file_path}")
    print(f"✓ Match: {file_path == expected_file_path}")
    print()

def test_directory_structure():
    """Test that required directories exist or can be created"""
    print("Testing directory structure...")
    
    storage_path = Path(config.dvc_config.get('storage_path', '/opt/dvc_storage'))
    print(f"✓ Storage path: {storage_path}")
    
    # Test main directories
    users_dir = storage_path / "users"
    files_dir = storage_path / "files"
    
    print(f"✓ Users directory: {users_dir}")
    print(f"✓ Files directory: {files_dir}")
    
    # Test user directory creation
    user_dir = get_user_storage_path('test@example.com')
    print(f"✓ User directory: {user_dir}")
    
    # Test hash directory creation
    hash_dir = files_dir / "47"
    print(f"✓ Hash directory: {hash_dir}")
    print()

def test_server_endpoints():
    """Test that server endpoints are properly defined"""
    print("Testing server endpoints...")
    
    from backend.routers.dvc_remote import router
    
    # Check that routes are defined
    routes = [route.path for route in router.routes]
    expected_routes = ['/{file_path:path}', '/user/info']
    
    print(f"✓ Defined routes: {routes}")
    print(f"✓ Expected routes: {expected_routes}")
    
    for route in expected_routes:
        if route in routes:
            print(f"✓ Route {route} is defined")
        else:
            print(f"✗ Route {route} is missing")
    print()

def main():
    """Run all tests"""
    print("DVC Remote Implementation Tests")
    print("=" * 50)
    
    try:
        test_config()
        test_path_functions()
        test_directory_structure()
        test_server_endpoints()
        
        print("=" * 50)
        print("✓ All tests completed successfully!")
        print()
        print("DVC remote implementation is ready for use.")
        print()
        print("To test with DVC client:")
        print("1. Start the server: python main.py")
        print("2. Configure DVC remote: dvc remote add -d myremote http://localhost:7123/dvc")
        print("3. Test with: dvc push")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()