## Fraud model start guide

작업 루트: `C:\fraud\41_ml_fraud`

### 폴더/서비스
- 데이터 원본: `C:\fraud\archive\credit_card_transactions-ibm_v2.csv` (24,386,900건)
- 로컬 폴더: `data/raw`(원본 링크/복사 위치), `data/processed`(필터 완료), `models`(학습 결과), `notebooks`(탐색)
- 도커/compose: 아직 없음(필요 시 추가)

### 실행/빌드
- 권장 Python: 3.10+
- 가상환경: `python -m venv .venv && .\\.venv\\Scripts\\activate`
- 패키지 예시: pandas, numpy, scikit-learn, imbalanced-learn, xgboost, pyarrow/fastparquet, hydra-core(or pydantic)
- 추후 CLI 예시: `python -m src.prepare_data --input archive/credit_card_transactions-ibm_v2.csv --output data/processed/train.parquet`

### 데이터 필터링 파이프라인(필수 단계)
1) 연도 필터: 2010-01-01~2020-12-31만 사용 (최근 10년)  
2) MCC 매핑 → 6개 카테고리 (매핑 불가 제거)  
   - 교통: 4000-4099, 4100-4199  
   - 생활: 4800-4899, 6000-6099  
   - 쇼핑: 5200-5299, 5300-5399, 5600-5699  
   - 식료품: 5411-5499  
   - 외식: 5811-5899  
   - 주유: 5500-5599  
3) 로열 고객 필터: 월평균 거래 ≥ 10건  
4) 시간 기반 split: Train 2010-03-02~2018-04-02 (약 80%), Test 2018-04-03~2020-02-28 (약 20%)  
5) 저장: parquet 권장(`data/processed/train.parquet`, `data/processed/test.parquet`)

### 피처 아이디어(사기 탐지용)
- 금액: 원금액, log1p 금액, 사용자 평균 대비 z-score, 최근 k건 평균/표준편차  
- 시간: Hour, DayOfWeek, IsWeekend, IsNight(22-6h), IsBusinessHour(9-18h), 거래 간 시간 간격(velocity)  
- 카테고리: 최근 k건 카테고리 모드/변화 여부, 카테고리 비율  
- 사용자: 누적 거래수, 평균/표준편차, 단말/지역/IP(가능 시), 카드별/사용자별 편향  
- 레이블 불균형: train만 SMOTE 또는 `class_weight`; 주요 지표는 PR-AUC, recall@precision

### 학습 베이스라인
- 모델: XGBoost/LightGBM(트리 기반, 스케일 필요 없음) + 비교용 로지스틱(class_weight)  
- 검증: 시간 순 K-fold 대신 단일 시계열 holdout(train/test) 유지  
- 하이퍼파라미터 스타터:  
  - n_estimators: 200-500, max_depth: 6-10, learning_rate: 0.05-0.2  
  - subsample/colsample_bytree: 0.6-0.9, scale_pos_weight: 양/음 샘플 비율로 설정

### 환경변수 (예시, 값은 빈칸)
- `DATA_PATH=archive/credit_card_transactions-ibm_v2.csv`
- `TRAIN_PATH=data/processed/train.parquet`
- `TEST_PATH=data/processed/test.parquet`
- `MODEL_PATH=models/fraud_xgb_v1.json`

### 테스트/검증
- 단위: 데이터 필터 함수, 날짜 split, 누수 여부 검사(pytest)  
- 빠른 샘플 실험: 100k 샘플로 피처/모델 스케치, 전체 학습은 배치 스크립트로 분리  
- 추후 API: FastAPI `/predict` (JSON: amount, mcc, tx_datetime, user_id, device_id …)

### 바로 다음 작업 제안
1) 가상환경 구성 후 의존성 설치:  
   - `python -m venv .venv && .\.venv\Scripts\activate`  
   - `pip install -r requirements.txt`
2) 학습 실행(샘플 50만행, 시간필터/로열고객/MCC매핑 포함):  
   - `python -m src.train --data ../archive/credit_card_transactions-ibm_v2.csv --sample-size 500000 --chunksize 200000 --output-dir models`
3) Streamlit 대시보드로 결과 확인:  
   - `streamlit run streamlit_app.py`  
   - 핵심 지표(F1/Accuracy), 필터링 요약, 불균형 대응 전략별 성능 비교(`strategy` 필드) 표시. 업데이트 시각은 2025-12-11 16:47으로 표시됨.  
4) 필요 시 `sample-size`를 조정해 속도/품질 트레이드오프 선택.

### 실험/참고 (Kaggle 커뮤니티 패턴)
- 다른 사용자 접근: 거래 간 시간 차·빈도, 최근 k건 금액/카테고리 통계, 위치/단말 플래그, 빈도 인코딩, SMOTE/ADASYN, class_weight/scale_pos_weight, PR-AUC 기반 임계값 튜닝, CatBoost/LightGBM 사용.
- 현재 반영/테스트한 것: 시간 간격(PrevTimeDiffHours), 최근 5건 금액 평균/표준편차/z-score, 누적 거래수, Zip 빈도/변화, 카테고리 변화, SMOTE, scale_pos_weight 계수, 전략명 로깅.
- 성능 메모(불균형 0.1%): 새 피처+SMOTE+spw1.5에서 0.2~0.33 F1까지 개선(샘플 0.2~1M 기준). 더 큰 데이터/추가 피처/모델 튜닝으로 상향 필요.
