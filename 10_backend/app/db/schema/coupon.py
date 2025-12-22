from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

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
    coupon: Optional[UserCouponResponse]

class UseCouponResponse(BaseModel):
    success: bool
    message: str
