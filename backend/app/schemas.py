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
    is_admin: bool = False
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
    upstream_model: Optional[str] = None
    upstream_endpoint: Optional[str] = None
    upstream_request_quality: Optional[str] = None
    upstream_request_size: Optional[str] = None
    upstream_response_format: Optional[str] = None
    upstream_request_id: Optional[str] = None
    upstream_content_type: Optional[str] = None
    upstream_elapsed_seconds: Optional[float] = None
    upstream_header_seconds: Optional[float] = None
    upstream_body_seconds: Optional[float] = None
    upstream_parse_seconds: Optional[float] = None
    upstream_save_seconds: Optional[float] = None
    upstream_body_bytes: Optional[int] = None
    upstream_content_length: Optional[int] = None
    upstream_transfer_encoding: Optional[str] = None
    upstream_payload_length: Optional[int] = None
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
    upstream_model: Optional[str] = None
    upstream_endpoint: Optional[str] = None
    upstream_request_quality: Optional[str] = None
    upstream_request_size: Optional[str] = None
    upstream_response_format: Optional[str] = None
    upstream_request_id: Optional[str] = None
    upstream_content_type: Optional[str] = None
    upstream_elapsed_seconds: Optional[float] = None
    upstream_header_seconds: Optional[float] = None
    upstream_body_seconds: Optional[float] = None
    upstream_parse_seconds: Optional[float] = None
    upstream_save_seconds: Optional[float] = None
    upstream_body_bytes: Optional[int] = None
    upstream_content_length: Optional[int] = None
    upstream_transfer_encoding: Optional[str] = None
    upstream_payload_length: Optional[int] = None
    progress_stage: Optional[str] = None
    progress_message: Optional[str] = None
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
    thumbnail_url: Optional[str] = None
    quality: str
    points_cost: int
    balance_source: Optional[str] = None
    workflow_type: str = "standard"
    workflow_cost: int = 0
    workflow_preset: Optional[str] = None
    upstream_model: Optional[str] = None
    upstream_endpoint: Optional[str] = None
    upstream_request_quality: Optional[str] = None
    upstream_request_size: Optional[str] = None
    upstream_response_format: Optional[str] = None
    upstream_request_id: Optional[str] = None
    upstream_content_type: Optional[str] = None
    upstream_elapsed_seconds: Optional[float] = None
    upstream_header_seconds: Optional[float] = None
    upstream_body_seconds: Optional[float] = None
    upstream_parse_seconds: Optional[float] = None
    upstream_save_seconds: Optional[float] = None
    upstream_body_bytes: Optional[int] = None
    upstream_content_length: Optional[int] = None
    upstream_transfer_encoding: Optional[str] = None
    upstream_payload_length: Optional[int] = None
    created_at: datetime


class HistoryPageResponse(BaseModel):
    records: list[HistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int


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


class QualityOption(BaseModel):
    label: str
    value: str


class ImageSizeOption(BaseModel):
    label: str
    value: str


class ImageSizeGroup(BaseModel):
    ratio: str
    name: str
    sizes: list[ImageSizeOption]


class GenerationConstraints(BaseModel):
    max_long_edge: int
    max_pixels: int
    min_edge: int
    allowed_upload_mime_types: list[str]


class GenerationOptionsResponse(BaseModel):
    qualities: list[QualityOption]
    image_size_groups: list[ImageSizeGroup]
    constraints: GenerationConstraints


class PlansResponse(BaseModel):
    trial_pack: TrialPack
    subscription_plans: list[SubscriptionPlan]
    workflow_presets: list[WorkflowPreset] = []
    generation_options: GenerationOptionsResponse


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
    is_admin: bool = False


class AdminApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    provider: str = Field(default="aiartmirror", min_length=1, max_length=40)
    api_url: str = Field(default="https://www.aiartmirror.com/v1", min_length=8, max_length=255)
    api_key: str = Field(..., min_length=8, max_length=4096)
    response_format: Optional[str] = Field(default=None, max_length=30)
    send_quality: bool = True
    is_enabled: bool = True
    activate: bool = True
    test_before_activate: bool = False


class AdminApiKeyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    provider: Optional[str] = Field(default=None, min_length=1, max_length=40)
    api_url: Optional[str] = Field(default=None, min_length=8, max_length=255)
    api_key: Optional[str] = Field(default=None, min_length=8, max_length=4096)
    response_format: Optional[str] = Field(default=None, max_length=30)
    clear_response_format: bool = False
    send_quality: Optional[bool] = None
    is_enabled: Optional[bool] = None


class AdminApiKeyResponse(BaseModel):
    id: int
    name: str
    provider: str
    api_url: str
    key_mask: str
    response_format: Optional[str] = None
    send_quality: bool = True
    is_active: bool
    is_enabled: bool
    circuit_state: str = "closed"
    circuit_reason: Optional[str] = None
    circuit_open_until: Optional[datetime] = None
    failure_count: int = 0
    last_failure_at: Optional[datetime] = None
    last_test_status: Optional[str] = None
    last_test_message: Optional[str] = None
    last_tested_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AdminApiKeyTestRequest(BaseModel):
    api_url: Optional[str] = Field(default=None, min_length=8, max_length=255)
    api_key: Optional[str] = Field(default=None, min_length=8, max_length=4096)
    response_format: Optional[str] = Field(default=None, max_length=30)


class AdminApiKeyTestResponse(BaseModel):
    ok: bool
    message: str
    tested_at: datetime
