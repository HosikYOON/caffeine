
import sys
import os
import joblib
import pandas as pd
import numpy as np
import math
from pathlib import Path

# Add backend to path to import app modules
backend_path = Path(r"c:\caffeine\10_backend")
sys.path.append(str(backend_path))

try:
    from app.services.paysim_features import build_model_inputs
    print("✅ Successfully imported paysim_features")
except ImportError as e:
    print(f"❌ Failed to import backend modules: {e}")
    sys.exit(1)

# Heuristic configuration
HEURISTIC_HIGH_AMOUNT = 1000000.0
HEURISTIC_Z_THRESHOLD = 3.0

def run_test():
    print("🚀 Starting NEW Fraud Model Test with '가계부이상거래.csv'...")

    # 1. Load Data
    csv_path = Path(r"c:\caffeine\forcodex\가계부이상거래.csv")
    if not csv_path.exists():
        print(f"❌ Data file not found: {csv_path}")
        return
    
    print(f"📂 Loading data from {csv_path}...")
    try:
        df_ledger = pd.read_csv(csv_path)
        print(f"   - Loaded {len(df_ledger)} transactions")
    except Exception as e:
        print(f"❌ Failed to read CSV: {e}")
        return

    # 2. Inject Synthetic Test Cases for New Heuristics
    print("🧪 Injecting synthetic data for Night/Burst/Keyword tests...")
    
    # Base time
    base_t = pd.to_datetime("2024-01-01 12:00:00")
    
    new_rows = []
    
    # Case A: Night Spend (03:00, 300k KRW - Should trigger Night Rule)
    new_rows.append({
        "날짜": "2024-01-02", "시간": "03:00:00", "내용": "심야편의점", 
        "금액": -300000, "타입": "지출", "대분류": "식비", "소분류": "간식", "메모": "야식"
    })
    
    # Case B: Keyword Trigger ("해외" - Should trigger Keyword Rule)
    new_rows.append({
        "날짜": "2024-01-02", "시간": "14:00:00", "내용": "해외직구", 
        "금액": -50000, "타입": "지출", "대분류": "쇼핑", "소분류": "기타", "메모": "직구"
    })
    
    # Case C: Rapid Burst (5 txs in 5 mins)
    for i in range(6):
        t = base_t + pd.Timedelta(minutes=i)
        new_rows.append({
            "날짜": t.strftime("%Y-%m-%d"), "시간": t.strftime("%H:%M:%S"), 
            "내용": f"초단타{i}", "금액": -60000, 
            "타입": "지출", "대분류": "식비", "소분류": "커피", "메모": "연속결제"
        })

    df_synthetic = pd.DataFrame(new_rows)
    df_ledger = pd.concat([df_ledger, df_synthetic], ignore_index=True)
    
    # Re-sort to ensure rolling windows work correctly
    # Note: `build_model_inputs` sorts by time internally using `_parse_datetime`, so simple concat is fine
    # but let's ensure '날짜'/'시간' are handled.
    print(f"   - Added {len(new_rows)} synthetic rows. Total: {len(df_ledger)}")
    try:
        # Returns 18 features expected by new model
        df_features = build_model_inputs(df_ledger)
        print(f"✅ Data transformation successful. Generated {len(df_features)} rows.")
        print(f"   Columns: {list(df_features.columns)}")
        
    except Exception as e:
        print(f"❌ Data transformation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Load Model
    model_path = Path(r"c:\caffeine\41_ml_fraud\model_fraud.joblib")
    print(f"🧠 Loading ML model from {model_path}...")
    try:
        model = joblib.load(model_path)
        print("✅ Model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return

    # 4. Predict & Apply Heuristics
    print("🔮 Running prediction and applying heuristics...")
    try:
        # Predict Probabilities
        probs = model.predict_proba(df_features)[:, 1]
        
        # We need raw stats for heuristics, but they heavily depend on history.
        # For this script, we can roughly calculate them from the ledger itself
        # similar to how paysim_features does internally but we dont have access to the intermediate df there.
        # Let's rebuild the raw Amount logic for heuristics here.
        
        # Parse Amount from ledger
        amount_col = next((c for c in df_ledger.columns if c.lower() in ["amount", "금액"]), None)
        raw_amounts = df_ledger[amount_col].abs().astype(float) if amount_col else pd.Series(np.zeros(len(df_ledger)))
        
        # Calculate Rolling Z (Simple approximation for test)
        # Using 5-window rolling mean/std
        roll = raw_amounts.rolling(5, min_periods=1)
        mean5 = roll.mean()
        std5 = roll.std().fillna(0)
        
        roll10 = raw_amounts.rolling(10, min_periods=1)
        mean10 = roll10.mean()
        std10 = roll10.std().fillna(0)
        
        # Calculate Time Diffs for Burst Check
        # Access TimeDiffMean5 from df_features (now it is returned by build_model_inputs)
        # Verify it exists
        if "TimeDiffMean5" not in df_features.columns:
            print("⚠️ 'TimeDiffMean5' not found in features. Heuristics might fail.")
            
        results = []
        
        # Define Heuristic Constants locally
        H_NIGHT_START = 0
        H_NIGHT_END = 6
        H_NIGHT_THRESH = 200000.0
        H_BURST_WIN = 0.17
        H_BURST_MIN = 50000.0
        H_KEYWORDS = ["해외", "상품권", "캐시", "게임", "bitcoin", "casino", "비트코인", "도박"]

        for i in range(len(df_features)):
            orig_row = df_ledger.iloc[i]  # Use df_ledger which now has synthetic rows
            row_feats = df_features.iloc[i]
            
            raw_amt = raw_amounts.iloc[i]
            
            # Z-calc
            z5 = (raw_amt - mean5.iloc[i]) / std5.iloc[i] if std5.iloc[i] > 0 else 0
            
            ml_prob = probs[i]
            is_fraud_ml = ml_prob > 0.5
            
            # Heuristic Logic
            heuristic_reasons = []
            
            # 1. High Amount (Night aware)
            hour = row_feats['hour']
            is_night = H_NIGHT_START <= hour < H_NIGHT_END
            thresh = H_NIGHT_THRESH if is_night else HEURISTIC_HIGH_AMOUNT
            
            if raw_amt >= thresh:
                heuristic_reasons.append(f"{'Night ' if is_night else ''}High Amount ({raw_amt:,.0f})")
                
            # 2. Z Score
            if abs(z5) >= HEURISTIC_Z_THRESHOLD:
                heuristic_reasons.append(f"High Z-Score {z5:.2f}")
                
            # 3. Burst
            # Use TimeDiffMean5 from features
            td5 = row_feats.get("TimeDiffMean5", 999.0)
            if td5 < H_BURST_WIN and raw_amt >= H_BURST_MIN:
                heuristic_reasons.append(f"Rapid Burst ({td5*60:.0f}m)")

            # 4. Keyword
            content = (str(orig_row.get('내용', '')) + " " + str(orig_row.get('메모', ''))).lower()
            hit_k = next((k for k in H_KEYWORDS if k in content), None)
            if hit_k:
                heuristic_reasons.append(f"Risky Keyword ({hit_k})")
                
            is_heuristic_hit = len(heuristic_reasons) > 0
            
            final_fraud = is_fraud_ml or is_heuristic_hit
            final_prob = ml_prob
            if is_heuristic_hit:
                final_prob = max(final_prob, 0.99)
                
            results.append({
                "Index": i,
                "Merchant": orig_row.get('내용', 'Unknown'),
                "Amount": raw_amt,
                "ML_Prob": ml_prob,
                "Heuristics": ", ".join(heuristic_reasons),
                "IsFraud": final_fraud
            })
            
        df_results = pd.DataFrame(results)
        n_fraud = df_results["IsFraud"].sum()
        n_ml_fraud = df_results[df_results["ML_Prob"] > 0.5].shape[0]

        print("-" * 30)
        print(f"📊 New Model Test Results:")
        print(f"   - Total Transactions: {len(df_results)}")
        print(f"   - ML-Detected Anomalies: {n_ml_fraud}")
        print(f"   - Hybrid (ML+Rule) Anomalies: {n_fraud}")
        print("-" * 30)
        
        if n_fraud > 0:
            print("🚨 Detected Anomalies:")
            fraud_rows = df_results[df_results["IsFraud"] == True].sort_values("ML_Prob", ascending=False)
            
            for _, row in fraud_rows.iterrows():
                print(f"\n   [Row {row['Index']}] {row['Merchant']}")
                print(f"     Amount: {row['Amount']:,.0f} KRW")
                print(f"     ML Probability: {row['ML_Prob']:.4f}")
                if row['Heuristics']:
                    print(f"     ⚠️ Heuristic Trigger: {row['Heuristics']}")
                else:
                    print(f"     🤖 Detected by ML Model")
        else:
            print("✅ No anomalies found.")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
