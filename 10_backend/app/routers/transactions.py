from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.orm import selectinload
from typing import Annotated, Optional, List
from datetime import datetime, timedelta
import logging
from pydantic import BaseModel

from app.db.database import get_db
from app.db.model.transaction import Transaction, Category, Anomaly
from app.db.model.user import User
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from app.core.jwt import verify_access_token

# 로거 설정
logger = logging.getLogger(__name__)

# 인증 스키마
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login", auto_error=False)

# 현재 인증된 유저 ID 가져오기
async def get_current_user_id(token: Optional[str] = Depends(oauth2_scheme)) -> int:
    if not token:
        logger.warning("인증 토큰 누락: 기본 사용자 ID 1 사용")
        return 1
    try:
        payload = verify_access_token(token)
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return 1
        return int(user_id_str)
    except (JWTError, Exception):
        return 1

# 라우터 설정
router = APIRouter(
    prefix="/transactions",
    tags=["transactions"],
    responses={404: {"description": "Not found"}},
)

# Pydantic Schemas
class TransactionBase(BaseModel):
    """거래 기본 정보 스키마"""
    id: int
    merchant: str
    amount: float
    category: str
    transaction_date: str
    description: Optional[str] = None
    status: str = "completed"
    currency: str = "KRW"

class TransactionList(BaseModel):
    """거래 목록 응답 스키마"""
    total: int
    page: int
    page_size: int
    transactions: List[TransactionBase]
    data_source: str = "DB"

class TransactionUpdate(BaseModel):
    """거래 수정 요청 스키마"""
    description: Optional[str] = None

class TransactionCreate(BaseModel):
    """거래 추가 요청"""
    amount: float
    category: str
    merchant_name: Optional[str] = None
    merchant: Optional[str] = None
    description: Optional[str] = None
    transaction_date: Optional[str] = None
    currency: Optional[str] = "KRW"

class TransactionBulkCreate(BaseModel):
    """거래 일괄 생성 요청 스키마"""
    user_id: int
    transactions: List[TransactionCreate]

class TransactionBulkResponse(BaseModel):
    """거래 일괄 생성 응답 스키마"""
    status: str
    created_count: int
    failed_count: int
    message: str

class AnomalyReport(BaseModel):
    """이상거래 신고 요청 스키마"""
    reason: str
    severity: str = "medium"

# DB 세션 의존성 타입을 위한 별칭
DB_Dependency = Annotated[AsyncSession, Depends(get_db)]

# 거래 내역 조회 API
@router.get("", response_model=TransactionList)
async def get_transactions(
    user_id: Optional[int] = Query(None, description="사용자 ID 필터"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    min_amount: Optional[float] = Query(None, description="최소 금액"),
    max_amount: Optional[float] = Query(None, description="최대 금액"),
    search: Optional[str] = Query(None, description="검색어 (가맹점명, 메모)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=1000000, description="페이지 크기"),
    db: AsyncSession = Depends(get_db)
):
    try:
        # user_id가 없으면 빈 목록 반환 (인증되지 않은 경우)
        if user_id is None:
            return TransactionList(total=0, page=page, page_size=page_size, transactions=[], data_source="DB")
        
        # 기본 쿼리 및 카운트 쿼리 생성
        query = select(Transaction).options(selectinload(Transaction.category))
        count_query = select(func.count(Transaction.id))
        
        conditions = [Transaction.user_id == user_id]
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                conditions.append(Transaction.transaction_time >= start_dt)
            except: pass
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                conditions.append(Transaction.transaction_time <= end_dt)
            except: pass
        if min_amount is not None:
            conditions.append(Transaction.amount >= min_amount)
        if max_amount is not None:
            conditions.append(Transaction.amount <= max_amount)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(or_(Transaction.merchant_name.ilike(search_pattern), Transaction.description.ilike(search_pattern)))
        
        # 조건 적용
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))
        
        # 총 개수 조회
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 페이징 적용 (최신순)
        offset = (page - 1) * page_size
        query = query.order_by(Transaction.transaction_time.desc()).offset(offset).limit(page_size)
        
        # 데이터 조회
        result = await db.execute(query)
        rows = result.scalars().all()
        
        # 응답 데이터 변환
        transactions = []
        for tx in rows:
            cat_name = tx.category.name if tx.category else "기타"
            if category and cat_name != category:
                continue
            transactions.append(TransactionBase(
                id=tx.id, merchant=tx.merchant_name or "알 수 없음", amount=float(tx.amount),
                category=cat_name, transaction_date=tx.transaction_time.strftime("%Y-%m-%d %H:%M") if tx.transaction_time else "",
                description=tx.description, status=tx.status, currency=tx.currency
            ))
        
        return TransactionList(total=total, page=page, page_size=page_size, transactions=transactions, data_source="DB (AWS RDS)")
    except Exception as e:
        logger.error(f"거래 내역 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="거래 내역을 불러올 수 없습니다.")

@router.post("/bulk", response_model=TransactionBulkResponse)
async def create_transactions_bulk(data: TransactionBulkCreate, db: AsyncSession = Depends(get_db)):
    try:
        from sqlalchemy import insert
        created_count = 0
        failed_count = 0
        cat_result = await db.execute(select(Category))
        categories = {c.name: c.id for c in cat_result.scalars().all()}
        
        for tx in data.transactions:
            try:
                category_id = categories.get(tx.category) or categories.get('기타')
                merchant = tx.merchant or tx.merchant_name
                
                # 날짜 처리 (유연한 파싱)
                tx_time = None
                formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
                for fmt in formats:
                    try:
                        tx_time = datetime.strptime(tx.transaction_date, fmt)
                        break
                    except: continue
                if not tx_time:
                    tx_time = datetime.now()
                
                insert_stmt = insert(Transaction).values(
                    user_id=data.user_id, category_id=category_id, amount=tx.amount,
                    currency=tx.currency, merchant_name=merchant, description=tx.description,
                    status="completed", transaction_time=tx_time
                )
                await db.execute(insert_stmt)
                created_count += 1
            except Exception as e:
                logger.warning(f"Individual transaction create failed: {e}")
                failed_count += 1
        await db.commit()
        return TransactionBulkResponse(status="success", created_count=created_count, failed_count=failed_count, message=f"{created_count}건 생성 완료")
    except Exception as e:
        logger.error(f"Bulk creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("")
async def delete_all_transactions(user_id: int = Query(..., description="사용자 ID"), db: AsyncSession = Depends(get_db)):
    try:
        stmt = delete(Transaction).where(Transaction.user_id == user_id)
        result = await db.execute(stmt)
        await db.commit()
        return {"status": "success", "message": f"{result.rowcount}건 삭제 완료", "deleted_count": result.rowcount}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{transaction_id}", response_model=TransactionBase)
async def get_transaction(transaction_id: int, db: AsyncSession = Depends(get_db)):
    try:
        query = select(Transaction).options(selectinload(Transaction.category)).where(Transaction.id == transaction_id)
        result = await db.execute(query)
        tx = result.scalar_one_or_none()
        if not tx: raise HTTPException(status_code=404, detail="Not found")
        return TransactionBase(
            id=tx.id, merchant=tx.merchant_name or "알 수 없음", amount=float(tx.amount),
            category=tx.category.name if tx.category else "기타",
            transaction_date=tx.transaction_time.strftime("%Y-%m-%d %H:%M") if tx.transaction_time else "",
            description=tx.description, status=tx.status, currency=tx.currency
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{transaction_id}/note")
async def update_transaction_note(transaction_id: int, update_data: TransactionUpdate, db: AsyncSession = Depends(get_db)):
    from app.db.crud import transaction as crud
    await crud.update_transaction_description(db, transaction_id, update_data.description)
    return {"status": "success", "message": "Updated"}

@router.post("/{transaction_id}/anomaly-report")
async def report_anomaly(transaction_id: int, report: AnomalyReport, db: AsyncSession = Depends(get_db)):
    from app.db.crud import transaction as crud
    tx = await crud.get_transaction_by_id(db, transaction_id)
    if not tx: raise HTTPException(status_code=404, detail="Not found")
    await crud.create_anomaly_report(db, transaction_id, tx.user_id, report.severity, report.reason)
    return {"status": "success", "message": "Reported"}
