#!/usr/bin/env python3
"""
Database management script for RINT Data Manager
Allows admin users to manage users directly via command line
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import User
from backend.auth import get_password_hash, verify_password
from backend.config import config

def get_db_session():
    DATABASE_URL = config.database.get('url', 'sqlite:///./rint_data_manager.db')
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def list_users():
    """List all users in the database"""
    db = get_db_session()
    try:
        users = db.query(User).all()
        print("ID | Email | Admin | Created")
        print("-" * 50)
        for user in users:
            print(f"{user.id} | {user.email} | {user.is_admin} | {user.created_at}")
    finally:
        db.close()

def reset_password(email, new_password):
    """Reset password for a specific user"""
    db = get_db_session()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User with email '{email}' not found")
            return False
        
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        print(f"Password reset successfully for user: {email}")
        return True
    except Exception as e:
        print(f"Error resetting password: {e}")
        return False
    finally:
        db.close()

def make_admin(email):
    """Grant admin privileges to a user"""
    db = get_db_session()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User with email '{email}' not found")
            return False
        
        user.is_admin = True
        db.commit()
        print(f"User {email} is now an admin")
        return True
    except Exception as e:
        print(f"Error making admin: {e}")
        return False
    finally:
        db.close()

def remove_admin(email):
    """Remove admin privileges from a user"""
    db = get_db_session()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User with email '{email}' not found")
            return False
        
        user.is_admin = False
        db.commit()
        print(f"Admin privileges removed from user: {email}")
        return True
    except Exception as e:
        print(f"Error removing admin: {e}")
        return False
    finally:
        db.close()

def delete_user(email):
    """Delete a user from the database"""
    db = get_db_session()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User with email '{email}' not found")
            return False
        
        db.delete(user)
        db.commit()
        print(f"User {email} deleted successfully")
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False
    finally:
        db.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python db_manager.py <command> [args...]")
        print("\nCommands:")
        print("  list                          - List all users")
        print("  reset-password <email> <pass> - Reset user password")
        print("  make-admin <email>            - Grant admin privileges")
        print("  remove-admin <email>          - Remove admin privileges")
        print("  delete-user <email>           - Delete user")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        list_users()
    elif command == "reset-password":
        if len(sys.argv) != 4:
            print("Usage: python db_manager.py reset-password <email> <new_password>")
            sys.exit(1)
        reset_password(sys.argv[2], sys.argv[3])
    elif command == "make-admin":
        if len(sys.argv) != 3:
            print("Usage: python db_manager.py make-admin <email>")
            sys.exit(1)
        make_admin(sys.argv[2])
    elif command == "remove-admin":
        if len(sys.argv) != 3:
            print("Usage: python db_manager.py remove-admin <email>")
            sys.exit(1)
        remove_admin(sys.argv[2])
    elif command == "delete-user":
        if len(sys.argv) != 3:
            print("Usage: python db_manager.py delete-user <email>")
            sys.exit(1)
        delete_user(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()