from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional, List
import logging

from app.db.database import get_db
from app.db.schema.transaction import (
    TransactionBase, TransactionList, TransactionBulkRequest, 
    TransactionBulkResponse, TransactionUpdate, AnomalyReport
)
from app.services import transaction as transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])
DB_Dependency = Annotated[AsyncSession, Depends(get_db)]

@router.get("", response_model=TransactionList)
async def get_transactions(
    user_id: Optional[int] = Query(None, description="사용자 ID 필터"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    min_amount: Optional[float] = Query(None, description="최소 금액"),
    max_amount: Optional[float] = Query(None, description="최대 금액"),
    search: Optional[str] = Query(None, description="검색어 (가맹점명, 메모)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=1000000, description="페이지 크기"),
    db: DB_Dependency = None
):
    """거래 내역 검색 및 필터링 조회"""
    total, transactions = await transaction_service.get_transactions_service(
        db, user_id, start_date, end_date, min_amount, max_amount, search, page, page_size
    )
    return TransactionList(total=total, transactions=transactions, page=page, page_size=page_size)

@router.post("/bulk", response_model=TransactionBulkResponse)
async def create_bulk_transactions(data: TransactionBulkRequest, db: DB_Dependency):
    """거래 내역 일괄 생성"""
    return await transaction_service.bulk_create_transactions_service(db, data.user_id, data.transactions)

@router.delete("")
async def delete_all_transactions(user_id: int = Query(..., description="사용자 ID"), db: DB_Dependency = None):
    """사용자의 모든 데이터 삭제"""
    from app.db.crud import transaction as crud
    count = await crud.delete_user_transactions(db, user_id)
    return {"status": "success", "message": f"{count}건 삭제 완료"}

@router.get("/{transaction_id}", response_model=TransactionBase)
async def get_transaction(transaction_id: int, db: DB_Dependency = None):
    """단일 거래 상세 조회"""
    from app.db.crud import transaction as crud
    tx = await crud.get_transaction_by_id(db, transaction_id)
    if not tx: raise HTTPException(status_code=404, detail="Not found")
    return TransactionBase(
        id=tx.id, merchant=tx.merchant_name or "알 수 없음", amount=float(tx.amount),
        category=tx.category.name if tx.category else "기타",
        transaction_date=tx.transaction_time.strftime("%Y-%m-%d %H:%M:%S") if tx.transaction_time else "",
        description=tx.description, status=tx.status, currency=tx.currency
    )

@router.patch("/{transaction_id}/note")
async def update_transaction_note(transaction_id: int, update_data: TransactionUpdate, db: DB_Dependency = None):
    """거래 메모 수정"""
    from app.db.crud import transaction as crud
    await crud.update_transaction_description(db, transaction_id, update_data.description)
    return {"status": "success", "message": "Updated"}

@router.post("/{transaction_id}/anomaly-report")
async def report_anomaly(transaction_id: int, report: AnomalyReport, db: DB_Dependency = None):
    """이상거래 신고"""
    from app.db.crud import transaction as crud
    tx = await crud.get_transaction_by_id(db, transaction_id)
    if not tx: raise HTTPException(status_code=404, detail="Not found")
    await crud.create_anomaly_report(db, transaction_id, tx.user_id, report.severity, report.reason)
    return {"status": "success", "message": "Reported"}
