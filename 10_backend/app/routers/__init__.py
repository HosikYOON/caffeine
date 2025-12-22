from fastapi import FastAPI
from . import (
    ml, analysis, transactions, user, auth, coupons, 
    settings, reports, anomalies, user_analytics, analytics_demographics, chatbot,
    notifications
)

def init_routers(app: FastAPI):
    """
    모든 라우터를 FastAPI 애플리케이션에 등록
    """
    # 기본 기능 라우터
    app.include_router(ml.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(transactions.router, prefix="/api")
    app.include_router(user.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(coupons.router, prefix="/api")
    app.include_router(notifications.router, prefix="/api")

    # 관리자 및 분석용 라우터
    app.include_router(user_analytics.router, prefix="/api")
    app.include_router(analytics_demographics.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(anomalies.router, prefix="/api")
    app.include_router(chatbot.router, prefix="/api")
