from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, List
import logging

from app.db.schema.analysis import (
    DashboardSummary, CategoryBreakdown, MonthlyTrend, AnalysisResponse
)
from app.db.crud import analysis as crud_analysis

logger = logging.getLogger(__name__)

async def get_user_summary(db: AsyncSession, user_id: int, year: Optional[int] = None, month: Optional[int] = None) -> DashboardSummary:
    try:
        now = datetime.now()
        start_date = datetime(year, month, 1) if year and month else now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 이번 달
        row = await crud_analysis.fetch_monthly_stats(db, user_id, start_date)
        total, avg, count = float(row.total), float(row.avg), row.count
        
        # 최다 카테고리
        cat_row = await crud_analysis.fetch_top_category(db, user_id, start_date)
        top_category = cat_row[0] if cat_row else "없음"
        
        # 전월 대비 (Mom) 계산 생략하거나 CRUD로 추가 이동 가능하나 여기서는 간결하게 유지
        return DashboardSummary(
            total_spending=total, average_transaction=avg, transaction_count=count,
            top_category=top_category, month_over_month_change=0.0, transaction_count_mom_change=0.0,
            data_source="DB (AWS RDS)"
        )
    except Exception as e:
        logger.warning(f"User Summary Error: {e}")
        return crud_analysis.get_mock_summary()

async def get_user_full_analysis(db: AsyncSession, user_id: int) -> AnalysisResponse:
    summary = await get_user_summary(db, user_id)
    return AnalysisResponse(
        summary=summary, 
        category_breakdown=crud_analysis.get_mock_category_breakdown(),
        monthly_trend=crud_analysis.get_mock_monthly_trend(),
        insights=crud_analysis.get_mock_insights(),
        data_source="Hybrid (DB+Mock)"
    )
