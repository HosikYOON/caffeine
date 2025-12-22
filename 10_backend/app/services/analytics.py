from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.model.user import User
from app.db.model.transaction import Transaction
from app.db.schema.user import UserResponse

async def is_user_churned_service(db: AsyncSession, user_id: int, days: int = 30) -> bool:
    cutoff_date = datetime.now() - timedelta(days=days)
    result = await db.execute(
        select(Transaction)
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.transaction_time >= cutoff_date
            )
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is None

async def get_all_users_admin_service(db: AsyncSession) -> List[UserResponse]:
    result = await db.execute(
        select(User)
        .where(User.is_superuser == False)
        .order_by(User.id.asc())
    )
    users = result.scalars().all()
    
    user_responses = []
    for user in users:
        has_activity = not await is_user_churned_service(db, user.id, days=30)
        user_responses.append(UserResponse(**{**user.__dict__, 'has_recent_activity': has_activity}))
    
    return user_responses

# (기타 지표 계산 로직들도 여기로 이관 가능)
