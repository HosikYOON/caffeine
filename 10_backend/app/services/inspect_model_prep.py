
import joblib
from pathlib import Path

try:
    model_path = Path(r"c:\caffeine\41_ml_fraud\model_fraud.joblib")
    pipeline = joblib.load(model_path)
    
    prep = pipeline.named_steps['prep']
    print("Preprocessor:", prep)
    
    # Inspect transformers
    if hasattr(prep, "transformers_"):
        for name, trans, cols in prep.transformers_:
            print(f"\nTransformer: {name}")
            print(f"   Type: {type(trans)}")
            print(f"   Columns: {cols}")
            
            if hasattr(trans, "categories_"):
                print(f"   Categories ({len(trans.categories_[0])}): {trans.categories_[0][:10]}...")
            elif hasattr(trans, "vocabulary_"):
                print(f"   Vocab size: {len(trans.vocabulary_)}")

except Exception as e:
    print(f"Error: {e}")
