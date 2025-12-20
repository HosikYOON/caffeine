
import joblib
import pandas as pd
import numpy as np
from pathlib import Path

def get_feature_names(pipeline):
    # This logic depends on the sklearn version and pipeline structure
    # prep is ColumnTransformer
    prep = pipeline.named_steps['prep']
    
    output_features = []
    
    # Iterate through transformers
    # [('cat', OneHotEncoder, ['type']), ('remainder', 'passthrough', [...])]
    
    for name, trans, cols in prep.transformers_:
        if name == 'cat':
            # OneHotEncoder
            if hasattr(trans, "get_feature_names_out"):
                feats = trans.get_feature_names_out(cols)
                output_features.extend(feats)
            elif hasattr(trans, "categories_"):
                 # Manual reconstruction if get_feature_names_out fails
                 for i, cat_list in enumerate(trans.categories_):
                     col_name = cols[i]
                     for cat in cat_list:
                         output_features.append(f"{col_name}_{cat}")
        elif name == 'remainder' or name == 'nume': # 'nume' based on previous checks it might not be named 'remainder'
             # Passthrough or Scaler
             # If trans is 'passthrough', cols is the list
             output_features.extend(cols)
        else:
             # Just append col names for safety
             output_features.extend(cols)
             
    return output_features

try:
    model_path = Path(r"c:\caffeine\41_ml_fraud\model_fraud.joblib")
    pipeline = joblib.load(model_path)
    
    feats = get_feature_names(pipeline)
    print(f"Total Features extracted: {len(feats)}")
    # print(feats)
    
    estimator = pipeline.named_steps["model"]
    imps = estimator.feature_importances_
    
    if len(feats) == len(imps):
        df = pd.DataFrame({"Feature": feats, "Importance": imps})
        df = df.sort_values("Importance", ascending=False)
        print("\n🏆 Mapped Feature Importance:")
        print(df.head(15).to_string(index=False))
    else:
        print(f"Length mismatch: {len(feats)} vs {len(imps)}")
        # Try to debug
        print("Feature list:", feats)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
