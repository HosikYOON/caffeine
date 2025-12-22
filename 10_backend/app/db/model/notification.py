"""
사용자 알림 모델

앱 내 알림 센터에서 사용되는 알림 데이터를 저장합니다.
"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # 알림 유형: anomaly, system, promotion 등
    type = Column(String(50), nullable=False, default="system")
    
    # 알림 내용
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # 읽음 상태
    is_read = Column(Boolean, default=False, nullable=False)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type='{self.type}')>"
