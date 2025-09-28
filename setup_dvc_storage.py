#!/usr/bin/env python3
"""
Migration script to add DVC remote support
This script creates the necessary directory structure for DVC remote storage
"""
import os
from pathlib import Path
from backend.config import config


def setup_dvc_storage():
    """Setup DVC storage directory structure"""
    storage_path = Path(
        config.dvc_config.get('storage_path', '/opt/dvc_storage'))

    # Create main storage directory
    storage_path.mkdir(parents=True, exist_ok=True)

    # Create users directory for user-isolated storage
    users_path = storage_path / "users"
    users_path.mkdir(exist_ok=True)

    # Create .gitkeep files to ensure directories are tracked
    (storage_path / ".gitkeep").touch()
    (users_path / ".gitkeep").touch()

    print(f"DVC storage directory created at: {storage_path}")
    print(f"Users directory created at: {users_path}")
    print("\nDirectory structure:")
    print(f"├── {storage_path}/")
    print(f"│   ├── .gitkeep")
    print(f"│   └── users/")
    print(f"│       ├── .gitkeep")
    print(f"│       └── [user_hashed_dirs]/")

    # Set proper permissions if running as root
    if os.geteuid() == 0:
        import pwd
        import grp

        # Try to get current user or default to 'nobody'
        try:
            user = pwd.getpwuid(os.getuid())
            username = user.pw_name
            uid = user.pw_uid
            gid = user.pw_gid
        except:
            username = 'nobody'
            uid = pwd.getpwnam('nobody').pw_uid
            gid = grp.getgrnam('nobody').gr_gid

        # Change ownership
        for path in [storage_path, users_path]:
            os.chown(path, uid, gid)
            print(f"Changed ownership of {path} to {username}:{username}")


if __name__ == "__main__":
    setup_dvc_storage()
