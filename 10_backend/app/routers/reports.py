"""
리포트 수동 발송 API 라우터

Settings 페이지에서 주간/월간 리포트를 즉시 발송할 수 있는 엔드포인트를 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import json
import tempfile
import os

from app.db.database import get_db
from app.db.model.user import User
from app.db.model.admin_settings import AdminSettings
from app.routers.user import get_current_user
from app.services.report_service import (
    generate_weekly_report,
    generate_monthly_report,
    format_report_html,
    generate_report_pdf
)
from app.services.email_service import send_report_email

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/reports",
    tags=["Admin Reports"]
)


async def get_report_recipient_email(db: AsyncSession) -> str | None:
    """
    데이터베이스에서 리포트 수신자 이메일을 가져옵니다.
    
    Returns:
        str | None: 수신자 이메일 주소 또는 None
    """
    result = await db.execute(
        select(AdminSettings).where(AdminSettings.key == "notification.recipient_email")
    )
    setting = result.scalar_one_or_none()
    
    if setting and setting.value:
        try:
            return json.loads(setting.value)
        except:
            return None
    return None


@router.post("/send-weekly")
async def send_weekly_report_now(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    주간 리포트를 즉시 생성하고 발송합니다.
    (PDF 대신 단일 HTML 슬라이드 덱으로 발송)
    
    **권한 필요**: 슈퍼유저
    
    Returns:
        dict: 발송 결과
    """
    # 슈퍼유저만 접근 가능
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    
    logger.info(f"Manual weekly report requested (User: {current_user.email})")
    
    try:
        # 수신자 이메일 확인
        recipient_email = await get_report_recipient_email(db)
        if not recipient_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="수신자 이메일이 설정되지 않았습니다. Settings에서 이메일을 설정해주세요."
            )
        
        # 리포트 데이터 생성
        report_data = await generate_weekly_report(db)
        
        # HTML 슬라이드 덱 포맷 생성
        from app.services.report_service import generate_report_html_slide
        
        html_content = generate_report_html_slide(report_data, title="Weekly Business Review")
        
        # HTML 파일 임시 저장
        period = f"{report_data['period_start']} ~ {report_data['period_end']}"
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode='w', encoding='utf-8') as tmp:
            tmp.write(html_content)
            html_path = tmp.name
        
        try:
            # 이메일 발송 (HTML 파일 첨부)
            success, message = await send_report_email(
                recipient_email=recipient_email,
                subject=f"[Caffeine] Weekly Report ({period})",
                report_type="Weekly",
                period=period,
                summary_html="<p>첨부된 <b>Weekly_Strategy_Deck.html</b> 파일을 <b>크롬 브라우저</b>에서 열어주세요.<br/>PC/모바일 어디서든 완벽한 프레젠테이션 뷰를 제공합니다.</p>",
                attachments=[html_path]
            )
        finally:
            if os.path.exists(html_path):
                os.remove(html_path)
        
        logger.info(f"Weekly HTML report processing completed: {message}")
        
        return {
            "success": success,
            "message": message,
            "period": period,
            "recipient": recipient_email,
            "has_attachment": True,
            "file_type": "html"
        }
        
    except ValueError as e:
        # SMTP 설정 누락 등 구성 오류
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Weekly report failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send report: {str(e)}"
        )


@router.post("/send-monthly")
async def send_monthly_report_now(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    월간 리포트를 즉시 생성하고 발송합니다.
    (PDF 대신 단일 HTML 슬라이드 덱으로 발송)
    
    **권한 필요**: 슈퍼유저
    
    Returns:
        dict: 발송 결과
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    
    logger.info(f"Manual monthly report requested (User: {current_user.email})")
    
    try:
        # 수신자 이메일 확인
        recipient_email = await get_report_recipient_email(db)
        if not recipient_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="수신자 이메일이 설정되지 않았습니다. Settings에서 이메일을 설정해주세요."
            )
        
        # 리포트 데이터 생성
        report_data = await generate_monthly_report(db)
        
        # HTML 슬라이드 덱 포맷 생성 (generate_report_html_slide 내부에서 스트링 리턴)
        # report_service.py에 generate_report_html_slide 함수 추가 필요
        from app.services.report_service import generate_report_html_slide
        
        html_content = generate_report_html_slide(report_data)
        
        # HTML 파일 임시 저장
        # 이메일 전송을 위해 파일로 저장
        period = f"{report_data['period_start']} ~ {report_data['period_end']}"
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode='w', encoding='utf-8') as tmp:
            tmp.write(html_content)
            html_path = tmp.name
            
        try:
            # 이메일 발송 (HTML 파일 첨부)
            success, message = await send_report_email(
                recipient_email=recipient_email,
                subject=f"[Vertex AI] Monthly Strategic Report ({period})",
                report_type="Monthly",
                period=period,
                summary_html="<p>첨부된 <b>Strategy_Deck.html</b> 파일을 <b>크롬 브라우저</b>에서 열어주세요.<br/>PC/모바일 어디서든 완벽한 프레젠테이션 뷰를 제공합니다.</p>",
                attachments=[html_path]
            )
        finally:
            if os.path.exists(html_path):
                os.remove(html_path)
        
        logger.info(f"Monthly HTML report processing completed: {message}")
        
        return {
            "success": success,
            "message": message,
            "period": period,
            "recipient": recipient_email,
            "has_attachment": True,
            "file_type": "html"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Monthly report failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed: {str(e)}")
