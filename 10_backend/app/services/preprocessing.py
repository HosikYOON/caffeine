import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple

from app.services.ml import data_cleaner, feature_engineering

class DataPreprocessor:
    def __init__(self, metadata_path: str = None):
        if metadata_path is None:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            metadata_path = os.path.join(app_dir, "model_metadata.json")
            if not os.path.exists(metadata_path):
                raise FileNotFoundError(f"메타데이터 없음: {metadata_path}")
        
        self.metadata_path = metadata_path
        self._load_metadata()
        
    def _load_metadata(self):
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
        
        if 'features' in self.metadata:
            self.feature_names = self.metadata['features']
            self.feature_stats = None
        elif 'input_spec' in self.metadata:
            self.feature_stats = self.metadata['input_spec']['feature_statistics']
            self.feature_names = self.metadata['input_spec']['feature_names']
        else:
            raise ValueError("Invalid metadata format")
        
    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        df_clean = data_cleaner.clean_transaction_data(df)
        df_eng = feature_engineering.create_time_features(df_clean)
        df_eng = feature_engineering.create_amount_features(df_eng)
        
        # 추가적인 시퀀스/유저 통계 로직 (feature_engineering에 위임 가능)
        df_eng['User_AvgAmount'] = df_eng['Amount'].mean()
        df_eng['User_StdAmount'] = df_eng['Amount'].std().fillna(0)
        df_eng['User_TxCount'] = len(df_eng)
        df_eng['Time_Since_Last'] = df_eng['CreateDate'].diff().dt.total_seconds().fillna(0) / 60
        df_eng['Transaction_Sequence'] = np.arange(len(df_eng)) / len(df_eng)
        # ... 카테고리 관련 등
        
        if self.feature_stats:
            df_final = data_cleaner.apply_scaling(df_eng, self.feature_names, self.feature_stats)
        else:
            df_final = df_eng
            
        return df_final[[f for f in self.feature_names if f in df_final.columns]]

    def preprocess_for_next_prediction(self, df: pd.DataFrame, prediction_time: datetime = None) -> pd.DataFrame:
        """다음 거래 예측 전용 전처리 (컨텍스트 기반)"""
        if prediction_time is None: prediction_time = datetime.now()
        df_clean = data_cleaner.clean_transaction_data(df)
        user_stats = feature_engineering.calculate_user_stats(df_clean)
        
        if len(df_clean) == 0: raise ValueError("No transaction history")
        last_tx = df_clean.iloc[-1]
        
        # 가상의 다음 거래 피처 구성
        features = {
            'Hour': prediction_time.hour,
            'DayOfWeek': prediction_time.weekday(),
            'DayOfMonth': prediction_time.day,
            'IsWeekend': 1 if prediction_time.weekday() >= 5 else 0,
            'IsLunchTime': 1 if 11 <= prediction_time.hour <= 13 else 0,
            'IsEvening': 1 if 18 <= prediction_time.hour <= 20 else 0,
            'IsMorningRush': 1 if 7 <= prediction_time.hour <= 9 else 0,
            'IsNight': 1 if prediction_time.hour >= 22 or prediction_time.hour <= 4 else 0,
            'IsBusinessHour': 1 if (9 <= prediction_time.hour <= 17) and prediction_time.weekday() < 5 else 0,
            'Amount': user_stats['avg_amount'],
            'Amount_log': np.log1p(abs(user_stats['avg_amount'])),
            'AmountBin_encoded': (abs(user_stats['avg_amount']) // 5000),
            'User_AvgAmount': user_stats['avg_amount'],
            'User_StdAmount': user_stats['std_amount'],
            'User_TxCount': len(df_clean),
            'Time_Since_Last': (prediction_time - last_tx['CreateDate']).total_seconds() / 60,
            'Transaction_Sequence': 1.0,
            'Previous_Category_encoded': last_tx.get('cat_encoded', 4),
            'Current_Category_encoded': user_stats['fav_category'],
            'User_FavCategory_encoded': user_stats['fav_category'],
            'User_Category_Count': user_stats['category_count'],
            'Amount_clean': user_stats['avg_amount'],
            'AmountBin': (abs(user_stats['avg_amount']) // 5000),
            'Previous_Category': last_tx.get('cat_encoded', 4)
        }
        
        # 비율 피처 추가
        for cat_name, ratio in user_stats.get('category_ratios', {}).items():
            features[f'User_{cat_name}_Ratio'] = ratio
            
        next_df = pd.DataFrame([features])
        if self.feature_stats:
            next_df = data_cleaner.apply_scaling(next_df, self.feature_names, self.feature_stats)
            
        return next_df[[f for f in self.feature_names if f in next_df.columns]]

_instance = None
def get_preprocessor():
    global _instance
    if _instance is None:
        _instance = DataPreprocessor()
    return _instance
