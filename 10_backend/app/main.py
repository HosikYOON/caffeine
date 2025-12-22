from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
from dotenv import load_dotenv

# 로컬 모듈 임포트
from app.core.logging import setup_logging
from app.core.middleware import security_headers_middleware, audit_log_middleware
from app.core.lifespan import lifespan
from app.routers import init_routers

# 환경 변수 및 로깅 초기화
load_dotenv()
setup_logging()

# Rate Limiter 초기화
limiter = Limiter(key_func=get_remote_address)

# FastAPI 앱 생성 (Lifespan 도입)
app = FastAPI(
    title="Caffeine API",
    description="AI 기반 스마트 금융 관리 앱 백엔드 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 기본 설정 주입
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 미들웨어 순서대로 등록 (역순으로 쌓임)
app.middleware("http")(audit_log_middleware)
app.middleware("http")(security_headers_middleware)

# 라우터 통합 등록
init_routers(app)

# CORS 설정
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
    # 127.0.0.1 (Local)
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:8001",
    "http://127.0.0.1:8081",
    "http://127.0.0.1:8082",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:19000",
    "http://127.0.0.1:19006",
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

ALLOWED_ORIGINS = LOCAL_ORIGINS + [CLOUDFRONT_URL] + CUSTOM_DOMAINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 기본 헬스체크 엔드포인트
@app.get("/")
async def root():
    return {"message": "Caffeine API v1.0", "status": "running", "docs": "/docs"}

@app.get("/health")
@limiter.limit("10/minute")
async def health(request: Request):
    from datetime import datetime
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}