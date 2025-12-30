"""
Anomaly Service Layer
이상거래 관련 비즈니스 로직

라우터에서 분리한 비즈니스 로직을 담당
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

from app.db.model.transaction import Anomaly, Transaction
from app.db.model.user import User

logger = logging.getLogger(__name__)


class AnomalyServiceError(Exception):
    """이상거래 서비스 에러"""
    pass


class AnomalyNotFoundError(AnomalyServiceError):
    """이상거래를 찾을 수 없음"""
    pass


class AnomalyAccessDeniedError(AnomalyServiceError):
    """접근 권한 없음"""
    pass


async def report_anomaly(
    db: AsyncSession,
    anomaly_id: int,
    current_user: User
) -> dict:
    """
    사용자가 이상거래를 신고함
    
    - anomalies 테이블의 reason을 'User Reported'로 변경
    - transactions 테이블의 is_fraudulent를 True로 설정 (소비 집계에서 제외)
    
    Args:
        db: 데이터베이스 세션
        anomaly_id: 이상거래 ID
        current_user: 현재 로그인한 사용자
        
    Returns:
        dict: {"status": "reported", "id": anomaly_id, "transactionId": transaction_id}
        
    Raises:
        AnomalyNotFoundError: 이상거래를 찾을 수 없음
        AnomalyAccessDeniedError: 접근 권한 없음
    """
    # 이상거래 조회
    query = select(Anomaly).where(Anomaly.id == anomaly_id)
    result = await db.execute(query)
    anomaly = result.scalar_one_or_none()
    
    if not anomaly:
        raise AnomalyNotFoundError(f"Anomaly {anomaly_id} not found")
    
    # 권한 확인 (관리자가 아니면 자신의 이상거래만 신고 가능)
    if not current_user.is_superuser and anomaly.user_id != current_user.id:
        raise AnomalyAccessDeniedError("Access denied to this anomaly")
    
    # Anomaly 상태 업데이트
    anomaly.is_resolved = False
    anomaly.reason = 'User Reported'
    
    # Transaction의 is_fraudulent 플래그 설정 (소비 집계에서 제외)
    tx_query = select(Transaction).where(Transaction.id == anomaly.transaction_id)
    tx_result = await db.execute(tx_query)
    transaction = tx_result.scalar_one_or_none()
    
    if transaction:
        transaction.is_fraudulent = True
        logger.info(f"Transaction {transaction.id} marked as fraudulent (User Reported)")
    
    await db.commit()
    await db.refresh(anomaly)
    
    return {
        "status": "reported",
        "id": anomaly.id,
        "transactionId": anomaly.transaction_id
    }


async def ignore_anomaly(
    db: AsyncSession,
    anomaly_id: int,
    current_user: User
) -> dict:
    """
    사용자가 이상거래를 무시함 (정상 거래로 확인)
    
    - anomalies 테이블의 is_resolved를 True로 변경
    - anomalies 테이블의 reason을 'User Ignored'로 변경
    - is_fraudulent는 False 유지 (정상 거래이므로)
    
    Args:
        db: 데이터베이스 세션
        anomaly_id: 이상거래 ID
        current_user: 현재 로그인한 사용자
        
    Returns:
        dict: {"status": "ignored", "id": anomaly_id, "transactionId": transaction_id}
        
    Raises:
        AnomalyNotFoundError: 이상거래를 찾을 수 없음
        AnomalyAccessDeniedError: 접근 권한 없음
    """
    # 이상거래 조회
    query = select(Anomaly).where(Anomaly.id == anomaly_id)
    result = await db.execute(query)
    anomaly = result.scalar_one_or_none()
    
    if not anomaly:
        raise AnomalyNotFoundError(f"Anomaly {anomaly_id} not found")
    
    # 권한 확인
    if not current_user.is_superuser and anomaly.user_id != current_user.id:
        raise AnomalyAccessDeniedError("Access denied to this anomaly")
    
    # Anomaly 상태 업데이트 (무시 = 정상 거래로 확인)
    anomaly.is_resolved = True
    anomaly.reason = 'User Ignored'
    
    await db.commit()
    await db.refresh(anomaly)
    
    return {
        "status": "ignored",
        "id": anomaly.id,
        "transactionId": anomaly.transaction_id
    }
