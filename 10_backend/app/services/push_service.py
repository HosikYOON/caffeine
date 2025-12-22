"""
Expo Push Notification 서비스

Expo Push API를 사용하여 모바일 앱에 푸시 알림을 전송하는 서비스입니다.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_push_notification(
    push_token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    sound: str = "default",
    priority: str = "high"
) -> Dict[str, Any]:
    """
    단일 사용자에게 Expo 푸시 알림을 전송합니다.
    
    Args:
        push_token: Expo Push Token (ExponentPushToken[xxx] 형식)
        title: 알림 제목
        body: 알림 내용
        data: 추가 데이터 (앱에서 처리 가능)
        sound: 알림 소리 ("default" 또는 null)
        priority: 알림 우선순위 ("high", "normal", "low")
    
    Returns:
        Expo Push API 응답
    """
    if not push_token:
        logger.warning("Push token이 없어 알림을 전송할 수 없습니다.")
        return {"success": False, "error": "No push token"}
    
    # Expo Push Token 형식 검증
    if not push_token.startswith("ExponentPushToken"):
        logger.warning(f"유효하지 않은 Push Token 형식: {push_token[:20]}...")
        return {"success": False, "error": "Invalid push token format"}
    
    message = {
        "to": push_token,
        "title": title,
        "body": body,
        "sound": sound,
        "priority": priority,
        "channelId": "anomaly",  # Android 알림 채널
    }
    
    if data:
        message["data"] = data
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                EXPO_PUSH_URL,
                json=message,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate",
                },
                timeout=10.0
            )
            
            result = response.json()
            
            if response.status_code == 200:
                logger.info(f"푸시 알림 전송 성공: {push_token[:30]}...")
                return {"success": True, "result": result}
            else:
                logger.error(f"푸시 알림 전송 실패: {result}")
                return {"success": False, "error": result}
                
    except httpx.TimeoutException:
        logger.error("푸시 알림 전송 타임아웃")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        logger.error(f"푸시 알림 전송 오류: {str(e)}")
        return {"success": False, "error": str(e)}


async def send_anomaly_alert(
    push_token: str,
    transaction_id: int,
    amount: float,
    category: str,
    reason: str
) -> Dict[str, Any]:
    """
    이상 거래 알림을 전송합니다.
    
    Args:
        push_token: 사용자의 Expo Push Token
        transaction_id: 거래 ID
        amount: 거래 금액
        category: 거래 카테고리
        reason: 의심 사유
    
    Returns:
        전송 결과
    """
    title = "⚠️ 이상 거래 감지"
    body = f"{category}에서 ₩{amount:,.0f} 거래가 의심됩니다.\n• {reason}"
    
    data = {
        "type": "anomaly",
        "transactionId": transaction_id,
        "amount": amount,
        "category": category,
        "reason": reason,
    }
    
    return await send_push_notification(
        push_token=push_token,
        title=title,
        body=body,
        data=data,
        priority="high"
    )


async def send_bulk_push_notifications(
    messages: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    여러 사용자에게 동시에 푸시 알림을 전송합니다.
    
    Args:
        messages: 메시지 목록 (각 메시지는 to, title, body 필드 포함)
    
    Returns:
        전송 결과
    """
    if not messages:
        return {"success": True, "sent": 0}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30.0
            )
            
            result = response.json()
            return {"success": True, "result": result, "sent": len(messages)}
            
    except Exception as e:
        logger.error(f"대량 푸시 알림 전송 오류: {str(e)}")
        return {"success": False, "error": str(e), "sent": 0}
