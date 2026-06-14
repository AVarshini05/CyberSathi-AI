import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = Field(None, pattern=r"^\+?[0-9]{10,15}$")
    full_name: Optional[str] = None
    role: Optional[str] = "citizen"  # citizen, officer, admin
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    mobile_number: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    full_name: str
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_superuser: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    login_identifier: str
    password: str


class OTPRequest(BaseModel):
    mobile_number: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")


class OTPVerify(BaseModel):
    mobile_number: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    otp: str = Field(..., min_length=4, max_length=6)
