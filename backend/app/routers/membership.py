from fastapi import APIRouter

from app.schemas import MembershipPlan

router = APIRouter(prefix="/membership", tags=["membership"])


@router.get("/plans", response_model=list[MembershipPlan])
async def list_plans():
    return []
