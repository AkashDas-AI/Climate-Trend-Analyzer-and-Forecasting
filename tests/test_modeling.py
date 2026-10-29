"""Unit Tests for Machine Learning Modeling and Evaluation Module.

Author: Akash Das
"""

import pytest
import numpy as np
import pandas as pd
from climate_analyzer.modeling import (
    temporal_train_test_split,
    compute_forecast_metrics,
    train_and_evaluate_climate_model,
)
from climate_analyzer.features import engineer_monthly_features


def test_temporal_train_test_split_no_leakage():
    df = pd.DataFrame({
        "year": list(range(1980, 2011)),
        "tavg_mean": np.linspace(10.0, 15.0, 31),
    })

    train, test = temporal_train_test_split(df, split_year=2000, time_col="year")
    assert train["year"].max() == 2000
    assert test["year"].min() == 2001
    assert len(train) + len(test) == len(df)


def test_temporal_train_test_split_empty_raises():
    df = pd.DataFrame({"year": [1990, 1991], "tavg_mean": [10.0, 11.0]})
    with pytest.raises(ValueError, match="resulted in an empty partition"):
        temporal_train_test_split(df, split_year=2050, time_col="year")


def test_compute_forecast_metrics():
    y_true = np.array([10.0, 12.0, 14.0])
    y_pred = np.array([10.2, 11.8, 14.1])

    metrics = compute_forecast_metrics(y_true, y_pred)
    assert metrics["rmse"] > 0
    assert metrics["mae"] > 0
    assert metrics["r2"] > 0.95


def test_temporal_train_test_split_target_date_boundary():
    """Assert that splitting by target_year strictly isolates training targets to <= split_year."""
    dates = pd.date_range("1999-01-01", "2002-12-01", freq="MS")
    df = pd.DataFrame({
        "date": dates,
        "year": dates.year,
        "month": dates.month,
        "tavg_mean": np.linspace(10.0, 15.0, len(dates)),
        "prcp_total": np.ones(len(dates)) * 50.0,
    })
    feat_df = engineer_monthly_features(df)
    valid = feat_df.dropna(subset=["target_next_tavg"]).copy()

    train, test = temporal_train_test_split(valid, split_year=2000)

    # Feature origin assertions
    assert train["date"].max() == pd.Timestamp("2000-11-01")
    assert test["date"].min() == pd.Timestamp("2000-12-01")

    # Target date assertions
    assert train["target_year"].max() == 2000
    assert test["target_year"].min() == 2001
    assert train["target_date"].max() == pd.Timestamp("2000-12-01")
    assert test["target_date"].min() == pd.Timestamp("2001-01-01")

    # Zero target overlap
    assert len(train) + len(test) == len(valid)
    assert set(train["target_date"]).isdisjoint(set(test["target_date"]))


def test_train_and_evaluate_climate_model_baselines():
    # Build 10 years of synthetic monthly sine temperature data for testing
    months = np.tile(np.arange(1, 13), 10)
    years = np.repeat(np.arange(1990, 2000), 12)
    # Seasonal cycle + slight warming
    base_temps = 10.0 + 8.0 * np.sin(2 * np.pi * (months - 4) / 12) + 0.05 * (years - 1990)

    dates = pd.to_datetime(years.astype(str) + "-" + months.astype(str) + "-01")
    df = pd.DataFrame({
        "date": dates,
        "year": years,
        "month": months,
        "tavg_mean": base_temps,
        "prcp_total": np.ones(len(years)) * 50.0,
        "monthly_anomaly": np.zeros(len(years)),
    })

    feat_df = engineer_monthly_features(df)
    res = train_and_evaluate_climate_model(feat_df, split_year=1997)

    assert "metrics" in res
    assert "ml_model" in res["metrics"]
    assert "climatology_baseline" in res["metrics"]
    assert "persistence_baseline" in res["metrics"]

    # Verify metrics exist and are non-negative
    assert res["metrics"]["ml_model"]["rmse"] >= 0
    assert res["metrics"]["climatology_baseline"]["rmse"] >= 0
    assert res["metrics"]["persistence_baseline"]["rmse"] >= 0

    # Predictions structure
    assert not res["predictions"].empty
    assert "pred_ml" in res["predictions"].columns
    assert "residual_ml" in res["predictions"].columns

    # Verify boundary dates and sample reconciliation
    assert res["train_target_range"][1].startswith("1997")
    assert res["test_target_range"][0].startswith("1998")
    assert res["train_samples"] > 0
    assert res["test_samples"] > 0


def test_real_data_boundary_dates_and_leakage():
    """Assert exact feature and target boundary dates on processed real climate series if present."""
    from pathlib import Path
    data_path = Path("data/processed/USW00094728_monthly_features.csv")
    if not data_path.exists():
        pytest.skip("Processed monthly climate data file not present for offline test.")

    monthly_df = pd.read_csv(data_path)
    res = train_and_evaluate_climate_model(monthly_df, split_year=2000)

    # Exact sample counts under target-date split
    assert res["train_samples"] == 1570
    assert res["test_samples"] == 309

    # Exact feature origin boundaries
    assert res["train_feature_range"] == ("1870-01", "2000-11")
    assert res["test_feature_range"] == ("2000-12", "2026-08")

    # Exact target evaluation boundaries
    assert res["train_target_range"] == ("1870-02", "2000-12")
    assert res["test_target_range"] == ("2001-01", "2026-09")

    # Assert test predictions dataframe has exactly 309 rows
    preds = res["predictions"]
    assert len(preds) == 309
    assert preds["date"].iloc[0] == "2000-12-01"  # feature month for Jan 2001 target
    assert preds["date"].iloc[-1] == "2026-08-01"  # feature month for Sep 2026 target
