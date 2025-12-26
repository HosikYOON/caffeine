import pandas as pd
import numpy as np
import math
from datetime import datetime
from typing import List
from app.db.model.transaction import Transaction

class FraudPreprocessor:
    """
    Fraud Detection Model (XGBoost) Preprocessor
    Converts Transaction objects into the feature vector expected by the model.
    """
    
    def __init__(self):
        # PaySim simulation started roughly at step 1. 
        # We can map real time to steps if needed, or just use cyclic features.
        # Here we mock 'step' as hour variance or similar.
        pass

    def preprocess_transaction(self, tx: Transaction, history: List[Transaction]) -> pd.DataFrame:
        """
        Single transaction preprocessing.
        
        Args:
            tx: Current transaction to predict
            history: List of recent transactions (for z-score, etc.)
            
        Returns:
            DataFrame with 1 row and all required features.
        """
        features = {}
        
        # 1. Time Features
        dt = tx.transaction_time
        # PaySim 'step' is usually hours. We'll approximate it as "hour of month" or global counter if possible.
        # For this implementation, we'll try to keep it simple.
        # If the model relies heavily on 'step' being a specific range, this might be an issue.
        # But 'hour', 'dow' are also present.
        
        features['step'] = dt.day * 24 + dt.hour # Simple monotonic increasing step within a month
        features['day'] = dt.day
        features['hour'] = dt.hour
        features['dow'] = dt.weekday()
        
        # Cyclic time features
        features['hour_sin'] = np.sin(2 * np.pi * dt.hour / 24.0)
        features['hour_cos'] = np.cos(2 * np.pi * dt.hour / 24.0)
        
        # 2. Amount Features
        amount = float(tx.amount)
        # Avoid log(0)
        amount_log = np.log1p(abs(amount))
        features['amount_log'] = amount_log
        
        # Z-scores (requires history)
        # We need history of amounts to calculate mean/std
        if not history:
            amounts = [amount]
        else:
            amounts = [float(t.amount) for t in history]
            # Ensure current tx amount is comprised if not in history
            # But history usually implies 'past'. preprocessing should consider 'context'.
            # If 'history' excludes 'tx', we append it for stats? 
            # Usually Z-score is (Current - Mean_Past) / Std_Past
            pass
            
        # Filter history to recent N
        # This is a simplified calculation. Real-time system might need Redis.
        past_amounts = np.array(amounts)
        
        # Rolling stats (approximate with entire history provided)
        mean = np.mean(past_amounts)
        std = np.std(past_amounts) + 1e-9
        
        features['amount_log_z3'] = (amount_log - np.log1p(mean)) / (np.log1p(std) + 1e-9) # Approximation
        features['amount_log_z5'] = features['amount_log_z3'] # Placeholder if distinct windows not avail
        features['amount_log_z10'] = features['amount_log_z3']
        features['amount_log_iqr_z'] = 0 # Complex to calc on fly without robust history
        
        features['amount_bin'] = int(amount / 10000) # Arbitrary binning
        features['amount_rank_pct'] = 0.5 # Placeholder
        
        # 3. Type Features
        # Map our categories/types to PaySim types: PAYMENT, TRANSFER, CASH_OUT, DEBIT, CASH_IN
        # Our types: '체크', '신용' -> maybe mapped to PAYMENT?
        # Or category based? 
        # PaySim is mobile money. 
        # Let's map: 
        #   Transfer/Send -> TRANSFER
        #   Payment -> PAYMENT
        #   Cash -> CASH_OUT
        
        # For now, default to PAYMENT as it's most common for card txs
        tx_type = 'PAYMENT'
        
        features['type_PAYMENT'] = 1 if tx_type == 'PAYMENT' else 0
        features['type_CASH_IN'] = 0
        features['type_TRANSFER'] = 0
        features['type_CASH_OUT'] = 0
        features['type_DEBIT'] = 0
        
        # Change rates (requires history of types)
        features['type_change_rate2'] = 0
        features['type_change_rate3'] = 0
        features['type_change_rate5'] = 0
        features['type_change_rate10'] = 0

        # Fill missing columns expected by model with 0
        # This corresponds to "one_hot_expanded_count" in metadata
        
        # Convert to DataFrame
        df = pd.DataFrame([features])
        
        # Ensure all columns from metadata exist (we'll implement robustness in loader)
        return df

    def get_feature_names(self):
        # Based on metadata
        return [
            "step", "day", "hour", "dow", "hour_sin", "hour_cos",
            "amount_log", "amount_log_z3", "amount_log_z5", "amount_log_z10", "amount_log_iqr_z", "amount_bin", "amount_rank_pct",
            "type_change_rate2", "type_change_rate3", "type_change_rate5", "type_change_rate10",
            "type_PAYMENT", "type_CASH_IN", "type_TRANSFER", "type_CASH_OUT", "type_DEBIT"
        ]
