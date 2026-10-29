# End-to-End Data Flow Architecture

This document tracks the complete lifecycle of genuine climate observation records through the **Climate Trend Analyzer** processing, analysis, and modeling pipelines.

**Author**: Akash Das

---

## 1. Data Pipeline Overview

The system processes meteorological observations through six deterministic stages:

```mermaid
flowchart TD
    subgraph S1["Stage 1: Real-Data Ingestion"]
        A["NOAA NCEI Public Server<br/>(GHCN-Daily Access)"] -->|HTTPS GET| B["Raw CSV Storage<br/>data/raw/USW00094728.csv<br/>(57,640 daily records)"]
        B --> C["load_noaa_ghcn_daily()<br/>Convert tenths of °C to °C<br/>Convert tenths of mm to mm<br/>Derive TAVG = (TMAX + TMIN)/2"]
    end

    subgraph S2["Stage 2: Validation & QC"]
        C --> D["validate_ghcn_dataframe()<br/>Verify monotonic calendar dates<br/>Assert physical bounds: [-60°C, 60°C]<br/>Verify PRCP >= 0<br/>Flag historical observer anomalies"]
    end

    subgraph S3["Stage 3: Transformation & Baselining"]
        D --> E["clean_daily_observations()<br/>Reindex continuous calendar dates<br/>Interpolate isolated gaps (<= 3 days)"]
        E --> F["aggregate_to_monthly()<br/>Completeness check: >= 25 days/month<br/>Compute tavg_mean, prcp_total"]
        F --> G["compute_climatological_anomalies()<br/>1951-1980 WMO Reference Baseline<br/>monthly_anomaly = tavg - baseline_month"]
        G --> H["aggregate_to_annual()<br/>Completeness check: >= 11 months/year"]
    end

    subgraph S4["Stage 4: Feature Engineering"]
        G --> I["engineer_monthly_features()<br/>sin/cos cyclical month encodings<br/>time_fraction continuous year<br/>Autoregressive lags (t-1, t-2, t-12)<br/>Rolling statistics (3m, 12m)<br/>Target: target_next_tavg (t+1)"]
        H --> J["engineer_annual_features()<br/>5-yr and 10-yr moving averages<br/>10-yr rolling standard deviation"]
        I --> K["data/processed/USW00094728_monthly_features.csv"]
        J --> L["data/processed/USW00094728_annual_features.csv"]
    end

    subgraph S5["Stage 5: Analytics & Modeling"]
        L --> M["Statistical Trend Analysis<br/>OLS linear warming slope<br/>Mann-Kendall rank test<br/>Sen's non-parametric slope<br/>Decadal shift summaries"]
        K --> N["Extreme Event Detection<br/>Z-score thresholding (|z| >= 2.0)<br/>IQR dispersion filters<br/>Top warmest years ranking"]
        K --> O["Out-of-Sample ML Evaluation<br/>Chronological Split: 1870-2000 vs. 2001-2026<br/>StandardScaler (train-only fit)<br/>Ridge Regression vs.<br/>Seasonal Climatology & Persistence Baselines"]
    end

    subgraph S6["Stage 6: Artifacts & Reporting"]
        M --> P["outputs/figures/<br/>temperature_trend.png<br/>decadal_temperature_shifts.png"]
        N --> Q["outputs/figures/<br/>anomaly_distribution.png"]
        O --> R["outputs/figures/<br/>model_forecast_vs_actual.png"]
        M & N & O --> S["outputs/metrics/pipeline_metrics.json"]
        M & N & O --> T["outputs/reports/pipeline_report.md<br/>& reports/PROJECT_REPORT.md"]
        K & L --> U["Streamlit Dashboard<br/>app/streamlit_app.py"]
    end
```

---

## 2. Detailed Data Lifecycle Stages

### Stage 1: Data Ingestion (`src/climate_analyzer/ingest.py`)
- **Input**: NOAA GHCN-Daily station file (`USW00094728.csv`) retrieved via HTTPS from NOAA NCEI.
- **Transformations**:
  - `TMAX` and `TMIN` are stored by NOAA in tenths of degrees Celsius; divided by $10.0$ to produce standard °C.
  - `PRCP` is stored in tenths of millimetres; divided by $10.0$ to produce standard millimetres.
  - `TAVG` is provided by NOAA for only 2,648 days (1998–2005). For all other records, `TAVG` is derived as the midpoint:
    $$T_{\text{avg}} = \frac{T_{\text{max}} + T_{\text{min}}}{2.0}$$
- **Output**: Daily DataFrame with 57,640 records spanning January 1, 1869 to October 24, 2026.

### Stage 2: Quality Assertion & Schema Validation (`src/climate_analyzer/validation.py`)
- **Input**: Daily DataFrame.
- **Checks**:
  - Required columns: `date`, `year`, `month`, `day`, `tmax`, `tmin`, `tavg`, `prcp`.
  - Date ordering: Chronologically sorted with zero duplicate timestamps.
  - Sanity bounds: $T \in [-60.0, 60.0]^\circ\text{C}$, $\text{PRCP} \ge 0.0$.
  - Observer anomaly detection: Identifies historical transcription swaps (e.g. 1894-10-05 and 1897-02-07 where $T_{\text{min}} > T_{\text{max}}$).

### Stage 3: Transformation & Baselining (`src/climate_analyzer/transform.py`)
- **Daily Cleaning**: Reindexes over complete calendar days. Flags the 2 isolated historical inverted records via `is_inverted_temp = True` while preserving source values. Interpolates isolated gaps strictly $\le 3$ days (leaving gaps $> 3$ days un-interpolated).
- **Monthly Aggregation**:
  - Aggregates daily temperatures to mean, daily precipitation to sum.
  - Completeness requirement: $\ge 25$ valid days per month. (May 1869 and October 2026 each have 24 observed days, and are correctly filtered out).
  - Reindexes onto continuous monthly calendar sequence to ensure exact lag alignment without phase distortion.
- **1951–1980 Baseline Anomaly Computation**:
  - Calculates 30-year monthly mean for each of the 12 calendar months: $\mu_{\text{baseline}, m}$.
  - Subtracts monthly baseline to compute $\text{Anomaly}_t = T_t - \mu_{\text{baseline}, m}$.
- **Annual Aggregation**:
  - Computes annual mean temperature and anomaly.
  - Completeness requirement: $\ge 11$ complete months per year.

### Stage 4: Feature Engineering (`src/climate_analyzer/features.py`)
- **Monthly Features**:
  - Cyclical encodings: $\sin(2\pi m/12)$ and $\cos(2\pi m/12)$.
  - Decimal time fraction: $\text{year} + (m - 1)/12.0$.
  - Autoregressive lags: $T_{t-1}, T_{t-2}, T_{t-12}$.
  - Rolling windows: 3-month and 12-month rolling means and standard deviations.
  - Target variable: $T_{t+1}$ (`target_next_tavg`).
- **Zero Future-Data Leakage**:
  - At index $t$ (end of month $t$), only observations from month $t$ and prior are used.
  - The target $T_{t+1}$ is strictly from the subsequent month.

### Stage 5: Analytics & Predictive Modeling (`src/climate_analyzer/analysis.py`, `modeling.py`)
- **Statistical Trends**:
  - Parametric OLS linear trend slope on annual anomalies.
  - Non-parametric Mann-Kendall test statistic $S$, variance $\text{Var}(S)$, normalized score $Z$, and two-tailed $p$-value.
  - Sen's slope estimator (median of pairwise slopes).
- **Machine Learning Evaluation**:
  - Chronological target-date split: Training on targets 1870–2000 (1,570 months); testing on targets 2001–2026 (309 months).
  - Preprocessing: `StandardScaler` fit strictly on training set ($t \le 2000$).
  - Models evaluated: Ridge Regression, Seasonal Climatology Baseline, Persistence Baseline.
  - Out-of-sample metrics: RMSE, MAE, $R^2$.

### Stage 6: Serving & Artifact Export (`src/climate_analyzer/visualization.py`, `reporting.py`, `app/`)
- Export 4 publication-quality PNG figures to `outputs/figures/`.
- Export metrics JSON to `outputs/metrics/pipeline_metrics.json`.
- Compile formal reports in `outputs/reports/pipeline_report.md` and `reports/PROJECT_REPORT.md`.
- Serve interactive Streamlit UI in `app/streamlit_app.py`.

