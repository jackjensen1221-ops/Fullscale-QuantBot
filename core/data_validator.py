import pandas as pd
import numpy as np

class DataValidator:
    @staticmethod
    def clean_and_validate(df, symbol="Unknown"):
        """
        Validates historical price/volume matrices for NaNs, infs, 
        and look-ahead anomalies.
        """
        if df is None or df.empty:
            print(f"   ❌ [Data Integrity Error]: Empty dataframe received for {symbol}.")
            return None

        # Check for infinite values or NaNs
        if df.isin([np.inf, -np.inf]).any().any():
            print(f"   ⚠️ [Data Warning]: Infinite values detected in data for {symbol}. Cleaning...")
            df.replace([np.inf, -np.inf], np.nan, inplace=True)

        # Forward fill minor gaps, drop trailing NaNs to prevent look-ahead corruption
        df = df.ffill().dropna()

        if len(df) < 10:
            print(f"   ❌ [Data Error]: Insufficient clean history rows ({len(df)}) for {symbol}.")
            return None

        return df
