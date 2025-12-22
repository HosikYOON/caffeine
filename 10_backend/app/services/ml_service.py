import joblib
import pandas as pd
import numpy as np
import os
import io
import logging
from datetime import datetime
from fastapi import HTTPException, UploadFile

from app.services.preprocessing import get_preprocessor

logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    0: '교통', 1: '생활', 2: '쇼핑', 3: '식료품', 4: '외식', 5: '주유'
}

class MLService:
    def __init__(self):
        self.model = None
        self.fraud_model = None
        self._load_model()
        self._load_fraud_model()

    def _load_model(self):
        try:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(app_dir, "model_xgboost_acc_73.47.joblib")
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
        except Exception as e:
            logger.error(f"Category Model Load Failed: {e}")

    def _load_fraud_model(self):
        try:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            paths = [
                os.path.join(app_dir, "models", "fraud_model.joblib"),
                os.path.join(app_dir, "models", "model.joblib"),
                os.path.join(app_dir, "fraud_model.joblib")
            ]
            for path in paths:
                if os.path.exists(path):
                    self.fraud_model = joblib.load(path)
                    print(f"DEBUG: Fraud Detection Model Loaded from {path}")
                    logger.info(f"Fraud Detection Model Loaded from: {path}")
                    break
            if self.fraud_model is None:
                print("DEBUG: No Fraud Model found in search paths")
        except Exception as e:
            logger.error(f"Fraud Model Load Failed: {e}")

    async def predict_single(self, features: dict):
        if self.model is None: self._load_model()
        if self.model is None: raise HTTPException(status_code=500, detail="Model unavailable")
        
        input_data = pd.DataFrame([features])
        if '날짜' not in input_data.columns: input_data['날짜'] = datetime.now().strftime('%Y-%m-%d')
        if '시간' not in input_data.columns: input_data['시간'] = datetime.now().strftime('%H:%M')
        
        processed = get_preprocessor().preprocess(input_data)
        prediction = self.model.predict(processed)[0]
        return {"prediction": CATEGORY_MAP.get(int(prediction), '기타')}

    async def detect_anomaly(self, transaction_data: dict) -> dict:
        """거래 데이터를 입력받아 이상 여부 탐지"""
        if self.fraud_model is None: self._load_fraud_model()
        
        if self.fraud_model is None:
            return {"is_anomaly": False, "score": 0.0, "reason": "Model unavailable", "source": "rule"}

        try:
            input_df = pd.DataFrame([transaction_data])
            processed = get_preprocessor().preprocess(input_df)
            
            prediction = self.fraud_model.predict(processed)[0]
            
            # 1 또는 -1이 이상징후 (모델에 따라 다름)
            is_anomaly = bool(prediction == 1 or prediction == -1)
            
            score = 0.0
            if hasattr(self.fraud_model, "predict_proba"):
                score = float(np.max(self.fraud_model.predict_proba(processed)[0]))
            
            if is_anomaly:
                logger.info(f"Anomaly detected by ML: Score={score}")
                print(f"DEBUG: Anomaly Detected! Score={score}")
                
            return {
                "is_anomaly": is_anomaly,
                "score": score,
                "reason": "AI 분석 결과 이상 징후 감지" if is_anomaly else "정상 거래",
                "source": "ml"
            }
        except Exception as e:
            logger.error(f"Anomaly Detection Error: {e}")
            return {"is_anomaly": False, "score": 0.0, "reason": f"Detection Error: {e}", "source": "error"}

    def calculate_confidence_metrics(self, probabilities: np.ndarray) -> dict:
        """예측 신뢰도 계산 (Entropy, Gap 등)"""
        top1_prob = np.max(probabilities)
        sorted_probs = np.sort(probabilities)[::-1]
        top2_gap = sorted_probs[0] - sorted_probs[1] if len(sorted_probs) > 1 else 1.0
        entropy = -np.sum(probabilities * np.log(probabilities + 1e-10))
        return {
            "top1_confidence": float(top1_prob),
            "top2_gap": float(top2_gap),
            "entropy": float(entropy),
            "confidence_level": "high" if top1_prob > 0.7 else "medium" if top1_prob > 0.4 else "low"
        }

    async def predict_csv(self, file: UploadFile):
        if self.model is None: self._load_model()
        content = await file.read()
        try:
            df_original = pd.read_csv(io.BytesIO(content), encoding='utf-8')
        except:
            df_original = pd.read_csv(io.BytesIO(content), encoding='cp949')
            
        preprocessor = get_preprocessor()
        df_processed = preprocessor.preprocess(df_original)
        
        if self.model is None: raise HTTPException(status_code=500, detail="Model unavailable")
        
        predictions = self.model.predict(df_processed)
        predicted_categories = [CATEGORY_MAP.get(int(pred), '기타') for pred in predictions]
        
        # 프론트엔드용 상세 포맷팅
        transactions_formatted = []
        for idx, row in df_original.iterrows():
            date_str = str(row.get('날짜', '')).strip()
            time_str = str(row.get('시간', '')).strip()
            transactions_formatted.append({
                "id": str(idx + 1),
                "merchant": str(row.get('내용', '알 수 없음')),
                "amount": abs(int(row.get('금액', 0))) if pd.notna(row.get('금액')) else 0,
                "category": predicted_categories[idx],
                "date": f"{date_str} {time_str}".strip(),
                "cardType": '체크' if '체크' in str(row.get('결제수단', '')) else '신용',
                "aiPredicted": True
            })
        
        return {
            "filename": file.filename,
            "total_rows": len(df_original),
            "transactions": transactions_formatted,
            "summary": {"by_category": pd.Series(predicted_categories).value_counts().to_dict(), "total": len(predictions)}
        }

    async def predict_next_category(self, file: UploadFile):
        """거래 이력 기반 다음 소비 카테고리 예측"""
        if self.model is None: self._load_model()
        content = await file.read()
        try:
            df = pd.read_csv(io.BytesIO(content), encoding='utf-8')
        except:
            df = pd.read_csv(io.BytesIO(content), encoding='cp949')
            
        if len(df) == 0: raise HTTPException(status_code=400, detail="Empty CSV")
        
        preprocessor = get_preprocessor()
        # preprocess_for_next_prediction (preprocessing.py에 구현되어 있어야 함)
        try:
            df_next = preprocessor.preprocess_for_next_prediction(df)
        except AttributeError:
            # 보강된 preprocessing.py를 사용하지 않는 경우의 폴백
            df_next = preprocessor.preprocess(df).tail(1)

        prob = self.model.predict_proba(df_next)
        pred = self.model.predict(df_next)
        
        conf = self.calculate_confidence_metrics(prob[0])
        
        return {
            "predicted_category": CATEGORY_MAP.get(int(pred[0]), '기타'),
            "predicted_category_code": int(pred[0]),
            "confidence": conf["top1_confidence"],
            "probabilities": {CATEGORY_MAP[i]: float(prob[0][i]) for i in range(len(prob[0]))},
            "confidence_metrics": conf
        }

ml_service = MLService()
def get_ml_service():
    return ml_service
