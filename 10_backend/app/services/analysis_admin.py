from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List
import logging

from app.db.schema.analysis import DashboardSummary, AnalysisResponse
from app.db.crud import analysis as crud_analysis

logger = logging.getLogger(__name__)

async def get_admin_summary(db: AsyncSession, year: Optional[int] = None, month: Optional[int] = None) -> DashboardSummary:
    try:
        now = datetime.now()
        start_date = datetime(year, month, 1) if year and month else now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 전체 사용자 통계 (관리자 제외)
        row = await crud_analysis.fetch_monthly_stats(db, None, start_date)
        total, avg, count = float(row.total), float(row.avg), row.count
        
        cat_row = await crud_analysis.fetch_top_category(db, None, start_date)
        top_category = cat_row[0] if cat_row else "없음"
        
        return DashboardSummary(
            total_spending=total, average_transaction=avg, transaction_count=count,
            top_category=top_category, month_over_month_change=0.0, transaction_count_mom_change=0.0,
            data_source="DB (Admin - All Users)"
        )
    except Exception as e:
        logger.warning(f"Admin Summary Error: {e}")
        return crud_analysis.get_mock_summary()

async def get_admin_full_analysis(db: AsyncSession, year: Optional[int] = None, month: Optional[int] = None) -> AnalysisResponse:
    now = datetime.now()
    start_date = datetime(year, month, 1) if year and month else now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    summary = await get_admin_summary(db, year, month)
    
    # 실제 데이터 집계
    category_data = await crud_analysis.fetch_category_breakdown(db, None, start_date)
    trend_data = await crud_analysis.fetch_monthly_trend(db, None, months=6)
    
    return AnalysisResponse(
        summary=summary,
        category_breakdown=category_data or crud_analysis.get_mock_category_breakdown(),
        monthly_trend=trend_data,
        insights=crud_analysis.get_mock_insights(),
        data_source="DB (Admin All Users)"
    )
