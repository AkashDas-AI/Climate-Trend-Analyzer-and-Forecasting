"""Unit Tests for Statistical Trend and Hypothesis Testing Modules.

Author: Akash Das
"""

import pytest
import numpy as np
import pandas as pd
from climate_analyzer.analysis import (
    calculate_linear_trend,
    mann_kendall_test,
    sens_slope,
    calculate_decadal_summary,
)


def test_linear_trend_exact_line():
    years = np.arange(1950, 2000)
    anomalies = 0.02 * years - 39.0

    res = calculate_linear_trend(years, anomalies)
    assert np.isclose(res["slope_per_year"], 0.02, atol=1e-5)
    assert np.isclose(res["decadal_rate"], 0.20, atol=1e-5)
    assert np.isclose(res["r_squared"], 1.0, atol=1e-5)
    assert res["p_value"] < 0.001


def test_mann_kendall_strictly_increasing():
    series = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    res = mann_kendall_test(series)
    assert res["trend"] == "increasing"
    assert res["z"] > 0
    assert res["is_significant"] is True
    assert res["s"] == 45


def test_mann_kendall_strictly_decreasing():
    series = np.array([1.0, 0.8, 0.6, 0.4, 0.2, 0.0])
    res = mann_kendall_test(series)
    assert res["trend"] == "decreasing"
    assert res["z"] < 0
    assert res["is_significant"] is True


def test_sens_slope_robustness():
    years = np.arange(2000, 2010)
    anomalies = 0.05 * (years - 2000)
    anomalies[4] = 9.99

    res = sens_slope(years, anomalies)
    assert np.isclose(res["sens_slope_per_year"], 0.05, atol=0.01)
    assert np.isclose(res["sens_decadal_rate"], 0.50, atol=0.10)


def test_calculate_decadal_summary():
    df = pd.DataFrame({
        "year": [1980, 1985, 1990, 1995],
        "annual_tavg": [10.0, 11.0, 12.0, 13.0],
    })
    summary = calculate_decadal_summary(df, value_col="annual_tavg")
    assert len(summary) == 2
    assert np.isclose(summary.loc[summary["decade"] == 1980, "mean_annual_tavg"].iloc[0], 10.5)
    assert np.isclose(summary.loc[summary["decade"] == 1990, "mean_annual_tavg"].iloc[0], 12.5)


def test_linear_trend_hac_standard_error():
    """Verify that Newey-West HAC standard error is correctly calculated."""
    years = np.arange(1900, 2000)
    # Series with positive autocorrelation in errors
    np.random.seed(42)
    err = np.zeros(len(years))
    for t in range(1, len(years)):
        err[t] = 0.6 * err[t - 1] + np.random.normal(0, 0.5)
    anomalies = 0.015 * (years - 1900) + err

    res = calculate_linear_trend(years, anomalies)
    assert "hac_std_err" in res
    assert "hac_decadal_std_err" in res
    assert "hac_std_err_fs" in res
    assert "hac_decadal_std_err_fs" in res
    assert "hac_t_stat" in res
    assert "hac_t_stat_fs" in res
    assert "hac_p_value" in res
    assert "p_value_bound" in res
    assert "hac_df" in res
    assert res["hac_df"] == len(years) - 2
    assert res["hac_std_err"] > 0
    assert res["hac_std_err_fs"] > res["hac_std_err"]
    assert np.isclose(res["hac_decadal_std_err"], res["hac_std_err"] * 10.0)
    assert np.isclose(res["hac_decadal_std_err_fs"], res["hac_std_err_fs"] * 10.0)
    assert res["decadal_rate"] > 0.10


def test_mann_kendall_autocorrelation_adjustment():
    """Verify that serial autocorrelation adjusts variance and Z score appropriately."""
    # Create an autocorrelated trending series
    np.random.seed(42)
    n = 60
    series = np.zeros(n)
    for t in range(1, n):
        series[t] = 0.02 * t + 0.5 * series[t - 1] + np.random.normal(0, 0.2)

    res = mann_kendall_test(series, adjust_autocorr=True)
    assert res["rho1"] > 0
    assert res["vif"] > 1.0
    assert res["var_s_adj"] > res["var_s"]
    assert res["z_adj"] < res["z"]
    assert "rho1_detrended" in res
    assert "vif_detrended" in res
    assert "z_adj_detrended" in res
    assert res["trend_adj"] == "increasing"
    assert res["is_significant_adj"] is True
    assert isinstance(res["p_value_adj_bound"], str)

    # Strongly trending series with tiny p-value formatted as scientific bound
    strong_series = np.linspace(0, 10, 50) + np.random.normal(0, 0.1, 50)
    res_strong = mann_kendall_test(strong_series)
    assert "<" in res_strong["p_value_bound"] or "e" in res_strong["p_value_bound"]


def test_mann_kendall_ties_and_constant():
    """Verify Mann-Kendall tie adjustment and constant series edge case."""
    # Series with multiple ties
    tied_series = np.array([1.0, 2.0, 2.0, 3.0, 3.0, 3.0, 4.0, 5.0])
    res_tied = mann_kendall_test(tied_series)
    assert res_tied["s"] > 0
    assert res_tied["trend"] == "increasing"
    assert res_tied["var_s"] > 0

    # Constant series
    const_series = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
    res_const = mann_kendall_test(const_series)
    assert res_const["s"] == 0
    assert res_const["z"] == 0.0
    assert res_const["trend"] == "no trend"
    assert res_const["is_significant"] is False


def test_linear_trend_and_sens_constant_shift_invariance():
    """Verify that shifting values by an arbitrary constant leaves OLS and Sen slopes mathematically invariant."""
    years = np.arange(1920, 2020)
    rng = np.random.default_rng(99)
    y = 12.0 + 0.015 * (years - 1920) + rng.normal(0, 0.4, len(years))

    base_ols = calculate_linear_trend(years, y)
    base_sens = sens_slope(years, y)
    base_mk = mann_kendall_test(y)

    for c in [-15.2, -1.0, 0.42, 10.0]:
        y_shifted = y + c
        s_ols = calculate_linear_trend(years, y_shifted)
        s_sens = sens_slope(years, y_shifted)
        s_mk = mann_kendall_test(y_shifted)

        # OLS slope, R2, and HAC SE must be invariant
        assert np.isclose(s_ols["slope_per_year"], base_ols["slope_per_year"], atol=1e-13)
        assert np.isclose(s_ols["decadal_rate"], base_ols["decadal_rate"], atol=1e-12)
        assert np.isclose(s_ols["r_squared"], base_ols["r_squared"], atol=1e-12)
        assert np.isclose(s_ols["hac_decadal_std_err"], base_ols["hac_decadal_std_err"], atol=1e-12)
        assert np.isclose(s_ols["hac_t_stat"], base_ols["hac_t_stat"], atol=1e-12)

        # Sen's slope must be invariant
        assert np.isclose(s_sens["sens_decadal_rate"], base_sens["sens_decadal_rate"], atol=1e-13)

        # Mann-Kendall statistics must be invariant
        assert s_mk["s"] == base_mk["s"]
        assert np.isclose(s_mk["z"], base_mk["z"], atol=1e-13)
        assert s_mk["trend"] == base_mk["trend"]



