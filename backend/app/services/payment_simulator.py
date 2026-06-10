import random
import time
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus


class PaymentSimulator:
    @staticmethod
    def generate_order_no() -> str:
        timestamp = str(int(time.time() * 1000))
        rand = "".join(random.choices("0123456789", k=6))
        return f"ORD{timestamp}{rand}"

    @staticmethod
    async def create_order(
        db: AsyncSession,
        user_id: int,
        order_type: str,
        product_id: int,
        amount: float,
        plan_period: str | None = None,
    ) -> Order:
        order = Order(
            user_id=user_id,
            order_no=PaymentSimulator.generate_order_no(),
            order_type=order_type,
            product_id=product_id,
            plan_period=plan_period,
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
        order.paid_at = datetime.utcnow()
        await db.flush()
        return order
