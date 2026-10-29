#!/usr/bin/env python
"""End-to-End Real-Data Execution Pipeline for Climate Trend Analyzer.

Ingests, validates, transforms, analyzes, and models genuine public climate observations
from the NOAA Global Historical Climatology Network (GHCN-Daily).

Author: Akash Das
"""

import argparse
import os
import sys
from pathlib import Path
import pandas as pd

from climate_analyzer.config import Config, get_project_paths

# Redirect matplotlib cache to project-local outputs directory
cfg = Config()
cfg.ensure_directories()
os.environ["MPLCONFIGDIR"] = str(cfg.paths.outputs_dir / ".matplotlib_cache")

from climate_analyzer.ingest import load_climate_dataset, load_noaa_ghcn_daily
from climate_analyzer.validation import validate_ghcn_dataframe
from climate_analyzer.transform import (
    clean_daily_observations,
    aggregate_to_monthly,
    compute_climatological_anomalies,
    aggregate_to_annual,
)
from climate_analyzer.features import (
    engineer_monthly_features,
    engineer_annual_features,
)
from climate_analyzer.analysis import (
    calculate_linear_trend,
    mann_kendall_test,
    sens_slope,
    calculate_decadal_summary,
)
from climate_analyzer.anomaly_detection import detect_anomalies, get_top_extreme_records
from climate_analyzer.modeling import train_and_evaluate_climate_model
from climate_analyzer.visualization import (
    plot_historical_temperature_trend,
    plot_anomalies,
    plot_decadal_temperature_shifts,
    plot_model_forecast_vs_actual,
)
from climate_analyzer.reporting import export_metrics, generate_markdown_report


def run_pipeline(
    station_id: str = "USW00094728",
    station_name: str = "NYC Central Park, NY US",
    raw_path: str | Path | None = None,
    allow_download: bool = True,
) -> int:
    """Execute complete real-world climate analysis and modeling pipeline.

    Args:
        station_id: NOAA GHCN station code.
        station_name: Human-readable station location.
        raw_path: Optional explicit path to raw station CSV.
        allow_download: Whether to fetch file from NOAA if missing.

    Returns:
        0 on success, non-zero on failure.
    """
    cfg = Config()
    cfg.ensure_directories()
    paths = cfg.paths

    print("=" * 70)
    print("Climate Trend Analyzer - Real Public Data Pipeline")
    print(f"Author: Akash Das | Dataset: NOAA GHCN-Daily ({station_id})")
    print("=" * 70)

    # 1. Ingestion of Genuine Public Climate Data
    print("\n[Stage 1/6] Ingesting genuine NOAA GHCN-Daily records...")
    df_daily: pd.DataFrame
    try:
        if raw_path is not None:
            raw_file = Path(raw_path)
            print(f"  Loading specified raw file: {raw_file}")
            df_daily = load_noaa_ghcn_daily(raw_file)
        else:
            df_daily = load_climate_dataset(
                station_id=station_id,
                raw_dir=paths.raw_data_dir,
                allow_download=allow_download,
            )
    except Exception as e:
        print(f"\n[ERROR] Failed to ingest real climate data: {e}", file=sys.stderr)
        print("Note: This project strictly operates on real public data. No synthetic fallback is permitted.", file=sys.stderr)
        return 1

    station_name_actual = df_daily["name"].iloc[0] if not df_daily.empty else station_name
    lat_val = float(df_daily["latitude"].iloc[0]) if "latitude" in df_daily.columns else 0.0
    lon_val = float(df_daily["longitude"].iloc[0]) if "longitude" in df_daily.columns else 0.0
    elev_val = float(df_daily["elevation"].iloc[0]) if "elevation" in df_daily.columns else 0.0

    print(f"  [+] Station: {station_name_actual} ({station_id})")
    print(f"  [+] Location: Lat {lat_val:.2f}, Lon {lon_val:.2f}, Elevation {elev_val:.1f}m")
    print(f"  [+] Ingested {len(df_daily):,} daily observation records.")

    # 2. Quality Assertion & Schema Validation
    print("\n[Stage 2/6] Validating dataset integrity & physical bounds...")
    val_report = validate_ghcn_dataframe(df_daily, raise_on_error=True)
    print(f"  [+] Observation span: {val_report['start_date']} to {val_report['end_date']}")
    print(f"  [+] Temporal continuity: {val_report['total_records']:,} calendar records validated")
    if val_report["warnings"]:
        for w in val_report["warnings"][:3]:
            print(f"  [!] Note: {w}")

    # 3. Data Transformation & Temporal Aggregation
    print("\n[Stage 3/6] Cleaning observations & computing climatological baselines...")
    clean_daily = clean_daily_observations(df_daily)
    monthly_df = aggregate_to_monthly(clean_daily, min_days_per_month=25)
    monthly_anom = compute_climatological_anomalies(
        monthly_df,
        baseline_start=cfg.baseline_start,
        baseline_end=cfg.baseline_end,
    )
    annual_df = aggregate_to_annual(monthly_anom, min_months_per_year=11)

    # 4. Feature Engineering
    print("\n[Stage 4/6] Engineering time-aware features & rolling indicators...")
    monthly_feats = engineer_monthly_features(monthly_anom)
    annual_feats = engineer_annual_features(annual_df)

    processed_csv = paths.processed_data_dir / f"{station_id}_monthly_features.csv"
    annual_csv = paths.processed_data_dir / f"{station_id}_annual_features.csv"
    monthly_feats.to_csv(processed_csv, index=False)
    annual_feats.to_csv(annual_csv, index=False)
    print(f"  [+] Saved processed monthly features ({len(monthly_feats)} rows) to: {processed_csv.name}")
    print(f"  [+] Saved processed annual features ({len(annual_feats)} rows) to: {annual_csv.name}")

    # 5. Statistical Trend Analysis & Anomaly Detection
    print("\n[Stage 5/6] Quantifying long-term trends & meteorological extremes...")
    trend_res = calculate_linear_trend(annual_feats["year"], annual_feats["annual_anomaly"])
    mk_res = mann_kendall_test(annual_feats["annual_anomaly"])
    sens_res = sens_slope(annual_feats["year"], annual_feats["annual_anomaly"])
    decadal_df = calculate_decadal_summary(annual_feats, value_col="annual_tavg")

    print(f"  [+] Linear Trend (OLS): {trend_res['decadal_rate']:+.3f} deg C / decade (R2 = {trend_res['r_squared']:.3f}, p = {trend_res['p_value_bound']}, HAC SE = {trend_res['hac_decadal_std_err']:.4f} deg C/dec, HAC p = {trend_res['hac_p_value_bound']})")
    print(f"  [+] Sen's Slope: {sens_res['sens_decadal_rate']:+.3f} deg C / decade")
    print(f"  [+] Mann-Kendall Test: {mk_res['trend'].upper()} (S = {mk_res['s']:,}, Z = {mk_res['z']:.2f}, p = {mk_res['p_value_bound']})")
    print(f"  [+] Modified Mann-Kendall: Raw rho1 = {mk_res['rho1']:.3f} (VIF = {mk_res['vif']:.2f}, Adj Z* = {mk_res['z_adj']:.2f}, p = {mk_res['p_value_adj_bound']}); Detrended rho1 = {mk_res['rho1_detrended']:.3f} (Adj Z* = {mk_res['z_adj_detrended']:.2f}, p = {mk_res['p_value_adj_detrended_bound']})")

    monthly_anom_detected = detect_anomalies(monthly_feats, column="monthly_anomaly")
    top_warmest_years = get_top_extreme_records(annual_feats, value_col="annual_tavg", top_n=5, warmest=True)
    print("  [+] Top 5 Warmest Years on Record:")
    for _, row in top_warmest_years.iterrows():
        print(f"     Rank {int(row['rank'])}: Year {int(row['year'])} (Mean Temp: {row['annual_tavg']:.2f} deg C, Anomaly: {row['annual_anomaly']:+.2f} deg C)")

    # 6. Machine Learning Modeling on Held-Out Real Data
    print("\n[Stage 6/6] Training predictive model & evaluating on held-out test records...")
    model_res = train_and_evaluate_climate_model(monthly_feats, split_year=cfg.ml_split_year)
    m_ml = model_res["metrics"]["ml_model"]
    m_clim = model_res["metrics"]["climatology_baseline"]
    m_pers = model_res["metrics"]["persistence_baseline"]

    print(f"  [+] Test Set: {model_res['test_period'][0]} to {model_res['test_period'][1]} ({model_res['test_samples']} held-out months)")
    print(f"  [+] Ridge ML Model:         RMSE = {m_ml['rmse']:.3f} deg C, MAE = {m_ml['mae']:.3f} deg C, R2 = {m_ml['r2']:.3f}")
    print(f"  [+] Climatology Baseline:   RMSE = {m_clim['rmse']:.3f} deg C, MAE = {m_clim['mae']:.3f} deg C, R2 = {m_clim['r2']:.3f}")
    print(f"  [+] Persistence Baseline:   RMSE = {m_pers['rmse']:.3f} deg C, MAE = {m_pers['mae']:.3f} deg C, R2 = {m_pers['r2']:.3f}")

    # 7. Visualization & Chart Export
    print("\n[Stage 7/7] Generating publication-quality charts & formal report...")
    plot_historical_temperature_trend(
        annual_feats,
        trend_dict=trend_res,
        output_path=paths.figures_dir / "temperature_trend.png",
        station_name=station_name_actual,
    )
    plot_anomalies(
        monthly_anom_detected,
        date_col="date",
        val_col="monthly_anomaly",
        output_path=paths.figures_dir / "anomaly_distribution.png",
        station_name=station_name_actual,
    )
    plot_decadal_temperature_shifts(
        decadal_df,
        val_col="mean_annual_tavg",
        output_path=paths.figures_dir / "decadal_temperature_shifts.png",
        station_name=station_name_actual,
    )
    plot_model_forecast_vs_actual(
        model_res["predictions"],
        target_col="target_next_tavg",
        pred_col="pred_ml",
        output_path=paths.figures_dir / "model_forecast_vs_actual.png",
        station_name=station_name_actual,
    )
    print(f"  [+] Exported 4 publication charts to: {paths.figures_dir}")

    # Compile Summary Data
    summary_data = {
        "execution_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dataset_info": {
            "dataset_name": "NOAA GHCN-Daily",
            "station_id": station_id,
            "station_name": station_name_actual,
            "latitude": lat_val,
            "longitude": lon_val,
            "elevation": elev_val,
            "start_date": val_report["start_date"],
            "end_date": val_report["end_date"],
            "total_daily_records": val_report["total_records"],
            "total_monthly_records": len(monthly_feats),
            "baseline_period": f"{cfg.baseline_start}-{cfg.baseline_end} Mean",
        },
        "linear_trend": trend_res,
        "mann_kendall": mk_res,
        "sens_slope": sens_res,
        "model_evaluation": model_res,
        "top_warmest_records": top_warmest_years.to_dict(orient="records"),
    }

    metrics_file = paths.metrics_dir / "pipeline_metrics.json"
    export_metrics(summary_data, metrics_file)
    print(f"  [+] Exported metrics to: {metrics_file}")

    report_file = paths.reports_dir / "pipeline_report.md"
    generate_markdown_report(summary_data, report_file)
    generate_markdown_report(summary_data, paths.root_dir / "reports" / "PROJECT_REPORT.md")
    print(f"  [+] Formal reports generated in {report_file.name} and reports/PROJECT_REPORT.md")

    print("\n" + "=" * 70)
    print("[SUCCESS] Real-data pipeline executed successfully!")
    print("=" * 70)
    return 0


def main() -> None:
    """CLI entry point for real-data pipeline."""
    parser = argparse.ArgumentParser(description="Climate Trend Analyzer - Real Public Data Pipeline")
    parser.add_argument("--station", type=str, default="USW00094728", help="NOAA GHCN station code (default: USW00094728)")
    parser.add_argument("--name", type=str, default="NYC Central Park, NY US", help="Station name description")
    parser.add_argument("--raw-file", type=str, default=None, help="Explicit path to raw GHCN CSV file")
    parser.add_argument("--offline", action="store_true", help="Disallow network download if file missing")
    args = parser.parse_args()

    sys.exit(
        run_pipeline(
            station_id=args.station,
            station_name=args.name,
            raw_path=args.raw_file,
            allow_download=not args.offline,
        )
    )


if __name__ == "__main__":
    main()
