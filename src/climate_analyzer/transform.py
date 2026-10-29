"""Data Transformation, Aggregation, and Climatological Baseline Module.

Author: Akash Das
"""

import numpy as np
import pandas as pd


def interpolate_bounded_gaps(series: pd.Series, max_gap: int) -> pd.Series:
    """Linearly interpolate missing values only if the entire consecutive gap length is <= max_gap.

    Prevents partial interpolation of long missing periods (e.g. 7-day gap in May 1869).
    """
    if max_gap <= 0:
        return series.copy()
    is_na = series.isna()
    if not is_na.any():
        return series.copy()
    gap_id = (~is_na).cumsum()
    gap_sizes = is_na.groupby(gap_id).transform("sum")
    fillable_mask = is_na & (gap_sizes <= max_gap) & (gap_sizes > 0)
    if fillable_mask.any():
        interpolated = series.interpolate(method="linear")
        result = series.copy()
        result[fillable_mask] = interpolated[fillable_mask]
        return result
    return series.copy()


def clean_daily_observations(
    df: pd.DataFrame,
    max_gap_interpolation: int = 3,
) -> pd.DataFrame:
    """Clean daily observations while preserving genuine meteorological extremes.

    Args:
        df: Raw daily observations DataFrame.
        max_gap_interpolation: Maximum consecutive missing days to interpolate.
            Gaps larger than this limit are strictly preserved as unobserved NaNs.

    Returns:
        Clean daily DataFrame with temporal continuity.
    """
    clean_df = df.copy()
    clean_df.sort_values("date", inplace=True)
    clean_df.drop_duplicates(subset=["date"], inplace=True)

    # Reindex across complete calendar day range
    min_date = clean_df["date"].min()
    max_date = clean_df["date"].max()
    full_dates = pd.date_range(min_date, max_date, freq="D", name="date")
    clean_df = clean_df.set_index("date").reindex(full_dates).reset_index()

    # Recompute calendar components
    clean_df["year"] = clean_df["date"].dt.year
    clean_df["month"] = clean_df["date"].dt.month
    clean_df["day"] = clean_df["date"].dt.day

    # Fill metadata columns
    for col in ["station", "name", "latitude", "longitude", "elevation"]:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].ffill().bfill()

    # Identify and flag historical inverted records (TMIN > TMAX) without altering source values
    clean_df["is_inverted_temp"] = (
        clean_df["tmax"].notna() & clean_df["tmin"].notna() & (clean_df["tmin"] > clean_df["tmax"])
    )

    # Carefully interpolate small isolated gaps (<= max_gap_interpolation only)
    clean_df["tmax"] = interpolate_bounded_gaps(clean_df["tmax"], max_gap=max_gap_interpolation)
    clean_df["tmin"] = interpolate_bounded_gaps(clean_df["tmin"], max_gap=max_gap_interpolation)
    clean_df["tavg"] = (clean_df["tmax"] + clean_df["tmin"]) / 2.0
    # Missing precipitation days are filled with 0.0 (no precipitation reported)
    clean_df["prcp"] = clean_df["prcp"].fillna(0.0)

    clean_df.reset_index(drop=True, inplace=True)
    return clean_df


def aggregate_to_monthly(
    daily_df: pd.DataFrame,
    min_days_per_month: int = 25,
    reindex_full_calendar: bool = True,
) -> pd.DataFrame:
    """Aggregate daily meteorological observations into monthly climate summaries.

    Args:
        daily_df: Clean daily observations DataFrame.
        min_days_per_month: Minimum valid observation days required to retain month.
        reindex_full_calendar: Whether to reindex onto full monthly calendar range
            to ensure lag calculations align with exact calendar months without phase distortion.

    Returns:
        pd.DataFrame of monthly aggregated climate indicators.
    """
    grouped = daily_df.groupby(["year", "month"])

    monthly = grouped.agg(
        tavg_mean=("tavg", "mean"),
        tmax_mean=("tmax", "mean"),
        tmin_mean=("tmin", "mean"),
        tmax_extreme=("tmax", "max"),
        tmin_extreme=("tmin", "min"),
        prcp_total=("prcp", "sum"),
        days_valid=("tavg", "count"),
    ).reset_index()

    # Retain only months that meet the completeness threshold
    monthly = monthly[monthly["days_valid"] >= min_days_per_month].copy()
    monthly["date"] = pd.to_datetime(
        monthly["year"].astype(str) + "-" + monthly["month"].astype(str) + "-01"
    )

    if reindex_full_calendar and not monthly.empty:
        full_dates = pd.date_range(monthly["date"].min(), monthly["date"].max(), freq="MS", name="date")
        monthly = monthly.set_index("date").reindex(full_dates).reset_index()
        monthly["year"] = monthly["date"].dt.year
        monthly["month"] = monthly["date"].dt.month

    monthly.sort_values(["year", "month"], inplace=True)
    monthly.reset_index(drop=True, inplace=True)
    return monthly


def compute_climatological_anomalies(
    monthly_df: pd.DataFrame,
    baseline_start: int = 1951,
    baseline_end: int = 1980,
) -> pd.DataFrame:
    """Compute monthly temperature anomalies relative to a fixed baseline period.

    Uses standard reference baseline (1951-1980) calculated separately for each
    of the 12 calendar months to remove annual seasonal cycles.

    Args:
        monthly_df: Monthly climate summary DataFrame.
        baseline_start: First year of reference period.
        baseline_end: Last year of reference period.

    Returns:
        DataFrame enriched with monthly baseline means and 'monthly_anomaly'.
    """
    df = monthly_df.copy()

    # Calculate baseline mean for each of the 12 calendar months
    baseline_records = df[(df["year"] >= baseline_start) & (df["year"] <= baseline_end)]
    if baseline_records.empty:
        raise ValueError(
            f"No monthly records found within baseline period [{baseline_start}, {baseline_end}]."
        )

    monthly_baselines = (
        baseline_records.groupby("month")["tavg_mean"]
        .mean()
        .to_dict()
    )

    df["baseline_tavg"] = df["month"].map(monthly_baselines)
    df["monthly_anomaly"] = df["tavg_mean"] - df["baseline_tavg"]

    return df


def aggregate_to_annual(
    monthly_df: pd.DataFrame,
    min_months_per_year: int = 11,
) -> pd.DataFrame:
    """Aggregate monthly anomalies to an annual climate series.

    Args:
        monthly_df: DataFrame with 'year', 'month', 'monthly_anomaly', and 'prcp_total'.
        min_months_per_year: Completeness threshold in valid months.

    Returns:
        Annual climate summary DataFrame.
    """
    grouped = monthly_df.groupby("year")
    annual = grouped.agg(
        annual_tavg=("tavg_mean", "mean"),
        annual_anomaly=("monthly_anomaly", "mean"),
        annual_prcp=("prcp_total", "sum"),
        months_count=("tavg_mean", "count"),
    ).reset_index()

    annual = annual[annual["months_count"] >= min_months_per_year].copy()
    annual.sort_values("year", inplace=True)
    annual.reset_index(drop=True, inplace=True)
    return annual
