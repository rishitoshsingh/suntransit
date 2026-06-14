"""Small shared helpers."""
import math
import pandas as pd


def clean_records(records: list[dict]) -> list[dict]:
    """Replace NaN/Inf with None so the JSON is valid for the browser."""
    def v(x):
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return None
        return x
    return [{k: v(val) for k, val in row.items()} for row in records]


def remove_outliers(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if df.empty or df[col].dropna().empty:
        return df
    q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
    iqr = q3 - q1
    return df[(df[col] >= q1 - 1.5 * iqr) & (df[col] <= q3 + 1.5 * iqr)]
