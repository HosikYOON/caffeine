from pydantic import BaseModel
from typing import Optional, List

class DashboardSummary(BaseModel):
    total_spending: float
    average_transaction: float
    transaction_count: int
    top_category: str
    month_over_month_change: float
    transaction_count_mom_change: float
    data_source: str = "DB"

class CategoryBreakdown(BaseModel):
    category: str
    total_amount: float
    transaction_count: int
    percentage: float

class MonthlyTrend(BaseModel):
    month: str
    total_amount: float
    transaction_count: int

class SpendingInsight(BaseModel):
    insight_type: str
    title: str
    description: str
    category: Optional[str] = None
    amount: Optional[float] = None

class AnalysisResponse(BaseModel):
    summary: DashboardSummary
    category_breakdown: List[CategoryBreakdown]
    monthly_trend: List[MonthlyTrend]
    insights: List[SpendingInsight]
    data_source: str = "DB"
