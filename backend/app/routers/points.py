from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ADMIN_USERNAMES
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    GenerationOptionsResponse,
    PlansResponse,
    PointsBalanceResponse,
    PointsPack,
    SubscriptionPlan,
    TrialPack,
    WorkflowPreset,
)
from app.services.generation_options import GenerationOptions
from app.services.quota_manager import QuotaManager

router = APIRouter(prefix="/points", tags=["points"])


@router.get("/packs", response_model=list[PointsPack])
async def list_packs():
    return []


@router.get("/plans", response_model=PlansResponse)
async def list_plans():
    return PlansResponse(
        trial_pack=TrialPack(**QuotaManager.get_trial_pack()),
        subscription_plans=[
            SubscriptionPlan(**plan) for plan in QuotaManager.get_subscription_plans()
        ],
        workflow_presets=[
            WorkflowPreset(**preset) for preset in QuotaManager.get_workflow_presets()
        ],
        generation_options=GenerationOptionsResponse(
            qualities=GenerationOptions.get_quality_options(),
            image_size_groups=GenerationOptions.get_image_size_groups(),
            constraints=GenerationOptions.get_constraints(),
        ),
    )


@router.get("/balance", response_model=PointsBalanceResponse)
async def get_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    QuotaManager.refresh_user_state(current_user)
    await db.commit()
    await db.refresh(current_user)

    return PointsBalanceResponse(
        username=current_user.username,
        points=current_user.points,
        free_points=current_user.free_points,
        free_points_expire_at=current_user.free_points_expire_at,
        is_member=current_user.is_member,
        member_expire_at=current_user.member_expire_at,
        subscription_plan=current_user.subscription_plan,
        subscription_period=current_user.subscription_period,
        subscription_expire_at=current_user.member_expire_at,
        monthly_quota_remaining=current_user.monthly_quota_remaining,
        monthly_quota_total=current_user.monthly_quota_total,
        monthly_quota_reset_at=current_user.monthly_quota_reset_at,
        trial_activated=current_user.trial_activated,
        trial_expire_at=current_user.trial_expire_at,
        is_admin=current_user.is_admin or current_user.username in ADMIN_USERNAMES,
    )
