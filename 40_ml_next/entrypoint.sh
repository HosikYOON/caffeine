#!/bin/bash
set -e

echo "[INFO] S3에서 모델 다운로드 시작..."

aws s3 cp s3://caf-fin-models/ml_next/model.pkl /app/model.pkl

echo "[INFO] 모델 다운로드 완료!"

echo "[INFO] FastAPI 서버 시작..."
exec uvicorn app:app --host 0.0.0.0 --port 9001
