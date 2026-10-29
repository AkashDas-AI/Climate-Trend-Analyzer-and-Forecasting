# Module Reference & API Specification

This document provides a comprehensive technical reference for all software modules in the `climate_analyzer` package.

**Author**: Akash Das  
**Package Path**: `src/climate_analyzer/`

---

## 1. Module Architecture & Call Graph

```
run_pipeline.py / app/streamlit_app.py
   │
   ├──► config.py               (Paths & Global Constants)
   ├──► ingest.py               (NOAA GHCN Ingestion & Daily Parsing)
   ├──► validation.py           (Data Integrity & Physical Bounds Checking)
   ├──► transform.py            (Cleaning, Imputation & Monthly/Annual Aggregation)
   ├──► features.py             (Cyclical Encoding, Lags & Rolling Statistics)
   ├──► analysis.py             (OLS Linear Trend, Mann-Kendall Test, Sen's Slope)
   ├──► anomaly_detection.py    (Z-Score, IQR & Historical Record Ranking)
   ├──► modeling.py             (StandardScaler + Ridge Regression vs. Baselines)
   ├──► visualization.py       (Matplotlib/Seaborn Chart Export)
   └──► reporting.py            (JSON Metrics Serialization & Markdown Generation)
```

---

## 2. Detailed Module Catalog

### 2.1 `climate_analyzer.config`
- **Source**: [`src/climate_analyzer/config.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/config.py)
- **Role**: Centralized configuration and path management rooted at the repository base.
- **Key Classes & Functions**:
  - `ProjectPaths`: Dataclass holding absolute paths to `data/raw`, `data/processed`, `outputs/figures`, `outputs/metrics`, `outputs/reports`, and `docs`.
  - `get_project_paths(base_dir=None)`: Resolves project root via `Path(__file__).resolve().parents[2]`.
  - `Config`: Main configuration dataclass (default station `USW00094728`, baseline 1951–1980, split year 2000, thresholds).

### 2.2 `climate_analyzer.ingest`
- **Source**: [`src/climate_analyzer/ingest.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/ingest.py)
- **Role**: Ingestion of verified real-world public climate records from NOAA NCEI.
- **Key Functions**:
  - `download_noaa_ghcn_station(station_id, target_dir)`: Downloads genuine station CSV from NOAA NCEI. Raises `FileNotFoundError` if station doesn't exist, `ConnectionError` on network failure.
  - `load_noaa_ghcn_daily(file_path)`: Parses raw CSV, performs unit conversion (tenths of °C $\to$ °C, tenths of mm $\to$ mm), derives midpoint $T_{\text{avg}} = (T_{\text{max}} + T_{\text{min}})/2.0$.
  - `load_climate_dataset(station_id, raw_dir, allow_download)`: High-level retrieval entry point with offline mode enforcement.

### 2.3 `climate_analyzer.validation`
- **Source**: [`src/climate_analyzer/validation.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/validation.py)
- **Role**: Automated quality assurance, monotonicity checks, and physical plausibility assertions.
- **Key Functions & Classes**:
  - `ClimateDataValidationError`: Custom exception raised when essential schema constraints are violated.
  - `validate_ghcn_dataframe(df, min_year, max_year, min_temp, max_temp, raise_on_error)`: Checks schema completeness, chronological monotonicity, physical bounds ($[-60^\circ\text{C}, 60^\circ\text{C}]$, $\text{PRCP} \ge 0$), and detects 19th-century observer transcription swaps.

### 2.4 `climate_analyzer.transform`
- **Source**: [`src/climate_analyzer/transform.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/transform.py)
- **Role**: Daily cleaning, monthly/annual grouping, and climatological baseline computation.
- **Key Functions**:
  - `clean_daily_observations(df, max_gap_interpolation=3)`: Reindexes across full calendar days, flags historical inverted records via `is_inverted_temp` without mutating source values, and interpolates gaps strictly $\le 3$ days (leaving gaps $> 3$ days un-interpolated).
  - `aggregate_to_monthly(daily_df, min_days_per_month=25, reindex_full_calendar=True)`: Computes monthly summaries (`tavg_mean`, `tmax_mean`, `tmin_mean`, `prcp_total`). Enforces $\ge 25$ days completeness threshold (excluding May 1869 and Oct 2026), and reindexes onto continuous monthly timeline to ensure lag alignment.
  - `compute_climatological_anomalies(monthly_df, baseline_start=1951, baseline_end=1980)`: Computes 30-year monthly baseline means and appends `monthly_anomaly`.
  - `aggregate_to_annual(monthly_df, min_months_per_year=11)`: Aggregates to annual series with $\ge 11$ months completeness threshold.

### 2.5 `climate_analyzer.features`
- **Source**: [`src/climate_analyzer/features.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/features.py)
- **Role**: Time-aware predictor feature engineering with strict zero future-data leakage.
- **Key Functions**:
  - `engineer_monthly_features(monthly_df)`: Generates cyclical features (`sin_month`, `cos_month`), decimal time fraction, autoregressive lags (`tavg_lag_1`, `tavg_lag_2`, `tavg_lag_12`, `prcp_lag_1`), rolling smoothers (`rolling_tavg_3m`, `rolling_tavg_12m`), and target `target_next_tavg`.
  - `engineer_annual_features(annual_df)`: Generates 5-year and 10-year rolling moving averages and decadal indicators.

### 2.6 `climate_analyzer.analysis`
- **Source**: [`src/climate_analyzer/analysis.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/analysis.py)
- **Role**: Statistical trend estimation and non-parametric hypothesis testing.
- **Key Functions**:
  - `calculate_linear_trend(time_series, values)`: Fits OLS linear regression and converts annual slope to decadal rate.
  - `mann_kendall_test(series)`: Rank-based monotonic trend test with exact tie corrections, $S$ statistic, $Z$ score, and two-tailed $p$-value.
  - `sens_slope(time_series, values)`: Non-parametric median of all pairwise slopes.
  - `calculate_decadal_summary(df, value_col)`: Aggregates observations by decade.

### 2.7 `climate_analyzer.anomaly_detection`
- **Source**: [`src/climate_analyzer/anomaly_detection.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/anomaly_detection.py)
- **Role**: Statistical outlier flagging and historical record ranking.
- **Key Functions**:
  - `detect_zscore_anomalies(df, column, threshold=2.0)`: Standard score cutoff.
  - `detect_iqr_anomalies(df, column, multiplier=1.5)`: Interquartile Range dispersion filter.
  - `get_top_extreme_records(df, value_col, top_n, warmest)`: Ranks top historical records (e.g. warmest recorded years).
  - `detect_anomalies(df, column, z_threshold, iqr_multiplier)`: Merges Z-score and IQR flags.

### 2.8 `climate_analyzer.modeling`
- **Source**: [`src/climate_analyzer/modeling.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/modeling.py)
- **Role**: Chronological out-of-sample machine learning evaluation and baseline benchmarking.
- **Key Functions**:
  - `temporal_train_test_split(df, split_year=2000)`: Strictly chronological train/test partitioning.
  - `compute_forecast_metrics(y_true, y_pred)`: Computes RMSE, MAE, and $R^2$.
  - `train_and_evaluate_climate_model(monthly_features_df, split_year=2000)`: Evaluates `StandardScaler` + `Ridge(alpha=10.0)` pipeline against Seasonal Climatology and Persistence baselines on identical held-out test rows.

### 2.9 `climate_analyzer.visualization`
- **Source**: [`src/climate_analyzer/visualization.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/visualization.py)
- **Role**: Publication-quality chart export using non-interactive Matplotlib and Seaborn.
- **Key Functions**:
  - `plot_historical_temperature_trend()`: Bar anomaly chart with 5/10-year smoothers and OLS trend line.
  - `plot_anomalies()`: Time series highlighting statistical extremes.
  - `plot_decadal_temperature_shifts()`: Colored decadal temperature bar chart.
  - `plot_model_forecast_vs_actual()`: Held-out ML forecasts vs. actual observations with prediction residual trace.

### 2.10 `climate_analyzer.reporting`
- **Source**: [`src/climate_analyzer/reporting.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/reporting.py)
- **Role**: Metrics serialization and automated markdown report compilation.
- **Key Functions**:
  - `export_metrics(metrics_data, output_path)`: Exports metrics dictionary to JSON.
  - `generate_markdown_report(summary_data, output_path)`: Compiles formatted project report.

