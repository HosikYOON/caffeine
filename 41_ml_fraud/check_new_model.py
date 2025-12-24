
import sys
import os
import joblib
from pathlib import Path

# Load model
model_path = Path(r"c:\caffeine\41_ml_fraud\model_fraud.joblib")
try:
    model = joblib.load(model_path)
    print(f"✅ Model loaded successfully: {model}")
    
    if hasattr(model, "feature_names_in_"):
        print(f"📊 Features expected by model ({len(model.feature_names_in_)}):")
        print(model.feature_names_in_)
    else:
        print("⚠️ Model does not store feature names explicitly (might be a pipeline without named steps exposing them).")
        # Try to drill down if pipeline
        if hasattr(model, "named_steps"):
            print("Pipeline steps:", model.named_steps.keys())
            
except Exception as e:
    print(f"❌ Failed to load model: {e}")
