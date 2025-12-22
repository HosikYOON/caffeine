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
    summary = await get_admin_summary(db, year, month)
    return AnalysisResponse(
        summary=summary,
        category_breakdown=crud_analysis.get_mock_category_breakdown(),
        monthly_trend=crud_analysis.get_mock_monthly_trend(),
        insights=crud_analysis.get_mock_insights(),
        data_source="Hybrid (Admin DB+Mock)"
    )
