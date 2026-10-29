# Data Dictionary

This document specifies the schema, definitions, storage types, and units for all observation and derived feature tables handled by the **Climate Trend Analyzer**.

---

## 1. Daily Observations Schema (`data/raw/` and Ingestion)

Source: NOAA GHCN-Daily (`USW00094728.csv`)

| Column Name | Storage Type | Physical Unit | Nullable | Description | Valid Range / Bounds |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `station` | `string` | ID | No | NOAA Station Identifier | Format: `USW00094728` |
| `name` | `string` | Text | No | Station name and location | e.g. `NY CITY CENTRAL PARK, NY US` |
| `latitude` | `float64` | Degrees (°N) | No | Station geographic latitude | `[-90.0, 90.0]` |
| `longitude` | `float64` | Degrees (°E/°W) | No | Station geographic longitude | `[-180.0, 180.0]` |
| `elevation` | `float64` | Metres (m) | No | Station elevation above sea level | `[0.0, 5000.0]` |
| `date` | `datetime64[ns]` | ISO 8601 | No | Calendar observation date | 1869-01-01 to Present |
| `year` | `int32` | Year (CE) | No | Calendar year | `[1850, 2100]` |
| `month` | `int32` | Month (1-12) | No | Calendar month | `[1, 12]` |
| `day` | `int32` | Day (1-31) | No | Calendar day | `[1, 31]` |
| `tmax` | `float64` | °C | Yes | Maximum daily surface air temperature | `[-50.0, 55.0]` |
| `tmin` | `float64` | °C | Yes | Minimum daily surface air temperature | `[-60.0, 50.0]` |
| `tavg_native` | `float64` | °C | Yes | Native NOAA-reported daily mean (available 1998–2005) | `[-55.0, 50.0]` |
| `has_native_tavg` | `bool` | Boolean | No | True if source file contains a native NOAA TAVG reading | `True` / `False` |
| `tavg_midpoint` | `float64` | °C | Yes | Arithmetic midpoint: `(tmax + tmin) / 2.0` (NaN if either extreme missing) | `[-55.0, 50.0]` |
| `is_tavg_derived` | `bool` | Boolean | No | True if operational daily mean is derived from midpoint | `True` / `False` |
| `is_inverted_temp` | `bool` | Boolean | No | True if source record has $T_{\text{min}} > T_{\text{max}}$ | `True` / `False` |
| `tavg` | `float64` | °C | Yes | Standardized operational daily temperature (`tavg_midpoint`) | `[-55.0, 50.0]` |
| `prcp` | `float64` | mm | No | Daily total precipitation | `>= 0.0` |
| `snow` | `float64` | mm | Yes | Daily total snowfall | `>= 0.0` |

---

## 2. Monthly Climate Summary & Feature Schema (`data/processed/`)

| Column Name | Storage Type | Physical Unit | Description |
| :--- | :--- | :--- | :--- |
| `date` | `datetime64[ns]` | Date | First day of observation month (`YYYY-MM-01`) |
| `year` | `int32` | Year | Calendar year |
| `month` | `int32` | Month | Calendar month (1–12) |
| `tavg_mean` | `float64` | °C | Monthly mean of daily average temperatures |
| `tmax_mean` | `float64` | °C | Monthly mean of daily maximum temperatures |
| `tmin_mean` | `float64` | °C | Monthly mean of daily minimum temperatures |
| `tmax_extreme` | `float64` | °C | Highest single daily maximum recorded in month |
| `tmin_extreme` | `float64` | °C | Lowest single daily minimum recorded in month |
| `prcp_total` | `float64` | mm | Total accumulated monthly precipitation |
| `days_valid` | `int64` | Count | Number of valid observation days in month (>= 25) |
| `baseline_tavg` | `float64` | °C | 1951–1980 climatological baseline mean for this calendar month |
| `monthly_anomaly` | `float64` | °C | Deviation from 1951–1980 baseline (`tavg_mean - baseline_tavg`) |
| `sin_month` | `float64` | Unit circle | Cyclical seasonal encoding: $\sin(2\pi \cdot \text{month} / 12)$ |
| `cos_month` | `float64` | Unit circle | Cyclical seasonal encoding: $\cos(2\pi \cdot \text{month} / 12)$ |
| `time_fraction` | `float64` | Year fraction | Continuous decimal year (`year + (month - 1) / 12`) |
| `tavg_lag_1` | `float64` | °C | 1-month lookback temperature ($T_{t-1}$) |
| `tavg_lag_2` | `float64` | °C | 2-month lookback temperature ($T_{t-2}$) |
| `tavg_lag_12` | `float64` | °C | 12-month lookback temperature ($T_{t-12}$, same month prior year) |
| `rolling_tavg_3m` | `float64` | °C | 3-month backward rolling average temperature |
| `rolling_tavg_12m` | `float64` | °C | 12-month backward rolling average temperature |
| `rolling_std_12m` | `float64` | °C | 12-month backward rolling sample standard deviation |
| `prcp_lag_1` | `float64` | mm | 1-month lookback precipitation ($P_{t-1}$) |
| `target_next_tavg`| `float64` | °C | Target variable: Next month's mean temperature ($T_{t+1}$) |
| `target_date` | `datetime64[ns]` | Date | Calendar date of next observation month ($t+1$) |
| `target_year` | `float64` | Year | Calendar year of target month ($t+1$) |
| `target_month` | `float64` | Month | Calendar month of target month ($t+1$) |
| `z_score` | `float64` | Standard deviations | Standard score of monthly anomaly |
| `is_anomaly_zscore` | `bool` | Boolean | True if $\|z\| \ge 2.0$ |
| `is_anomaly_iqr` | `bool` | Boolean | True if value falls outside $[Q1 - 1.5 \cdot IQR, Q3 + 1.5 \cdot IQR]$ |

---

## 3. Annual Summary Schema (`data/processed/`)

| Column Name | Storage Type | Physical Unit | Description |
| :--- | :--- | :--- | :--- |
| `year` | `int32` | Year | Calendar year |
| `annual_tavg` | `float64` | °C | Mean of monthly average temperatures for the year |
| `annual_anomaly` | `float64` | °C | Mean of monthly anomalies relative to 1951–1980 baseline |
| `annual_prcp` | `float64` | mm | Total annual precipitation |
| `months_count` | `int64` | Count | Number of valid months observed (>= 11) |
| `rolling_mean_5yr` | `float64` | °C | 5-year backward moving average of annual anomaly |
| `rolling_mean_10yr`| `float64` | °C | 10-year backward moving average of annual anomaly |
| `rolling_std_10yr` | `float64` | °C | 10-year backward moving standard deviation |
| `decade` | `int32` | Year | Decade identifier (e.g. 1980 for 1980–1989) |
