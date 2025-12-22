from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from app.db.model.transaction import Transaction
from app.db.schema.analysis import (
    DashboardSummary, CategoryBreakdown, MonthlyTrend, SpendingInsight
)

# --- Mock Data Fallbacks ---

def get_mock_summary() -> DashboardSummary:
    return DashboardSummary(
        total_spending=1250000, average_transaction=25000, transaction_count=50,
        top_category="외식", month_over_month_change=-5.2,
        transaction_count_mom_change=-3.8, data_source="[MOCK]"
    )

def get_mock_category_breakdown() -> List[CategoryBreakdown]:
    return [
        CategoryBreakdown(category="외식", total_amount=450000, transaction_count=18, percentage=36.0),
        CategoryBreakdown(category="교통", total_amount=280000, transaction_count=12, percentage=22.4),
        CategoryBreakdown(category="쇼핑", total_amount=220000, transaction_count=8, percentage=17.6),
    ]

def get_mock_monthly_trend() -> List[MonthlyTrend]:
    return [
        MonthlyTrend(month="2025-10", total_amount=1320000, transaction_count=52),
        MonthlyTrend(month="2025-11", total_amount=1180000, transaction_count=47),
        MonthlyTrend(month="2025-12", total_amount=1250000, transaction_count=50),
    ]

def get_mock_insights() -> List[SpendingInsight]:
    return [
        SpendingInsight(insight_type="warning", title="외식비 주의",
                       description="이번 달 외식비가 전월 대비 15% 증가했습니다.", category="외식"),
        SpendingInsight(insight_type="tip", title="다음 소비 예측",
                       description="AI 분석 결과, 다음 결제는 '외식' 카테고리일 확률이 78%입니다.", category="외식"),
    ]

# --- Shared Query Helpers ---

async def fetch_monthly_stats(db: AsyncSession, user_id: Optional[int], start_date: datetime):
    query = select(
        func.coalesce(func.sum(Transaction.amount), 0).label('total'),
        func.coalesce(func.avg(Transaction.amount), 0).label('avg'),
        func.count(Transaction.id).label('count')
    ).where(Transaction.transaction_time >= start_date)
    
    if user_id is not None:
        query = query.where(Transaction.user_id == user_id)
    else:
        # Admin: All non-admin users
        from app.db.model.user import User
        query = query.join(User, Transaction.user_id == User.id).where(User.is_superuser == False)
        
    result = await db.execute(query)
    return result.fetchone()

async def fetch_top_category(db: AsyncSession, user_id: Optional[int], start_date: datetime):
    filter_sql = "t.user_id = :user_id" if user_id is not None else "u.is_superuser = false"
    join_sql = "" if user_id is not None else "JOIN users u ON t.user_id = u.id"
    
    cat_query = text(f"""
        SELECT c.name, SUM(t.amount) as cat_total
        FROM transactions t
        {join_sql}
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.transaction_time >= :start_date AND {filter_sql}
        GROUP BY c.name
        ORDER BY cat_total DESC
        LIMIT 1
    """)
    
    params = {"start_date": start_date}
    if user_id is not None:
        params["user_id"] = user_id
        
    result = await db.execute(cat_query, params)
    return result.fetchone()

async def fetch_monthly_trend(db: AsyncSession, user_id: Optional[int], months: int = 6) -> List[MonthlyTrend]:
    """최근 N개월간의 월별 지출 추이 집계"""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    # 최근 N개월의 시작일 계산
    now = datetime.now()
    start_date = (now - relativedelta(months=months-1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # PostgreSQL/SQLite 호환을 위한 날짜 포맷팅 및 그룹화
    # AWS RDS가 PostgreSQL이므로 TO_CHAR 사용, 로컬 SQLite 등을 위해 strftime 고려 (여기서는 PostgreSQL 우선)
    date_format = "TO_CHAR(transaction_time, 'YYYY-MM')"
    
    query = select(
        text(f"{date_format} as month_str"),
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).where(Transaction.transaction_time >= start_date)
    
    if user_id is not None:
        query = query.where(Transaction.user_id == user_id)
    else:
        from app.db.model.user import User
        query = query.join(User, Transaction.user_id == User.id).where(User.is_superuser == False)
        
    query = query.group_by(text("month_str")).order_by(text("month_str ASC"))
    
    result = await db.execute(query)
    rows = result.all()
    
    return [
        MonthlyTrend(month=row[0], total_amount=float(row[1]), transaction_count=row[2])
        for row in rows
    ]

async def fetch_category_breakdown(db: AsyncSession, user_id: Optional[int], start_date: datetime) -> List[CategoryBreakdown]:
    """카테고리별 지출 비중 집계"""
    from app.db.model.transaction import Category
    
    # 1. 특정 기간 전체 금액 합계
    total_query = select(func.sum(Transaction.amount)).where(Transaction.transaction_time >= start_date)
    if user_id is not None:
        total_query = total_query.where(Transaction.user_id == user_id)
    else:
        from app.db.model.user import User
        total_query = total_query.join(User, Transaction.user_id == User.id).where(User.is_superuser == False)
    
    total_res = await db.execute(total_query)
    grand_total = float(total_res.scalar() or 0)
    
    if grand_total == 0:
        return []

    # 2. 카테고리별 합계
    query = select(
        Category.name,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).join(Category, Transaction.category_id == Category.id).where(Transaction.transaction_time >= start_date)
    
    if user_id is not None:
        query = query.where(Transaction.user_id == user_id)
    else:
        from app.db.model.user import User
        query = query.join(User, Transaction.user_id == User.id).where(User.is_superuser == False)
        
    query = query.group_by(Category.name).order_by(text("total DESC"))
    
    result = await db.execute(query)
    rows = result.all()
    
    return [
        CategoryBreakdown(
            category=row[0], 
            total_amount=float(row[1]), 
            transaction_count=row[2],
            percentage=round(float(row[1]) / grand_total * 100, 1) if grand_total > 0 else 0
        )
        for row in rows
    ]
