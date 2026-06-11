from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import (
    DEFAULT_WORKFLOW_TYPE,
    EXPERIENCE_POINTS_QUALITIES,
    FREE_POINTS_TTL_DAYS,
    QUOTA_COST,
    STANDARD_WORKFLOW_TYPE,
    SUBSCRIPTION_PLANS,
    TRIAL_PACK,
    WORKFLOW_QUOTA_COST,
    WORKFLOW_PRESETS,
)
from app.models import User


BALANCE_SOURCE_FREE_POINTS = "free_points"
BALANCE_SOURCE_QUOTA = "quota"
BALANCE_SOURCE_POINTS = "points"


class QuotaError(ValueError):
    pass


@dataclass(frozen=True)
class DeductionResult:
    cost: int
    balance_source: str
    workflow_type: str
    workflow_cost: int


class QuotaManager:
    @staticmethod
    def get_trial_pack() -> dict:
        return TRIAL_PACK

    @staticmethod
    def get_subscription_plans() -> list[dict]:
        return SUBSCRIPTION_PLANS

    @staticmethod
    def get_workflow_presets() -> list[dict]:
        presets: list[dict] = []
        for preset in WORKFLOW_PRESETS:
            workflow_type = QuotaManager.normalize_workflow_type(str(preset["workflow_type"]))
            presets.append(
                {
                    **preset,
                    "workflow_type": workflow_type,
                    "costs": {
                        quality: QuotaManager.get_cost(quality, workflow_type)
                        for quality in QUOTA_COST
                    },
                    "uses_experience_points": workflow_type == STANDARD_WORKFLOW_TYPE,
                }
            )
        return presets

    @staticmethod
    def get_plan_by_id(plan_id: int) -> dict | None:
        return next((plan for plan in SUBSCRIPTION_PLANS if plan["id"] == plan_id), None)

    @staticmethod
    def get_plan_by_key(plan_key: str | None) -> dict | None:
        if not plan_key:
            return None
        return next((plan for plan in SUBSCRIPTION_PLANS if plan["plan_key"] == plan_key), None)

    @staticmethod
    def normalize_workflow_type(workflow_type: str | None) -> str:
        normalized = (workflow_type or DEFAULT_WORKFLOW_TYPE).strip().lower()
        if not normalized:
            normalized = DEFAULT_WORKFLOW_TYPE
        if normalized not in WORKFLOW_QUOTA_COST:
            raise QuotaError(f"Invalid workflow type: {workflow_type}")
        return normalized

    @staticmethod
    def normalize_workflow_preset(workflow_preset: str | None) -> str | None:
        normalized = (workflow_preset or "").strip()
        return normalized or None

    @staticmethod
    def get_cost(quality: str, workflow_type: str | None = None) -> int:
        normalized = quality.lower()
        normalized_workflow = QuotaManager.normalize_workflow_type(workflow_type)
        cost_table = WORKFLOW_QUOTA_COST[normalized_workflow]
        if normalized not in QUOTA_COST or normalized not in cost_table:
            raise QuotaError(f"Invalid quality: {quality}")
        return int(cost_table[normalized])

    @staticmethod
    def get_subscription_price(plan: dict, period: str) -> float:
        if period == "monthly":
            return float(plan["monthly_price"])
        if period == "yearly":
            return float(plan["yearly_price"])
        raise QuotaError("plan_period must be monthly or yearly")

    @staticmethod
    def _period_days(period: str) -> int:
        if period == "monthly":
            return 30
        if period == "yearly":
            return 365
        raise QuotaError("plan_period must be monthly or yearly")

    @staticmethod
    def _free_points_expired(user: User, now: datetime) -> bool:
        return bool(user.free_points_expire_at and user.free_points_expire_at <= now)

    @staticmethod
    def _subscription_active(user: User, now: datetime) -> bool:
        return bool(
            user.subscription_plan
            and user.subscription_plan != "trial"
            and user.member_expire_at
            and user.member_expire_at > now
        )

    @staticmethod
    def subscription_active(user: User, now: datetime | None = None) -> bool:
        return QuotaManager._subscription_active(user, now or datetime.utcnow())

    @staticmethod
    def _trial_active(user: User, now: datetime) -> bool:
        return bool(user.trial_activated and user.trial_expire_at and user.trial_expire_at > now)

    @staticmethod
    def _has_usable_quota(user: User, now: datetime) -> bool:
        return QuotaManager._subscription_active(user, now) or QuotaManager._trial_active(user, now)

    @staticmethod
    def refresh_user_state(user: User, now: datetime | None = None) -> None:
        now = now or datetime.utcnow()

        if QuotaManager._free_points_expired(user, now):
            user.free_points = 0
            user.free_points_expire_at = None

        if QuotaManager._subscription_active(user, now):
            plan = QuotaManager.get_plan_by_key(user.subscription_plan)
            if plan:
                quota = int(plan["monthly_quota"])
                user.monthly_quota_total = quota
                if user.monthly_quota_reset_at is None:
                    user.monthly_quota_reset_at = now + timedelta(days=30)
                elif user.monthly_quota_reset_at <= now:
                    reset_at = user.monthly_quota_reset_at
                    while reset_at <= now:
                        reset_at = reset_at + timedelta(days=30)
                    user.monthly_quota_remaining = quota
                    user.monthly_quota_reset_at = reset_at
            user.is_member = True
            return

        user.is_member = False
        if QuotaManager._trial_active(user, now):
            user.monthly_quota_total = int(TRIAL_PACK["quota"])
            if user.monthly_quota_reset_at is None:
                user.monthly_quota_reset_at = user.trial_expire_at
            return

        if user.monthly_quota_remaining:
            user.monthly_quota_remaining = 0
        if user.monthly_quota_total:
            user.monthly_quota_total = 0
        if user.subscription_plan == "trial":
            user.subscription_plan = None
            user.subscription_period = None
        user.monthly_quota_reset_at = None

    @staticmethod
    async def refresh_user_state_for_update(db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id).with_for_update())
        user = result.scalar_one_or_none()
        if user is None:
            return None
        QuotaManager.refresh_user_state(user)
        await db.flush()
        return user

    @staticmethod
    async def deduct_for_generation(
        db: AsyncSession,
        user_id: int,
        quality: str,
        workflow_type: str | None = None,
    ) -> DeductionResult:
        normalized_quality = quality.lower()
        normalized_workflow = QuotaManager.normalize_workflow_type(workflow_type)
        cost = QuotaManager.get_cost(normalized_quality, normalized_workflow)
        user = await QuotaManager.refresh_user_state_for_update(db, user_id)
        if user is None:
            raise QuotaError("User not found")

        if (
            normalized_workflow == STANDARD_WORKFLOW_TYPE
            and normalized_quality in EXPERIENCE_POINTS_QUALITIES
            and (user.free_points or 0) >= cost
        ):
            user.free_points -= cost
            await db.flush()
            return DeductionResult(
                cost=cost,
                balance_source=BALANCE_SOURCE_FREE_POINTS,
                workflow_type=normalized_workflow,
                workflow_cost=cost,
            )

        if QuotaManager._has_usable_quota(user, datetime.utcnow()) and (user.monthly_quota_remaining or 0) >= cost:
            user.monthly_quota_remaining -= cost
            await db.flush()
            return DeductionResult(
                cost=cost,
                balance_source=BALANCE_SOURCE_QUOTA,
                workflow_type=normalized_workflow,
                workflow_cost=cost,
            )

        if normalized_quality == "high":
            raise QuotaError("High quality generation requires subscription quota")
        raise QuotaError("Insufficient experience points and subscription quota")

    @staticmethod
    async def refund_generation(db: AsyncSession, user_id: int, cost: int, balance_source: str | None) -> None:
        result = await db.execute(select(User).where(User.id == user_id).with_for_update())
        user = result.scalar_one_or_none()
        if user is None or cost <= 0:
            return

        if balance_source == BALANCE_SOURCE_FREE_POINTS:
            user.free_points = (user.free_points or 0) + cost
            now = datetime.utcnow()
            if not user.free_points_expire_at or user.free_points_expire_at <= now:
                user.free_points_expire_at = now + timedelta(days=FREE_POINTS_TTL_DAYS)
        elif balance_source == BALANCE_SOURCE_QUOTA:
            total = user.monthly_quota_total or 0
            next_value = (user.monthly_quota_remaining or 0) + cost
            user.monthly_quota_remaining = min(total, next_value) if total else next_value
        else:
            user.points = (user.points or 0) + cost

        await db.flush()

    @staticmethod
    async def activate_trial(db: AsyncSession, user_id: int) -> None:
        result = await db.execute(select(User).where(User.id == user_id).with_for_update())
        user = result.scalar_one_or_none()
        if user is None:
            return

        now = datetime.utcnow()
        if QuotaManager._subscription_active(user, now):
            raise QuotaError("Trial pack is not available for active subscriptions")
        user.trial_activated = True
        user.trial_expire_at = now + timedelta(days=int(TRIAL_PACK["duration_days"]))
        user.trial_high_quality_used = 0
        user.subscription_plan = "trial"
        user.subscription_period = "trial"
        user.monthly_quota_total = int(TRIAL_PACK["quota"])
        user.monthly_quota_remaining = int(TRIAL_PACK["quota"])
        user.monthly_quota_reset_at = user.trial_expire_at
        await db.flush()

    @staticmethod
    async def activate_subscription(db: AsyncSession, user_id: int, plan_key: str, period: str) -> None:
        plan = QuotaManager.get_plan_by_key(plan_key)
        if plan is None:
            raise QuotaError("Invalid subscription plan")
        duration_days = QuotaManager._period_days(period)

        result = await db.execute(select(User).where(User.id == user_id).with_for_update())
        user = result.scalar_one_or_none()
        if user is None:
            return

        now = datetime.utcnow()
        QuotaManager.refresh_user_state(user, now)
        active_same_plan = (
            QuotaManager._subscription_active(user, now)
            and user.subscription_plan == plan_key
            and user.subscription_period == period
        )
        active_base = user.member_expire_at if user.member_expire_at and user.member_expire_at > now else now

        user.subscription_plan = plan_key
        user.subscription_period = period
        user.member_expire_at = active_base + timedelta(days=duration_days)
        user.is_member = True
        user.monthly_quota_total = int(plan["monthly_quota"])

        if not active_same_plan:
            user.monthly_quota_remaining = int(plan["monthly_quota"])
            user.monthly_quota_reset_at = now + timedelta(days=30)
        elif user.monthly_quota_reset_at is None:
            user.monthly_quota_reset_at = now + timedelta(days=30)

        await db.flush()
