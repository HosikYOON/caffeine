
import joblib
import pandas as pd
import numpy as np
from pathlib import Path

try:
    model_path = Path(r"c:\caffeine\41_ml_fraud\model_fraud.joblib")
    pipeline = joblib.load(model_path)
    
    # The new model architecture might be different (e.g. XGBoost based on metadata desc)
    # Metadata said: "XGBoost with feature-plus set"
    # Structure is usually Pipeline -> [prep, model]
    
    if "model" in pipeline.named_steps:
        estimator = pipeline.named_steps["model"]
        print(f"Estimator Type: {type(estimator)}")
        
        if hasattr(estimator, "feature_importances_"):
            imps = estimator.feature_importances_
            
            # Get names
            names = []
            if hasattr(estimator, "feature_name_"): # LightGBM
                 names = estimator.feature_name_
            elif hasattr(estimator, "feature_names_in_"): # XGBoost / Sklearn
                 names = estimator.feature_names_in_
            else:
                 # Try to get from pipeline feature names if possible or raw index
                 names = [f"f{i}" for i in range(len(imps))]

            if len(names) == len(imps):
                df_imp = pd.DataFrame({"Feature": names, "Importance": imps})
                df_imp = df_imp.sort_values("Importance", ascending=False)
                print("\n🏆 Top Important Features (New Model):")
                print(df_imp.head(15).to_string(index=False))
            else:
                print(f"Mismatch: Names {len(names)} vs Imps {len(imps)}")
                print("Raw Importances:", imps)

except Exception as e:
    print(f"Error: {e}")
