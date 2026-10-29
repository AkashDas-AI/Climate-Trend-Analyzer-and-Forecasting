"""Feature Engineering Module for Real Climate Analysis and Predictive Modeling.

Constructs cyclical calendar features, autoregressive lookback lags, and rolling statistical indicators.

Author: Akash Das
"""

import numpy as np
import pandas as pd


def engineer_monthly_features(
    monthly_df: pd.DataFrame,
    lags: tuple[int, ...] = (1, 2, 12),
    rolling_windows: tuple[int, ...] = (3, 12),
) -> pd.DataFrame:
    """Compute temporal predictor features for next-month temperature modeling.

    Strictly avoids future-data leakage: all features at index t are computed
    using observations at or before index t.

    Args:
        monthly_df: Monthly climate indicators DataFrame.
        lags: Lookback intervals in months (e.g. 1, 2, 12).
        rolling_windows: Window sizes in months for rolling mean/std.

    Returns:
        DataFrame enriched with features and 'target_next_tavg'.
    """
    feat_df = monthly_df.copy()
    feat_df.sort_values(["year", "month"], inplace=True)
    feat_df.reset_index(drop=True, inplace=True)

    # Cyclical Calendar Month Encodings (Period = 12 months)
    feat_df["sin_month"] = np.sin(2.0 * np.pi * feat_df["month"] / 12.0)
    feat_df["cos_month"] = np.cos(2.0 * np.pi * feat_df["month"] / 12.0)

    # Continuous Year Fraction
    feat_df["time_fraction"] = feat_df["year"] + (feat_df["month"] - 1) / 12.0

    # Decade Indicator
    feat_df["decade"] = (feat_df["year"] // 10) * 10

    # Autoregressive Temperature & Precipitation Lags
    for lag in lags:
        feat_df[f"tavg_lag_{lag}"] = feat_df["tavg_mean"].shift(lag)
        if "monthly_anomaly" in feat_df.columns:
            feat_df[f"anomaly_lag_{lag}"] = feat_df["monthly_anomaly"].shift(lag)

    if "prcp_total" in feat_df.columns:
        feat_df["prcp_lag_1"] = feat_df["prcp_total"].shift(1)
    else:
        feat_df["prcp_lag_1"] = np.nan

    # Rolling Means and Volatilities
    for w in rolling_windows:
        feat_df[f"rolling_tavg_{w}m"] = (
            feat_df["tavg_mean"]
            .rolling(window=w, min_periods=1)
            .mean()
        )
        if w >= 3:
            feat_df[f"rolling_std_{w}m"] = (
                feat_df["tavg_mean"]
                .rolling(window=w, min_periods=2)
                .std()
                .fillna(0.0)
            )

    # Prediction Target: Next Month's Average Temperature and Calendar Alignment
    feat_df["target_next_tavg"] = feat_df["tavg_mean"].shift(-1)
    if "date" in feat_df.columns:
        feat_df["target_date"] = pd.to_datetime(feat_df["date"]).shift(-1)
    feat_df["target_year"] = feat_df["year"].shift(-1)
    feat_df["target_month"] = feat_df["month"].shift(-1)

    return feat_df


def engineer_annual_features(
    annual_df: pd.DataFrame,
    rolling_windows: tuple[int, ...] = (5, 10),
) -> pd.DataFrame:
    """Compute multi-year rolling smoothers on annual climate series.

    Args:
        annual_df: Annual climate summary DataFrame.
        rolling_windows: Window sizes in years.

    Returns:
        Enriched annual DataFrame.
    """
    feat_df = annual_df.copy()
    feat_df.sort_values("year", inplace=True)
    feat_df.reset_index(drop=True, inplace=True)

    feat_df["decade"] = (feat_df["year"] // 10) * 10
    feat_df["cumulative_anomaly"] = feat_df["annual_anomaly"].cumsum()

    for w in rolling_windows:
        feat_df[f"rolling_mean_{w}yr"] = (
            feat_df["annual_anomaly"]
            .rolling(window=w, min_periods=1)
            .mean()
        )
        if w >= 3:
            feat_df[f"rolling_std_{w}yr"] = (
                feat_df["annual_anomaly"]
                .rolling(window=w, min_periods=2)
                .std()
                .fillna(0.0)
            )

    return feat_df
