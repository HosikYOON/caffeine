발표용 코드 워크스루(요약)
========================

1) 데이터 분할·누수 차단 (src/train.py)
- 핵심: 시간 순 정렬 → Train/Test 먼저 자른 뒤 피처 계산.
```python
# src/train.py:350~
def time_split(df: pd.DataFrame) -> DatasetSplit:
    train = df[df["Date"] <= TRAIN_END].copy()
    test = df[(df["Date"] >= TEST_START) & (df["Date"] <= TEST_END)].copy()

    zip_freq_map = train["ZipClean"].value_counts(normalize=True)
    train = add_velocity_features(train, zip_freq_map=zip_freq_map)
    test = add_velocity_features(test, zip_freq_map=zip_freq_map)
```
- MCC 매핑 (미매핑 제거):
```python
# src/train.py:113~
def mcc_to_category(mcc: float) -> str | None:
    if pd.isna(mcc): return None
    mcc = int(mcc)
    if 4000 <= mcc <= 4099 or 4100 <= mcc <= 4199: return "transport"
    if 4800 <= mcc <= 4899 or 6000 <= mcc <= 6099: return "living"
    if 5200 <= mcc <= 5299 or 5300 <= mcc <= 5399 or 5600 <= mcc <= 5699: return "shopping"
    if 5411 <= mcc <= 5499: return "grocery"
    if 5811 <= mcc <= 5899: return "dining"
    if 5500 <= mcc <= 5599: return "fuel"
    return None
```
- 피처 계산은 Train/Test 각각에서 롤링/증분을 구해 누수 차단:
```python
# src/train.py:199~
def add_velocity_features(df: pd.DataFrame, zip_freq_map: Dict | None = None) -> pd.DataFrame:
    df = df.sort_values(["User", "DateTime"]).reset_index(drop=True)
    df["TxCountCumulative"] = df.groupby("User").cumcount()
    df["PrevTimeDiffHours"] = (
        df.groupby("User")["DateTime"].diff().dt.total_seconds().div(3600)
    ).fillna(9999.0)
    # 이후 TimeDiffMean/Std(5,10), AmtMean/Std/Z(5,10), 카테고리/Zip 변화율 등 계산
```

2) 불균형·모델 전략 정의 (src/train.py)
- 전략 라인업: 베이스라인(가중치+`scale_pos_weight`), SMOTE+가중치 조합, XGB 튜닝(depth 7/8, spw≈2, lr 0.05, 샘플 120만~150만), LGBM 튜닝(leaves=127, lr=0.05, n_estimators~800).
- 전략명 예시: `baseline_class_weight+scale_pos_weight`, `smote+spw1.5+feat`, `xgb_tuned_depth8_spw2_lr005_1.2M_newfeat`, `lgbm_tuned_leaves127_lr005_1.2M_final`(현재 최고).

3) 임계값 튜닝 (streamlit_app.py)
- 고정 임계값 5점(0.01~0.05) 재계산 → Altair 라인(y=F1, 도메인 0.63~0.69)로 “0.03 최고, 0.04부터 하락”을 바로 보여줌. 자동 PR 스캔 그래프는 숨김.

4) 실험 노트 (streamlit_app.py, 실험 노트 탭)
- 누수로 F1=0.99까지 올랐던 실험은 무효.
- 균형(50:50) 실험은 보고에서 제외; 실분포(사기 ~0.12%) 결과만 사용.
- 현재 베스트: LGBM (leaves=127, lr=0.05, n_estimators~800, subsample/colsample=0.8) 실분포 테스트 F1≈0.675 @ thr≈0.03.

발표 멘트 예시
- “여기 `time_split`에서 시간을 먼저 끊고, `add_velocity_features`는 Train/Test 각각에서 계산해 미래 정보가 섞이지 않습니다.”
- “전략은 세 갈래: 가중치 베이스라인, SMOTE+가중치 계열, XGB/LGBM 튜닝. 최신 피처를 쓴 LGBM 구성이 실분포 F1 최고입니다.”
- “임계값은 0.01~0.05만 재계산해서 0.03이 정점, 0.04부터 내려가는 걸 한 그래프로 보여줍니다.”
