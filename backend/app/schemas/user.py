from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    nickname: str = Field(default="", max_length=50)
    is_active: bool = True
    is_superuser: bool = False


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    nickname: str | None = Field(default=None, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    is_active: bool | None = None
    is_superuser: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    nickname: str | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class PageResult(BaseModel):
    total: int
    items: list[UserOut]
