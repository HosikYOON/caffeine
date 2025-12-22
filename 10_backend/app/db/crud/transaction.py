from sqlalchemy import and_, func, or_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
from app.db.model.transaction import Transaction, Category, Anomaly

async def get_transactions(
    db: AsyncSession,
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    query = select(Transaction).options(selectinload(Transaction.category))
    count_query = select(func.count(Transaction.id))
    
    conditions = []
    if user_id is not None:
        conditions.append(Transaction.user_id == user_id)
    if start_date:
        conditions.append(Transaction.transaction_time >= start_date)
    if end_date:
        conditions.append(Transaction.transaction_time <= end_date)
    if min_amount is not None:
        conditions.append(Transaction.amount >= min_amount)
    if max_amount is not None:
        conditions.append(Transaction.amount <= max_amount)
    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                Transaction.merchant_name.ilike(search_pattern),
                Transaction.description.ilike(search_pattern)
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    offset = (page - 1) * page_size
    query = query.order_by(Transaction.transaction_time.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    return total, result.scalars().all()

async def delete_user_transactions(db: AsyncSession, user_id: int):
    delete_stmt = delete(Transaction).where(Transaction.user_id == user_id)
    result = await db.execute(delete_stmt)
    await db.commit()
    return result.rowcount

async def get_transaction_by_id(db: AsyncSession, transaction_id: int):
    query = select(Transaction).options(selectinload(Transaction.category)).where(Transaction.id == transaction_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def update_transaction_description(db: AsyncSession, transaction_id: int, description: str):
    update_query = (
        update(Transaction)
        .where(Transaction.id == transaction_id)
        .values(description=description)
    )
    await db.execute(update_query)
    await db.commit()
    return True

async def create_anomaly_report(db: AsyncSession, transaction_id: int, user_id: int, severity: str, reason: str):
    from sqlalchemy import insert
    insert_query = insert(Anomaly).values(
        transaction_id=transaction_id,
        user_id=user_id,
        severity=severity,
        reason=reason,
        is_resolved=False
    )
    await db.execute(insert_query)
    await db.commit()
    return True
