import pandas as pd
import numpy as np

def clean_transaction_data(df: pd.DataFrame) -> pd.DataFrame:
    """거래 데이터 정제 (날짜 변환, 금액 파싱, 정렬)"""
    df = df.copy()
    
    # 날짜 처리 (날짜 + 시간 병합)
    if '날짜' in df.columns and '시간' in df.columns:
        df['CreateDate'] = pd.to_datetime(df['날짜'] + ' ' + df['시간'], errors='coerce')
    elif 'transaction_time' in df.columns:
        df['CreateDate'] = pd.to_datetime(df['transaction_time'])
    
    # 금액 처리 (문자열 -> 숫자)
    if '금액' in df.columns:
        if df['금액'].dtype == object:
            df['Amount'] = pd.to_numeric(df['금액'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        else:
            df['Amount'] = df['금액'].fillna(0)
    elif 'amount' in df.columns:
        df['Amount'] = df['amount']
        
    df = df.sort_values('CreateDate').reset_index(drop=True)
    return df

def apply_scaling(df: pd.DataFrame, feature_names: list, feature_stats: dict) -> pd.DataFrame:
    """Z-Score Scaling (StandardScaler) 적용"""
    result_df = df.copy()
    for feature_name in feature_names:
        original_col = feature_name.replace('_scaled', '')
        if feature_name == 'AmountBin_encoded_scaled': original_col = 'AmountBin_encoded'
        
        if original_col in result_df.columns:
            stats = feature_stats[feature_name]
            mean, std = stats['mean'], stats['std']
            if std == 0: std = 1
            result_df[feature_name] = (result_df[original_col] - mean) / std
        else:
            result_df[feature_name] = 0
    return result_df
