import random
import string
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.model.transaction import CouponTemplate, UserCoupon
from app.db.schema.coupon import (
    UserCouponResponse, IssueCouponRequest, IssueCouponResponse, UseCouponResponse
)

def generate_coupon_code(length: int = 12) -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

async def get_user_coupons_service(db: AsyncSession, user_id: int, status: Optional[str] = None) -> List[UserCouponResponse]:
    query = select(UserCoupon).options(selectinload(UserCoupon.template)).where(UserCoupon.user_id == user_id)
    if status: query = query.where(UserCoupon.status == status)
    
    result = await db.execute(query.order_by(UserCoupon.issued_at.desc()))
    user_coupons = result.scalars().all()
    
    # 만료 업데이트 및 변환
    now = datetime.now(timezone.utc)
    response = []
    for uc in user_coupons:
        if uc.status == "available" and uc.valid_until < now:
            uc.status = "expired"
            await db.commit()
        
        t = uc.template
        response.append(UserCouponResponse(
            id=uc.id, code=uc.code, status=uc.status, valid_until=uc.valid_until,
            issued_at=uc.issued_at, used_at=uc.used_at,
            merchant_name=t.merchant_name if t else None,
            title=t.title if t else "쿠폰",
            description=t.description if t else None,
            discount_type=t.discount_type if t else "amount",
            discount_value=t.discount_value if t else 0,
            min_amount=t.min_amount if t else None
        ))
    return response

async def issue_coupon_service(db: AsyncSession, user_id: int, request: IssueCouponRequest) -> IssueCouponResponse:
    # 템플릿 찾기 또는 생성
    if request.template_id:
        result = await db.execute(select(CouponTemplate).where(CouponTemplate.id == request.template_id))
        template = result.scalar_one_or_none()
    elif request.merchant_name:
        result = await db.execute(select(CouponTemplate).where(CouponTemplate.merchant_name == request.merchant_name))
        template = result.scalar_one_or_none()
        if not template:
            template = CouponTemplate(
                merchant_name=request.merchant_name, title=f"{request.merchant_name} 할인 쿠폰",
                discount_type="amount", discount_value=request.discount_value or 1000,
                validity_days=30, is_active=True
            )
            db.add(template)
            await db.flush()
    else:
        raise ValueError("Invalid request")

    # 발급 및 반환
    user_coupon = UserCoupon(
        user_id=user_id, template_id=template.id, code=generate_coupon_code(),
        status="available", valid_until=datetime.now(timezone.utc) + timedelta(days=template.validity_days)
    )
    db.add(user_coupon)
    await db.commit()
    await db.refresh(user_coupon)
    
    return IssueCouponResponse(success=True, message="Issued", coupon=None) # 상세 변환 생략

async def use_coupon_service(db: AsyncSession, user_id: int, coupon_id: int) -> UseCouponResponse:
    result = await db.execute(select(UserCoupon).where(and_(UserCoupon.id == coupon_id, UserCoupon.user_id == user_id)))
    coupon = result.scalar_one_or_none()
    if not coupon or coupon.status != "available":
        return UseCouponResponse(success=False, message="Unavailable")
    
    coupon.status = "used"
    coupon.used_at = datetime.now(timezone.utc)
    await db.commit()
    return UseCouponResponse(success=True, message="Used")
