"""
리포트 생성 서비스

주간/월간 소비 데이터를 집계하고 리포트를 생성합니다.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.model.transaction import Transaction, Category
from app.db.model.user import User

logger = logging.getLogger(__name__)



from app.services.ai_service import call_gemini_api, generate_report_prompt

async def generate_weekly_report(db: AsyncSession) -> Dict[str, Any]:
    """
    주간 리포트 데이터를 생성합니다.
    
    Args:
        db: 데이터베이스 세션
    
    Returns:
        dict: 리포트 데이터
    """
    # 이번 주 (월요일 ~ 일요일)
    today = datetime.now()
    # 이번 주 월요일
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    # 다음 주 월요일 (이번 주 일요일 23:59:59)
    end_of_week = start_of_week + timedelta(days=7)
    
    # 지난 주
    last_week_start = start_of_week - timedelta(days=7)
    last_week_end = start_of_week
    
    # 이번 주 거래 데이터
    this_week_query = select(
        func.count(Transaction.id).label("count"),
        func.sum(Transaction.amount).label("total_amount")
    ).where(
        and_(
            Transaction.transaction_time >= start_of_week,
            Transaction.transaction_time < end_of_week,
            Transaction.status == "completed"
        )
    )
    this_week_result = await db.execute(this_week_query)
    this_week_data = this_week_result.first()
    
    # 지난 주 거래 데이터
    last_week_query = select(
        func.sum(Transaction.amount).label("total_amount")
    ).where(
        and_(
            Transaction.transaction_time >= last_week_start,
            Transaction.transaction_time < last_week_end,
            Transaction.status == "completed"
        )
    )
    last_week_result = await db.execute(last_week_query)
    last_week_data = last_week_result.first()
    
    # 카테고리별 집계
    category_query = select(
        Category.name,
        func.sum(Transaction.amount).label("amount"),
        func.count(Transaction.id).label("count")
    ).join(
        Transaction, Transaction.category_id == Category.id
    ).where(
        and_(
            Transaction.transaction_time >= start_of_week,
            Transaction.transaction_time < end_of_week,
            Transaction.status == "completed"
        )
    ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).limit(5)
    
    category_result = await db.execute(category_query)
    categories = category_result.all()
    
    # 전주 대비 증감율 계산
    this_week_total = float(this_week_data.total_amount or 0)
    last_week_total = float(last_week_data.total_amount or 0)
    
    if last_week_total > 0:
        change_rate = ((this_week_total - last_week_total) / last_week_total) * 100
    else:
        change_rate = 0
    
    report_data = {
        "period_start": start_of_week.strftime("%Y-%m-%d"),
        "period_end": (end_of_week - timedelta(days=1)).strftime("%Y-%m-%d"),
        "total_amount": this_week_total,
        "transaction_count": this_week_data.count or 0,
        "change_rate": round(change_rate, 1),
        "top_categories": [
            {"name": cat.name, "amount": float(cat.amount), "count": int(cat.count)}
            for cat in categories
        ]
    }

    # AI Insight 생성
    try:
        prompt = generate_report_prompt("주간 소비", report_data)
        ai_insight = await call_gemini_api(prompt)
        report_data["ai_insight"] = ai_insight
        logger.info(f"Generated AI Insight (Weekly): {ai_insight}")
    except Exception as e:
        logger.error(f"Failed to generate AI insight: {e}")
        report_data["ai_insight"] = "AI 분석을 불러올 수 없습니다."

    return report_data


async def generate_monthly_report(db: AsyncSession) -> Dict[str, Any]:
    """
    월간 리포트 데이터를 생성합니다.
    
    Args:
        db: 데이터베이스 세션
    
    Returns:
        dict: 리포트 데이터
    """
    # 이번 달 (1일 ~ 말일)
    today = datetime.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 다음 달 1일
    if today.month == 12:
        end_of_month = start_of_month.replace(year=today.year + 1, month=1)
    else:
        end_of_month = start_of_month.replace(month=today.month + 1)
    
    # 지난 달
    if start_of_month.month == 1:
        last_month_start = start_of_month.replace(year=today.year - 1, month=12)
    else:
        last_month_start = start_of_month.replace(month=today.month - 1)
    last_month_end = start_of_month
    
    # 이번 달 거래 데이터
    this_month_query = select(
        func.count(Transaction.id).label("count"),
        func.sum(Transaction.amount).label("total_amount")
    ).where(
        and_(
            Transaction.transaction_time >= start_of_month,
            Transaction.transaction_time < end_of_month,
            Transaction.status == "completed"
        )
    )
    this_month_result = await db.execute(this_month_query)
    this_month_data = this_month_result.first()
    
    # 지난 달 거래 데이터
    last_month_query = select(
        func.sum(Transaction.amount).label("total_amount")
    ).where(
        and_(
            Transaction.transaction_time >= last_month_start,
            Transaction.transaction_time < last_month_end,
            Transaction.status == "completed"
        )
    )
    last_month_result = await db.execute(last_month_query)
    last_month_data = last_month_result.first()
    
    # 카테고리별 집계
    category_query = select(
        Category.name,
        func.sum(Transaction.amount).label("amount"),
        func.count(Transaction.id).label("count")
    ).join(
        Transaction, Transaction.category_id == Category.id
    ).where(
        and_(
            Transaction.transaction_time >= start_of_month,
            Transaction.transaction_time < end_of_month,
            Transaction.status == "completed"
        )
    ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).limit(5)
    
    category_result = await db.execute(category_query)
    categories = category_result.all()
    
    # 전월 대비 증감율 계산
    this_month_total = float(this_month_data.total_amount or 0)
    last_month_total = float(last_month_data.total_amount or 0)
    
    if last_month_total > 0:
        change_rate = ((this_month_total - last_month_total) / last_month_total) * 100
    else:
        change_rate = 0
    
    report_data = {
        "period_start": start_of_month.strftime("%Y-%m-%d"),
        "period_end": (end_of_month - timedelta(days=1)).strftime("%Y-%m-%d"),
        "total_amount": this_month_total,
        "transaction_count": this_month_data.count or 0,
        "change_rate": round(change_rate, 1),
        "top_categories": [
            {"name": cat.name, "amount": float(cat.amount), "count": int(cat.count)}
            for cat in categories
        ]
    }

    # AI Insight 생성
    try:
        prompt = generate_report_prompt("월간 소비", report_data)
        ai_insight = await call_gemini_api(prompt)
        report_data["ai_insight"] = ai_insight
        logger.info(f"Generated AI Insight (Monthly): {ai_insight}")
    except Exception as e:
        logger.error(f"Failed to generate AI insight: {e}")
        report_data["ai_insight"] = "AI 분석을 불러올 수 없습니다."

    return report_data


def format_report_html(report_data: Dict[str, Any]) -> str:
    """
    리포트 데이터를 HTML 형식으로 변환합니다.
    """
    # 증감율에 따른 색상 및 아이콘
    change_rate = report_data["change_rate"]
    if change_rate > 0:
        change_color = "#dc3545"  # 빨강 (증가)
        change_icon = "↑"
    elif change_rate < 0:
        change_color = "#28a745"  # 초록 (감소)
        change_icon = "↓"
    else:
        change_color = "#6c757d"  # 회색 (동일)
        change_icon = "="
    
    # 총 소비
    total_amount_formatted = f"₩{report_data['total_amount']:,.0f}"
    
    # 거래 건수
    transaction_count = f"{report_data['transaction_count']}건"
    
    # 전기 대비
    change_text = f"{change_icon} {abs(change_rate):.1f}%"
    
    # 상위 카테고리 HTML 생성 (거래 건수 포함)
    categories_html = ""
    for cat in report_data["top_categories"][:3]:
        categories_html += f"""
        <tr>
            <td style="padding: 6px 8px; border-bottom: 1px solid #f1f3f5; font-size: 14px;">
                {cat['name']} <span style="font-size: 12px; color: #868e96; margin-left: 4px;">({cat['count']}건)</span>
            </td>
            <td style="text-align: right; padding: 6px 8px; border-bottom: 1px solid #f1f3f5; font-size: 14px;">₩{cat['amount']:,.0f}</td>
        </tr>
        """
    
    # NEW: AI Insight Section (줄바꿈 처리)
    ai_insight_html = ""
    if "ai_insight" in report_data and report_data["ai_insight"]:
        # 줄바꿈을 <br>로 변환하고, **굵게**를 <b>굵게</b><br>로 변환 (타이틀 후 줄바꿈)
        formatted_insight = report_data['ai_insight'].replace("\n", "<br>")
        formatted_insight = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b><br>', formatted_insight)
        ai_insight_html = f"""
        <div style="margin-top: 24px; padding: 16px; background-color: #f8f9fa; border-left: 4px solid #6610f2; border-radius: 4px;">
            <p style="margin: 0 0 12px 0; font-weight: bold; color: #6610f2; font-size: 0.95em;">AI 소비 분석</p>
            <p style="margin: 0; color: #495057; font-size: 0.95em; line-height: 1.6;">{formatted_insight}</p>
        </div>
        """

    # HTML Table Construction (여백 축소)
    html = f"""
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
        <tr>
            <th style="text-align: left; padding: 6px 8px; border-bottom: 2px solid #dee2e6; color: #495057; font-size: 14px;">항목</th>
            <th style="text-align: right; padding: 6px 8px; border-bottom: 2px solid #dee2e6; color: #495057; font-size: 14px;">값</th>
        </tr>
        <tr>
            <td style="padding: 6px 8px; border-bottom: 1px solid #f1f3f5; font-size: 14px;">총 소비</td>
            <td style="text-align: right; padding: 6px 8px; border-bottom: 1px solid #f1f3f5; font-weight: bold; font-size: 14px;">{total_amount_formatted}</td>
        </tr>
        <tr>
            <td style="padding: 6px 8px; border-bottom: 1px solid #f1f3f5; font-size: 14px;">거래 건수</td>
            <td style="text-align: right; padding: 6px 8px; border-bottom: 1px solid #f1f3f5; font-size: 14px;">{transaction_count}</td>
        </tr>
        <tr>
            <td style="padding: 6px 8px; border-bottom: 1px solid #f1f3f5; font-size: 14px;">전기 대비</td>
            <td style="text-align: right; padding: 6px 8px; border-bottom: 1px solid #f1f3f5; font-size: 14px; color: {change_color};">{change_text}</td>
        </tr>
    </table>

    <h3 style="margin: 24px 0 12px 0; font-size: 15px; color: #495057; border-bottom: 1px solid #dee2e6; padding-bottom: 8px;">상위 지출 카테고리</h3>
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 0;">
        {categories_html}
    </table>

    {ai_insight_html}
    """
    
    return html
