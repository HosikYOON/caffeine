from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
import os

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 시작 및 종료 이벤트를 관리하는 lifespan 컨텍스트 매니저
    """
    # [STARTUP] 애플리케이션 시작 시 로직
    logger.info("=" * 60)
    logger.info("Caffeine API starting...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    # 1. 데이터베이스 테이블 생성 및 초기화
    try:
        from app.services.db_init import ensure_database_and_tables
        await ensure_database_and_tables()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # 2. ML 모델 로드 (싱글톤 초기화)
    try:
        from app.services.ml_service import get_ml_service
        get_ml_service()
    except Exception as e:
        logger.error(f"ML Model loading failed: {e}")
    
    # 3. 스케줄러 시작 (리포트 자동 생성 등)
    try:
        from app.services.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        logger.error(f"Scheduler start failed: {e}")
    
    logger.info("Caffeine API startup complete.")
    logger.info("=" * 60)
    
    yield
    
    # [SHUTDOWN] 애플리케이션 종료 시 로직
    logger.info("Caffeine API shutting down...")
    
    # 1. 스케줄러 안전 종료
    try:
        from app.services.scheduler import shutdown_scheduler
        shutdown_scheduler()
    except Exception as e:
        logger.error(f"Scheduler shutdown error: {e}")
        
    logger.info("Caffeine API stopped.")
    logger.info("=" * 60)
