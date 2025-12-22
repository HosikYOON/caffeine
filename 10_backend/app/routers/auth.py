from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
import logging

from app.db.database import get_db
from app.db.schema.auth import (
    KakaoLoginRequest, KakaoLoginResponse,
    FindEmailRequest, FindEmailResponse,
    RequestPasswordResetRequest, VerifyCodeRequest, ResetPasswordRequest
)
from app.core.jwt import verify_access_token
from app.services import auth_social, auth_account
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
DB_Dependency = Annotated[AsyncSession, Depends(get_db)]

# --- 소셜 로그인 엔드포인트 ---

@router.post("/kakao", response_model=KakaoLoginResponse)
async def kakao_login(payload: KakaoLoginRequest, db: DB_Dependency):
    """카카오 소셜 로그인"""
    return await auth_social.kakao_login_service(payload, db)

@router.post("/kakao/signup", response_model=KakaoLoginResponse)
async def kakao_signup(payload: KakaoLoginRequest, db: DB_Dependency):
    """카카오 소셜 회원가입"""
    return await auth_social.kakao_signup_service(payload, db)

@router.get("/kakao/callback")
async def kakao_callback(code: str):
    """카카오 OAuth 콜백 (테스트용)"""
    return {
        "message": "카카오 인증 코드 수신 완료",
        "code": code,
        "next_step": "이 코드를 POST /auth/kakao 엔드포인트로 전송하세요"
    }

# --- 계정 복구 / 패스워드 재설정 엔드포인트 ---

@router.post("/find-email", response_model=FindEmailResponse)
async def find_email(request: FindEmailRequest, db: DB_Dependency):
    """이름과 전화번호로 가입된 이메일 찾기"""
    return await auth_account.find_email_service(request, db)

@router.post("/request-password-reset")
async def request_password_reset(request: RequestPasswordResetRequest, db: DB_Dependency):
    """비밀번호 재설정 요청 (인증 코드 이메일 발송)"""
    return await auth_account.request_password_reset_service(request, db)

@router.post("/verify-reset-code")
async def verify_reset_code(request: VerifyCodeRequest):
    """이메일 인증 코드 확인"""
    return await auth_account.verify_reset_code_service(request)

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: DB_Dependency):
    """인증 코드 확인 후 비밀번호 재설정"""
    return await auth_account.reset_password_service(request, db)

# --- 회원 관리 엔드포인트 ---

class DeleteAccountResponse(BaseModel):
    success: bool
    message: str

@router.delete("/delete-account", response_model=DeleteAccountResponse)
async def delete_account(
    db: DB_Dependency,
    authorization: str = Header(None, alias="Authorization")
):
    """회원 탈퇴 및 모든 정보 삭제"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 토큰이 필요합니다.")
    
    token = authorization.replace("Bearer ", "")
    payload = verify_access_token(token)
    user_id = int(payload.get("sub"))
    
    await auth_account.delete_account_service(user_id, db)
    
    return DeleteAccountResponse(
        success=True,
        message="회원 탈퇴가 완료되었습니다. 이용해주셔서 감사합니다."
    )
