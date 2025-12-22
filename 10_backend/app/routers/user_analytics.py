from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.model.user import User
from app.db.schema.user import UserResponse
from app.routers.user import get_current_user
from app.services import analytics as analytics_service
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin/users", tags=["Admin - User Analytics"])

class ChurnMetrics(BaseModel):
    churn_rate: float
    total_churned: int
    active_users: int
    new_signups: int
    total_users: int

async def verify_superuser(current_user: User) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user

@router.get("/", response_model=List[UserResponse])
async def get_all_users_admin(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await verify_superuser(current_user)
    return await analytics_service.get_all_users_admin_service(db)

# (기타 엔드포인트들도 유사하게 서비스 호출로 변경)


@router.get("/new-signups", response_model=List[UserResponse])
async def get_new_signups(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get users who signed up in the last N days (excluding superusers) with recent activity status
    
    **Admin only endpoint**
    """
    await verify_superuser(current_user)
    cutoff_date = datetime.now() - timedelta(days=days)
    
    result = await db.execute(
        select(User)
        .where(
            and_(
                User.created_at >= cutoff_date,
                User.is_superuser == False
            )
        )
        .order_by(User.created_at.desc())
    )
    
    users = result.scalars().all()
    
    # Calculate has_recent_activity for each user
    user_responses = []
    for user in users:
        has_activity = not await is_user_churned(db, user.id, days=30)
        user_dict = {
            **user.__dict__,
            'has_recent_activity': has_activity
        }
        user_responses.append(UserResponse(**user_dict))
    
    return user_responses


@router.get("/churned", response_model=List[UserResponse])
async def get_churned_users(
    days: int = Query(30, ge=1, le=365, description="Days of inactivity to consider churned"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get users with no transactions in the last N days (excluding superusers)
    
    **Admin only endpoint**
    **Note**: This returns users based on transaction history, not is_active field
    """
    await verify_superuser(current_user)
    
    # Get all non-superuser users
    result = await db.execute(
        select(User)
        .where(User.is_superuser == False)
    )
    all_users = result.scalars().all()
    
    # Filter churned users (no transactions in last N days)
    churned_user_responses = []
    for user in all_users:
        if await is_user_churned(db, user.id, days):
            user_dict = {
                **user.__dict__,
                'has_recent_activity': False  # Churned users have no recent activity
            }
            churned_user_responses.append(UserResponse(**user_dict))
    
    return churned_user_responses


@router.get("/stats/churn-rate", response_model=ChurnMetrics)
async def get_churn_rate(
    churn_days: int = Query(30, ge=1, le=365, description="Days of inactivity for churn"),
    signup_days: int = Query(30, ge=1, le=365, description="Days to count new signups"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get churn rate and related metrics based on transaction history
    
    **Admin only endpoint**
    
    - **churn_rate**: Percentage of users with no transactions in last N days
    - **total_churned**: Number of users with no recent transactions
    - **active_users**: Number of users with recent transactions
    - **new_signups**: New users in the specified period
    - **total_users**: Total registered users (excluding superusers)
    """
    await verify_superuser(current_user)
    
    # Get total non-superuser users
    total_result = await db.execute(
        select(func.count(User.id))
        .where(User.is_superuser == False)
    )
    total_users = total_result.scalar() or 0
    
    # Get new signups (excluding superusers)
    signup_cutoff = datetime.now() - timedelta(days=signup_days)
    signup_result = await db.execute(
        select(func.count(User.id))
        .where(
            and_(
                User.created_at >= signup_cutoff,
                User.is_superuser == False
            )
        )
    )
    new_signups = signup_result.scalar() or 0
    
    # Get all non-superuser users and check transaction history
    result = await db.execute(
        select(User)
        .where(User.is_superuser == False)
    )
    all_users = result.scalars().all()
    
    total_churned = 0
    for user in all_users:
        if await is_user_churned(db, user.id, churn_days):
            total_churned += 1
    
    active_users = total_users - total_churned
    churn_rate = (total_churned / total_users * 100) if total_users > 0 else 0.0
    
    return ChurnMetrics(
        churn_rate=round(churn_rate, 2),
        total_churned=total_churned,
        active_users=active_users,
        new_signups=new_signups,
        total_users=total_users
    )
