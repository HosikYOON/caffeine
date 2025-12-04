from fastapi import FastAPI
import os
from dotenv import load_dotenv
import joblib
import boto3
from io import BytesIO

load_dotenv()

app = FastAPI()  # 반드시 있어야 함

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
MODEL_KEY = os.getenv("MODEL_KEY")

# 모델 로드 함수
def load_model_from_s3():
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    buffer = BytesIO()
    s3.download_fileobj(S3_BUCKET, MODEL_KEY, buffer)
    buffer.seek(0)
    model = joblib.load(buffer)
    return model

# 실제 모델 로딩
model = load_model_from_s3()

@app.get("/predict")
def predict(value: float):
    result = model.predict([[value]])
    return {"prediction": result[0]}
