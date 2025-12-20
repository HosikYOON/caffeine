"""
PaySim 타입 매퍼: 가계부 원본 거래를 PaySim의 type 스키마로 매핑합니다.

우선순위
- 환불/충전/입금/캐시백(양수) -> CASH_IN
- 이체/송금/자동이체 -> TRANSFER
- ATM/현금/출금 -> CASH_OUT
- 상점명 존재 + 지출(음수) -> PAYMENT
- 양수 기본 -> CASH_IN, 음수 기본 -> PAYMENT
- 매칭 실패 -> UNKNOWN
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

import pandas as pd

PAYMENT_KEYWORDS = ["카드", "승인", "결제", "매출전표", "pos", "가맹점"]
TRANSFER_KEYWORDS = ["이체", "송금", "자동이체", "펀드이체", "계좌이체"]
CASH_OUT_KEYWORDS = ["atm", "현금", "출금", "인출"]
CASH_IN_KEYWORDS = ["입금", "충전", "환불", "리턴", "cashback", "캐시백", "리펀드"]


def _contains(text: str, keywords: Iterable[str]) -> bool:
    text_l = text.lower()
    return any(k.lower() in text_l for k in keywords)


def map_type_row(
    amount: float,
    description: str = "",
    memo: str = "",
    is_expense: Optional[bool] = None,
) -> str:
    """단일 거래를 PaySim type으로 매핑"""
    text = f"{description} {memo}".strip()
    sign = "pos" if amount >= 0 else "neg"

    # 1) 환불/입금 계열
    if sign == "pos" and _contains(text, CASH_IN_KEYWORDS):
        return "CASH_IN"

    # 2) 이체/송금
    if _contains(text, TRANSFER_KEYWORDS):
        return "TRANSFER"

    # 3) ATM/현금 출금
    if _contains(text, CASH_OUT_KEYWORDS):
        return "CASH_OUT" if sign == "neg" else "CASH_IN"

    # 4) 상점명 + 지출
    if is_expense is True or sign == "neg":
        if _contains(text, PAYMENT_KEYWORDS) or bool(re.search(r"[가-힣A-Za-z]", text)):
            return "PAYMENT"

    # 5) 기본 부호 규칙
    if sign == "pos":
        return "CASH_IN"
    if sign == "neg":
        return "PAYMENT"

    return "UNKNOWN"


def map_ledger_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    가계부 DataFrame에 PaySim type 열을 추가합니다.
    기대 컬럼: 금액(Amount), 내용/상점명(description), 메모(memo), 타입(수입/지출 여부)
    """
    df = df.copy()
    # 컬럼명 스펙에 맞춰 유연하게 선택
    amount_col = next((c for c in df.columns if c.lower() in ["amount", "금액"]), None)
    desc_col = next((c for c in df.columns if c.lower() in ["내용", "description", "merchant", "상점명"]), None)
    memo_col = next((c for c in df.columns if c.lower() in ["메모", "memo", "비고"]), None)
    type_col = next((c for c in df.columns if c.lower() in ["타입", "type"]), None)

    def is_expense(row) -> Optional[bool]:
        if type_col:
            t = str(row[type_col]).lower()
            if "지출" in t or "expense" in t:
                return True
            if "수입" in t or "income" in t:
                return False
        return None

    df["PaySimType"] = df.apply(
        lambda r: map_type_row(
            amount=float(r.get(amount_col, 0) or 0),
            description=str(r.get(desc_col, "") or ""),
            memo=str(r.get(memo_col, "") or ""),
            is_expense=is_expense(r),
        ),
        axis=1,
    )
    return df

