import os
import pytest
import sys
import tempfile
import yaml
from pathlib import Path
from sqlalchemy.orm import Session
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.config import config
from backend.routers.dvc_remote import (
    get_file_path_from_hash, get_user_storage_path, is_dvc_hash_path,
    handle_dvc_upload_data_item_creation, extract_metadata_from_dvc_file,
    extract_original_filename_from_dvc_file, create_data_item_from_dvc_upload)
from backend.database import get_db, User, DataItem
from backend.schemas import DataItemCreate


class TestDVCConfig:
    """Test configuration loading"""

    def test_storage_path_config(self):
        """Test storage path configuration"""
        storage_path = config.dvc_config.get('storage_path',
                                             '/opt/dvc_storage')
        assert storage_path == '/opt/dvc_storage'

    def test_remote_config(self):
        """Test remote configuration"""
        remote_config = config.dvc_remote
        assert 'enabled' in remote_config
        assert 'auth' in remote_config


class TestPathFunctions:
    """Test path manipulation functions"""

    @pytest.mark.parametrize(
        "path,expected",
        [('files/md5/47/3eee96816e270cfcbc2813602413b9', True),
         ('files/sha256/ab/cdef123456789', True), ('regular/file.txt', False),
         ('files/md5/incomplete', False), ('invalid/path', False)])
    def test_is_dvc_hash_path(self, path, expected):
        """Test DVC hash path detection"""
        assert is_dvc_hash_path(path) == expected

    def test_file_path_from_hash(self):
        """Test file path generation from hash"""
        test_hash = '473eee96816e270cfcbc2813602413b9'
        file_path = get_file_path_from_hash(test_hash)
        expected_file_path = Path(
            '/opt/dvc_storage/files/47/3eee96816e270cfcbc2813602413b9')
        assert file_path == expected_file_path

    def test_user_storage_path(self):
        """Test user storage path generation"""
        user_path = get_user_storage_path('test@example.com')
        expected_path = Path('/opt/dvc_storage/users/55502f40')
        assert user_path == expected_path


class TestMetadataExtraction:
    """Test metadata extraction functions"""

    def test_extract_metadata_from_dvc_file(self):
        """Test metadata extraction from DVC file"""
        # Create a temporary DVC file
        dvc_content = {
            'outs': [{
                'path': 'test_file.txt',
                'size': 1024,
                'nfiles': 1,
                'md5': '473eee96816e270cfcbc2813602413b9'
            }]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.dvc',
                                         delete=False) as f:
            yaml.dump(dvc_content, f)
            temp_dvc_file = Path(f.name)

        try:
            metadata = extract_metadata_from_dvc_file(temp_dvc_file, Mock())
            assert metadata.get('file_size') == 1024
            assert metadata.get('file_count') == 1
            assert metadata.get('is_directory') == False
        finally:
            temp_dvc_file.unlink()

    def test_extract_original_filename_from_dvc_file(self):
        """Test original filename extraction from DVC file"""
        # Create a temporary DVC file
        dvc_content = {
            'outs': [{
                'path': 'test_file.txt',
                'size': 1024,
                'nfiles': 1,
                'md5': '473eee96816e270cfcbc2813602413b9'
            }]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.dvc',
                                         delete=False) as f:
            yaml.dump(dvc_content, f)
            temp_dvc_file = Path(f.name)

        try:
            filename = extract_original_filename_from_dvc_file(temp_dvc_file)
            assert filename == "test_file.txt"
        finally:
            temp_dvc_file.unlink()


class TestDVCUploadHandling:
    """Test DVC upload handling functions"""

    @pytest.fixture
    def db_session(self):
        """Create a test database session"""
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()

    @pytest.fixture
    def test_user(self, db_session):
        """Create a test user"""
        user = db_session.query(User).filter(
            User.email == "test@example.com").first()
        if user is None:
            user = User(email="test@example.com",
                        hashed_password="test_password_hash",
                        is_admin=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
        return user

    def test_handle_dvc_upload_data_item_creation(self, db_session, test_user):
        """Test handle_dvc_upload_data_item_creation function"""
        # Create a test file
        temp_file = None
        dvc_file = None

        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(b"test content")
                temp_file = Path(f.name)

            # Create a corresponding DVC file
            dvc_content = {
                'outs': [{
                    'path': 'test_file.txt',
                    'size': 12,
                    'nfiles': 1,
                    'md5': '473eee96816e270cfcbc2813602413b9'
                }]
            }

            dvc_file = temp_file.parent / f"{temp_file.name}.dvc"
            with open(dvc_file, 'w') as f:
                yaml.dump(dvc_content, f)

            file_path = "files/md5/47/3eee96816e270cfcbc2813602413b9"
            full_path = temp_file

            # Test the function
            result = handle_dvc_upload_data_item_creation(file_path=file_path,
                                                          full_path=full_path,
                                                          user=test_user,
                                                          db=db_session)

            # Verify result
            assert result is not None
            assert result.name == "test_file.txt"
            assert result.file_size == 12

            # Cleanup
            db_session.delete(result)
            db_session.commit()

        finally:
            # Cleanup temp files
            if temp_file and temp_file.exists():
                temp_file.unlink()
            if dvc_file and dvc_file.exists():
                dvc_file.unlink()

    def test_handle_dvc_upload_with_debug(self, db_session, test_user):
        """Test handle_dvc_upload_data_item_creation with pdb debugging"""
        # Create a test file
        temp_file = None
        dvc_file = None

        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(b"test content")
                temp_file = Path(f.name)

            # Create a corresponding DVC file
            dvc_content = {
                'outs': [{
                    'path': 'test_file.txt',
                    'size': 12,
                    'nfiles': 1,
                    'md5': '473eee96816e270cfcbc2813602413b9'
                }]
            }

            dvc_file = temp_file.parent / f"{temp_file.name}.dvc"
            with open(dvc_file, 'w') as f:
                yaml.dump(dvc_content, f)

            file_path = "files/md5/47/3eee96816e270cfcbc2813602413b9"
            full_path = temp_file

            # Set breakpoint and call the function
            import pdb
            pdb.set_trace()

            result = handle_dvc_upload_data_item_creation(file_path=file_path,
                                                          full_path=full_path,
                                                          user=test_user,
                                                          db=db_session)

            assert result is not None
            print(f"Function returned: {result}")

            if result:
                # Cleanup
                db_session.delete(result)
                db_session.commit()

        finally:
            # Cleanup temp files
            if temp_file and temp_file.exists():
                temp_file.unlink()
            if dvc_file and dvc_file.exists():
                dvc_file.unlink()


class TestServerEndpoints:
    """Test server endpoints"""

    def test_router_import(self):
        """Test that router can be imported"""
        from backend.routers.dvc_remote import router
        assert router is not None

    def test_router_has_routes(self):
        """Test that router has routes defined"""
        from backend.routers.dvc_remote import router

        # Check that router exists and has routes
        route_count = len(router.routes)
        assert route_count > 0


# if __name__ == "__main__":
#     if len(sys.argv) > 1:
#         if sys.argv[1] == "--standalone":
#             run_standalone_tests()
#         elif sys.argv[1] == "--help":
#             print("Usage: python test/test_combined.py [option]")
#             print("Options:")
#             print("  --standalone    Run standalone tests without pytest")
#             print("  --help          Show this help message")
#             print()
#             print("To run with pytest:")
#             print("  uv run pytest test/test_combined.py -v")
#             print("  uv run pytest test/test_combined.py -v -k test_name")
#         else:
#             print("Unknown option. Use --help for usage information.")
#     else:
#         pytest.main([__file__, "-v"])
