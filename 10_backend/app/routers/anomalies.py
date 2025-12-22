"""
이상 거래 탐지 API (Anomaly Detection Router)

현재는 빈 목록을 반환하며, 추후 ML 모델 또는 룰 베이스 로직으로 확장 가능합니다.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from app.db.database import get_db
from app.db.model.transaction import Transaction, Category
from app.db.model.user import User
from app.services.ml_service import ml_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/anomalies",
    tags=["anomalies"],
    responses={404: {"description": "Not found"}},
)


# ============================================================
# Pydantic 스키마
# ============================================================

class AnomalyResponse(BaseModel):
    """이상 거래 응답 모델"""
    id: int
    userId: str
    userName: str
    category: str
    amount: float
    date: str
    riskLevel: str  # "위험", "경고", "주의"
    reason: str
    status: str  # "pending", "approved", "rejected"
    
    class Config:
        from_attributes = True


# ============================================================
# 헬퍼 함수
# ============================================================

def determine_risk_level(amount: float, avg_amount: float) -> tuple[str, str]:
    """
    거래 금액을 기반으로 위험 수준을 결정합니다.
    
    Args:
        amount: 현재 거래 금액
        avg_amount: 평균 거래 금액
    
    Returns:
        (위험 등급, 사유) 튜플
    """
    if avg_amount == 0:
        return ("주의", "평균 거래액 정보 없음")
    
    ratio = amount / avg_amount
    
    if ratio >= 5.0:
        return ("위험", f"평균 거래액의 {ratio:.1f}배 초과")
    elif ratio >= 3.0:
        return ("경고", f"평균 거래액의 {ratio:.1f}배 초과")
    elif amount >= 1000000:  # 100만원 이상
        return ("주의", "고액 거래 (100만원 이상)")
    else:
        return ("주의", "일반 거래")


# ============================================================
# API 엔드포인트
# ============================================================

@router.get("", response_model=List[AnomalyResponse])
async def get_anomalies(
    status: Optional[str] = Query(None, description="필터: pending, approved, rejected"),
    risk_level: Optional[str] = Query(None, description="필터: 위험, 경고, 주의"),
    days: int = Query(30, description="조회 기간 (일)"),
    db: AsyncSession = Depends(get_db)
):
    """
    이상 거래 목록을 조회합니다.
    
    현재는 최근 고액 거래(50만원 이상)를 반환하며,
    추후 ML 모델 기반 이상 탐지로 확장 가능합니다.
    
    Args:
        status: 처리 상태 필터 (pending, approved, rejected)
        risk_level: 위험 등급 필터 (위험, 경고, 주의)
        days: 조회 기간 (기본 30일)
        db: 데이터베이스 세션
    
    Returns:
        이상 거래 목록
    """
    try:
        # TODO: 실제 서비스에서는 별도 anomaly_transactions 테이블 사용 권장
        # 현재는 데모를 위해 고액 거래를 이상 거래로 간주
        
        start_date = datetime.now() - timedelta(days=days)
        
        # 사용자별 평균 거래액 계산 (서브쿼리)
        avg_query = select(
            Transaction.user_id,
            func.avg(Transaction.amount).label('avg_amount')
        ).group_by(Transaction.user_id).subquery()
        
        # 최근 모든 거래 조회 (시간 기준)
        query = select(
            Transaction.id,
            Transaction.user_id,
            Transaction.amount,
            Transaction.transaction_time,
            Category.name.label('category_name'),
            User.name.label('user_name'),
            avg_query.c.avg_amount
        ).join(
            Category, Transaction.category_id == Category.id, isouter=True
        ).join(
            User, Transaction.user_id == User.id, isouter=True
        ).join(
            avg_query, Transaction.user_id == avg_query.c.user_id, isouter=True
        ).where(
            Transaction.transaction_time >= start_date
        ).order_by(Transaction.transaction_time.desc()).limit(200)
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        anomalies = []
        for row in rows:
            amount_float = float(row.amount) if row.amount else 0.0
            avg_amount = float(row.avg_amount) if row.avg_amount else 0.0
            risk_level_str, reason = determine_risk_level(amount_float, avg_amount)
            
            # ML 탐지 연동
            tx_data = {
                "user_id": row.user_id,
                "amount": float(row.amount),
                "category": row.category_name or "기타",
                "transaction_time": row.transaction_time.isoformat()
            }
            ml_result = await ml_service.detect_anomaly(tx_data)
            
            # 탐지 여부 결정 (ML 우선, 룰 베이스 보조)
            is_detected = ml_result["is_anomaly"] or risk_level_str in ["위험", "경고"]
            
            if not is_detected:
                continue

            # ML 결과가 '이상'인 경우 정보 보강
            if ml_result["is_anomaly"]:
                risk_level_str = "위험" if ml_result["score"] > 0.8 else "경고"
                reason = f"ML 탐지: {ml_result['reason']} (신뢰도: {ml_result['score']:.2f})"
            
            # 위험 등급 필터 적용 (프론트엔드 요청 시)
            if risk_level and risk_level_str != risk_level:
                continue
            
            anomaly = AnomalyResponse(
                id=row.id,
                userId=f"user_{row.user_id}",
                userName=row.user_name or f"사용자 {row.user_id}",
                category=row.category_name or "기타",
                amount=float(row.amount),
                date=row.transaction_time.strftime("%Y-%m-%d %H:%M"),
                riskLevel=risk_level_str,
                reason=reason,
                status="pending"
            )
            anomalies.append(anomaly)
        
        # 상태 필터 적용 (현재는 모두 pending이므로 생략 가능)
        if status:
            anomalies = [a for a in anomalies if a.status == status]
        
        logger.info(f"Anomaly detection: Found {len(anomalies)} anomalies in last {days} days")
        return anomalies
        
    except Exception as e:
        logger.error(f"Failed to fetch anomalies: {e}", exc_info=True)
        # 에러 발생 시 빈 목록 반환 (Frontend 호환성 유지)
        return []


@router.post("/{anomaly_id}/approve")
async def approve_anomaly(
    anomaly_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    이상 거래를 정상으로 승인합니다.
    
    TODO: 실제 구현에서는 anomaly_transactions 테이블의 상태를 업데이트해야 합니다.
    """
    logger.info(f"Anomaly {anomaly_id} approved")
    return {"message": "Anomaly approved", "id": anomaly_id}


@router.post("/{anomaly_id}/reject")
async def reject_anomaly(
    anomaly_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    이상 거래를 거부합니다.
    
    TODO: 실제 구현에서는 anomaly_transactions 테이블의 상태를 업데이트하고,
    해당 거래를 차단하는 로직을 추가해야 합니다.
    """
    logger.info(f"Anomaly {anomaly_id} rejected")
    return {"message": "Anomaly rejected", "id": anomaly_id}


@router.post("/{anomaly_id}/notify")
async def notify_anomaly(
    anomaly_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    이상 거래에 대해 해당 사용자에게 알림을 전송합니다.
    
    - 앱 내 알림 센터에 저장 (항상)
    - 푸시 알림 전송 (토큰이 있을 경우)
    """
    from app.services.push_service import send_anomaly_alert
    from app.db.model.notification import Notification
    import json
    
    try:
        # 해당 거래 정보 조회
        query = select(
            Transaction.id,
            Transaction.user_id,
            Transaction.amount,
            Category.name.label('category_name'),
            User.push_token,
            User.name.label('user_name')
        ).join(
            Category, Transaction.category_id == Category.id, isouter=True
        ).join(
            User, Transaction.user_id == User.id
        ).where(
            Transaction.id == anomaly_id
        )
        
        result = await db.execute(query)
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        category_name = row.category_name or "기타"
        amount = float(row.amount)
        reason = "관리자가 이상 거래로 판단하여 알림을 보냈습니다."
        
        # 1. 앱 내 알림 센터에 저장 (항상 실행)
        notification = Notification(
            user_id=row.user_id,
            type="anomaly",
            title="⚠️ 이상 거래 감지",
            message=f"{category_name}에서 ₩{amount:,.0f} 거래가 의심됩니다. (거래 ID: {row.id})\n{reason}"
        )
        db.add(notification)
        await db.commit()
        
        logger.info(f"알림 저장 완료: user_id={row.user_id}, transaction_id={anomaly_id}")
        
        # 2. 푸시 알림 전송 (토큰이 있을 경우)
        push_result = {"success": False, "message": "푸시 토큰 없음"}
        
        if row.push_token:
            push_result = await send_anomaly_alert(
                push_token=row.push_token,
                transaction_id=row.id,
                amount=amount,
                category=category_name,
                reason=reason
            )
            logger.info(f"푸시 알림 전송: {push_result}")
        
        return {
            "success": True,
            "message": "알림이 전송되었습니다." + (" (푸시 포함)" if row.push_token else " (앱 내 알림만)"),
            "id": anomaly_id,
            "notification_saved": True,
            "push_sent": row.push_token is not None,
            "push_result": push_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send anomaly notification: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"알림 전송 중 오류가 발생했습니다: {str(e)}"
        )
