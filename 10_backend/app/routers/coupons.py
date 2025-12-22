from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List, Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.db.database import get_db
from app.core.jwt import verify_access_token
from app.db.schema.coupon import (
    UserCouponResponse, IssueCouponRequest, IssueCouponResponse, UseCouponResponse
)
from app.services import coupon_service

router = APIRouter(prefix="/coupons", tags=["쿠폰"])
DB_Dependency = Annotated[AsyncSession, Depends(get_db)]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    payload = verify_access_token(token)
    return int(payload.get("sub"))

@router.get("", response_model=List[UserCouponResponse])
async def get_user_coupons(
    status: Optional[str] = Query(None),
    db: DB_Dependency = None,
    user_id: int = Depends(get_current_user_id)
):
    return await coupon_service.get_user_coupons_service(db, user_id, status)

@router.post("/issue", response_model=IssueCouponResponse)
async def issue_coupon(
    request: IssueCouponRequest,
    db: DB_Dependency = None,
    user_id: int = Depends(get_current_user_id)
):
    return await coupon_service.issue_coupon_service(db, user_id, request)

@router.post("/{coupon_id}/use", response_model=UseCouponResponse)
async def use_coupon(
    coupon_id: int,
    db: DB_Dependency = None,
    user_id: int = Depends(get_current_user_id)
):
    return await coupon_service.use_coupon_service(db, user_id, coupon_id)
