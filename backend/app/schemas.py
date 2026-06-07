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
    free_points: int = 0
    free_points_expire_at: Optional[datetime] = None
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


class GenerationTaskResponse(BaseModel):
    id: int
    mode: str
    prompt: str
    quality: str
    size: str
    status: str
    points_cost: int
    image_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class HistoryItem(BaseModel):
    id: int
    task_id: Optional[int] = None
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


class LoginCheckinResponse(BaseModel):
    checkin_available: bool
    consecutive_days: int = 0
    day_number: int = 0
    reward: int = 0
    free_points: int = 0
    free_points_expire_at: Optional[datetime] = None
    bonus_rule: Optional[str] = None


class PointsBalanceResponse(BaseModel):
    username: str
    points: int
    free_points: int = 0
    free_points_expire_at: Optional[datetime] = None
    is_member: bool
    member_expire_at: Optional[datetime] = None
