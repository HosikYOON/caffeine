
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
import itertools

def find_trigger():
    print("🕵️ Hunting for AI Model Triggers...")
    res = {}
    
    try:
        model_path = Path(r"c:\caffeine\41_ml_fraud\model_fraud.joblib")
        pipeline = joblib.load(model_path)
        
        # 1. Inspect Categorical Features if possible
        # We know inputs are: Category, MerchantState, plus numerics
        
        # Valid categories from model inspection
        categories = ['dining', 'fuel', 'grocery', 'living', 'shopping', 'transport', 'transfer']
        # Valid states
        merchant_states = ['CA', 'NY', 'TX', 'Unknown', 'Foreign', 'China', 'Russia'] 
        
        print("   Generating random scenarios...")
        
        # Generate random numeric features
        # We will generate the *Projected* features (23 cols) directly to test the model core
        # Then we will try to explain what raw data generates them.
        
        n_trials = 10000
        
        # Feature schema from app.py
        # ["Category", "MerchantState", "Hour", "DayOfWeek", "IsWeekend", "IsNight", "UseChipFlag", "Amount", "AmountLog", ...]
        
        # We'll create a DataFrame of random candidates
        
        df_rand = pd.DataFrame({
            "Category": np.random.choice(categories, n_trials),
            "MerchantState": np.random.choice(merchant_states, n_trials),
            "Hour": np.random.randint(0, 24, n_trials),
            "DayOfWeek": np.random.randint(0, 7, n_trials),
            # Derived
            "UseChipFlag": np.random.choice([0, 1], n_trials),
            "Amount": 10**np.random.uniform(3, 9, n_trials), # 1,000 to 1,000,000,000
        })
        
        # Fill derived logic
        df_rand["IsWeekend"] = (df_rand["DayOfWeek"] >= 5).astype(float)
        df_rand["IsNight"] = df_rand["Hour"].apply(lambda h: 1.0 if h < 6 or h >= 23 else 0.0)
        df_rand["AmountLog"] = np.log1p(df_rand["Amount"])
        
        # Rolling stats (The key suspects)
        # Randomize these to simulate "Burst" or "Sudden Change"
        df_rand["TxCountCumulative"] = np.random.randint(1, 1000, n_trials)
        df_rand["PrevTimeDiffHours"] = np.random.exponential(1.0, n_trials) # Usually small
        
        # Sudden burst = small time diffs
        df_rand["TimeDiffMean5"] = np.random.uniform(0, 24, n_trials)
        df_rand["TimeDiffStd5"] = np.random.uniform(0, 10, n_trials)
        df_rand["TimeDiffMean10"] = df_rand["TimeDiffMean5"]  # Simplify
        df_rand["TimeDiffStd10"] = df_rand["TimeDiffStd5"]
        
        # Amount Z-score = High means anomaly
        df_rand["AmtMean5"] = df_rand["Amount"] * np.random.uniform(0.1, 2.0, n_trials) 
        df_rand["AmtStd5"] = df_rand["AmtMean5"] * 0.2
        df_rand["AmtZ"] = np.random.normal(0, 3, n_trials) # Vary widely
        
        df_rand["AmtMean10"] = df_rand["AmtMean5"]
        df_rand["AmtStd10"] = df_rand["AmtStd5"]
        df_rand["AmtZ10"] = df_rand["AmtZ"]
        
        # Category Change
        df_rand["CategoryChanged"] = np.random.choice([0.0, 1.0], n_trials)
        df_rand["CatChangeRate10"] = np.random.uniform(0, 1, n_trials) 
        
        # PREDICT
        # Need to ensure column order matches app.py
        cols = [
            "Category", "MerchantState", "Hour", "DayOfWeek", "IsWeekend", "IsNight", "UseChipFlag",
            "Amount", "AmountLog", "TxCountCumulative", "PrevTimeDiffHours",
            "TimeDiffMean5", "TimeDiffStd5", "TimeDiffMean10", "TimeDiffStd10",
            "AmtMean5", "AmtStd5", "AmtZ", "AmtMean10", "AmtStd10", "AmtZ10",
            "CategoryChanged", "CatChangeRate10"
        ]
        
        X = df_rand[cols]
        probs = pipeline.predict_proba(X)[:, 1]
        
        df_rand["Prob"] = probs
        df_high = df_rand[df_rand["Prob"] > 0.5].sort_values("Prob", ascending=False)
        
        print(f"\n📊 Search Results:")
        print(f"   Max Probability Found: {probs.max():.4f}")
        
        if len(df_high) > 0:
            print("\n🚨 Top AI Triggers Found:")
            for i in range(min(5, len(df_high))):
                row = df_high.iloc[i]
                print(f"   [{i+1}] Prob: {row['Prob']:.4f}")
                print(f"       Category: {row['Category']}")
                print(f"       Amount: {row['Amount']:,.0f} KRW")
                print(f"       AmtZ (Abnormality): {row['AmtZ']:.2f}")
                print(f"       PrevTimeDiff: {row['PrevTimeDiffHours']:.2f} hrs")
        else:
            print("   (No inputs > 50% found yet. Trying extreme values...)")
            
            # Try specific "Extreme" injection
            # High Z-score, Low Time Diff (Rapid High Spending)
            df_curr = X.iloc[:100].copy()
            df_curr["Amount"] = 1_000_000_000 # 1 Billion
            df_curr["AmtZ"] = 20.0 # Huge Z score
            df_curr["PrevTimeDiffHours"] = 0.001 # 3 seconds ago
            
            probs2 = pipeline.predict_proba(df_curr)[:, 1]
            print(f"   Extreme Attack Max Prob: {probs2.max():.4f}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_trigger()
