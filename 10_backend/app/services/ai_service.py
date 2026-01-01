
import os
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def call_gemini_api(prompt: str) -> str:
    """
    Google Gemini API를 호출하여 텍스트 응답을 생성합니다.
    (chatbot.py의 로직을 기반으로 재작성)
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is missing")
        return "AI 분석을 사용할 수 없습니다 (API Key 누락)."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url, 
                json=payload, 
                headers={"Content-Type": "application/json"}, 
                timeout=15.0
            )
            
            if response.status_code != 200:
                logger.error(f"Gemini API Error: {response.status_code} - {response.text}")
                return "AI 분석을 가져오는 중 오류가 발생했습니다."
                
            data = response.json()
            # 안전하게 응답 추출
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                logger.error(f"Gemini Response parsing error: {e}")
                return "AI 응답을 처리할 수 없습니다."
                
        except httpx.RequestError as e:
            logger.error(f"Gemini API Request Error: {e}")
            return "AI 서비스 연결 실패."

def generate_report_prompt(report_type: str, data: Dict[str, Any]) -> str:
    """
    CEO/C-Level 대상의 프리미엄 전략 보고서 생성을 위한 AI 프롬프트.
    HTML 슬라이드 자동 생성을 위해 엄격한 마크다운 구조를 사용합니다.
    """
    categories_text = "\n".join([
        f"- {cat['name']}: {int(cat['amount']):,}원 ({cat['percent']:.1f}%)" 
        for cat in data.get("top_categories", [])
    ])

    max_tx_text = "N/A"
    if data.get('max_transaction'):
        max_tx = data['max_transaction']
        max_tx_text = f"{max_tx['merchant_name']} ({int(max_tx['amount']):,}원) - {max_tx['category']} 분야"

    return f"""
Role: Senior Strategic Consultant & BI Developer
Context: 'Caffeine' Project (Vertex AI-based Financial Command Center)

당신은 데이터의 비즈니스 가치를 극대화하는 **전략 컨설턴트**입니다.
제공된 [Raw 데이터]를 분석하여 아래 **4가지 핵심 섹션**에 대한 내용을 작성하십시오.
각 섹션은 HTML 슬라이드로 변환되므로 **지정된 헤더(##)**를 정확히 지켜야 합니다.

[분석 데이터 (Fact)]
- 기간: {data['period_start']} ~ {data['period_end']}
- 총 지출: {int(data['total_amount']):,}원 (전기 대비 {data['change_rate']}%)
- 상위 카테고리:
{categories_text}
- 최대 지출 트랜잭션: {max_tx_text}

[작성 섹션 및 가이드]

## 1. Executive Summary
- 단순 현황 보고가 아닌, **리스크와 기회 요인**을 짚어주는 경영진 요약.
- 줄글 금지. **핵심 3가지를 불렛 포인트(-)**로 요약할 것.

## 2. B2C Consumer Insight
- 유저 데이터({categories_text})를 기반으로 '소비 맥락'과 '라이프스타일' 분석.
- **긴 문단 절대 금지**. 3~4개의 핵심 인사이트를 **불렛 포인트(-)**로 명확히 분리하여 작성.
- 예: "- (Insight 1) 교통비 비중 35% -> 모빌리티 중심의 라이프스타일..."

## 3. B2B Partnership Strategy
- 지출 비중이 높은 분야에서 실제 수익을 창출할 수 있는 **구체적 제휴 대상** 제안.
- 카카오T, 쿠팡, 배달의민족, 스타벅스 등 실존 기업명과 **제휴 아이템** 명시.
- 각 제안은 **불렛 포인트(-)**로 구분하여 가독성 확보.

## 4. Partnership Metrics
- 위 B2B 전략 실행 시 기대되는 KPI 변화를 반드시 **Markdown Table**로 작성.
| 타겟 기업 | 예상 수익 모델 | 기대 KPI (ROAS/Lock-in) |
|---|---|---|
| (기업명) | (모델명) | (수치) |

※ **Tone & Manner**: 객관적, 비판적, 수치 기반(Evidence-based).
※ **Format**: **모든 섹션은 가독성을 위해 불렛 포인트(-) 위주로 작성.** 한 문단이 3줄을 넘지 않도록 문장 길이를 조절하십시오.
"""
