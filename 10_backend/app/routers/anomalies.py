
"""
이상 거래 탐지 API (ML 기반 + 히리스틱)

통계적 규칙(Heuristics)과 ML 모델을 결합하여 이상 거래를 탐지합니다.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, timedelta
import logging
import httpx
import asyncio
import math

from app.db.database import get_db
from app.db.model.transaction import Transaction, Category, Anomaly
from app.db.model.user import User
from app.routers.user import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/anomalies",
    tags=["anomalies"],
    responses={404: {"description": "Not found"}},
)

# ML Service URL
ML_SERVICE_URL = "http://caf_llm_analysis:9102/predict"

# ============================================================
# Pydantic Models
# ============================================================

class AnomalyResponse(BaseModel):
    """이상 거래 응답"""
    id: int
    userId: str
    userName: str
    merchant: str
    category: str
    amount: float
    date: str
    riskLevel: str
    reason: str
    status: str
    
    class Config:
        from_attributes = True

# ============================================================
# Feature Calculation & Heuristics
# ============================================================

def calculate_features(tx: Transaction, avg_amt: float, user_txs: List[Transaction]) -> dict:
    """
    ML 모델 및 히리스틱에 사용할 피쳐 계산
    """
    features = {}
    
    # 1. Amount Z-Score-like (Simple Ratio)
    # Fix TypeError: Decimal vs Float
    amt_val = float(tx.amount)
    # If avg_amt is 0 (first time in category), ratio is 1.0 (Normal)
    features['amt_ratio'] = (amt_val / avg_amt) if avg_amt > 0 else 1.0
    
    # 2. Time Features
    hour = tx.transaction_time.hour
    features['is_night'] = 1 if 0 <= hour < 5 else 0
    
    # 3. Burst Detection (Same merchant in short time)
    burst_count = 0
    current_time = tx.transaction_time
    for other in user_txs:
        if other.id == tx.id: continue
        time_diff = abs((current_time - other.transaction_time).total_seconds())
        if time_diff < 600: # 10 minutes
            burst_count += 1
    features['burst_count'] = burst_count
    
    # 4. Keyword Checks
    merchant = tx.merchant_name or ""
    features['is_gangnam'] = 1 if "강남" in merchant else 0
    features['is_foreign'] = 1 if tx.currency != 'KRW' else 0
    
    return features

def apply_heuristics(tx: Transaction, features: dict) -> tuple[str, str]:
    """
    규칙 기반 이상 탐지 (Simplified)
    Returns: (risk_level, reason)
    """
    reasons = []
    score = 0
    
    # Rule 1: Category Average Ratio > 100x (User Request)
    if features['amt_ratio'] >= 100.0:
        score += 3
        reasons.append(f"평균액의 {features['amt_ratio']:.1f}배")
        
    # Other rules (Night, Absolute Amount, Keywords) REMOVED as per user request.

    if score >= 3:
        return ("주의", ", ".join(reasons))
    
    return ("정상", "정상")


# ============================================================
# API Endpoints
# ============================================================

@router.get("", response_model=List[AnomalyResponse])
async def get_anomalies(
    status: Optional[str] = Query(None),
    days: int = Query(30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        anomalies = []
        
        # ============================================================
        # 1. Fetch Persisted Anomalies (Prioritize DB Records)
        # ============================================================
        anom_query = (
            select(Anomaly)
            .options(
                selectinload(Anomaly.transaction).selectinload(Transaction.user),
                selectinload(Anomaly.transaction).selectinload(Transaction.category)
            )
            .order_by(Anomaly.created_at.desc())
        )
        
        print(f"DEBUG: Anomaly Request: status={status}, user={current_user.email}, is_superuser={current_user.is_superuser}")
        
        # User Filter
        if not current_user.is_superuser:
            anom_query = anom_query.where(Anomaly.user_id == current_user.id)
            
        # Status Filter (Basic mapping)
        if status == 'reported':
             # User Reported implies explicit report
             anom_query = anom_query.where(Anomaly.reason == "User Reported")
        elif status == 'pending':
             # Pending implies unresolved
             anom_query = anom_query.where(Anomaly.is_resolved == False)
             
        # Execute Anomaly Query
        anom_res = await db.execute(anom_query)
        persisted_anomalies = anom_res.scalars().all()
        
        details = []
        for a in persisted_anomalies:
            details.append(f"ID={a.id}, TxID={a.transaction_id}, HasTx={a.transaction is not None}")
            
        
        # Map to Response & Track IDs to avoid duplicates
        persisted_ids = set()
        
        for anom in persisted_anomalies:
            tx = anom.transaction
            if not tx: continue # Should not happen unless referential integrity broken
            
            persisted_ids.add(tx.id)
            
            # Use 'pending' status for unresolved items so they appear in Admin Dashboard list
            response_status = "pending" if not anom.is_resolved else "resolved"
            if anom.is_resolved and anom.reason == 'User Ignored':
                response_status = "ignored"
            
            # If specifically filtering for 'reported' via API param, and we found it via query, ensure it passes
            # (Query filter above handles this mostly, but response status might need to be consistent?)
            # Actually, frontend filters by response's 'status' field being 'pending'.
            # So unresolved items should return status='pending' regardless of source.
            
            anomalies.append(AnomalyResponse(
                id=tx.id,
                userId=f"user_{tx.user_id}",
                userName=tx.user.name if tx.user else f"User {tx.user_id}",
                merchant=tx.merchant_name or "Unknown",
                category=tx.category.name if tx.category else "기타",
                amount=float(tx.amount),
                date=tx.transaction_time.strftime("%Y-%m-%d %H:%M"),
                riskLevel=anom.severity or "위험",
                reason=anom.reason or "System Detected",
                status=response_status
            ))
            
        # ============================================================
        # 2. Heuristic Check on Recent Transactions (Catch NEW anomalies)
        # ============================================================
        # If user asked for specific 'reported' (User Reported), we usually only care about DB records.
        # But if they ask for 'pending' or all, we should check heuristics too.
        
        if status != 'reported':
            start_date = datetime.now() - timedelta(days=days)
            
            tx_query = (
                select(Transaction)
                .where(Transaction.transaction_time >= start_date)
                # Exclude already processed/persisted transactions from this check
                .where(Transaction.id.not_in(persisted_ids))
                .options(selectinload(Transaction.user), selectinload(Transaction.category))
                .order_by(Transaction.transaction_time.desc())
            )
            
            if not current_user.is_superuser:
                tx_query = tx_query.where(Transaction.user_id == current_user.id)
                
            tx_query = tx_query.limit(1000) # Check last 1000 txs for new patterns
            
            tx_res = await db.execute(tx_query)
            recent_txs = tx_res.scalars().all()
            
            # Calculate Averages (Optimization: Only if needed)
            if recent_txs:
                user_ids = list(set(tx.user_id for tx in recent_txs))
                user_category_avg_map = {} 
                
                avg_query = (
                    select(Transaction.user_id, Transaction.category_id, func.avg(Transaction.amount))
                    .where(Transaction.user_id.in_(user_ids))
                    .group_by(Transaction.user_id, Transaction.category_id)
                )
                avg_res = await db.execute(avg_query)
                for uid, cat_id, avg in avg_res.fetchall():
                    if uid not in user_category_avg_map:
                        user_category_avg_map[uid] = {}
                    user_category_avg_map[uid][cat_id] = float(avg) if avg else 0.0

                for tx in recent_txs:
                    # Heuristic Calculation
                    cat_id = tx.category_id
                    user_avgs = user_category_avg_map.get(tx.user_id, {})
                    avg_amt = user_avgs.get(cat_id, 0.0)
                    
                    features = calculate_features(tx, avg_amt, [t for t in recent_txs if t.user_id == tx.user_id])
                    risk, reason = apply_heuristics(tx, features)
                    
                    if risk != "정상":
                        anomalies.append(AnomalyResponse(
                            id=tx.id,
                            userId=f"user_{tx.user_id}",
                            userName=tx.user.name if tx.user else f"User {tx.user_id}",
                            merchant=tx.merchant_name or "Unknown",
                            category=tx.category.name if tx.category else "기타",
                            amount=float(tx.amount),
                            date=tx.transaction_time.strftime("%Y-%m-%d %H:%M"),
                            riskLevel=risk,
                            reason=reason,
                            status="pending" # New heuristic detections are pending
                        ))

        logger.info(f"Returned {len(anomalies)} anomalies (Persisted: {len(persisted_ids)})")
        return anomalies
        
    except Exception as e:
        logger.error(f"Error getting anomalies: {e}", exc_info=True)
        raise e
        # return []

@router.post("/{tx_id}/report", status_code=status.HTTP_201_CREATED)
async def report_anomaly(tx_id: int, db: AsyncSession = Depends(get_db)):
    """
    사용자가 이상 거래를 신고 (Confirm Fraud)
    """
    # Check if transaction exists
    tx = await db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Check if existing anomaly record
    query = select(Anomaly).where(Anomaly.transaction_id == tx_id)
    result = await db.execute(query)
    anomaly = result.scalar_one_or_none()

    if anomaly:
        anomaly.severity = "high"
        anomaly.reason = "User Reported"
        anomaly.is_resolved = False # Unresolved = needs admin attention
    else:
        anomaly = Anomaly(
            transaction_id=tx_id,
            user_id=tx.user_id,
            severity="high",
            reason="User Reported",
            is_resolved=False
        )
        db.add(anomaly)
    
    await db.commit()
    return {"status": "reported", "message": "Transaction reported as fraud"}

@router.post("/{tx_id}/ignore", status_code=status.HTTP_200_OK)
async def ignore_anomaly(tx_id: int, db: AsyncSession = Depends(get_db)):
    """
    사용자가 이상 거래를 무시 (Mark as Normal)
    """
    # Check if transaction exists
    tx = await db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Check if existing anomaly record
    query = select(Anomaly).where(Anomaly.transaction_id == tx_id)
    result = await db.execute(query)
    anomaly = result.scalar_one_or_none()

    if anomaly:
        anomaly.is_resolved = True
        anomaly.reason = "User Ignored"
        anomaly.resolved_at = datetime.now()
    else:
        anomaly = Anomaly(
            transaction_id=tx_id,
            user_id=tx.user_id,
            severity="low",
            reason="User Ignored",
            is_resolved=True,
            resolved_at=datetime.now()
        )
        db.add(anomaly)
    
    await db.commit()
    return {"status": "ignored", "message": "Transaction marked as normal"}

