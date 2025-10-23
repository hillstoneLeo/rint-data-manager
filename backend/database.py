from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey, LargeBinary
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import time
import logging
from .config import config
try:
    from .utils.timing import timing_logger, log_timing
except ImportError:
    # Fallback if utils module is not available
    def timing_logger(func):
        return func
    def log_timing(message, start_time=None):
        return time.time()

DATABASE_URL = config.database.get('url', 'sqlite:///./rint_data_manager.db')

# Set up logging for timing
logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    data_items = relationship("DataItem", back_populates="user")


class DataItem(Base):
    __tablename__ = "data_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    project = Column(String, nullable=True)
    source = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    hash = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String, nullable=True)
    is_folder = Column(Boolean, default=False)
    file_count = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("data_items.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="data_items")
    parent = relationship("DataItem",
                          remote_side=[id],
                          back_populates="children")
    children = relationship("DataItem", back_populates="parent")


class UploadedMetadata(Base):
    __tablename__ = "uploaded_metadata"

    id = Column(Integer, primary_key=True, index=True)
    file_hash = Column(String, nullable=False,
                       index=True)  # To match with data_items.hash
    original_filename = Column(String,
                               nullable=False)  # From .dvc file parsing
    host_ip = Column(String, nullable=True)  # From HTTP request client
    username = Column(String, nullable=True)  # From form field
    created_at = Column(DateTime, default=func.now())

    # Relationship to DataItem (optional, for easy joins)
    data_item = relationship(
        "DataItem",
        foreign_keys=[file_hash],
        primaryjoin="UploadedMetadata.file_hash == foreign(DataItem.hash)")


class UploadLog(Base):
    __tablename__ = "upload_logs"

    id = Column(Integer, primary_key=True, index=True)
    data_item_id = Column(Integer, ForeignKey("data_items.id"), nullable=False)
    action = Column(String, nullable=False)
    metadata_info = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now())

    data_item = relationship("DataItem")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)


@timing_logger
def ensure_tables_exist():
    """Check if tables exist and create them if they don't"""
    log_timing("ensure_tables_exist - starting table existence check")
    start_time = log_timing("ensure_tables_exist - creating database session")
    
    try:
        # Try to query the first user to see if tables exist
        db = SessionLocal()
        db_time = log_timing("ensure_tables_exist - database session created", start_time)
        
        try:
            query_start = log_timing("ensure_tables_exist - executing User.first() query")
            db.query(User).first()
            log_timing("ensure_tables_exist - User.first() query completed", query_start)
        finally:
            close_start = log_timing("ensure_tables_exist - closing database session")
            db.close()
            log_timing("ensure_tables_exist - database session closed", close_start)
            
        log_timing("ensure_tables_exist - tables exist, total check time", start_time)
    except Exception as e:
        log_timing(f"ensure_tables_exist - exception caught: {e}, creating tables")
        # If there's an error, tables likely don't exist, so create them
        create_start = log_timing("ensure_tables_exist - creating tables")
        create_tables()
        log_timing("ensure_tables_exist - tables created", create_start)
        log_timing("ensure_tables_exist - total time with table creation", start_time)
