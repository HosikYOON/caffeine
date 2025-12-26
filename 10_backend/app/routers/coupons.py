# 쿠폰 API 라우터
import random
import string
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from jose import JWTError

from app.db.database import get_db
from app.db.model.transaction import CouponTemplate, UserCoupon
from app.core.jwt import verify_access_token

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coupons", tags=["쿠폰"])

# DB 세션 의존성
DB_Dependency = Annotated[AsyncSession, Depends(get_db)]
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

# Pydantic 스키마
class CouponTemplateResponse(BaseModel):
    id: int
    merchant_name: Optional[str]
    title: str
    description: Optional[str]
    discount_type: str
    discount_value: int
    min_amount: Optional[int]

    class Config:
        from_attributes = True

class UserCouponResponse(BaseModel):
    id: int
    code: str
    status: str
    valid_until: datetime
    issued_at: datetime
    used_at: Optional[datetime]
    merchant_name: Optional[str]
    title: str
    description: Optional[str]
    discount_type: str
    discount_value: int
    min_amount: Optional[int]

class IssueCouponRequest(BaseModel):
    template_id: Optional[int] = None
    merchant_name: Optional[str] = None
    discount_value: Optional[int] = None

class IssueCouponResponse(BaseModel):
    success: bool
    message: str
    coupon: Optional[UserCouponResponse] = None

class UseCouponResponse(BaseModel):
    success: bool
    message: str

def generate_coupon_code(length: int = 12) -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

@router.get("", response_model=List[UserCouponResponse])
async def get_user_coupons(
    status: Optional[str] = Query(None, description="쿠폰 상태 필터 (available/used/expired)"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    query = select(UserCoupon).options(selectinload(UserCoupon.template)).where(UserCoupon.user_id == user_id)
    if status:
        query = query.where(UserCoupon.status == status)
    query = query.order_by(UserCoupon.issued_at.desc())
    result = await db.execute(query)
    user_coupons = result.scalars().all()
    
    # 만료 체크
    now = datetime.now(timezone.utc)
    for coupon in user_coupons:
        if coupon.status == "available" and coupon.valid_until < now:
            coupon.status = "expired"
    await db.commit()
    
    response = []
    for uc in user_coupons:
        template = uc.template
        response.append(UserCouponResponse(
            id=uc.id, code=uc.code, status=uc.status, valid_until=uc.valid_until,
            issued_at=uc.issued_at, used_at=uc.used_at,
            merchant_name=template.merchant_name if template else None,
            title=template.title if template else "쿠폰",
            description=template.description if template else None,
            discount_type=template.discount_type if template else "amount",
            discount_value=template.discount_value if template else 0,
            min_amount=template.min_amount if template else None
        ))
    return response

@router.post("/issue", response_model=IssueCouponResponse)
async def issue_coupon(
    request: IssueCouponRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    template = None
    if request.template_id:
        result = await db.execute(select(CouponTemplate).where(and_(CouponTemplate.id == request.template_id, CouponTemplate.is_active == True)))
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="쿠폰 템플릿을 찾을 수 없습니다.")
    elif request.merchant_name:
        result = await db.execute(select(CouponTemplate).where(and_(CouponTemplate.merchant_name == request.merchant_name, CouponTemplate.is_active == True)))
        template = result.scalar_one_or_none()
        if not template:
            discount = request.discount_value or 1000
            template = CouponTemplate(
                merchant_name=request.merchant_name, title=f"{request.merchant_name} 할인 쿠폰",
                description="AI 예측 기반 자동 발급 쿠폰", discount_type="amount",
                discount_value=discount, min_amount=5000, validity_days=30, is_active=True
            )
            db.add(template)
            await db.flush()
    else:
        raise HTTPException(status_code=400, detail="template_id 또는 merchant_name이 필요합니다.")
    
    # 중복 체크
    existing = await db.execute(select(UserCoupon).where(and_(UserCoupon.user_id == user_id, UserCoupon.template_id == template.id, UserCoupon.status == "available")))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 동일한 쿠폰을 보유하고 있습니다.")
    
    valid_until = datetime.now(timezone.utc) + timedelta(days=template.validity_days)
    user_coupon = UserCoupon(user_id=user_id, template_id=template.id, code=generate_coupon_code(), status="available", valid_until=valid_until)
    db.add(user_coupon)
    await db.commit()
    await db.refresh(user_coupon)
    
    return IssueCouponResponse(
        success=True, message=f"{template.title} 쿠폰이 발급되었습니다!",
        coupon=UserCouponResponse(
            id=user_coupon.id, code=user_coupon.code, status=user_coupon.status,
            valid_until=user_coupon.valid_until, issued_at=user_coupon.issued_at, used_at=None,
            merchant_name=template.merchant_name, title=template.title,
            description=template.description, discount_type=template.discount_type,
            discount_value=template.discount_value, min_amount=template.min_amount
        )
    )

@router.post("/{coupon_id}/use", response_model=UseCouponResponse)
async def use_coupon(coupon_id: int, db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    result = await db.execute(select(UserCoupon).options(selectinload(UserCoupon.template)).where(and_(UserCoupon.id == coupon_id, UserCoupon.user_id == user_id)))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="쿠폰을 찾을 수 없습니다.")
    if coupon.status == "used":
        raise HTTPException(status_code=400, detail="이미 사용된 쿠폰입니다.")
    if coupon.status == "expired" or coupon.valid_until < datetime.now(timezone.utc):
        coupon.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="만료된 쿠폰입니다.")
    
    coupon.status = "used"
    coupon.used_at = datetime.now(timezone.utc)
    await db.commit()
    return UseCouponResponse(success=True, message=f"{coupon.template.title} 쿠폰이 사용되었습니다!")

@router.delete("", response_model=dict)
async def delete_user_coupons(db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    stmt = delete(UserCoupon).where(UserCoupon.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()
    return {"success": True, "message": f"{result.rowcount}개의 쿠폰이 삭제되었습니다.", "deleted_count": result.rowcount}
