from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    avatar_url: Optional[str] = None
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPasswordUpdate(BaseModel):
    new_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class DataItemBase(BaseModel):
    description: Optional[str] = None
    source: str
    parent_id: Optional[int] = None


class DataItemCreate(DataItemBase):
    pass


class DataItemResponse(DataItemBase):
    id: int
    name: str
    file_path: str
    hash: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    is_folder: Optional[bool] = False
    file_count: Optional[int] = None
    user_id: int
    created_at: datetime
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)


class DataItemWithLineage(DataItemResponse):
    parent: Optional[DataItemResponse] = None
    children: List[DataItemResponse] = []


class UploadResponse(BaseModel):
    message: str
    data_item: DataItemResponse


class DVCFileResponse(BaseModel):
    path: str
    size: int
    modified: float
    exists: bool
    user_email: Optional[str] = None


class DVCUploadResponse(BaseModel):
    status: str
    path: str
    user_email: Optional[str] = None


class UploadedMetadataResponse(BaseModel):
    id: int
    file_hash: str
    original_filename: str
    host_ip: Optional[str] = None
    username: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetadataUploadResponse(BaseModel):
    message: str
    metadata_id: int
    file_hash: str
    original_filename: str


class DVCUserInfo(BaseModel):
    authenticated: bool
    user_id: Optional[int] = None
    email: Optional[str] = None
    is_admin: Optional[bool] = None
    created_at: Optional[datetime] = None
