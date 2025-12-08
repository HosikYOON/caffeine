from fastapi import FastAPI
import os
from dotenv import load_dotenv
import joblib
import boto3
from io import BytesIO

load_dotenv()

app = FastAPI()  # 반드시 있어야 함

# 로깅 설정
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2")
S3_BUCKET = os.getenv("S3_BUCKET")
MODEL_KEY = os.getenv("MODEL_KEY")

# 모델 로드 함수
def load_model_from_s3():
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_DEFAULT_REGION
        )
        buffer = BytesIO()
        logger.info(f"Downloading model from s3://{S3_BUCKET}/{MODEL_KEY}")
        s3.download_fileobj(S3_BUCKET, MODEL_KEY, buffer)
        buffer.seek(0)
        model = joblib.load(buffer)
        logger.info("Model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        # 실제 운영 환경에서는 여기서 에러를 raise하거나 None을 반환하여 처리가 필요함
        # 여기서는 None을 반환하고 API 호출 시 체크하도록 함
        return None

# 실제 모델 로딩
model = load_model_from_s3()

if model is None:
    logger.warning("Model failed to load. Predictions will fail.")

@app.get("/predict")
def predict(value: float):
    result = model.predict([[value]])
    return {"prediction": result[0]}
