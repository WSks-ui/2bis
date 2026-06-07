from datetime import datetime, timedelta
import asyncio

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ACCESS_TOKEN_EXPIRE_DAYS, ALGORITHM, SECRET_KEY
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import LoginCheckinResponse, TokenResponse, UserInfo, UserLogin, UserRegister
from app.services.checkin_service import checkin_status, perform_checkin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserInfo)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # bcrypt 是 CPU 密集型,放到线程池执行,避免阻塞 asyncio 事件循环
    hashed_password = await asyncio.to_thread(
        bcrypt.hashpw, data.password.encode("utf-8"), bcrypt.gensalt()
    )
    user = User(
        username=data.username,
        hashed_password=hashed_password.decode("utf-8"),
        points=0,
        is_member=False,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserInfo(
        id=user.id,
        username=user.username,
        points=user.points,
        free_points=user.free_points,
        free_points_expire_at=user.free_points_expire_at,
        is_member=user.is_member,
        member_expire_at=user.member_expire_at,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # 同样放到线程池,避免阻塞事件循环
    password_valid = await asyncio.to_thread(
        bcrypt.checkpw,
        data.password.encode("utf-8"),
        user.hashed_password.encode("utf-8"),
    )
    if not password_valid:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user.id), "exp": expire}
    access_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return TokenResponse(access_token=access_token)


@router.post("/checkin", response_model=LoginCheckinResponse)
async def daily_checkin(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    status = checkin_status(current_user)
    if not status["checkin_available"]:
        return LoginCheckinResponse(**status)

    result = await perform_checkin(current_user, db)
    return LoginCheckinResponse(
        checkin_available=True,
        consecutive_days=result["consecutive_days"],
        day_number=result["day_number"],
        reward=result["reward"],
        free_points=result["free_points"],
        free_points_expire_at=result["free_points_expire_at"],
        bonus_rule=checkin_status(current_user)["bonus_rule"],
    )


@router.get("/checkin/status", response_model=LoginCheckinResponse)
async def get_checkin_status(
    current_user: User = Depends(get_current_user),
):
    return LoginCheckinResponse(**checkin_status(current_user))
