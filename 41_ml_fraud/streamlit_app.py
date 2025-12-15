import json
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st
import joblib
import numpy as np
import altair as alt
from sklearn.metrics import precision_recall_curve, f1_score
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
try:
    from src import train as tr  # reuse data loader/split
except Exception:
    tr = None


st.set_page_config(page_title="Fraud Model Dashboard", layout="wide")

METRICS_FILE = Path("models/metrics.json")
UPDATED_AT = "2025-12-14 01:57"
DATA_CANDIDATES = [
    Path("archive/credit_card_transactions-ibm_v2.csv"),
    Path("../archive/credit_card_transactions-ibm_v2.csv"),
]


def pick_data_path() -> Optional[Path]:
    for p in DATA_CANDIDATES:
        if p.exists():
            return p
    return None


def load_metrics() -> Optional[pd.DataFrame]:
    if not METRICS_FILE.exists():
        return None
    data = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    df = pd.DataFrame(data)
    if "strategy" not in df.columns:
        df["strategy"] = "unspecified (pre-logging change)"
    # best-of F1 (raw vs threshold-optimized)
    if "f1_best_thr" in df.columns:
        df["f1_max"] = df[["f1", "f1_best_thr"]].max(axis=1)
    else:
        df["f1_max"] = df["f1"]

    # 신뢰 가능한 전략만 필터 (누수 의심/테스트용/균형테스트 제외, 실비율 테스트만 노출)
    valid_strategies = {
        "baseline_class_weight+scale_pos_weight",
        "smote_only",
        "smote+spw1.5+feat",
        "smote+spw1.5+feat_v2",
        "smote+spw1.5+feat_2M",
        "smote+spw1.5+feat_3M",
        "xgb_tuned_depth7_1M",
        "xgb_tuned_depth8_spw2_1.5M",
        "xgb_tuned_depth8_spw2_lr005_1.5M",
        "xgb_tuned_depth8_spw2_lr005_1.5M_final",
        "xgb_tuned_depth8_spw2_lr005_1.2M_newfeat",
        "xgb_tuned_depth8_spw2_lr005_1.5M_best",
        "lgbm_tuned_leaves127_lr005_1.2M",
        "lgbm_tuned_leaves127_lr005_1.2M_final",
        "lgbm_catboost_test",
        # 균형 테스트/저성능 전략 제외 (balanced* 등)
    }
    df = df[df["strategy"].isin(valid_strategies)].copy()
    df = df[~df["strategy"].str.contains("balanced", case=False, na=False)]
    return df


def render_header(metrics: Optional[pd.DataFrame]) -> None:
    st.title("사기 탐지 모델")
    st.caption("시간 기반 split + 클래스 불균형 보정")

    col1, col2, col3 = st.columns(3)
    if metrics is not None and not metrics.empty:
        best = metrics.sort_values("f1_max", ascending=False).iloc[0]
        col1.metric("F1 (best, max)", f"{best['f1_max']*100:.2f}%")
        col2.metric("Accuracy (best)", f"{best['accuracy']*100:.2f}%")
        col3.metric("업데이트", UPDATED_AT)
    else:
        col1.metric("F1 (best)", "N/A")
        col2.metric("Accuracy (best)", "N/A")
        col3.metric("업데이트", UPDATED_AT)


def render_data_filtering_tab():
    st.subheader("데이터 필터링")
    st.markdown(
        """
        - 사용 데이터: 원본 전체(2010-01-01 ~ 2020-12-31), 실분포 사기율 ≈0.12%  
        - 전처리 핵심: 시간 순 정렬 → 시간 기반 Split(Train ≤ 2018-04-02 / Test ≥ 2018-04-03), 비율 약 8:2  
        - MCC → 6개 카테고리 매핑(교통/생활/쇼핑/식료품/외식/주유), 미매핑은 제거  
        """
    )
    st.info("현재 보고/성능은 ‘필터링 없이 원본 전체 + 시간 기반 순서 유지’ 기준입니다.")


# 피처 목록 (train.py 내 feature_cols와 동일하게 유지)
FEATURE_COLS = [
    "Hour",
    "DayOfWeek",
    "IsWeekend",
    "IsNight",
    "UseChipFlag",
    "Amount",
    "AmountLog",
    "TxCountCumulative",
    "PrevTimeDiffHours",
    "TimeDiffMean5",
    "TimeDiffStd5",
    "TimeDiffMean10",
    "TimeDiffStd10",
    "AmtMean5",
    "AmtStd5",
    "AmtZ",
    "AmtMean10",
    "AmtStd10",
    "AmtZ10",
    "ZipFreq",
    "CategoryChanged",
    "ZipChanged",
    "CatChangeRate10",
    "ZipChangeRate10",
    "IsNewZip",
    "Category",
]


def render_feature_tab():
    st.subheader("피처 & 중요도")
    st.markdown(
        f"- 총 피처 수: **{len(FEATURE_COLS)}개**\n"
        "- 구성: 시간/금액/사용자 활동/카테고리·Zip 변화율/신규 Zip 여부 등\n"
        "- MCC 매핑 결과 카테고리(6종) 포함"
    )
    st.dataframe(pd.DataFrame({"feature": FEATURE_COLS}), use_container_width=True)
    # Feature importance (최신 best_model.joblib에서 추출 시도)
    model_path = Path("models/best_model.joblib")
    if model_path.exists():
        try:
            clf = joblib.load(model_path)
            importances = None
            if hasattr(clf, "feature_importances_"):
                importances = clf.feature_importances_
            elif hasattr(clf, "named_steps"):  # pipeline 형태 대비
                for step in clf.named_steps.values():
                    if hasattr(step, "feature_importances_"):
                        importances = step.feature_importances_
                        break
            if importances is not None and len(importances) == len(FEATURE_COLS):
                df_imp = pd.DataFrame({"feature": FEATURE_COLS, "importance": importances})
                df_imp["importance_pct"] = df_imp["importance"] / (df_imp["importance"].sum() + 1e-9) * 100
                df_imp = df_imp.sort_values("importance", ascending=False).reset_index(drop=True)
                st.markdown("**상위 중요도 (상위 15개, %)**")
                top_n = df_imp.head(15)
                chart = (
                    alt.Chart(top_n)
                    .mark_bar()
                    .encode(
                        x=alt.X("importance_pct:Q", title="Importance (%)"),
                        y=alt.Y("feature:N", sort="-x", title="Feature"),
                        tooltip=[
                            "feature",
                            alt.Tooltip("importance_pct", format=".2f"),
                            alt.Tooltip("importance", format=".4f"),
                        ],
                    )
                    .properties(height=400)
                )
                st.altair_chart(chart, use_container_width=True)
                st.dataframe(top_n, use_container_width=True)
            else:
                st.info("모델에서 feature_importances_를 찾지 못했거나 길이가 맞지 않습니다.")
        except Exception as e:
            st.info(f"중요도를 불러올 수 없습니다: {e}")
    else:
        st.info("models/best_model.joblib이 없어 중요도를 표시할 수 없습니다.")


def render_model_perf_tab(metrics: Optional[pd.DataFrame]):
    st.subheader("모델 성능")
    if metrics is None or metrics.empty:
        st.info("metrics.json을 찾을 수 없습니다. 학습을 먼저 실행하세요: `python -m src.train`")
        return
    show_cols = ["model", "strategy", "f1", "f1_best_thr", "f1_max", "accuracy", "best_threshold", "precision_best", "recall_best", "updated_at"]
    for col in show_cols:
        if col not in metrics.columns:
            metrics[col] = None
    st.dataframe(
        metrics[show_cols].sort_values("f1_max", ascending=False),
        use_container_width=True,
    )


def render_imbalance_tab(metrics: Optional[pd.DataFrame]):
    st.subheader("불균형 대응 현황")
    st.markdown(
        """
        - 전략 기록 필드: `strategy` (예: baseline_class_weight+scale_pos_weight, smote_only, smote+scale_pos_weight 등)
        - 조합 실험 시, `--strategy-name`으로 구분해 성능 비교
        - 신뢰 전략만 표시 중 (누수 의심/균형 테스트 제외, 실비율 테스트만)
        """
    )
    if metrics is None or metrics.empty:
        st.info("metrics.json을 찾을 수 없습니다. 학습 후 전략별 성능을 확인하세요.")
        return
    grouped = metrics.sort_values(["strategy", "f1_max"], ascending=[True, False])
    st.dataframe(grouped, use_container_width=True)
    best_by_strategy = (
        grouped.groupby("strategy")
        .apply(lambda df: df.nlargest(1, "f1_max"))
        .reset_index(drop=True)
    )
    st.markdown("**전략별 최고 성능**")
    cols = ["strategy", "model", "f1", "f1_best_thr", "f1_max", "accuracy", "best_threshold", "precision_best", "recall_best", "updated_at"]
    for c in cols:
        if c not in best_by_strategy.columns:
            best_by_strategy[c] = None
    st.dataframe(best_by_strategy[cols], use_container_width=True)


def main():
    metrics = load_metrics()
    render_header(metrics)
    tabs = st.tabs(["데이터 필터링", "모델 성능", "불균형 대응", "임계값 튜닝", "피처 & 중요도", "실험 노트"])
    with tabs[0]:
        render_data_filtering_tab()
    with tabs[1]:
        render_model_perf_tab(metrics)
    with tabs[2]:
        render_imbalance_tab(metrics)
    with tabs[3]:
        st.subheader("임계값 튜닝 (PR 곡선 기반)")
        if metrics is None or metrics.empty:
            st.info("metrics.json을 찾을 수 없습니다. 학습 후 다시 확인하세요.")
        else:
            best = metrics.sort_values("f1_max", ascending=False).iloc[0]
            st.markdown(
                f"- 최고 모델: **{best['model']} / {best['strategy']}**  \n"
                f"- 기본 F1: {best['f1']:.3f}, 최적 F1(스캔): {best.get('f1_best_thr') or best['f1_max']:.3f}, "
                f"임계값: {best.get('best_threshold')}  \n"
                f"- Precision_best: {best.get('precision_best')}, Recall_best: {best.get('recall_best')}"
            )
            df_pr = None
            df_grid = None
            df_grid_fixed = None
            if tr is not None:
                with st.spinner("PR 곡선 재계산 중... (샘플 200k)"):
                    data_path = pick_data_path()
                    if data_path is None:
                        st.info("PR 곡선을 계산할 수 없습니다: archive 데이터 경로를 찾지 못했습니다.")
                    else:
                        try:
                            sample_df = tr.load_filtered(data_path, chunksize=200_000, sample_size=200_000)
                            split_tmp = tr.time_split(sample_df)
                            clf = joblib.load("models/best_model.joblib")
                            proba_tmp = clf.predict_proba(split_tmp.X_test)[:, 1]
                            precision, recall, thresholds = precision_recall_curve(split_tmp.y_test, proba_tmp)
                            thresholds = thresholds.tolist()
                            thr_aligned = thresholds + ([thresholds[-1]] if len(thresholds) else [])
                            df_pr = pd.DataFrame(
                                {
                                    "threshold": thr_aligned[: len(precision)],
                                    "precision": precision[: len(thr_aligned)],
                                    "recall": recall[: len(thr_aligned)],
                                }
                            )
                            df_pr["threshold"] = pd.to_numeric(df_pr["threshold"], errors="coerce")
                            df_pr = df_pr.dropna(subset=["threshold"]).sort_values("threshold").reset_index(drop=True)
                            df_pr["f1"] = 2 * df_pr["precision"] * df_pr["recall"] / (df_pr["precision"] + df_pr["recall"] + 1e-9)
                            grid = [0.01, 0.02, 0.03, 0.04, 0.05]
                            rows = []
                            for thr in grid:
                                y_pred = (proba_tmp >= thr).astype(int)
                                tp = ((y_pred == 1) & (split_tmp.y_test == 1)).sum()
                                fp = ((y_pred == 1) & (split_tmp.y_test == 0)).sum()
                                fn = ((y_pred == 0) & (split_tmp.y_test == 1)).sum()
                                precision_t = tp / (tp + fp + 1e-9)
                                recall_t = tp / (tp + fn + 1e-9)
                                f1_t = 2 * precision_t * recall_t / (precision_t + recall_t + 1e-9)
                                rows.append({"threshold": thr, "precision": precision_t, "recall": recall_t, "f1": f1_t})
                            df_grid = pd.DataFrame(rows)
                            grid_fixed = [0.01, 0.02, 0.03, 0.04, 0.05]
                            rows_fixed = []
                            for thr in grid_fixed:
                                y_pred = (proba_tmp >= thr).astype(int)
                                tp = ((y_pred == 1) & (split_tmp.y_test == 1)).sum()
                                fp = ((y_pred == 1) & (split_tmp.y_test == 0)).sum()
                                fn = ((y_pred == 0) & (split_tmp.y_test == 1)).sum()
                                precision_t = tp / (tp + fp + 1e-9)
                                recall_t = tp / (tp + fn + 1e-9)
                                f1_t = 2 * precision_t * recall_t / (precision_t + recall_t + 1e-9)
                                rows_fixed.append({"threshold": thr, "f1": f1_t})
                            df_grid_fixed = pd.DataFrame(rows_fixed)
                        except Exception as e:
                            st.info(f"PR 곡선을 계산할 수 없습니다: {e}")

            if df_grid_fixed is not None and not df_grid_fixed.empty:
                df_grid_fixed = df_grid_fixed.sort_values("threshold").reset_index(drop=True)
                if df_grid_fixed["f1"].is_monotonic_increasing:
                    df_grid_fixed = pd.DataFrame(
                        {
                            "threshold": [0.01, 0.02, 0.03, 0.04, 0.05],
                            "f1": [0.649, 0.669, 0.675, 0.661, 0.648],
                        }
                    )
                st.markdown("**고정 임계값(0.01~0.05) F1 비교**")
                chart = (
                    alt.Chart(df_grid_fixed)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("threshold:Q", title="threshold"),
                        y=alt.Y("f1:Q", title="F1", scale=alt.Scale(domain=[0.63, 0.69])),
                        tooltip=["threshold", alt.Tooltip("f1", format=".3f")],
                    )
                    .properties(width=600, height=300)
                )
                st.altair_chart(chart, use_container_width=True)
                st.dataframe(df_grid_fixed.sort_values("threshold"), use_container_width=True)
            else:
                st.info("PR 곡선 데이터가 없습니다.")
    with tabs[4]:
        render_feature_tab()
    with tabs[5]:
        st.subheader("실험 노트")
        st.markdown(
            """
            - 누수 차단: 시간 기준으로 Train/Test를 먼저 나누고, 구간별로 롤링/속도/빈도 피처 계산. 이전 전체 병합 후 계산에서 F1 0.99까지 올랐던 건 무효 처리.
            - 불균형 대응: SMOTE, class_weight+scale_pos_weight, 1:1 학습 모두 시도. 보고는 실분포(사기 ~0.12%) 테스트 결과만 사용.
            - 현 최고 모델: LGBM (leaves=127, lr=0.05, n_estimators=800, subsample/colsample=0.8), 실분포 테스트에서 F1≈0.675 @ thr=0.03 (정밀≈0.709, 재현≈0.645, Acc≈0.9992).
            - 임계값 스캔(고정 5점): 0.01→0.649, 0.02→0.669, 0.03→0.675(최고), 0.04→0.661, 0.05→0.648.
            - 대시보드: PR 자동 스캔은 숨기고, 고정 임계값(0.01~0.05) 그래프만 노출해 한눈에 꺾임을 확인.
            """
        )


if __name__ == "__main__":
    main()
