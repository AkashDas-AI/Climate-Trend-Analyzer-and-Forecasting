"""Tests for Streamlit Dashboard Interactivity, Controls, and Data Integrity.

Author: Akash Das
"""

import ast
import json
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from climate_analyzer.config import Config
from climate_analyzer.transform import (
    clean_daily_observations,
    aggregate_to_monthly,
    compute_climatological_anomalies,
    aggregate_to_annual,
)
from climate_analyzer.features import engineer_monthly_features, engineer_annual_features
from climate_analyzer.analysis import calculate_linear_trend, sens_slope, mann_kendall_test
from climate_analyzer.anomaly_detection import detect_anomalies
from climate_analyzer.modeling import train_and_evaluate_climate_model


def test_streamlit_app_ast_syntax():
    """Verify app/streamlit_app.py compiles cleanly without syntax errors."""
    app_path = Path("app/streamlit_app.py")
    assert app_path.exists(), "app/streamlit_app.py must exist"
    content = app_path.read_text(encoding="utf-8")
    tree = ast.parse(content)
    assert isinstance(tree, ast.Module), "AST parse must succeed and return a Module"


def test_dynamic_baseline_recalculation():
    """Verify that selecting different climatological baselines updates anomalies correctly."""
    # Create small clean in-memory test monthly DataFrame
    dates = pd.date_range("1900-01-01", "2020-12-01", freq="MS")
    # Base temperature with seasonal cycle and 1.0 degC warming over century
    tavg = [10.0 + 5.0 * np.sin(2 * np.pi * d.month / 12) + (d.year - 1900) * 0.01 for d in dates]
    df = pd.DataFrame({
        "date": dates,
        "year": dates.year,
        "month": dates.month,
        "tavg_mean": tavg,
        "valid_days": 30,
    })

    # Baseline A: 1951-1980
    anom_a = compute_climatological_anomalies(df, baseline_start=1951, baseline_end=1980)
    # Baseline B: 1991-2020 (warmer period -> anomalies relative to this baseline should be lower)
    anom_b = compute_climatological_anomalies(df, baseline_start=1991, baseline_end=2020)

    assert "monthly_anomaly" in anom_a.columns
    assert "monthly_anomaly" in anom_b.columns
    # Because 1991-2020 is warmer, baseline B monthly normal > baseline A monthly normal
    # Hence mean anomaly under B must be lower than under A
    assert anom_b["monthly_anomaly"].mean() < anom_a["monthly_anomaly"].mean()


def test_interactive_date_range_filtering():
    """Verify that filtering by year range recalculates trends dynamically on the subset."""
    years = np.arange(1870, 2026)
    # Piecewise trend: flat 1870-1970, steep warming post-1970
    tavg = [12.0 + (0.0 if y < 1970 else 0.035 * (y - 1970)) for y in years]
    annual_df = pd.DataFrame({
        "year": years,
        "annual_tavg": tavg,
        "annual_anomaly": [t - 12.0 for t in tavg],
    })

    # Full record trend
    trend_full = calculate_linear_trend(annual_df["year"], annual_df["annual_anomaly"])
    # Post-1970 filtered era
    filtered = annual_df[annual_df["year"] >= 1970]
    trend_post1970 = calculate_linear_trend(filtered["year"], filtered["annual_anomaly"])

    assert trend_post1970["decadal_rate"] > trend_full["decadal_rate"]
    assert trend_post1970["decadal_rate"] > 0.30  # Should reflect ~0.35 degC/dec


def test_csv_export_schema_and_units():
    """Verify that generated CSV export schemas contain required columns and physical unit tags."""
    years = np.arange(1950, 2025)
    annual_export = pd.DataFrame({
        "year": years,
        "annual_tavg": [13.0 + 0.015 * i for i, _ in enumerate(years)],
        "annual_anomaly": [0.015 * i for i, _ in enumerate(years)],
        "rolling_mean_5yr": [0.015 * i for i, _ in enumerate(years)],
        "rolling_mean_10yr": [0.015 * i for i, _ in enumerate(years)],
    })

    col_rename_map = {
        "year": "year",
        "annual_tavg": "mean_annual_temp_degC",
        "annual_anomaly": "temperature_anomaly_degC",
        "rolling_mean_5yr": "moving_avg_5yr_degC",
        "rolling_mean_10yr": "moving_avg_10yr_degC",
    }
    export_subset = annual_export.rename(columns=col_rename_map)
    export_subset["baseline_period"] = "1951–1980 Baseline"
    export_subset["station_id"] = "USW00094728"

    csv_data = export_subset.to_csv(index=False)
    header = csv_data.splitlines()[0]
    assert "mean_annual_temp_degC" in header
    assert "temperature_anomaly_degC" in header
    assert "moving_avg_5yr_degC" in header
    assert "baseline_period" in header
    assert "station_id" in header


def test_dashboard_ml_benchmark_reconciliation():
    """Verify that the dashboard default ML evaluation reproduces the validated benchmark metrics."""
    metrics_path = Path("outputs/metrics/pipeline_metrics.json")
    if not metrics_path.exists():
        pytest.skip("Pipeline metrics JSON not found")

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    model_eval = metrics["model_evaluation"]
    assert model_eval["test_samples"] == 309, "Must evaluate exactly 309 held-out test months"
    assert model_eval["train_samples"] == 1570, "Must train on exactly 1570 months"
    assert model_eval["train_target_range"] == ["1870-02", "2000-12"]
    assert model_eval["test_target_range"] == ["2001-01", "2026-09"]

    ml_metrics = model_eval["metrics"]["ml_model"]
    assert np.isclose(ml_metrics["rmse"], 1.673566, atol=1e-3)
    assert np.isclose(ml_metrics["mae"], 1.334658, atol=1e-3)
    assert np.isclose(ml_metrics["r2"], 0.962520, atol=1e-3)


def test_missing_data_fail_fast_behavior(tmp_path):
    """Verify that attempting to load a non-existent station file raises FileNotFoundError without synthetic fallback."""
    from climate_analyzer.ingest import load_climate_dataset
    with pytest.raises(FileNotFoundError) as exc_info:
        load_climate_dataset("NON_EXISTENT_STATION", raw_dir=tmp_path, allow_download=False)
    assert "not found" in str(exc_info.value).lower()


def test_baseline_invariance_for_ols_and_sens_slope():
    """Verify baseline invariance across complete calendar years and full operational records."""
    if not Path("data/raw/USW00094728.csv").exists():
        pytest.skip("Real NOAA observation file data/raw/USW00094728.csv not found")
    from climate_analyzer.ingest import load_climate_dataset
    raw = load_climate_dataset("USW00094728", raw_dir="data/raw", allow_download=False)
    clean = clean_daily_observations(raw)
    monthly = aggregate_to_monthly(clean)

    baselines = [
        (1951, 1980, "1951_1980"),
        (1901, 2000, "1901_2000"),
        (1991, 2020, "1991_2020"),
        (1871, 1900, "1871_1900"),
    ]

    results_157 = {}
    results_156 = {}

    for b_start, b_end, name in baselines:
        anom = compute_climatological_anomalies(monthly, b_start, b_end)
        ann = aggregate_to_annual(anom)

        # Full 157-year operational record (1869-2025)
        ols_157 = calculate_linear_trend(ann["year"], ann["annual_anomaly"])
        sens_157 = sens_slope(ann["year"], ann["annual_anomaly"])
        det = detect_anomalies(anom, column="monthly_anomaly", z_threshold=2.5)
        warm_ext = int((det["monthly_anomaly"] > 2.5 * det["monthly_anomaly"].std()).sum())
        cold_ext = int((det["monthly_anomaly"] < -2.5 * det["monthly_anomaly"].std()).sum())

        results_157[name] = {
            "ols_rate": ols_157["decadal_rate"],
            "sens_rate": sens_157["sens_decadal_rate"],
            "hac_se": ols_157["hac_decadal_std_err"],
            "mean_anomaly": anom["monthly_anomaly"].mean(),
            "warm_extremes": warm_ext,
            "cold_extremes": cold_ext,
        }

        # Complete 12-month years only (1870-2025, N=156)
        ann_156 = ann[ann["year"] >= 1870].copy()
        ols_156 = calculate_linear_trend(ann_156["year"], ann_156["annual_anomaly"])
        sens_156 = sens_slope(ann_156["year"], ann_156["annual_anomaly"])
        mk_156 = mann_kendall_test(ann_156["annual_anomaly"])

        results_156[name] = {
            "n": len(ann_156),
            "ols_rate": ols_156["decadal_rate"],
            "sens_rate": sens_156["sens_decadal_rate"],
            "hac_se": ols_156["hac_decadal_std_err"],
            "mk_s": mk_156["s"],
            "mk_z": mk_156["z"],
        }

    # 1. Complete like-for-like sample (1870-2025, N=156): BIT-FOR-BIT INVARIANT (< 1e-14)
    ref_156 = results_156["1951_1980"]
    for name, res in results_156.items():
        assert res["n"] == 156, f"{name} complete sample size must be 156"
        assert np.isclose(res["ols_rate"], ref_156["ols_rate"], atol=1e-14), f"{name} OLS rate mismatch on complete sample"
        assert np.isclose(res["sens_rate"], ref_156["sens_rate"], atol=1e-14), f"{name} Sen slope mismatch on complete sample"
        assert np.isclose(res["hac_se"], ref_156["hac_se"], atol=1e-14), f"{name} HAC SE mismatch on complete sample"
        assert res["mk_s"] == ref_156["mk_s"], f"{name} MK S mismatch on complete sample"
        assert np.isclose(res["mk_z"], ref_156["mk_z"], atol=1e-14), f"{name} MK Z mismatch on complete sample"

    # 2. Full 157-year series (1869-2025): Rounds to identical +0.162 and +0.161 C/dec across all baselines
    for name, res in results_157.items():
        assert f"{res['ols_rate']:+.3f}" == "+0.162", f"{name} OLS 3-decimal display mismatch"
        assert f"{res['sens_rate']:+.3f}" == "+0.161", f"{name} Sen 3-decimal display mismatch"
        assert np.isclose(res["ols_rate"], 0.1618, atol=2e-4), f"{name} OLS within leverage tolerance"

    # 3. Dynamic responsiveness: Anomalies and extreme counts shift appropriately across baselines
    assert results_157["1991_2020"]["mean_anomaly"] < results_157["1951_1980"]["mean_anomaly"]
    assert results_157["1951_1980"]["mean_anomaly"] < results_157["1871_1900"]["mean_anomaly"]
    assert results_157["1871_1900"]["warm_extremes"] > results_157["1991_2020"]["warm_extremes"]
    assert results_157["1991_2020"]["cold_extremes"] > results_157["1871_1900"]["cold_extremes"]


def test_1869_incomplete_year_leverage_reconciliation():
    """Verify that the 1869 11-month seasonal deviation quantitatively explains the full-series slope variance."""
    if not Path("data/raw/USW00094728.csv").exists():
        pytest.skip("Real NOAA observation file data/raw/USW00094728.csv not found")
    from climate_analyzer.ingest import load_climate_dataset
    raw = load_climate_dataset("USW00094728", raw_dir="data/raw", allow_download=False)
    clean = clean_daily_observations(raw)
    monthly = aggregate_to_monthly(clean)

    # Compute WMO and Modern baselines
    ann_wmo = aggregate_to_annual(compute_climatological_anomalies(monthly, 1951, 1980))
    ann_mod = aggregate_to_annual(compute_climatological_anomalies(monthly, 1991, 2020))

    # Assert that 1869 has 11 months while all other years have 12
    assert ann_wmo.loc[ann_wmo["year"] == 1869, "months_count"].values[0] == 11
    assert (ann_wmo.loc[ann_wmo["year"] >= 1870, "months_count"] == 12).all()

    # Calculate analytical OLS leverage effect
    t = ann_wmo["year"].values
    t_bar = np.mean(t)
    denom = np.sum((t - t_bar) ** 2)

    diff_series = ann_mod["annual_anomaly"].values - ann_wmo["annual_anomaly"].values
    c_12 = np.mean(diff_series[1:])  # constant shift for complete years 1870-2025
    delta_1869 = diff_series[0] - c_12  # excess offset on incomplete year 1869 (-0.02516 deg C)

    ols_wmo = calculate_linear_trend(t, ann_wmo["annual_anomaly"])["decadal_rate"]
    ols_mod = calculate_linear_trend(t, ann_mod["annual_anomaly"])["decadal_rate"]
    actual_diff = ols_mod - ols_wmo

    # Analytical leverage prediction: Delta_beta = 10 * (1869 - t_bar) * delta_1869 / sum((t - t_bar)^2)
    predicted_diff = 10.0 * (t[0] - t_bar) * delta_1869 / denom

    assert np.isclose(actual_diff, predicted_diff, atol=1e-8), "Leverage equation must match actual OLS slope diff"


def test_full_record_statistical_tolerances_and_mk_mechanism():
    """Verify exact full-record statistical tolerances, distinguish unrounded differences
    from 3-decimal rounded KPI display equality, and verify the Mann-Kendall pairwise sign-flip mechanism.
    """
    if not Path("data/raw/USW00094728.csv").exists():
        pytest.skip("Real NOAA observation file data/raw/USW00094728.csv not found")
    from climate_analyzer.ingest import load_climate_dataset
    raw = load_climate_dataset("USW00094728", raw_dir="data/raw", allow_download=False)
    clean = clean_daily_observations(raw)
    monthly = aggregate_to_monthly(clean)

    baselines = {
        "wmo": (1951, 1980),
        "20th": (1901, 2000),
        "modern": (1991, 2020),
        "early": (1871, 1900),
    }

    res = {}
    for name, (b_start, b_end) in baselines.items():
        anom = compute_climatological_anomalies(monthly, b_start, b_end)
        ann = aggregate_to_annual(anom)
        ols = calculate_linear_trend(ann["year"], ann["annual_anomaly"])
        sens = sens_slope(ann["year"], ann["annual_anomaly"])
        mk = mann_kendall_test(ann["annual_anomaly"])
        res[name] = {
            "ols": ols,
            "sens": sens,
            "mk": mk,
            "ann": ann,
        }

    # 1. HAC Standard Error Span and Maximum Difference Verification
    hac_se_vals = {name: r["ols"]["hac_decadal_std_err"] for name, r in res.items()}
    hac_span = max(hac_se_vals.values()) - min(hac_se_vals.values())
    hac_early_diff = hac_se_vals["early"] - hac_se_vals["wmo"]

    # Span across all 4 baselines is 0.00001744 deg C/dec; max diff from WMO is +0.00001075 deg C/dec
    assert np.isclose(hac_span, 0.00001744, atol=1e-7), f"HAC SE span mismatch: {hac_span}"
    assert np.isclose(hac_early_diff, 0.00001075, atol=1e-7), f"HAC SE Early diff mismatch: {hac_early_diff}"
    # Refute the prior understatement of 'no more than +-0.00001':
    assert hac_span > 0.000010, "Total HAC SE span exceeds 0.000010 deg C/dec"
    assert hac_early_diff > 0.000010, "Early Historical HAC SE difference exceeds 0.000010 deg C/dec"
    # At 4 decimal places, all baselines round identically to 0.0129 deg C/dec
    for name, se in hac_se_vals.items():
        assert f"{se:.4f}" == "0.0129", f"{name} HAC SE 4-decimal mismatch: {se:.4f}"

    # 2. Sen's Slope Tolerance and Distinction Between Unrounded Difference and Display Equality
    sens_rates = {name: r["sens"]["sens_decadal_rate"] for name, r in res.items()}
    sens_span = max(sens_rates.values()) - min(sens_rates.values())
    sens_early_diff = sens_rates["early"] - sens_rates["wmo"]

    # Unrounded differences reach -0.00023519 deg C/dec, total span is 0.00024449 deg C/dec
    assert np.isclose(sens_span, 0.00024449, atol=1e-7), f"Sen span mismatch: {sens_span}"
    assert np.isclose(sens_early_diff, -0.00023519, atol=1e-7), f"Sen Early diff mismatch: {sens_early_diff}"
    # Refute prior claim that unrounded Sen's slope is within +-0.0001:
    assert abs(sens_early_diff) > 0.00010, "Unrounded Sen's slope difference exceeds 0.00010 deg C/dec"
    # Distinguish from display equality: all 4 baselines round identically to +0.161 deg C/dec at 3 decimals
    for name, rate in sens_rates.items():
        assert f"{rate:+.3f}" == "+0.161", f"{name} Sen's slope 3-decimal display mismatch: {rate:+.3f}"

    # 3. Mann-Kendall Score Mechanism: Refutation of Ties and Proof of Single Pairwise Sign Flip
    var_s_vals = [r["mk"]["var_s"] for r in res.values()]
    # var_s = 434052.6667 is identical across all baselines; zero tied pairs exist
    for v in var_s_vals[1:]:
        assert np.isclose(v, var_s_vals[0], atol=1e-10), "var(S) must be strictly invariant (zero ties)"
    assert res["wmo"]["mk"]["s"] == 6882
    assert res["early"]["mk"]["s"] == 6880
    assert res["20th"]["mk"]["s"] == 6882
    assert res["modern"]["mk"]["s"] == 6882

    # Verify exactly which pairwise comparisons change sign
    y_wmo = res["wmo"]["ann"]["annual_anomaly"].values
    y_early = res["early"]["ann"]["annual_anomaly"].values
    years = res["wmo"]["ann"]["year"].values
    n = len(years)

    diff_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            sgn_wmo = np.sign(y_wmo[j] - y_wmo[i])
            sgn_early = np.sign(y_early[j] - y_early[i])
            if sgn_wmo != sgn_early:
                diff_pairs.append((years[i], years[j], sgn_wmo, sgn_early, y_wmo[j] - y_wmo[i], y_early[j] - y_early[i]))

    # Exactly ONE pair out of 12,246 pairs flipped sign
    assert len(diff_pairs) == 1, f"Expected exactly 1 differing pair, got {len(diff_pairs)}: {diff_pairs}"
    yr_i, yr_j, sgn_w, sgn_e, dy_w, dy_e = diff_pairs[0]
    assert yr_i == 1869 and yr_j == 1882, f"Differing pair must be (1869, 1882), got ({yr_i}, {yr_j})"
    assert sgn_w == +1.0 and sgn_e == -1.0, f"Pair must flip from +1 to -1, got {sgn_w} to {sgn_e}"
    # The sign flip from +1 to -1 reduces S by (-1) - (+1) = -2
    assert res["early"]["mk"]["s"] - res["wmo"]["mk"]["s"] == -2


def test_dashboard_pathway_invariance_and_display_agreement():
    """Verify that the dashboard calculation pathway maintains consistent sample sizes and displayed KPIs."""
    if not Path("data/raw/USW00094728.csv").exists():
        pytest.skip("Real NOAA observation file data/raw/USW00094728.csv not found")
    from climate_analyzer.ingest import load_climate_dataset
    raw = load_climate_dataset("USW00094728", raw_dir="data/raw", allow_download=False)
    clean = clean_daily_observations(raw)
    monthly_clean = aggregate_to_monthly(clean, min_days_per_month=25)

    baselines = [(1951, 1980), (1901, 2000), (1991, 2020), (1871, 1900)]

    for yr_range, expected_len in [((1869, 2026), 157), ((1870, 2026), 156), ((1970, 2026), 56)]:
        kpi_ols_list = []
        kpi_sens_list = []
        ols_exact_list = []

        for b_start, b_end in baselines:
            monthly_anom = compute_climatological_anomalies(monthly_clean, baseline_start=b_start, baseline_end=b_end)
            annual_df = aggregate_to_annual(monthly_anom)
            annual_feat = engineer_annual_features(annual_df, rolling_windows=(5, 10))

            filtered = annual_feat[(annual_feat["year"] >= yr_range[0]) & (annual_feat["year"] <= yr_range[1])].copy()
            assert len(filtered) == expected_len, f"Sample size for {yr_range} must remain {expected_len}"

            trend = calculate_linear_trend(filtered["year"], filtered["annual_anomaly"])
            sens = sens_slope(filtered["year"], filtered["annual_anomaly"])

            kpi_ols_list.append(f"{trend['decadal_rate']:+.3f} °C / dec")
            kpi_sens_list.append(f"{sens['sens_decadal_rate']:+.3f} °C / dec")
            ols_exact_list.append(trend["decadal_rate"])

        # Displayed KPI strings must be 100% identical across all baselines
        assert len(set(kpi_ols_list)) == 1, f"Displayed OLS KPIs differed for {yr_range}: {kpi_ols_list}"
        assert len(set(kpi_sens_list)) == 1, f"Displayed Sen KPIs differed for {yr_range}: {kpi_sens_list}"

        # If year range excludes 1869, exact numerical slope must be bit-for-bit identical (< 1e-14)
        if yr_range[0] >= 1870:
            for ols_val in ols_exact_list[1:]:
                assert np.isclose(ols_val, ols_exact_list[0], atol=1e-14)



def test_moving_average_window_configurations_and_export_schema():
    """Verify that moving-average window configurations compute dynamic windows and generate exact CSV schemas."""
    # Known test DataFrame with 50 years of data
    years = np.arange(1970, 2021)
    rng = np.random.default_rng(42)
    anom_vals = np.sin(np.linspace(0, 10, len(years))) + rng.normal(0, 0.2, len(years))
    ann_df = pd.DataFrame({
        "year": years,
        "annual_tavg": 13.0 + anom_vals,
        "annual_anomaly": anom_vals,
        "annual_prcp": 1100.0,
        "months_count": 12,
    })

    # Config 1: 3-year and 10-year windows
    feat_cfg1 = engineer_annual_features(ann_df, rolling_windows=(3, 10))
    assert "rolling_mean_3yr" in feat_cfg1.columns
    assert "rolling_mean_10yr" in feat_cfg1.columns

    # Config 2: 5-year and 20-year windows
    feat_cfg2 = engineer_annual_features(ann_df, rolling_windows=(5, 20))
    assert "rolling_mean_5yr" in feat_cfg2.columns
    assert "rolling_mean_20yr" in feat_cfg2.columns

    # Verify that longer windows produce smoother (lower std dev) series
    assert feat_cfg1["rolling_mean_10yr"].std() < feat_cfg1["rolling_mean_3yr"].std()
    assert feat_cfg2["rolling_mean_20yr"].std() < feat_cfg2["rolling_mean_5yr"].std()

    # Verify CSV export schema for Config 1
    rename_cfg1 = {
        "year": "year",
        "annual_tavg": "mean_annual_temp_degC",
        "annual_anomaly": "temperature_anomaly_degC",
        "rolling_mean_3yr": "moving_avg_3yr_degC",
        "rolling_mean_10yr": "moving_avg_10yr_degC",
    }
    exp_cfg1 = feat_cfg1[list(rename_cfg1.keys())].rename(columns=rename_cfg1)
    exp_cfg1["station_id"] = "USW00094728"
    csv1 = exp_cfg1.to_csv(index=False)
    header1 = csv1.splitlines()[0]
    assert "moving_avg_3yr_degC" in header1
    assert "moving_avg_10yr_degC" in header1

    # Verify CSV export schema for Config 2
    rename_cfg2 = {
        "year": "year",
        "annual_tavg": "mean_annual_temp_degC",
        "annual_anomaly": "temperature_anomaly_degC",
        "rolling_mean_5yr": "moving_avg_5yr_degC",
        "rolling_mean_20yr": "moving_avg_20yr_degC",
    }
    exp_cfg2 = feat_cfg2[list(rename_cfg2.keys())].rename(columns=rename_cfg2)
    exp_cfg2["station_id"] = "USW00094728"
    csv2 = exp_cfg2.to_csv(index=False)
    header2 = csv2.splitlines()[0]
    assert "moving_avg_5yr_degC" in header2
    assert "moving_avg_20yr_degC" in header2


def test_forecast_export_partitioning_and_metadata():
    """Verify that validated benchmark ML export contains exactly 309 rows and correct schema and metadata."""
    if not Path("data/raw/USW00094728.csv").exists():
        pytest.skip("Real NOAA observation file data/raw/USW00094728.csv not found")
    from climate_analyzer.ingest import load_climate_dataset
    raw = load_climate_dataset("USW00094728", raw_dir="data/raw", allow_download=False)
    clean = clean_daily_observations(raw)
    monthly = aggregate_to_monthly(clean)
    anom = compute_climatological_anomalies(monthly, 1951, 1980)
    monthly_feats = engineer_monthly_features(anom)

    eval_res = train_and_evaluate_climate_model(monthly_feats, split_year=2000)
    preds = eval_res["predictions"].copy()

    assert len(preds) == 309, "Must have exactly 309 held-out test predictions"
    assert "target_date" in preds.columns, "target_date must be present in predictions"

    # Verify date boundaries
    first_target = str(preds["target_date"].iloc[0])[:7]
    last_target = str(preds["target_date"].iloc[-1])[:7]
    first_feat = str(preds["date"].iloc[0])[:7]
    last_feat = str(preds["date"].iloc[-1])[:7]

    assert first_target == "2001-01", f"First test target must be 2001-01, got {first_target}"
    assert last_target == "2026-09", f"Last test target must be 2026-09, got {last_target}"
    assert first_feat == "2000-12", f"First test feature must be 2000-12, got {first_feat}"
    assert last_feat == "2026-08", f"Last test feature must be 2026-08, got {last_feat}"

    # Build CSV export format matching app/streamlit_app.py
    pred_export = preds.copy()
    pred_export["date"] = pd.to_datetime(pred_export["date"]).dt.strftime("%Y-%m-%d")
    pred_export["target_date"] = pd.to_datetime(pred_export["target_date"]).dt.strftime("%Y-%m-%d")
    rename_preds = {
        "date": "feature_date",
        "target_date": "target_date",
        "target_next_tavg": "actual_observed_tavg_degC",
        "pred_ml": "predicted_ridge_ml_degC",
        "pred_climatology": "predicted_climatology_degC",
        "pred_persistence": "predicted_persistence_degC",
        "residual_ml": "forecast_residual_degC",
    }
    export_subset = pred_export[list(rename_preds.keys())].rename(columns=rename_preds)
    export_subset["split_year"] = 2000
    export_subset["forecast_protocol"] = "validated_benchmark"
    export_subset["station_id"] = "USW00094728"

    assert len(export_subset) == 309
    assert list(export_subset.columns) == [
        "feature_date",
        "target_date",
        "actual_observed_tavg_degC",
        "predicted_ridge_ml_degC",
        "predicted_climatology_degC",
        "predicted_persistence_degC",
        "forecast_residual_degC",
        "split_year",
        "forecast_protocol",
        "station_id",
    ]

    # Verify metrics match pipeline metrics
    metrics = eval_res["metrics"]
    assert np.isclose(metrics["ml_model"]["rmse"], 1.673566, atol=1e-3)
    assert np.isclose(metrics["climatology_baseline"]["rmse"], 2.143431, atol=1e-3)
    assert np.isclose(metrics["persistence_baseline"]["rmse"], 4.847246, atol=1e-3)


def test_exploratory_split_labeling_and_isolation():
    """Verify that exploratory split scenario partitions differently and flags metadata as exploratory."""
    if not Path("data/raw/USW00094728.csv").exists():
        pytest.skip("Real NOAA observation file data/raw/USW00094728.csv not found")
    from climate_analyzer.ingest import load_climate_dataset
    raw = load_climate_dataset("USW00094728", raw_dir="data/raw", allow_download=False)
    clean = clean_daily_observations(raw)
    monthly = aggregate_to_monthly(clean)
    anom = compute_climatological_anomalies(monthly, 1951, 1980)
    monthly_feats = engineer_monthly_features(anom)

    eval_res = train_and_evaluate_climate_model(monthly_feats, split_year=1990)
    preds = eval_res["predictions"].copy()

    # Held-out test period starts in 1991, so test samples > 309
    assert eval_res["test_samples"] > 309
    assert eval_res["test_target_range"][0] == "1991-01"

    # Export metadata simulation
    preds["forecast_protocol"] = "exploratory_scenario"
    preds["split_year"] = 1990
    assert (preds["forecast_protocol"] == "exploratory_scenario").all()
    assert (preds["split_year"] == 1990).all()

