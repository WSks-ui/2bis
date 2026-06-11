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
    subscription_plan: Optional[str] = None
    subscription_period: Optional[str] = None
    subscription_expire_at: Optional[datetime] = None
    monthly_quota_total: int = 0
    monthly_quota_remaining: int = 0
    monthly_quota_reset_at: Optional[datetime] = None
    trial_activated: bool = False
    trial_expire_at: Optional[datetime] = None
    created_at: datetime


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    quality: str = Field(default="low")
    size: str = Field(default="1024x1024")
    workflow_type: str = Field(default="standard", max_length=40)
    workflow_preset: Optional[str] = Field(default=None, max_length=80)


class GenerateResponse(BaseModel):
    id: int
    prompt: str
    image_url: str
    quality: str
    points_cost: int
    balance_source: Optional[str] = None
    workflow_type: str = "standard"
    workflow_cost: int = 0
    workflow_preset: Optional[str] = None
    created_at: datetime


class GenerationTaskResponse(BaseModel):
    id: int
    mode: str
    prompt: str
    quality: str
    size: str
    status: str
    points_cost: int
    balance_source: Optional[str] = None
    workflow_type: str = "standard"
    workflow_cost: int = 0
    workflow_preset: Optional[str] = None
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
    balance_source: Optional[str] = None
    workflow_type: str = "standard"
    workflow_cost: int = 0
    workflow_preset: Optional[str] = None
    created_at: datetime


class OrderCreate(BaseModel):
    order_type: str
    product_id: int
    plan_period: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    order_no: str
    order_type: str
    product_id: int
    plan_period: Optional[str] = None
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


class SubscriptionPlan(BaseModel):
    id: int
    name: str
    plan_key: str
    monthly_price: float
    yearly_price: float
    monthly_quota: int


class TrialPack(BaseModel):
    id: int
    name: str
    price: float
    quota: int
    duration_days: int
    trial_high_quality_limit: int = 0


class WorkflowPreset(BaseModel):
    workflow_type: str
    workflow_preset: Optional[str] = None
    name: str
    description: str
    costs: dict[str, int]
    uses_experience_points: bool = False


class PlansResponse(BaseModel):
    trial_pack: TrialPack
    subscription_plans: list[SubscriptionPlan]
    workflow_presets: list[WorkflowPreset] = []


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
    subscription_plan: Optional[str] = None
    subscription_period: Optional[str] = None
    subscription_expire_at: Optional[datetime] = None
    monthly_quota_remaining: int = 0
    monthly_quota_total: int = 0
    monthly_quota_reset_at: Optional[datetime] = None
    trial_activated: bool = False
    trial_expire_at: Optional[datetime] = None
