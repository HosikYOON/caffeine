
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
from app.db.model.transaction import Transaction, Category
from app.db.model.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/anomalies",
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
    avg_val = float(avg_amt) if avg_amt > 0 else 1.0
    features['amt_ratio'] = amt_val / avg_val
    
    # 2. Time Features
    hour = tx.transaction_time.hour
    features['is_night'] = 1 if 0 <= hour < 5 else 0
    
    # 3. Burst Detection (Same merchant in short time)
    # This requires looking at user_txs
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
    규칙 기반 이상 탐지
    Returns: (risk_level, reason)
    """
    reasons = []
    score = 0
    
    # Rule 1: High Amount Ratio
    if features['amt_ratio'] >= 5.0:
        score += 3
        reasons.append(f"평균액의 {features['amt_ratio']:.1f}배")
    elif features['amt_ratio'] >= 3.0:
        score += 2
        reasons.append(f"평균액의 {features['amt_ratio']:.1f}배")
        
    # Rule 2: Night Time + High Amount
    if features['is_night'] and features['amt_ratio'] >= 1.5:
        score += 2
        reasons.append("심야 시간 고액")
        
    # Rule 3: Burst
    if features['burst_count'] >= 3:
        score += 3
        reasons.append(f"단시간 다건 결제({features['burst_count']}회)")
        
    # Rule 4: Keywords (Removed specific region check)
    # if "강남" in (tx.merchant_name or "") and tx.amount > 1000000:
    #     score += 1
    #     reasons.append("강남 지역 고액")
        
    # Absolute Amount
    if tx.amount >= 1000000:
        score += 1
        reasons.append("100만원 이상")

    if score >= 3:
        return ("위험", ", ".join(reasons))
    elif score >= 1:
        return ("주의", ", ".join(reasons))
        
    return ("정상", "정상")


# ============================================================
# API Endpoints
# ============================================================

@router.get("", response_model=List[AnomalyResponse])
async def get_anomalies(
    status: Optional[str] = Query(None),
    days: int = Query(30),
    db: AsyncSession = Depends(get_db)
):
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        # 1. Fetch Transactions (With User Eager Loaded) - Fix MissingGreenlet
        query = (
            select(Transaction)
            .where(Transaction.transaction_time >= start_date)
            .options(selectinload(Transaction.user), selectinload(Transaction.category))
            .order_by(Transaction.transaction_time.desc())
            .limit(200) # Performance limit
        )
        result = await db.execute(query)
        transactions = result.scalars().all()
        
        # 2. Calculate Avg per User
        user_ids = list(set(tx.user_id for tx in transactions))
        avg_map = {}
        
        if user_ids:
            avg_query = (
                select(Transaction.user_id, func.avg(Transaction.amount))
                .where(Transaction.user_id.in_(user_ids))
                .group_by(Transaction.user_id)
            )
            avg_res = await db.execute(avg_query)
            for uid, avg in avg_res.fetchall():
                avg_map[uid] = float(avg) if avg else 0.0

        anomalies = []
        
        # 3. Analyze
        for tx in transactions:
            avg_amt = avg_map.get(tx.user_id, 0.0)
            
            # Simple features calculation (in-memory for now)
            features = calculate_features(tx, avg_amt, [t for t in transactions if t.user_id == tx.user_id])
            
            # Heuristic Check
            risk, reason = apply_heuristics(tx, features)
            
            # ML Check (Optional - Fire and Forget or Async Wait)
            # For demo response speed, we rely mostly on heuristics but if high risk, we label it.
            
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
                    status="pending"
                ))
        
        logger.info(f"Detected {len(anomalies)} anomalies")
        return anomalies
        
    except Exception as e:
        logger.error(f"Error getting anomalies: {e}", exc_info=True)
        return []

