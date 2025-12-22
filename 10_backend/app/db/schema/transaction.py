from pydantic import BaseModel
from typing import Optional, List

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
    """거래 생성 요청 스키마"""
    merchant: str
    amount: float
    category: str
    transaction_date: str
    description: Optional[str] = None
    currency: str = "KRW"

class TransactionBulkRequest(BaseModel):
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
    severity: str = "medium"  # low/medium/high
