from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    password: str = Field(..., min_length=8, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10, max_length=1024)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=10, max_length=1024)


class UserMe(BaseModel):
    id: int
    username: str


class TaskCreate(BaseModel):
    host: str = Field(..., min_length=1, max_length=255)


class TaskRead(BaseModel):
    id: int
    host: str
    status: str
    result: str
    user_id: int
    job_id: str | None = None

    class Config:
        orm_mode = True
