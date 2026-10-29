"""Unit Tests for Climate Data Validation and Transformation Modules.

Author: Akash Das
"""

import pytest
import numpy as np
import pandas as pd
from climate_analyzer.validation import validate_ghcn_dataframe, ClimateDataValidationError
from climate_analyzer.transform import (
    clean_daily_observations,
    aggregate_to_monthly,
    compute_climatological_anomalies,
    aggregate_to_annual,
)


def create_sample_daily_df() -> pd.DataFrame:
    """Helper to generate a small controlled daily observations DataFrame."""
    dates = pd.date_range("1960-01-01", "1960-03-31", freq="D")
    n = len(dates)
    return pd.DataFrame({
        "station": ["USW00094728"] * n,
        "name": ["TEST STATION"] * n,
        "date": dates,
        "year": dates.year,
        "month": dates.month,
        "day": dates.day,
        "tmax": np.linspace(5.0, 15.0, n),
        "tmin": np.linspace(-5.0, 5.0, n),
        "tavg": np.linspace(0.0, 10.0, n),
        "prcp": np.abs(np.sin(np.arange(n))) * 5.0,
    })


def test_validate_ghcn_dataframe_valid():
    df = create_sample_daily_df()
    res = validate_ghcn_dataframe(df)
    assert res["is_valid"] is True
    assert res["total_records"] == len(df)


def test_validate_ghcn_dataframe_inverted_temps():
    df = create_sample_daily_df()
    # Invert TMIN > TMAX on row 0
    df.loc[0, "tmin"] = 30.0
    df.loc[0, "tmax"] = 10.0
    res = validate_ghcn_dataframe(df, raise_on_error=False)
    assert any("TMIN > TMAX" in w for w in res["warnings"])


def test_validate_ghcn_dataframe_negative_prcp():
    df = create_sample_daily_df()
    df.loc[0, "prcp"] = -10.0
    with pytest.raises(ClimateDataValidationError, match="negative precipitation"):
        validate_ghcn_dataframe(df, raise_on_error=True)


def test_clean_daily_observations():
    df = create_sample_daily_df()
    # Introduce a 1-day gap by dropping Jan 15
    df = df[df["date"] != pd.Timestamp("1960-01-15")].copy()
    cleaned = clean_daily_observations(df, max_gap_interpolation=2)
    # The gap should be filled
    assert len(cleaned) == 91
    assert pd.Timestamp("1960-01-15") in cleaned["date"].values
    assert not cleaned.loc[cleaned["date"] == "1960-01-15", "tavg"].isna().any()


def test_clean_daily_bounded_gap_preservation():
    """Verify that multi-day gaps exceeding max_gap_interpolation are NOT interpolated."""
    df = create_sample_daily_df()
    # Introduce a 5-day gap (Jan 10 to Jan 14)
    gap_dates = pd.date_range("1960-01-10", "1960-01-14", freq="D")
    df = df[~df["date"].isin(gap_dates)].copy()
    cleaned = clean_daily_observations(df, max_gap_interpolation=3)
    # The 5-day gap should NOT be interpolated
    assert len(cleaned) == 91
    assert cleaned.loc[cleaned["date"].isin(gap_dates), "tmax"].isna().sum() == 5
    assert cleaned.loc[cleaned["date"].isin(gap_dates), "tmin"].isna().sum() == 5


def test_clean_daily_inversion_flagging_without_mutation():
    """Verify that historical TMIN > TMAX records are flagged without altering source values."""
    df = create_sample_daily_df()
    df.loc[0, "tmax"] = 5.0
    df.loc[0, "tmin"] = 12.0
    cleaned = clean_daily_observations(df)
    assert cleaned.loc[0, "is_inverted_temp"] == True
    # Values are preserved as recorded, not swapped
    assert cleaned.loc[0, "tmax"] == 5.0
    assert cleaned.loc[0, "tmin"] == 12.0


def test_aggregate_to_monthly_and_baseline():
    # Create 3 years of daily observations (1951, 1952, 1953)
    dates = pd.date_range("1951-01-01", "1953-12-31", freq="D")
    df = pd.DataFrame({
        "station": ["USW00094728"] * len(dates),
        "name": ["TEST STATION"] * len(dates),
        "date": dates,
        "year": dates.year,
        "month": dates.month,
        "day": dates.day,
        "tmax": np.ones(len(dates)) * 20.0,
        "tmin": np.ones(len(dates)) * 10.0,
        "tavg": np.ones(len(dates)) * 15.0,
        "prcp": np.zeros(len(dates)),
    })

    monthly = aggregate_to_monthly(df, min_days_per_month=25)
    assert len(monthly) == 36  # 3 years * 12 months
    assert np.isclose(monthly["tavg_mean"].iloc[0], 15.0)

    # Compute anomaly against baseline
    anom_df = compute_climatological_anomalies(monthly, baseline_start=1951, baseline_end=1953)
    assert "monthly_anomaly" in anom_df.columns
    # Since all values are 15.0, anomaly should be 0.0
    assert np.allclose(anom_df["monthly_anomaly"], 0.0)

    # Annual aggregation
    annual = aggregate_to_annual(anom_df, min_months_per_year=11)
    assert len(annual) == 3
    assert np.isclose(annual["annual_tavg"].iloc[0], 15.0)
