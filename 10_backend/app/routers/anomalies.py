"""
이상 거래 탐지 API (ML 기반 + 히리스틱)

통계적 규칙(Heuristics)과 ML 모델을 결합하여 이상 거래를 탐지합니다.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status, Header, Body
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
import os
import joblib
import pandas as pd
import numpy as np

from app.db.database import get_db
from app.db.model.transaction import Transaction, Category, Anomaly
from app.db.model.user import User
from app.routers.user import get_current_user
from app.services.ml_service import ml_service
from app.services.fraud_preprocessing import FraudPreprocessor
from fastapi.security import OAuth2PasswordRequestForm
from app.db.schema.auth import Token
from app.routers.user import login_for_user as original_login_function

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["anomalies"],
    responses={404: {"description": "Not found"}},
)

# Ugly hack router to fix /api/api login issue as per user request
fix_router = APIRouter()

@fix_router.post("/users/login", response_model=Token, include_in_schema=False)
async def fixed_login_for_user_route(
    user: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    user_agent: str | None = Header(default=None),
):
    """
    This is a workaround to handle incorrect /api/api/login paths.
    It delegates the call to the original login function.
    """
    return await original_login_function(user, db, user_agent)


# ML Service URL
ML_SERVICE_URL = "http://caf_llm_analysis:9102/predict"

# ============================================================
# Fraud Model Loading
# ============================================================
fraud_model = None
fraud_preprocessor = FraudPreprocessor()

# Category absolute cutoffs for cold start (KRW)
CATEGORY_CUTOFFS = {
    "식비": 5_000_000,
    "쇼핑": 9_990_000,
    "공과금": 5_000_000,
    "여가": 9_990_000,
    "문화": 9_990_000,
    "교통": 1_000_000,
    "의료": 9_990_000,
    "교육": 5_000_000,
    "기타": 9_990_000,
}

# Default cutoff if category not matched
DEFAULT_CUTOFF = 9_990_000

def load_fraud_model():
    """
    Load the XGBoost Fraud Detection Model.
    """
    global fraud_model
    try:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(app_dir, "models", "paysim_generic_no_flag_featplus.joblib")
        
        if os.path.exists(model_path):
            fraud_model = joblib.load(model_path)
            logger.info(f"Fraud model loaded from {model_path}")
        else:
            logger.warning(f"Fraud model not found at {model_path}")
    except Exception as e:
        logger.error(f"Failed to load fraud model: {e}")

# Load model on module import (or first use)
load_fraud_model()

# ============================================================
# Pydantic Models
# ============================================================

class AnomalyResponse(BaseModel):
    """이상 거래 응답"""
    id: int              # anomaly id
    transactionId: int   # underlying transaction id
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

def apply_heuristics(tx: Transaction, features: dict) -> tuple[Optional[str], Optional[str]]:
    """
    Apply statistical rules.
    """
    # Single Rule: Ratio Check (Leave-One-Out Average)
    if features['amt_ratio'] >= 100.0:
        return ("위험", f"평균액의 {features['amt_ratio']:.1f}배")

    # Cold-start absolute cutoff by category
    cat_name = (tx.category.name if tx.category else tx.merchant_name) or ""
    cutoff = DEFAULT_CUTOFF
    for key, val in CATEGORY_CUTOFFS.items():
        if key in cat_name:
            cutoff = val
            break
    if float(tx.amount) >= cutoff:
        return ("위험", f"카테고리 컷오프 초과 ({cutoff:,.0f}원)")

    return None, None


# ============================================================
# ML Detection
# ============================================================

def detect_fraud_with_model(tx: Transaction, history: List[Transaction]) -> tuple[str, str]:
    """
    ML 모델 기반 이상 탐지
    Returns: (risk_level, reason)
    """
    global fraud_model, fraud_preprocessor
    
    if not fraud_model:
        return ("정상", "정상")
        
    try:
        # Preprocess
        df_features = fraud_preprocessor.preprocess_transaction(tx, history)
        
        # Predict Probability
        if hasattr(fraud_model, "predict_proba"):
            probs = fraud_model.predict_proba(df_features)
            fraud_prob = probs[0][1]
            threshold = 0.955
            
            if fraud_prob >= threshold:
                return ("위험", f"AI 모델 탐지 (확률 {(fraud_prob*100):.1f}%)")
            elif fraud_prob >= 0.8: # Lower threshold for warning
                return ("주의", f"AI 모델 의심 (확률 {(fraud_prob*100):.1f}%)")
                
        else:
            # Fallback to hard prediction
            pred = fraud_model.predict(df_features)
            if pred[0] == 1:
                return ("위험", "AI 모델 탐지")
                
    except Exception as e:
        logger.error(f"Error in AI fraud detection: {e}")
        return ("정상", "정상")
        
    return ("정상", "정상")

# ============================================================
# API Endpoints
# ============================================================

@router.get("/anomalies", response_model=List[AnomalyResponse])
async def get_anomalies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(60),
    status: Optional[str] = Query(None), 
    risk_level: Optional[str] = Query(None)
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
        
        # User Filter
        if not current_user.is_superuser:
            anom_query = anom_query.where(Anomaly.user_id == current_user.id)
            
        # Status Filter
        if status == 'all':
             pass
        elif status == 'reported':
             anom_query = anom_query.where(Anomaly.reason == "User Reported")
        elif status == 'pending' or status is None:
             anom_query = anom_query.where(Anomaly.is_resolved == False)
             
        # Execute Anomaly Query
        anom_res = await db.execute(anom_query)
        persisted_anomalies = anom_res.scalars().all()
        
        # Map to Response & Track IDs to avoid duplicates
        persisted_ids = set()
        
        for anom in persisted_anomalies:
            tx = anom.transaction
            if not tx: continue
            
            persisted_ids.add(tx.id)
            
            if anom.status:
                response_status = anom.status
            else:
                response_status = "pending" if not anom.is_resolved else "resolved"
                
                if anom.is_resolved and anom.reason == 'User Ignored':
                    response_status = "ignored"
                elif not anom.is_resolved and anom.reason == 'User Reported':
                    response_status = "reported"
            
            if response_status == "reported" and not anom.is_resolved:
                response_status = "pending"
            
            # Risk Level filter
            if risk_level and (anom.severity or "위험") != risk_level:
                continue

            anomalies.append(AnomalyResponse(
                id=anom.id,
                transactionId=tx.id,
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
        # 2. Heuristic & AI Check on Recent Transactions (Catch NEW anomalies)
        # ============================================================
        if status != 'reported':
            start_date = datetime.now() - timedelta(days=days)
            
            tx_query = (
                select(Transaction)
                .where(Transaction.transaction_time >= start_date)
                .where(Transaction.id.not_in(persisted_ids))
                .options(selectinload(Transaction.user), selectinload(Transaction.category))
                .order_by(Transaction.transaction_time.desc())
            )
            
            if not current_user.is_superuser:
                tx_query = tx_query.where(Transaction.user_id == current_user.id)
                
            tx_query = tx_query.limit(1000) 
            
            tx_res = await db.execute(tx_query)
            recent_txs = tx_res.scalars().all()
            
            # Safety Net: Force Include High Value Transactions (>= 100M)
            high_val_query = (
                select(Transaction)
                .where(Transaction.transaction_time >= start_date)
                .where(Transaction.amount >= 100000000) # 100 Million
                .where(Transaction.id.not_in(persisted_ids))
                .options(selectinload(Transaction.user), selectinload(Transaction.category))
            )
            if not current_user.is_superuser:
                 high_val_query = high_val_query.where(Transaction.user_id == current_user.id)
            
            high_val_res = await db.execute(high_val_query)
            high_val_txs = high_val_res.scalars().all()
            
            recent_tx_ids = set(t.id for t in recent_txs)
            for hv in high_val_txs:
                if hv.id not in recent_tx_ids:
                    recent_txs.append(hv)
            
            # Calculate Averages
            if recent_txs:
                user_ids = list(set(tx.user_id for tx in recent_txs))
                
                history_query = (
                    select(
                        Transaction.user_id,
                        Transaction.category_id,
                        Transaction.amount,
                        Transaction.id,
                        Transaction.transaction_time
                    )
                    .where(Transaction.user_id.in_(user_ids))
                    .order_by(Transaction.transaction_time.desc())
                )
                
                history_res = await db.execute(history_query)
                rows = history_res.fetchall()
                
                user_cat_history: dict[int, dict[int, list[tuple[float, int]]]] = {}

                for uid, cat_id, amt, tx_id, tx_time in rows:
                    if uid not in user_cat_history:
                        user_cat_history[uid] = {}
                    if cat_id not in user_cat_history[uid]:
                        user_cat_history[uid][cat_id] = []
                    if len(user_cat_history[uid][cat_id]) < 50:
                        user_cat_history[uid][cat_id].append((float(amt), int(tx_id)))

                for tx in recent_txs:
                    if tx.id in persisted_ids:
                        continue

                    cat_id = tx.category_id
                    history_list = user_cat_history.get(tx.user_id, {}).get(cat_id, [])
                    valid_history = [amt for amt, tid in history_list if tid != tx.id]
                    recent_30_amts = valid_history[:30]
                    
                    if not recent_30_amts:
                        avg_amt = float(tx.amount) if tx.amount else 1.0
                    else:
                        avg_amt = sum(recent_30_amts) / len(recent_30_amts)
                    if avg_amt == 0: avg_amt = 1.0

                    user_recent_history = [t for t in recent_txs if t.user_id == tx.user_id]
                    features = calculate_features(tx, avg_amt, user_recent_history)
                    
                    risk, reason = apply_heuristics(tx, features)
                    
                    if risk == "정상" or risk is None:
                        risk, reason = detect_fraud_with_model(tx, user_recent_history)
                    
                    if risk != "정상" and risk is not None:
                        # Risk Level filter
                        if risk_level and risk != risk_level:
                            continue

                        is_duplicate = False
                        for a in anomalies:
                            if a.transactionId == tx.id:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            reason_str = reason[:255] if reason else "System Detected"
                            
                            new_anomaly = Anomaly(
                                user_id=tx.user_id,
                                transaction_id=tx.id,
                                reason=reason_str,
                                severity=risk,
                                is_resolved=False,
                                status="pending",
                                created_at=datetime.utcnow()
                            )
                            db.add(new_anomaly)
                            await db.flush()
                            
                            anomalies.append(AnomalyResponse(
                                id=new_anomaly.id,
                                transactionId=tx.id,
                                userId=f"user_{tx.user_id}",
                                userName=tx.user.name if tx.user else f"User {tx.user_id}",
                                merchant=tx.merchant_name or "Unknown",
                                category=tx.category.name if tx.category else "기타",
                                amount=float(tx.amount),
                                date=tx.transaction_time.strftime("%Y-%m-%d %H:%M"),
                                riskLevel=risk,
                                reason=reason_str,
                                status="pending"
                            ))
                await db.commit()

        logger.info(f"Returned {len(anomalies)} anomalies")
        return anomalies
        
    except Exception as e:
        logger.error(f"Error getting anomalies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/anomalies/{anomaly_id}/report")
async def report_anomaly(
    anomaly_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Anomaly).where(Anomaly.id == anomaly_id)
    result = await db.execute(query)
    anomaly = result.scalar_one_or_none()
    
    if not anomaly or (not current_user.is_superuser and anomaly.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Anomaly not found")
        
    anomaly.is_resolved = False
    anomaly.reason = 'User Reported'
    anomaly.status = 'pending'
    
    await db.commit()
    await db.refresh(anomaly)
    return {"status": "pending", "id": anomaly.id, "transactionId": anomaly.transaction_id}

@router.post("/anomalies/{anomaly_id}/ignore")
async def ignore_anomaly(
    anomaly_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Anomaly).where(Anomaly.id == anomaly_id)
    result = await db.execute(query)
    anomaly = result.scalar_one_or_none()
    
    if not anomaly or (not current_user.is_superuser and anomaly.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Anomaly not found")
        
    anomaly.is_resolved = True
    anomaly.reason = 'User Ignored'
    anomaly.status = 'ignored'
    
    await db.commit()
    await db.refresh(anomaly)
    return {"status": "ignored", "id": anomaly.id, "transactionId": anomaly.transaction_id}

@router.post("/anomalies/{anomaly_id}/approve")
async def approve_anomaly(
    anomaly_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    query = select(Anomaly).where(Anomaly.id == anomaly_id)
    result = await db.execute(query)
    anomaly = result.scalar_one_or_none()
    
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
        
    anomaly.is_resolved = True
    anomaly.status = 'approved'
    await db.commit()
    return {"status": "approved", "id": anomaly_id}

@router.post("/anomalies/{anomaly_id}/reject")
async def reject_anomaly(
    anomaly_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    query = select(Anomaly).where(Anomaly.id == anomaly_id)
    result = await db.execute(query)
    anomaly = result.scalar_one_or_none()
    
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
        
    anomaly.is_resolved = True
    anomaly.status = 'rejected'
    await db.commit()
    return {"status": "rejected", "id": anomaly_id}

@router.post("/anomalies/{anomaly_id}/reset")
async def reset_anomaly(
    anomaly_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    query = select(Anomaly).where(Anomaly.id == anomaly_id)
    result = await db.execute(query)
    anomaly = result.scalar_one_or_none()
    
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
        
    anomaly.is_resolved = False
    anomaly.status = 'pending'
    await db.commit()
    return {"status": "pending", "id": anomaly_id}

@router.post("/anomalies/{anomaly_id}/notify")
async def notify_anomaly(
    anomaly_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    이상 거래에 대해 해당 사용자에게 알림을 전송합니다.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    from app.services.push_service import send_anomaly_alert
    from app.db.model.notification import Notification
    
    try:
        # Get anomaly first to get transaction_id
        anom_query = select(Anomaly).where(Anomaly.id == anomaly_id)
        anom_res = await db.execute(anom_query)
        anomaly = anom_res.scalar_one_or_none()
        
        if not anomaly:
             raise HTTPException(status_code=404, detail="Anomaly record not found")
        
        tx_id = anomaly.transaction_id

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
            Transaction.id == tx_id
        )
        
        result = await db.execute(query)
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        category_name = row.category_name or "기타"
        amount = float(row.amount)
        reason = "관리자가 이상 거래로 판단하여 알림을 보냈습니다."
        
        # 1. 앱 내 알림 센터에 저장
        notification = Notification(
            user_id=row.user_id,
            type="anomaly",
            title="⚠️ 이상 거래 감지",
            message=f"{category_name}에서 ₩{amount:,.0f} 거래가 의심됩니다. (거래 ID: {row.id})\n{reason}"
        )
        db.add(notification)
        await db.commit()
        
        # 2. 푸시 알림 전송 (토큰이 있을 경우)
        push_sent = False
        if row.push_token:
            push_res = await send_anomaly_alert(
                push_token=row.push_token,
                transaction_id=row.id,
                amount=amount,
                category=category_name,
                reason=reason
            )
            push_sent = push_res.get("success", False)
        
        return {
            "success": True,
            "message": "알림이 전송되었습니다.",
            "id": anomaly_id,
            "push_sent": push_sent
        }
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to send notification")
