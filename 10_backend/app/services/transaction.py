from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Tuple
from datetime import datetime
from app.db.crud import transaction as transaction_crud
from app.db.schema.transaction import TransactionBase, TransactionList, TransactionCreate, TransactionBulkResponse

async def get_transactions_service(
    db: AsyncSession,
    user_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[int, List[TransactionBase]]:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
    
    total, rows = await transaction_crud.get_transactions(
        db, user_id, start_dt, end_dt, min_amount, max_amount, search, page, page_size
    )
    
    transactions = []
    for tx in rows:
        cat_name = tx.category.name if tx.category else "기타"
        transactions.append(TransactionBase(
            id=tx.id,
            merchant=tx.merchant_name or "알 수 없음",
            amount=float(tx.amount),
            category=cat_name,
            transaction_date=tx.transaction_time.strftime("%Y-%m-%d %H:%M:%S") if tx.transaction_time else "",
            description=tx.description,
            status=tx.status,
            currency=tx.currency
        ))
    
    return total, transactions

from sqlalchemy import insert, select
from app.db.model.transaction import Transaction, Category
import logging

logger = logging.getLogger(__name__)

async def bulk_create_transactions_service(
    db: AsyncSession,
    user_id: int,
    transactions_data: List[TransactionCreate]
) -> TransactionBulkResponse:
    try:
        created_count = 0
        failed_count = 0
        
        # 카테고리 매핑 조회
        cat_result = await db.execute(select(Category))
        categories = {c.name.strip(): c.id for c in cat_result.scalars().all()}
        
        for tx in transactions_data:
            try:
                # 카테고리 결정
                category_id = categories.get(tx.category.strip())
                if not category_id:
                    category_id = categories.get('기타') or (list(categories.values())[0] if categories else None)
                
                # 날짜 처리
                try:
                    tx_time = datetime.strptime(tx.transaction_date, "%Y-%m-%d %H:%M:%S")
                except:
                    tx_time = datetime.now()
                
                insert_stmt = insert(Transaction).values(
                    user_id=user_id, category_id=category_id, amount=tx.amount,
                    currency=tx.currency, merchant_name=tx.merchant,
                    description=tx.description, status="completed", transaction_time=tx_time
                )
                await db.execute(insert_stmt)
                created_count += 1
            except Exception as e:
                logger.warning(f"Individual transaction create failed: {e}")
                failed_count += 1
        
        await db.commit()
        return TransactionBulkResponse(
            status="success", created_count=created_count, failed_count=failed_count,
            message=f"{created_count}건 생성 완료"
        )
    except Exception as e:
        logger.error(f"Bulk creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
