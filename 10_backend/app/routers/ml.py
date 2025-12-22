from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Dict, Any
from app.services.ml_service import get_ml_service

router = APIRouter(prefix="/ml", tags=["machine-learning"])

class PredictionRequest(BaseModel):
    features: Dict[str, Any]

@router.post("/predict")
async def predict(request: PredictionRequest, service=Depends(get_ml_service)):
    return await service.predict_single(request.features)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), service=Depends(get_ml_service)):
    return await service.predict_csv(file)

@router.post("/predict-next")
async def predict_next_category(file: UploadFile = File(...), service=Depends(get_ml_service)):
    """다음 소비 카테고리 예측"""
    return await service.predict_next_category(file)
