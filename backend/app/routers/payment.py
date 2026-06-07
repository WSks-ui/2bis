from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Order, OrderStatus, User
from app.schemas import OrderCreate, OrderResponse
from app.services.payment_simulator import PaymentSimulator
from app.services.point_manager import PointManager

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/orders", response_model=OrderResponse)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.order_type == "points_pack":
        pack = next(
            (p for p in PaymentSimulator.POINTS_PACKS if p["id"] == data.product_id),
            None,
        )
        if pack is None:
            raise HTTPException(status_code=400, detail="Invalid product_id")
        amount = pack["price"]
    elif data.order_type == "membership":
        plan = next(
            (p for p in PaymentSimulator.MEMBERSHIP_PLANS if p["id"] == data.product_id),
            None,
        )
        if plan is None:
            raise HTTPException(status_code=400, detail="Invalid product_id")
        amount = plan["price"]
    else:
        raise HTTPException(
            status_code=400, detail="order_type must be points_pack or membership"
        )

    order = await PaymentSimulator.create_order(
        db, current_user.id, data.order_type, data.product_id, amount
    )
    await db.commit()
    await db.refresh(order)

    qr_code_text = f"模拟支付订单: {order.order_no}，请点击模拟支付按钮完成支付"
    return OrderResponse(
        id=order.id,
        order_no=order.order_no,
        order_type=order.order_type,
        product_id=order.product_id,
        amount=order.amount,
        status=order.status.value,
        created_at=order.created_at,
        qr_code_text=qr_code_text,
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

        if order.order_type == "points_pack":
            pack = next(
                (p for p in PaymentSimulator.POINTS_PACKS if p["id"] == order.product_id),
                None,
            )
            if pack:
                await PointManager.add_points(db, current_user.id, pack["points"])
        elif order.order_type == "membership":
            plan = next(
                (p for p in PaymentSimulator.MEMBERSHIP_PLANS if p["id"] == order.product_id),
                None,
            )
            if plan:
                await PointManager.activate_membership(
                    db, current_user.id, plan["duration_days"], plan["points_bonus"]
                )

    await db.commit()
    await db.refresh(current_user)
    await db.refresh(order)

    return {
        "message": "支付成功" if not already_paid else "订单已支付",
        "order_no": order.order_no,
        "status": order.status.value,
        "points": current_user.points,
        "is_member": current_user.is_member,
        "member_expire_at": current_user.member_expire_at,
    }
