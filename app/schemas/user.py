"""
Pydantic schemas for User entity.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    department_id: Optional[int] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.STUDENT


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
