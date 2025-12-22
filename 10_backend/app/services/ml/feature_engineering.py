import pandas as pd
import numpy as np
from datetime import datetime

CATEGORY_MAP = {
    '교통': 0, '생활': 1, '쇼핑': 2, '식료품': 3, '외식': 4, '주유': 5,
    '식비': 4, '카페': 4, '간식': 3, '마트': 3, '편의점': 3, '카페/간식': 4
}

def create_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """시간 관련 파생변수 생성 (Hour, DayOfWeek, IsWeekend 등)"""
    df = df.copy()
    df['Hour'] = df['CreateDate'].dt.hour
    df['DayOfWeek'] = df['CreateDate'].dt.dayofweek
    df['DayOfMonth'] = df['CreateDate'].dt.day
    df['IsWeekend'] = df['DayOfWeek'].apply(lambda x: 1 if x >= 5 else 0)
    df['IsLunchTime'] = df['Hour'].apply(lambda x: 1 if 11 <= x <= 13 else 0)
    df['IsEvening'] = df['Hour'].apply(lambda x: 1 if 18 <= x <= 20 else 0)
    df['IsMorningRush'] = df['Hour'].apply(lambda x: 1 if 7 <= x <= 9 else 0)
    df['IsNight'] = df['Hour'].apply(lambda x: 1 if x >= 22 or x <= 4 else 0)
    df['IsBusinessHour'] = df.apply(lambda row: 1 if (9 <= row['Hour'] <= 17) and (row['IsWeekend'] == 0) else 0, axis=1)
    return df

def create_amount_features(df: pd.DataFrame) -> pd.DataFrame:
    """금액 관련 파생변수 생성 (Log 변환, Binning 등)"""
    df = df.copy()
    df['Amount_log'] = np.log1p(df['Amount'].abs())
    df['AmountBin_encoded'] = (df['Amount'].abs() // 5000).clip(upper=20)
    df['Amount_clean'] = df['Amount']
    df['AmountBin'] = df['AmountBin_encoded']
    return df

def calculate_user_stats(df: pd.DataFrame) -> dict:
    """사용자 통합 통계 계산"""
    total_count = len(df)
    if total_count == 0:
        return {"avg_amount": 0, "std_amount": 0, "fav_category": 4, "category_ratios": {}}
    
    df['cat_encoded'] = df['대분류'].map(CATEGORY_MAP).fillna(6)
    cat_counts = df['cat_encoded'].value_counts()
    
    return {
        "avg_amount": df['Amount'].mean(),
        "std_amount": df['Amount'].std() if total_count > 1 else 0,
        "tx_count": total_count,
        "fav_category": df['cat_encoded'].mode()[0] if not df['cat_encoded'].mode().empty else 4,
        "category_count": df['cat_encoded'].nunique(),
        "category_ratios": {k: cat_counts.get(v, 0) / total_count for k, v in CATEGORY_MAP.items() if v < 6}
    }
