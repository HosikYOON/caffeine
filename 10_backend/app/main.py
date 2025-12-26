# 10_backend/app/main.py
"""
Caffeine Backend API (v1.0)

이 파일은 FastAPI 애플리케이션의 메인 진입점입니다.

✅ 실제 구현 보안 기능 (v1.0):
- JWT 인증 + 라이트 RBAC (user/admin 역할 구분)
- slowapi Rate Limiting (API 요청 속도 제한)
- 부분적 PII 암호화 (카드번호, 전화번호만)
- 라이트 Audit 로그 (파일/콘솔 기반 간단한 로깅)
- HTTPS + 보안 헤더 (Nginx와 함께 사용)

📋 추후 확장 예정 (v2.0+):
- JWT 블랙리스트 (로그아웃 시 토큰 무효화)
- 풀스펙 Audit 시스템 (데이터베이스 기반 영구 로그)
- 복잡한 보안 정책 문서

작성일: 2025-12
버전: 1.0.0
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# ============================================================
# 환경 변수 로드
# ============================================================
load_dotenv()  # 현재 디렉토리 또는 상위의 .env (override=False가 기본값)

# ============================================================
# 로거 설정 (라이트 Audit 로그)
# ============================================================
# v1.0에서는 파일과 콘솔에 간단히 로깅만 수행합니다.
# 모든 HTTP 요청/응답이 audit.log 파일과 콘솔에 기록됩니다.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audit.log'),  # 파일 로깅
        logging.StreamHandler()             # 콘솔 로깅
    ]
)
logger = logging.getLogger(__name__)
audit_logger = logging.getLogger('audit')  # Audit 전용 로거

# ============================================================
# Rate Limiter 초기화 (slowapi)
# ============================================================
# slowapi를 사용하여 API 엔드포인트별 요청 속도를 제한합니다.
# 기본적으로 클라이언트 IP 주소를 기준으로 제한합니다.
limiter = Limiter(key_func=get_remote_address)

# ============================================================
# FastAPI 앱 생성
# ============================================================
app = FastAPI(
    title="Caffeine API",
    description="AI 기반 스마트 금융 관리 앱 백엔드 API",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc"     # ReDoc
)

# Rate Limiter를 앱 상태에 연결
app.state.limiter = limiter
# Rate Limit 초과 시 에러 핸들러 등록
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============================================================
# CORS 설정 (Cross-Origin Resource Sharing)
# ============================================================

CLOUDFRONT_URL = "https://d26uyg5darllja.cloudfront.net"

LOCAL_ORIGINS = [
    # Localhost (Dev)
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8001",
    "http://localhost:8081",
    "http://localhost:8082",
    "http://localhost:8080",
    "http://localhost:19000",
    "http://localhost:19006",
    # 127.0.0.1 variants (same as localhost but treated as different origin by browsers)
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:8001",
    "http://127.0.0.1:8082",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:19000",
    "http://127.0.0.1:19006"
]

CUSTOM_DOMAINS = [
    "https://caffeineai.net",
    "https://admin.caffeineai.net",
    "https://api.caffeineai.net",
    # Trailing slash versions for safety
    "https://caffeineai.net/",
    "https://admin.caffeineai.net/",
    "https://api.caffeineai.net/",
]

allowed_origins = LOCAL_ORIGINS + [CLOUDFRONT_URL] + CUSTOM_DOMAINS

# 보안 헤더 미들웨어
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """
    모든 응답에 보안 헤더를 추가하는 미들웨어
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# 라이트 Audit 로그 미들웨어
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    """
    모든 HTTP 요청/응답을 로깅하는 미들웨어
    """
    start_time = datetime.utcnow()
    
    # 요청 로깅
    audit_logger.info(
        f"Request: {request.method} {request.url.path} | "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    
    # 실제 요청 처리
    response = await call_next(request)
    
    # 응답 로깅
    duration = (datetime.utcnow() - start_time).total_seconds()
    audit_logger.info(
        f"Response: {response.status_code} | Duration: {duration:.3f}s"
    )
    
    return response

# CORS 미들웨어 등록
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 기본 엔드포인트
@app.get("/")
async def root():
    return {
        "message": "Caffeine API v1.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
@limiter.limit("10/minute")
async def health(request: Request):
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }

# 라우터 등록
from app.routers import (
    ml, analysis, transactions, user, coupons, 
    settings, reports, anomalies, user_analytics, analytics_demographics,
    admin_transactions
)
from app.routers.chatbot import router as chatbot_router
from app.routers.auth import kakao_router, google_router, password_router
from app.routers.anomalies import fix_router

# 라우터 포함
# 0. /api/api hotfix
app.include_router(fix_router, prefix="/api")

# 1. /api prefix 추가 그룹: 내부 prefix가 제거된 라우터들 (/admin/...) 또는 원래 없는 라우터들 (/users)
app.include_router(transactions.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(kakao_router, prefix="/api")      # 카카오 로그인
app.include_router(google_router, prefix="/api")     # 구글 로그인
app.include_router(password_router, prefix="/api")   # 비밀번호/회원탈퇴
app.include_router(coupons.router, prefix="/api")

# 관리자/분석 라우터 추가
app.include_router(analysis.router, prefix="/api")  # /api/analysis/* 라우터 (admin/full 포함)
app.include_router(user_analytics.router, prefix="/api")
app.include_router(analytics_demographics.router, prefix="/api")
app.include_router(admin_transactions.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(anomalies.router, prefix="/api") # Added anomalies router
app.include_router(ml.router, prefix="/api")

# 챗봇 API (/api/chat/*)
app.include_router(chatbot_router, prefix="/api")

# ============================================================
# 시작 / 종료 이벤트
# ============================================================

@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler
    """
    logger.info("=" * 60)
    logger.info("Caffeine API started")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"CORS Allowed Origins: {allowed_origins}")
    
    # ML 모델 로드 (자동 로드됨)
    # ml.load_model()
    
    # 스케줄러 시작
    from app.services.scheduler import start_scheduler
    start_scheduler()
    
    # DB 연결 초기화
    from app.services.db_init import ensure_database_and_tables
    await ensure_database_and_tables()
    
    # Anomaly status column migration (Auto-fix)
    from app.db.database import ensure_status_column_exists
    await ensure_status_column_exists()


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler
    """
    # 스케줄러 종료
    from app.services.scheduler import shutdown_scheduler
    shutdown_scheduler()
    
    logger.info("Caffeine API stopped")
    logger.info("=" * 60)
