import random
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus


class PaymentSimulator:
    POINTS_PACKS = [
        {"id": 1, "name": "50积分", "price": 10.0, "points": 50},
        {"id": 2, "name": "140积分", "price": 25.0, "points": 140},
        {"id": 3, "name": "300积分", "price": 50.0, "points": 300},
    ]

    MEMBERSHIP_PLANS = [
        {"id": 1, "name": "月度会员", "price": 39.0, "points_bonus": 260, "duration_days": 30},
        {"id": 2, "name": "季度会员", "price": 109.0, "points_bonus": 720, "duration_days": 90},
        {"id": 3, "name": "年度会员", "price": 399.0, "points_bonus": 2700, "duration_days": 365},
    ]

    @staticmethod
    def generate_order_no() -> str:
        timestamp = str(int(time.time() * 1000))
        rand = "".join(random.choices("0123456789", k=6))
        return f"ORD{timestamp}{rand}"

    @staticmethod
    async def create_order(
        db: AsyncSession, user_id: int, order_type: str, product_id: int, amount: float
    ) -> Order:
        order_no = PaymentSimulator.generate_order_no()
        order = Order(
            user_id=user_id,
            order_no=order_no,
            order_type=order_type,
            product_id=product_id,
            amount=amount,
            status=OrderStatus.PENDING,
        )
        db.add(order)
        await db.flush()
        return order

    @staticmethod
    async def process_callback(db: AsyncSession, order_no: str) -> Order:
        result = await db.execute(select(Order).where(Order.order_no == order_no))
        order = result.scalar_one_or_none()
        if order is None:
            raise ValueError("Order not found")
        if order.status == OrderStatus.PAID:
            raise ValueError("Order already paid")
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Order is not pending, current status: {order.status}")

        order.status = OrderStatus.PAID
        from datetime import datetime

        order.paid_at = datetime.utcnow()
        await db.flush()
        return order
