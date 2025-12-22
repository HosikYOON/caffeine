import random
import string
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from passlib.context import CryptContext

from app.db.model.user import User as UserModel
from app.db.model.transaction import Transaction, UserCoupon
from app.db.schema.auth import (
    FindEmailRequest, FindEmailResponse, 
    RequestPasswordResetRequest, VerifyCodeRequest, ResetPasswordRequest
)
from app.core.email import send_verification_email

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 인증 코드 저장소 (임시 메모리)
verification_codes: Dict[str, Dict[str, Any]] = {}

def generate_verification_code() -> str:
    return ''.join(random.choices(string.digits, k=6))

def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email
    local, domain = email.split("@")
    masked_local = local[:2] + "***" if len(local) > 2 else local[0] + "***"
    return f"{masked_local}@{domain}"

async def find_email_service(request: FindEmailRequest, db: AsyncSession) -> FindEmailResponse:
    query = select(UserModel).where(
        UserModel.name == request.name,
        UserModel.phone == request.phone
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        return FindEmailResponse(found=False, message="일치하는 계정을 찾을 수 없습니다.")
    
    return FindEmailResponse(
        found=True,
        masked_email=mask_email(user.email),
        message="가입된 이메일을 찾았습니다."
    )

async def request_password_reset_service(request: RequestPasswordResetRequest, db: AsyncSession) -> dict:
    query = select(UserModel).where(UserModel.email == request.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        return {"success": True, "message": "이메일이 존재하면 인증 코드가 발송됩니다."}
    
    code = generate_verification_code()
    expires = datetime.utcnow() + timedelta(minutes=5)
    verification_codes[request.email] = {"code": code, "expires": expires}
    
    if send_verification_email(request.email, code):
        return {"success": True, "message": "인증 코드가 이메일로 발송되었습니다."}
    
    raise HTTPException(status_code=500, detail="이메일 발송 실패")

async def verify_reset_code_service(request: VerifyCodeRequest) -> dict:
    stored = verification_codes.get(request.email)
    if not stored or datetime.utcnow() > stored["expires"]:
        verification_codes.pop(request.email, None)
        raise HTTPException(status_code=400, detail="인증 코드가 만료되었거나 존재하지 않습니다.")
    
    if stored["code"] != request.code:
        raise HTTPException(status_code=400, detail="인증 코드가 일치하지 않습니다.")
    
    return {"success": True, "message": "인증 코드가 확인되었습니다."}

async def reset_password_service(request: ResetPasswordRequest, db: AsyncSession) -> dict:
    await verify_reset_code_service(VerifyCodeRequest(email=request.email, code=request.code))
    
    query = select(UserModel).where(UserModel.email == request.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    user.password_hash = pwd_context.hash(request.new_password)
    user.updated_at = datetime.utcnow()
    await db.commit()
    verification_codes.pop(request.email, None)
    
    return {"success": True, "message": "비밀번호가 성공적으로 변경되었습니다."}

async def delete_account_service(user_id: int, db: AsyncSession) -> bool:
    query = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    await db.execute(delete(Transaction).where(Transaction.user_id == user_id))
    await db.execute(delete(UserCoupon).where(UserCoupon.user_id == user_id))
    await db.delete(user)
    await db.commit()
    return True
