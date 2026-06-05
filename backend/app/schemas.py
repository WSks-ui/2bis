from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: int
    username: str
    points: int
    is_member: bool
    member_expire_at: Optional[datetime] = None
    created_at: datetime


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    quality: str = Field(default="low")
    size: str = Field(default="1024x1024")


class GenerateResponse(BaseModel):
    id: int
    prompt: str
    image_url: str
    quality: str
    points_cost: int
    created_at: datetime


class HistoryItem(BaseModel):
    id: int
    prompt: str
    image_url: Optional[str] = None
    quality: str
    points_cost: int
    created_at: datetime


class OrderCreate(BaseModel):
    order_type: str
    product_id: int


class OrderResponse(BaseModel):
    id: int
    order_no: str
    order_type: str
    product_id: int
    amount: float
    status: str
    created_at: datetime
    qr_code_text: str = ""


class PointsPack(BaseModel):
    id: int
    name: str
    price: float
    points: int


class MembershipPlan(BaseModel):
    id: int
    name: str
    price: float
    points_bonus: int
    duration_days: int


class PointsBalanceResponse(BaseModel):
    username: str
    points: int
    is_member: bool
    member_expire_at: Optional[datetime] = None
