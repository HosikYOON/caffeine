"""
PaySim 스타일 피처 생성 유틸

파이프라인:
1) map_ledger_df로 PaySimType을 부여 (가계부 -> PaySim 스키마)
2) add_time_amount_features로 시간/금액 파생치 계산
3) add_type_change_features로 type_change_rate* 계산
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import List
from datetime import datetime

from app.services.paysim_mapper import map_ledger_df


def _parse_datetime(row: pd.Series) -> datetime:
    # 우선순위: transaction_time 컬럼 -> (날짜, 시간) 문자열 -> now()
    if "transaction_time" in row and pd.notna(row["transaction_time"]):
        try:
            return pd.to_datetime(row["transaction_time"])
        except Exception:
            pass
    date_col = next((c for c in ["날짜", "date"] if c in row and pd.notna(row[c])), None)
    time_col = next((c for c in ["시간", "time"] if c in row and pd.notna(row[c])), None)
    if date_col:
        try:
            dt_str = str(row[date_col])
            if time_col:
                dt_str = f"{dt_str} {row[time_col]}"
            return pd.to_datetime(dt_str)
        except Exception:
            pass
    return datetime.now()


def add_time_amount_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["dt"] = df.apply(_parse_datetime, axis=1)
    df = df.sort_values("dt").reset_index(drop=True)

    df["Hour"] = df["dt"].dt.hour.astype(float)
    df["DayOfWeek"] = df["dt"].dt.weekday.astype(float)
    df["IsWeekend"] = (df["DayOfWeek"] >= 5).astype(float)
    df["IsNight"] = ((df["Hour"] < 6) | (df["Hour"] >= 23)).astype(float)

    amount_col = next((c for c in df.columns if c.lower() in ["amount", "금액"]), None)
    if amount_col is None:
        df["Amount"] = 0.0
    else:
        df["Amount"] = df[amount_col].astype(float).abs()

    df["AmountLog"] = np.log1p(df["Amount"].abs())

    # 롤링 Z-score (로그 금액 기준)
    for window in [3, 5, 10]:
        roll = df["AmountLog"].rolling(window, min_periods=1)
        mean = roll.mean()
        std = roll.std().replace(0, np.nan)
        df[f"amount_log_z{window}"] = (df["AmountLog"] - mean) / std
        df[f"amount_log_z{window}"] = df[f"amount_log_z{window}"].fillna(0.0)

    # IQR Z
    q1 = df["AmountLog"].rolling(10, min_periods=1).quantile(0.25)
    q3 = df["AmountLog"].rolling(10, min_periods=1).quantile(0.75)
    iqr = (q3 - q1).replace(0, np.nan)
    df["amount_log_iqr_z"] = (df["AmountLog"] - q3) / iqr
    df["amount_log_iqr_z"] = df["amount_log_iqr_z"].fillna(0.0)

    # 금액 bin / rank_pct
    bins = [0, 1e3, 1e4, 5e4, 1e5, 5e5, 1e6, np.inf]
    df["amount_bin"] = pd.cut(df["Amount"].abs(), bins=bins, labels=False, include_lowest=True).fillna(0).astype(int)
    df["amount_rank_pct"] = df["Amount"].rank(pct=True).fillna(0.0)

    return df


def add_type_change_features(df: pd.DataFrame, type_col: str = "PaySimType") -> pd.DataFrame:
    df = df.copy()
    if type_col not in df:
        df[type_col] = "UNKNOWN"

    df["type_num"] = df[type_col].astype("category").cat.codes
    df["type_changed"] = (df["type_num"].diff().fillna(0) != 0).astype(int)

    for window in [2, 3, 5, 10]:
        roll = df["type_changed"].rolling(window, min_periods=1)
        df[f"type_change_rate{window}"] = (roll.sum() / window).fillna(0.0)

    df.drop(columns=["type_num", "type_changed"], inplace=True)
    return df


def preprocess_ledger_to_paysim(df: pd.DataFrame) -> pd.DataFrame:
    """
    가계부 DataFrame -> PaySim 피처 세트
    - PaySimType 매핑
    - 시간/금액 파생
    - type_change_rate* 추가
    """
    df_mapped = map_ledger_df(df)
    df_feats = add_time_amount_features(df_mapped)
    df_feats = add_type_change_features(df_feats, type_col="PaySimType")
    return df_feats


def build_model_inputs(df: pd.DataFrame) -> pd.DataFrame:
    """
    모델 입력 스키마(ml_fraud가 요구하는 18개 피처)로 변환
    New Model: paysim_generic_no_flag_featplus
    Features: ['step', 'day', 'hour', 'dow', 'hour_sin', 'hour_cos', 'amount_log', 
               'amount_log_z3', 'amount_log_z5', 'amount_log_z10', 'amount_log_iqr_z', 
               'amount_bin', 'amount_rank_pct', 'type_change_rate2', 'type_change_rate3', 
               'type_change_rate5', 'type_change_rate10', 'type']
    """
    # 1. Preprocess basic stats
    df_feat = preprocess_ledger_to_paysim(df)
    df_feat = df_feat.sort_values("dt").reset_index(drop=True)

    # 2. Add missing features for specific model requirements
    df_feat["step"] = df_feat.index + 1  # Logic from PaySim (1 step = 1 hour usually, but index is fine proxy)
    df_feat["day"] = df_feat["dt"].dt.day
    df_feat["dow"] = df_feat["dt"].dt.weekday
    
    # Cyclic hour encoding
    df_feat["hour_sin"] = np.sin(2 * np.pi * df_feat["Hour"] / 24.0)
    df_feat["hour_cos"] = np.cos(2 * np.pi * df_feat["Hour"] / 24.0)
    
    # Lowercase names to match model expectations
    df_feat["amount_log"] = df_feat["AmountLog"]
    df_feat["type"] = df_feat["PaySimType"]

    # Ensure all columns exist (fill derived ones if missing from preprocess)
    # type_change_rate* are already created in preprocess_ledger_to_paysim (2,3,5,10)
    
    # Rename columns to match model exactly
    cols_order = [
       'step', 'day', 'Hour', 'dow', 'hour_sin', 'hour_cos', 
       'amount_log', 'amount_log_z3', 'amount_log_z5', 'amount_log_z10', 'amount_log_iqr_z', 
       'amount_bin', 'amount_rank_pct', 
       'type_change_rate2', 'type_change_rate3', 'type_change_rate5', 'type_change_rate10', 
       'type'
    ]
    
    # Note: 'Hour' in dataframe is 'Hour' logic but model wants 'hour'? Metadata said 'hour', let's check.
    # Metadata: "groups": {"time": ["step", "day", "hour", "dow", "hour_sin", "hour_cos"]}
    # My inspect script said: ['step' 'day' 'hour' 'dow' 'hour_sin' 'hour_cos' ... ]
    # So I should map 'Hour' -> 'hour'
    
    df_feat["hour"] = df_feat["Hour"]
    
    df_feat["hour"] = df_feat["Hour"]
    
    # [HEURISTIC SUPPORT]
    # We need TimeDiffMean5 for burst detection heuristic.
    # Logic copied/adapted from old version:
    if "PrevTimeDiffHours" not in df_feat.columns:
         df_feat["PrevTimeDiffHours"] = df_feat["dt"].diff().dt.total_seconds().div(3600).fillna(0.0)
    df_feat["TimeDiffMean5"] = df_feat["PrevTimeDiffHours"].rolling(5, min_periods=1).mean().fillna(0.0)

    # Return ALL columns (including 'Amount', 'TimeDiffMean5', '내용', '메모') 
    # so caller can use them for heuristics. Caller must select specific columns for ML model.
    return df_feat
