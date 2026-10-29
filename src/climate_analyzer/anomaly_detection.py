"""Anomaly Detection and Extreme Weather Pattern Identification Module.

Provides Z-score thresholding, IQR dispersion filters, and genuine record ranking.

Author: Akash Das
"""

import numpy as np
import pandas as pd


def detect_zscore_anomalies(
    df: pd.DataFrame,
    column: str = "monthly_anomaly",
    threshold: float = 2.0,
) -> pd.DataFrame:
    """Flag observations exceeding standard normal Z-score cutoff.

    Args:
        df: Input DataFrame.
        column: Numerical column to evaluate.
        threshold: Absolute Z-score cutoff (default 2.0).

    Returns:
        DataFrame with 'z_score' and 'is_anomaly_zscore' columns.
    """
    res_df = df.copy()
    vals = res_df[column]
    mean_val = vals.mean()
    std_val = vals.std(ddof=1)

    if std_val == 0 or np.isnan(std_val):
        res_df["z_score"] = 0.0
        res_df["is_anomaly_zscore"] = False
    else:
        res_df["z_score"] = (vals - mean_val) / std_val
        res_df["is_anomaly_zscore"] = res_df["z_score"].abs() >= threshold

    return res_df


def detect_iqr_anomalies(
    df: pd.DataFrame,
    column: str = "monthly_anomaly",
    multiplier: float = 1.5,
) -> pd.DataFrame:
    """Flag statistical outliers based on Interquartile Range (IQR).

    Args:
        df: Input DataFrame.
        column: Numerical column to evaluate.
        multiplier: IQR range coefficient (default 1.5).

    Returns:
        DataFrame with 'is_anomaly_iqr' column.
    """
    res_df = df.copy()
    vals = res_df[column].dropna()

    q1 = vals.quantile(0.25)
    q3 = vals.quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    res_df["is_anomaly_iqr"] = (res_df[column] < lower_bound) | (res_df[column] > upper_bound)
    return res_df


def get_top_extreme_records(
    df: pd.DataFrame,
    value_col: str = "tavg_mean",
    top_n: int = 10,
    warmest: bool = True,
) -> pd.DataFrame:
    """Extract top N warmest or coolest recorded periods from genuine observations.

    Args:
        df: Climate observations DataFrame.
        value_col: Column to rank by.
        top_n: Number of records to return.
        warmest: True for warmest, False for coolest.

    Returns:
        Ranked subset DataFrame.
    """
    res = df.sort_values(value_col, ascending=not warmest).head(top_n).copy()
    res["rank"] = range(1, len(res) + 1)
    keep_cols = ["rank", "year"]
    for c in ["month", "date", value_col, "annual_tavg", "annual_anomaly", "monthly_anomaly", "z_score"]:
        if c in res.columns and c not in keep_cols:
            keep_cols.append(c)
    return res[keep_cols]


def detect_anomalies(
    df: pd.DataFrame,
    column: str = "monthly_anomaly",
    z_threshold: float = 2.0,
    iqr_multiplier: float = 1.5,
) -> pd.DataFrame:
    """Run all anomaly detection algorithms and return merged outlier flags.

    Args:
        df: Input DataFrame.
        column: Target anomaly or temperature column.
        z_threshold: Standard score cutoff.
        iqr_multiplier: IQR spread factor.

    Returns:
        Annotated DataFrame.
    """
    res = detect_zscore_anomalies(df, column=column, threshold=z_threshold)
    res = detect_iqr_anomalies(res, column=column, multiplier=iqr_multiplier)
    res["is_anomaly_any"] = res["is_anomaly_zscore"] | res["is_anomaly_iqr"]
    return res
