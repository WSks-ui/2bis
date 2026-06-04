from fastapi import APIRouter

from app.schemas import MembershipPlan
from app.services.payment_simulator import PaymentSimulator

router = APIRouter(prefix="/membership", tags=["membership"])


@router.get("/plans", response_model=list[MembershipPlan])
async def list_plans():
    return [MembershipPlan(**p) for p in PaymentSimulator.MEMBERSHIP_PLANS]
