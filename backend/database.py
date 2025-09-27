from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey, LargeBinary
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
from .config import config

DATABASE_URL = config.database.get('url', 'sqlite:///./rint_data_manager.db')

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
    parent = relationship("DataItem", remote_side=[id], back_populates="children")
    children = relationship("DataItem", back_populates="parent")

class UploadedMetadata(Base):
    __tablename__ = "uploaded_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    file_hash = Column(String, nullable=False, index=True)  # To match with data_items.hash
    original_filename = Column(String, nullable=False)     # From .dvc file parsing
    host_ip = Column(String, nullable=True)                # From HTTP request client
    username = Column(String, nullable=True)               # From form field
    created_at = Column(DateTime, default=func.now())
    
    # Relationship to DataItem (optional, for easy joins)
    data_item = relationship("DataItem", foreign_keys=[file_hash], primaryjoin="UploadedMetadata.file_hash == foreign(DataItem.hash)")

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

def ensure_tables_exist():
    """Check if tables exist and create them if they don't"""
    try:
        # Try to query the first user to see if tables exist
        db = SessionLocal()
        db.query(User).first()
        db.close()
    except Exception:
        # If there's an error, tables likely don't exist, so create them
        create_tables()
