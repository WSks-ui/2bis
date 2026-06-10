from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Order, OrderStatus, User
from app.schemas import OrderCreate, OrderResponse
from app.services.payment_simulator import PaymentSimulator
from app.services.quota_manager import QuotaError, QuotaManager

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/orders", response_model=OrderResponse)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order_type = data.order_type.lower()
    plan_period = data.plan_period.lower() if data.plan_period else None

    if order_type == "trial":
        if current_user.trial_activated:
            raise HTTPException(status_code=400, detail="Trial pack has already been used")
        if QuotaManager.subscription_active(current_user):
            raise HTTPException(
                status_code=400,
                detail="Trial pack is not available for active subscriptions",
            )
        trial_pack = QuotaManager.get_trial_pack()
        if data.product_id != trial_pack["id"]:
            raise HTTPException(status_code=400, detail="Invalid product_id")
        amount = float(trial_pack["price"])
        plan_period = None
    elif order_type == "subscription":
        plan = QuotaManager.get_plan_by_id(data.product_id)
        if plan is None:
            raise HTTPException(status_code=400, detail="Invalid product_id")
        try:
            amount = QuotaManager.get_subscription_price(plan, plan_period or "")
        except QuotaError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        raise HTTPException(status_code=400, detail="order_type must be trial or subscription")

    order = await PaymentSimulator.create_order(
        db,
        current_user.id,
        order_type,
        data.product_id,
        amount,
        plan_period=plan_period,
    )
    await db.commit()
    await db.refresh(order)

    return OrderResponse(
        id=order.id,
        order_no=order.order_no,
        order_type=order.order_type,
        product_id=order.product_id,
        plan_period=order.plan_period,
        amount=order.amount,
        status=order.status.value,
        created_at=order.created_at,
        qr_code_text=f"Mock payment order: {order.order_no}",
    )


@router.post("/mock-pay-callback")
async def mock_pay_callback(
    order_no: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Order).where(Order.order_no == order_no).with_for_update()
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Order does not belong to current user")

    already_paid = order.status == OrderStatus.PAID
    if not already_paid:
        order.status = OrderStatus.PAID
        order.paid_at = datetime.utcnow()

        if order.order_type == "trial":
            try:
                await QuotaManager.activate_trial(db, current_user.id)
            except QuotaError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        elif order.order_type == "subscription":
            plan = QuotaManager.get_plan_by_id(order.product_id)
            if plan is None:
                raise HTTPException(status_code=400, detail="Invalid subscription plan")
            try:
                await QuotaManager.activate_subscription(
                    db,
                    current_user.id,
                    plan["plan_key"],
                    order.plan_period or "",
                )
            except QuotaError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=400, detail="Unsupported order type")

    await db.commit()
    await db.refresh(current_user)
    await db.refresh(order)
    QuotaManager.refresh_user_state(current_user)

    return {
        "message": "Payment successful" if not already_paid else "Order already paid",
        "order_no": order.order_no,
        "status": order.status.value,
        "free_points": current_user.free_points,
        "monthly_quota_remaining": current_user.monthly_quota_remaining,
        "monthly_quota_total": current_user.monthly_quota_total,
        "monthly_quota_reset_at": current_user.monthly_quota_reset_at,
        "subscription_plan": current_user.subscription_plan,
        "subscription_period": current_user.subscription_period,
        "subscription_expire_at": current_user.member_expire_at,
        "trial_activated": current_user.trial_activated,
        "trial_expire_at": current_user.trial_expire_at,
    }
