# Experiments Log

전처리/필터: 2010-2020, MCC→6카테고리, 로열고객(월평균 ≥10), 시간 split(Train ≤2018-04-02 / Test 2018-04-03~2020-02-28). 불균형: 사기 0.1006%, 정상 99.8994%.

| 전략(strategy) | 샘플 | 옵션 | 모델 | F1 | ACC | 메모 |
| --- | --- | --- | --- | --- | --- | --- |
| baseline_class_weight+scale_pos_weight | 10M | 가중치만 | XGB | 0.0100 | 0.9014 | SMOTE 없음 |
| smote_only | 0.5M | SMOTE | XGB | 0.0133 | 0.9773 | 현재 최고 F1(소규모 샘플) |
| smote+spw1.5+feat | 0.5M | SMOTE + scale_pos_weight 1.5 | XGB | 0.0133 | 0.9757 | 시간간격/rolling 금액 피처 포함 |
| spw_2x | 10M | scale_pos_weight 2x | RF | 0.0095 | 0.8974 | XGB 0.0090 |
| quick_smote_test | 0.2M | SMOTE + scale_pos_weight 1.5 | XGB | 0.3333 | 0.9986 | 새 피처(시간간격/Zip/카테고리 변화) 추가 후 소규모 샘플 |
| smote+spw1.5+feat_v2 | 1.0M | SMOTE + scale_pos_weight 1.5 | XGB | 0.2014 | 0.9948 | 새 피처로 1M 샘플 학습 |
| smote+spw1.5+feat_2M | 2.0M | SMOTE + scale_pos_weight 1.5 | XGB | 0.1536 (best_thr F1 0.4482 @ thr≈0.99) | 0.9886 | 더 큰 샘플, 최적 임계값에서 F1 크게 상승 |
| smote+spw1.5+feat_3M | 3.0M | SMOTE + scale_pos_weight 1.5 | XGB | 0.0929 (best_thr F1 0.3354 @ thr≈0.99) | 0.9822 | 3M 샘플은 성능 하락, 2M 대비 열세 |
| xgb_tuned_depth7_1M | 1.0M | SMOTE + scale_pos_weight 1.5, n_estimators=500, max_depth=7, lr=0.08, subsample=0.85, colsample=0.85 | XGB | 0.4536 (best_thr F1 0.5553 @ thr≈0.93) | 0.9984 | 현재 최고 성능 |

추가 시도 예정:
- 위치/단말/Zip 빈도, 새로운 지역/단말 플래그
- 카테고리 시퀀스 변화/엔트로피, 최근 k건 time-diff 평균/표준편차
- CatBoost/LightGBM 비교, PR-AUC/임계값 튜닝 리포트
