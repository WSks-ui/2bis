import enum
from datetime import datetime, date

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)
    points = Column(Integer, default=0, nullable=False)
    free_points = Column(Integer, default=0, nullable=False)
    free_points_expire_at = Column(DateTime, nullable=True)
    last_checkin_date = Column(Date, nullable=True)
    consecutive_days = Column(Integer, default=0, nullable=False)
    is_member = Column(Boolean, default=False, nullable=False)
    member_expire_at = Column(DateTime, nullable=True)
    subscription_plan = Column(String(30), nullable=True)
    subscription_period = Column(String(20), nullable=True)
    monthly_quota_total = Column(Integer, default=0, nullable=False)
    monthly_quota_remaining = Column(Integer, default=0, nullable=False)
    monthly_quota_reset_at = Column(DateTime, nullable=True)
    trial_activated = Column(Boolean, default=False, nullable=False)
    trial_expire_at = Column(DateTime, nullable=True)
    trial_high_quality_used = Column(Integer, default=0, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    histories = relationship("GenerateHistory", back_populates="user", lazy="dynamic")
    tasks = relationship("GenerationTask", back_populates="user", lazy="dynamic")
    orders = relationship("Order", back_populates="user", lazy="dynamic")


class DailyCheckin(Base):
    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    checkin_date = Column(Date, nullable=False, index=True)
    day_number = Column(Integer, nullable=False)
    reward = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class GenerationTaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class GenerationTask(Base):
    __tablename__ = "generation_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mode = Column(String(20), nullable=False, default="text2img")
    prompt = Column(Text, nullable=False)
    quality = Column(String(20), nullable=False, default="medium")
    size = Column(String(40), nullable=False, default="1024x1024")
    status = Column(Enum(GenerationTaskStatus), default=GenerationTaskStatus.PENDING, nullable=False, index=True)
    points_cost = Column(Integer, nullable=False, default=0)
    balance_source = Column(String(20), nullable=True)
    workflow_type = Column(String(40), nullable=False, default="standard")
    workflow_cost = Column(Integer, nullable=False, default=0)
    workflow_preset = Column(String(80), nullable=True)
    image_url = Column(Text, nullable=True)
    source_image_path = Column(Text, nullable=True)
    source_image_mime_type = Column(String(50), nullable=True)
    source_image_paths = Column(Text, nullable=True)
    source_image_mime_types = Column(Text, nullable=True)
    upstream_model = Column(String(80), nullable=True)
    upstream_endpoint = Column(String(120), nullable=True)
    upstream_request_quality = Column(String(30), nullable=True)
    upstream_request_size = Column(String(40), nullable=True)
    upstream_response_format = Column(String(30), nullable=True)
    upstream_request_id = Column(String(120), nullable=True)
    upstream_content_type = Column(String(120), nullable=True)
    upstream_elapsed_seconds = Column(Float, nullable=True)
    upstream_header_seconds = Column(Float, nullable=True)
    upstream_body_seconds = Column(Float, nullable=True)
    upstream_parse_seconds = Column(Float, nullable=True)
    upstream_save_seconds = Column(Float, nullable=True)
    upstream_body_bytes = Column(Integer, nullable=True)
    upstream_content_length = Column(Integer, nullable=True)
    upstream_transfer_encoding = Column(String(80), nullable=True)
    upstream_payload_length = Column(Integer, nullable=True)
    progress_stage = Column(String(40), nullable=True)
    progress_message = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=2)
    locked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="tasks")


class GenerateHistory(Base):
    __tablename__ = "generate_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("generation_tasks.id"), nullable=True, index=True)
    prompt = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    quality = Column(String(20), nullable=False, default="medium")
    points_cost = Column(Integer, nullable=False, default=0)
    balance_source = Column(String(20), nullable=True)
    workflow_type = Column(String(40), nullable=False, default="standard")
    workflow_cost = Column(Integer, nullable=False, default=0)
    workflow_preset = Column(String(80), nullable=True)
    upstream_model = Column(String(80), nullable=True)
    upstream_endpoint = Column(String(120), nullable=True)
    upstream_request_quality = Column(String(30), nullable=True)
    upstream_request_size = Column(String(40), nullable=True)
    upstream_response_format = Column(String(30), nullable=True)
    upstream_request_id = Column(String(120), nullable=True)
    upstream_content_type = Column(String(120), nullable=True)
    upstream_elapsed_seconds = Column(Float, nullable=True)
    upstream_header_seconds = Column(Float, nullable=True)
    upstream_body_seconds = Column(Float, nullable=True)
    upstream_parse_seconds = Column(Float, nullable=True)
    upstream_save_seconds = Column(Float, nullable=True)
    upstream_body_bytes = Column(Integer, nullable=True)
    upstream_content_length = Column(Integer, nullable=True)
    upstream_transfer_encoding = Column(String(80), nullable=True)
    upstream_payload_length = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="histories")


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    order_no = Column(String(64), unique=True, nullable=False, index=True)
    order_type = Column(String(20), nullable=False)
    product_id = Column(Integer, nullable=False)
    plan_period = Column(String(20), nullable=True)
    amount = Column(Float, nullable=False, default=0.0)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="orders")


class ApiKeyConfig(Base):
    __tablename__ = "api_key_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), nullable=False)
    provider = Column(String(40), nullable=False, default="aiartmirror")
    api_url = Column(String(255), nullable=False)
    encrypted_api_key = Column(Text, nullable=False)
    key_mask = Column(String(80), nullable=False)
    response_format = Column(String(30), nullable=True)
    send_quality = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    is_enabled = Column(Boolean, default=True, nullable=False, index=True)
    circuit_state = Column(String(20), default="closed", nullable=False)
    circuit_reason = Column(Text, nullable=True)
    circuit_open_until = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0, nullable=False)
    last_failure_at = Column(DateTime, nullable=True)
    last_test_status = Column(String(20), nullable=True)
    last_test_message = Column(Text, nullable=True)
    last_tested_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    target_type = Column(String(60), nullable=False)
    target_id = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
