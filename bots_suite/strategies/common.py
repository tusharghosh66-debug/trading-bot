"""
Common Data & OHLCV Utilities for Trading Strategies
Safely handles yfinance MultiIndex columns and series conversion.
"""

import pandas as pd
import numpy as np


def clean_ohlcv(df):
    """Flattens MultiIndex columns and ensures lowercase names."""
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower() for col in df.columns]
    else:
        df.columns = [str(col).lower() for col in df.columns]

    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            # If still a dataframe column (duplicate names)
            if isinstance(df[col], pd.DataFrame):
                df[col] = df[col].iloc[:, 0]
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df.dropna()


def to_float(val):
    """Safely extracts a single Python float from pandas scalar or 1-item series."""
    if hasattr(val, 'item'):
        try:
            return float(val.item())
        except Exception:
            pass
    if hasattr(val, 'values'):
        try:
            return float(val.values[0])
        except Exception:
            pass
    return float(val)
