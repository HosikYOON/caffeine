from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

# 로그인 요청 (일반)
class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="로그인 이메일")
    password: str = Field(..., description="비밀번호(평문 입력)")
    device_info: Optional[str] = Field(None, description="디바이스 정보(선택)")

# 토큰 응답
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    class Config:
        from_attributes = True

# 토큰 페어 응답
class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

# 로그인 응답 (일반)
class LoginResponse(BaseModel):
    user_id: int
    email: EmailStr
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

# --- 카카오 소셜 인증 스키마 ---

class KakaoLoginRequest(BaseModel):
    """카카오 로그인 요청"""
    code: str

class KakaoUserResponse(BaseModel):
    """카카오 로그인 응답 - 사용자 정보"""
    id: int
    nickname: str
    email: Optional[str] = None
    profile_image: Optional[str] = None
    provider: str = "kakao"
    birth_date: Optional[str] = None

class KakaoLoginResponse(BaseModel):
    """카카오 로그인 응답"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: KakaoUserResponse

# --- 아이디 찾기 / 비밀번호 재설정 스키마 ---

class FindEmailRequest(BaseModel):
    """아이디(이메일) 찾기 요청"""
    name: str
    phone: str

class FindEmailResponse(BaseModel):
    """아이디(이메일) 찾기 응답"""
    found: bool
    masked_email: Optional[str] = None
    message: str

class RequestPasswordResetRequest(BaseModel):
    """비밀번호 재설정 요청 (인증 코드 발송)"""
    email: str

class VerifyCodeRequest(BaseModel):
    """인증 코드 확인 요청"""
    email: str
    code: str

class ResetPasswordRequest(BaseModel):
    """비밀번호 재설정 요청"""
    email: str
    code: str
    new_password: str
