# Climate Trend Analyzer - Real Public Data Execution Report

**Project Author**: Akash Das  
**Execution Timestamp**: 2026-10-29 01:22:23  
**Dataset**: NOAA GHCN-Daily  
**Station**: NY CITY CENTRAL PARK, NY US (USW00094728)  
**Status**: Complete (Verified Real Public Data)  

---

## 1. Executive Summary
This report documents empirical climate trends, non-parametric hypothesis tests, and out-of-sample machine learning evaluations conducted strictly on genuine observational records from the NOAA Global Historical Climatology Network (GHCN-Daily). Zero synthetic datasets or simulated scenarios were used.

## 2. Dataset Provenance & Profile
- **Data Provider**: NOAA National Centers for Environmental Information (NCEI)
- **Station Location**: Lat 40.77898, Lon -73.96925, Elev 42.7m
- **Observation Period**: 1869-01-01 to 2026-10-24
- **Daily Observations Ingested**: 57,640 days
- **Monthly Aggregates Evaluated**: 1893 months
- **Climatological Baseline**: 1951-1980 Mean

## 3. Long-Term Trend Quantification

| Statistical Method | Empirical Warming Rate | Significance & Diagnostics | Autocorrelation & Uncertainty Quantification |
| :--- | :--- | :--- | :--- |
| **Linear Trend (OLS)** | +0.162 °C / decade | R² = 0.571, p = < 1e-24 | Nominal OLS SE = 0.0113 °C/dec |
| **OLS with Newey-West HAC (Asymptotic)** | +0.162 °C / decade | t = 12.58, p = < 1e-24 | HAC SE = 0.0129 °C/dec (df = 155) |
| **OLS with Newey-West HAC (Finite-Sample)** | +0.162 °C / decade | t = 12.50, p = < 1e-24 | HAC SE (fs) = 0.0129 °C/dec |
| **Sen's Non-Parametric Slope** | +0.161 °C / decade | Robust pairwise median slope | Insensitive to single-year outlier extremes |
| **Mann-Kendall Test (Nominal)** | Trend: increasing (S = 6,882) | Z = 10.44, p = < 1e-24 | Uncorrected nominal variance (Var = 434,052.7) |
| **Modified MK (Raw AR1 Diagnostic)** | Trend: increasing | Z* = 5.09, p = 3.56e-07 | Raw ρ₁ = 0.616, VIF = 4.21 (trend-inflated) |
| **Modified MK (Detrended Residuals)** | Trend: increasing | Z* = 9.23, p = < 1e-24 | Detrended r₁ = 0.123, VIF = 1.28 |

> [!NOTE]
> **Scientific Note on Long-Term Warming Dynamics & Attribution Boundaries**:
> 1. **Empirical Observation**: Observed annual temperature anomalies at NYC Central Park show a statistically
>    significant centennial warming trend (+0.162 °C/decade, p < 1e-24 with Newey-West HAC SE = 0.0129 °C/decade).
> 2. **Trend Non-Linearity**: Close agreement between OLS (+0.162 °C/dec) and Sen's slope (+0.161 °C/dec)
>    confirms robustness against single-year outlier extremes, but does **not** imply uniform or steady warming.
>    The historical series exhibits multi-decadal variability: early warming (1870–1940), mid-century cooling/plateau
>    (~1940–1970), and accelerated post-1970 warming (+0.36 °C/decade).
> 3. **Plausible Physical Mechanisms**: External peer-reviewed literature typically links these decadal shifts to
>    combinations of greenhouse gas forcing, tropospheric sulfate aerosols, internal ocean variability, and local urbanization.
> 4. **Attribution Boundary**: Statistical analysis of a single station cannot isolate or quantify the specific
>    fractional contribution of each mechanism, and one urban station is not equivalent to a global temperature index.

## 4. Top Recorded Warmest Years on Record

| Rank | Year | Annual Average Temp (°C) | Anomaly vs. 1951-1980 Baseline (°C) |
| :---: | :---: | :---: | :---: |
| 1 | 2024 | 14.40 °C | +1.89 °C |
| 2 | 2023 | 14.39 °C | +1.88 °C |
| 3 | 2012 | 14.06 °C | +1.55 °C |
| 4 | 2020 | 14.05 °C | +1.54 °C |
| 5 | 1991 | 14.00 °C | +1.48 °C |

## 5. Machine Learning Evaluation (Held-Out Test Set: 2001 - Present)

All models evaluated on the exact same held-out chronological test observations:

| Model Architecture | Test RMSE (°C) | Test MAE (°C) | Out-of-Sample R² | Evaluation Role |
| :--- | :---: | :---: | :---: | :--- |
| **Ridge ML Regressor** | **1.674** | **1.335** | **0.963** | Primary Predictive Model |
| **Seasonal Climatology** | 2.143 | 1.660 | 0.939 | Historical Month Mean Baseline |
| **Persistence Baseline** | 4.847 | 4.257 | 0.686 | Naive Lookback Baseline |

- **Training Partition**: Feature months 1870-01 to 2000-11 predicting Target months 1870-02 to 2000-12 (1570 months)
- **Held-Out Test Partition**: Feature months 2000-12 to 2026-08 predicting Target months 2001-01 to 2026-09 (309 months)
- **Final Observation Month Evaluated**: September 2026 (target of August 2026 feature row)

## 6. Generated Visualizations
- `outputs/figures/temperature_trend.png`: Historical observed temperature anomaly timeline and smoothers
- `outputs/figures/anomaly_distribution.png`: Statistical outlier and extreme event distribution
- `outputs/figures/decadal_temperature_shifts.png`: Mean observed temperature by decade
- `outputs/figures/model_forecast_vs_actual.png`: Out-of-sample ML forecast vs. genuine test observations

---
*Report automatically generated from verified real-world public climate data.*