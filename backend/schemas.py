from pydantic import BaseModel, EmailStr
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
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class DataItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    source: str
    parent_id: Optional[int] = None

class DataItemCreate(DataItemBase):
    pass

class DataItemResponse(DataItemBase):
    id: int
    file_path: str
    dvc_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    user_id: int
    created_at: datetime
    user: UserResponse
    
    class Config:
        from_attributes = True

class DataItemWithLineage(DataItemResponse):
    parent: Optional[DataItemResponse] = None
    children: List[DataItemResponse] = []
    
    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    message: str
    data_item: DataItemResponse