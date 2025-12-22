"""
알림 API 라우터

사용자 알림 조회 및 관리 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import List, Optional
from datetime import datetime
import json
import logging

from app.db.database import get_db
from app.db.model.notification import Notification
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# Pydantic 모델
class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    user_id: int
    type: str = "system"
    title: str
    message: str


@router.get("/user/{user_id}", response_model=List[NotificationResponse])
async def get_user_notifications(
    user_id: int,
    limit: int = 50,
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 사용자의 알림 목록을 조회합니다.
    """
    try:
        query = select(Notification).where(
            Notification.user_id == user_id
        ).order_by(Notification.created_at.desc()).limit(limit)
        
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        # metadata JSON 파싱
        response = []
        for n in notifications:
            notification_dict = {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at
            }
            response.append(notification_dict)
        
        return response
        
    except Exception as e:
        logger.error(f"알림 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/unread-count")
async def get_unread_count(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    읽지 않은 알림 개수를 조회합니다.
    """
    try:
        query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
        result = await db.execute(query)
        count = result.scalar() or 0
        
        return {"unread_count": count}
        
    except Exception as e:
        logger.error(f"읽지 않은 알림 개수 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    알림을 읽음 처리합니다.
    """
    try:
        stmt = update(Notification).where(
            Notification.id == notification_id
        ).values(
            is_read=True,
            read_at=datetime.utcnow()
        )
        
        await db.execute(stmt)
        await db.commit()
        
        return {"message": "알림을 읽음 처리했습니다.", "id": notification_id}
        
    except Exception as e:
        logger.error(f"알림 읽음 처리 실패: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/{user_id}/read-all")
async def mark_all_as_read(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    해당 사용자의 모든 알림을 읽음 처리합니다.
    """
    try:
        stmt = update(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).values(
            is_read=True,
            read_at=datetime.utcnow()
        )
        
        await db.execute(stmt)
        await db.commit()
        
        return {"message": "모든 알림을 읽음 처리했습니다."}
        
    except Exception as e:
        logger.error(f"전체 알림 읽음 처리 실패: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_notification(
    payload: NotificationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    새 알림을 생성합니다. (관리자용)
    """
    try:
        notification = Notification(
            user_id=payload.user_id,
            type=payload.type,
            title=payload.title,
            message=payload.message
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        logger.info(f"알림 생성 완료: user_id={payload.user_id}, type={payload.type}")
        
        return {
            "message": "알림이 생성되었습니다.",
            "id": notification.id
        }
        
    except Exception as e:
        logger.error(f"알림 생성 실패: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
