# Data Processing, Cleaning & Quality Control

This document provides a detailed technical reference for all data cleaning, imputation, validation, and aggregation routines in the **Climate Trend Analyzer**.

**Author**: Akash Das  
**Operational Status**: Fully Audited & Verified (Real Public Data)  

---

## 1. Raw Observations Ingestion & Unit Harmonization

The ingestion module ([`src/climate_analyzer/ingest.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/ingest.py)) processes the official NOAA GHCN-Daily CSV format.

### 1.1 Unit Conversion Standards
NOAA GHCN-Daily records temperatures and precipitation in integer tenths to avoid floating-point representation in archive storage. During ingestion, physical units are converted immediately:

$$T_{\text{max}} = \frac{\text{TMAX}_{\text{raw}}}{10.0} \; (^\circ\text{C})$$

$$T_{\text{min}} = \frac{\text{TMIN}_{\text{raw}}}{10.0} \; (^\circ\text{C})$$

$$\text{PRCP} = \frac{\text{PRCP}_{\text{raw}}}{10.0} \; (\text{mm})$$

### 1.2 Daily Mean Temperature ($T_{\text{avg}}$) Accounting, Quality Policy & Provenance
- In the raw NOAA station file (`USW00094728.csv`), the `TAVG` column contains values for only **2,648 days** (from April 1998 to July 2005).
- For the remaining **54,992 days** (95.4% of the 157-year record), `TAVG` is unpopulated in the raw source.
- **Audit Discovery on Native `TAVG` Outliers**: An inspection of NOAA quality flags revealed that native `TAVG` contains 5 corrupted records in 2001–2002 where `TAVG = -17.8 °C` (0 °F) during July, August, and September with Quality Flag `G` ("Failed gap check"). Blindly using native `TAVG` introduces erroneous negative temperature spikes into summer records.
- **Operational Temperature Quality Policy**:
  1. **Operational Standardization**: Daily mean temperature is computed across the entire record as the arithmetic midpoint between valid daily extremes:
     $$T_{\text{avg}} = \frac{T_{\text{max}} + T_{\text{min}}}{2.0}$$
  2. **Operational Proxy Status**: The midpoint $(T_{\text{max}} + T_{\text{min}})/2.0$ is an operational climatological proxy (often denoted $T_{\text{mid}}$), standard across historical climatological network operations. It is not identical to a true continuous 24-hour integrated mean ($\bar{T}_{24} = \frac{1}{24} \int_0^{24} T(t)\,dt$) due to diurnal solar curve asymmetries.
  3. **Strict Pairwise Validity**: Midpoint is calculated strictly when **both** $T_{\text{max}}$ and $T_{\text{min}}$ are valid and uncorrupted. If either extreme is missing or `NaN`, $T_{\text{avg}}$ strictly evaluates to `NaN` (no fabricated values).
  4. **Isolation of Corrupted Source Records**: Bad native values (e.g. the 5 corrupted summer records) never enter the operational series.
- **Provenance Preservation**: The ingestion DataFrame explicitly retains:
  - `tavg_native`: Raw NOAA-provided TAVG (or `NaN` where absent).
  - `has_native_tavg`: Boolean flag indicating whether source record contained a non-null native NOAA TAVG entry (source presence, not necessarily validity).
  - `tavg_midpoint`: Midpoint estimate from daily extremes (strictly `NaN` if either extreme is missing).
  - `is_tavg_derived`: Boolean flag indicating whether the operational daily mean was derived from midpoint extremes (`tavg.notna()`).
  - `tavg`: Standardized operational daily temperature (equal to `tavg_midpoint`).

---

## 2. Quality Control & Historical Sanity Assertions

The validation module ([`src/climate_analyzer/validation.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/validation.py)) executes automated assertions on every observation record:

1. **Schema Check**: Verifies presence of essential columns (`date`, `year`, `month`, `day`, `tmax`, `tmin`, `tavg`, `prcp`).
2. **Chronological Monotonicity**: Verifies that date timestamps advance day-by-day with zero duplicate timestamps.
3. **Physical Bounds**:
   - Surface temperatures must fall within $[-60.0^\circ\text{C}, +60.0^\circ\text{C}]$.
   - Daily precipitation must satisfy $\text{PRCP} \ge 0.0\text{ mm}$.
4. **Historical Transcription Inversions ($T_{\text{min}} > T_{\text{max}}$)**:
   - In 57,640 records, exactly **2 days** in the 19th-century record contain $T_{\text{min}} > T_{\text{max}}$:
     - `1894-10-05`: $T_{\text{max}} = 15.6^\circ\text{C}, T_{\text{min}} = 16.1^\circ\text{C}$ (difference: $+0.5^\circ\text{C}$) — NOAA Quality Flag `I` on both readings.
     - `1897-02-07`: $T_{\text{max}} = 3.9^\circ\text{C}, T_{\text{min}} = 6.1^\circ\text{C}$ (difference: $+2.2^\circ\text{C}$) — NOAA Quality Flag `I` on $T_{\text{min}}$.
   - **Disposition & Preservation**:
     - The pipeline **does not mutate or swap source observations**, as there is no independent historical observer evidence justifying an arbitrary swap.
     - Observations are preserved exactly as recorded and flagged with `is_inverted_temp = True`.
     - Because daily mean temperature is computed as $(T_{\text{max}} + T_{\text{min}}) / 2.0$, addition is commutative ($a + b = b + a$); therefore, daily $T_{\text{avg}}$ has the exact same value ($15.85^\circ\text{C}$ and $5.00^\circ\text{C}$) regardless of value ordering.
     - Neither date constitutes a monthly extreme for its respective month.

---

## 3. Missing Data Policy & Bounded Gap Interpolation

Across 157 years (57,640 calendar days from 1869-01-01 to 2026-10-24):
- **Calendar Continuity**: Exactly **0 missing calendar days** across the entire 157-year sequence.
- **Post-June 1869**: **Zero missing values** in $T_{\text{max}}$, $T_{\text{min}}$, or $\text{PRCP}$ (100% complete across 57,489 consecutive daily observations).
- **May 1869 Missing Gap**: Exactly **7 consecutive days** (`1869-05-02` to `1869-05-08`) lack temperature observations.

### Bounded Gap Interpolation Protocol
- Function: `interpolate_bounded_gaps(series, max_gap)`
- **Rule**: Linear interpolation is applied **only if the entire contiguous missing gap length is $\le \text{max\_gap}$** (default: 3 days).
- **Enforcement**: If a gap exceeds `max_gap`, **none** of the missing values are interpolated. The 7-day gap in May 1869 ($7 > 3$) is strictly preserved as unobserved `NaN` values, preventing the fabrication of synthetic climate records.

---

## 4. Temporal Aggregation Standards

### 4.1 Monthly Completeness Rule ($\ge 25$ days)
- A calendar month is retained as a valid climate record only if at least **25 valid observation days** are present.
- **Excluded Months**:
  1. **May 1869**: Contains 24 observed days ($24 < 25$). Properly recognized as incomplete and excluded from valid monthly records.
  2. **October 2026**: Observations end on October 24, 2026 (24 days observed, $24 < 25$). Properly recognized as incomplete and excluded.
- **Valid Complete Monthly Records**: Exactly **1,892 months** out of 1,894 total calendar months between January 1869 and October 2026.
- **Calendar Alignment**: The monthly summary is reindexed across the full calendar sequence (`1869-01-01` to `2026-09-01`, 1,893 calendar months) with May 1869 represented as an explicit `NaN` gap. This ensures that 12-month lookback lags (`tavg_lag_12`) strictly reference the same calendar month of the prior year with zero phase distortion.

### 4.2 Climatological Baseline Anomaly (1951–1980 Reference)
- The 30-year climatological baseline mean $\mu_{\text{baseline}, m}$ is computed separately for each calendar month $m \in \{1, 2, \dots, 12\}$ across 1951–1980:
  $$\mu_{\text{baseline}, m} = \frac{1}{30} \sum_{y=1951}^{1980} T_{\text{avg}, y, m}$$
- The monthly anomaly is defined as:
  $$\text{Anomaly}_{y, m} = T_{\text{avg}, y, m} - \mu_{\text{baseline}, m}$$

### 4.3 Annual Completeness Rule ($\ge 11$ months)
- A calendar year is retained in annual trend analyses only if at least **11 valid months** are present.
- **Year 1869**: Contains 11 valid months (Jan–Apr, Jun–Dec; May excluded). Meets threshold ($11 \ge 11$) and is retained.
- **Years 1870–2025**: All contain 12 valid months ($12 \ge 11$) and are retained (156 years).
- **Year 2026**: Contains 9 valid months (Jan–Sep; Oct excluded). Fails threshold ($9 < 11$) and is excluded from annual summaries.
- **Total Valid Annual Records**: Exactly **157 years** (1869–2025).
