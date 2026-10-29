# Architecture Decisions & Engineering Change Log

This document records the foundational architectural decisions, scientific trade-offs, and engineering modifications made during the development and real-data migration of the **Climate Trend Analyzer**.

**Project Author**: Akash Das  
**Current Status**: Active (Real Public Data Only)  

---

## 1. Architectural Decision Records (ADRs)

### ADR-01: Selection of NOAA GHCN-Daily as Primary Terrestrial Dataset
- **Date**: 2026-10-28
- **Status**: Approved & Implemented
- **Context**: The project required a genuine, high-quality, long-term public meteorological dataset to replace all synthetic data and Monte Carlo simulations.
- **Alternatives Considered**:
  1. *Copernicus ERA5 Reanalysis*: Gridded global reanalysis from 1940 to present. Highly detailed, but requires registering a personal account on the ECMWF Climate Data Store, accepting legal terms, and provisioning an API token in `~/.cdsapirc`. Not suitable for frictionless, zero-credential automated reproducibility.
  2. *NASA GISTEMP v4*: Global and hemispheric monthly surface temperature anomaly series from 1880. Highly respected for macro-anomalies, but public endpoints experienced intermittent network timeouts, and the dataset is a single scalar anomaly series lacking daily meteorological drivers (precipitation, daily extremes) required for multi-feature machine learning.
  3. *NOAA GHCN-Daily Station `USW00094728` (NYC Central Park)*: Provides unauthenticated, permanent, high-bandwidth CSV access to over 157 years (1869–2026) of continuous daily observations (>57,600 records) maintained by NOAA NCEI.
- **Decision**: Select NOAA GHCN-Daily (`USW00094728`) as the authoritative operational dataset.

---

### ADR-02: Total Retirement of Synthetic Simulation & Monte Carlo Projections
- **Date**: 2026-10-28
- **Status**: Approved & Implemented
- **Context**: Previous codebase iterations included synthetic climate data generators, Monte Carlo scenario projections, and a `--synthetic` CLI flag.
- **Decision**: Permanently eliminate all synthetic simulation modules, test files, and CLI branches:
  - Deleted `src/climate_analyzer/simulation.py`.
  - Deleted `tests/test_simulation.py`.
  - Removed `--synthetic` from `run_pipeline.py`.
- **Justification**: Fabricated climate data creates misleading impressions of real-world climate trends and undermines scientific validity.

---

### ADR-03: Derivation Protocol for Missing Daily Mean Temperature ($T_{\text{avg}}$)
- **Date**: 2026-10-28
- **Status**: Approved & Implemented
- **Context**: An exhaustive audit of the 57,640 daily records revealed that NOAA natively populates the `TAVG` column for only **2,648 rows** (4.59% of the record, spanning 1998 to 2005). Prior to 1998 and after 2005, NOAA GHCN-Daily records $T_{\text{max}}$ and $T_{\text{min}}$, leaving $T_{\text{avg}}$ blank.
- **Decision**: When native `TAVG` is missing, derive daily mean temperature as:
  $$T_{\text{avg}} = \frac{T_{\text{max}} + T_{\text{min}}}{2.0}$$
- **Justification**: The midpoint between daily maximum and minimum temperatures is the standard historical proxy utilized by the World Meteorological Organization (WMO) and the National Weather Service (NWS) for cooperative observer networks prior to automated continuous electronic sensor logging. This derivation is transparently documented across all data dictionaries.

---

### ADR-04: Preservation of Source Observations for Historical Inversions (TMIN > TMAX)
- **Date**: 2026-10-28
- **Status**: Approved & Implemented (Supersedes unverified value swapping)
- **Context**: Automated data validation detected two days in the 1890s (`1894-10-05` and `1897-02-07`) where recorded $T_{\text{min}}$ was higher than $T_{\text{max}}$.
- **Former Approach**: Previous implementation silently swapped $T_{\text{max}}$ and $T_{\text{min}}$.
- **Audited Decision**:
  1. Do not infer which value is wrong solely from the inversion.
  2. Preserve original source observations unchanged.
  3. Flag the records via boolean column `is_inverted_temp = True`.
  4. Daily midpoint mean temperature $(T_{\text{max}} + T_{\text{min}}) / 2.0$ remains mathematically identical due to commutativity of addition.
- **Justification**: Respects archival data integrity and avoids introducing unverified manual edits into historical public data records.

---

### ADR-05: Inclusion of `StandardScaler` in Ridge ML Pipeline
- **Date**: 2026-10-28
- **Status**: Approved & Implemented
- **Context**: The feature matrix combines variables across disparate physical units and orders of magnitude (`time_fraction` $\sim 1900$, `prcp_lag_1` up to $300$ mm, `sin_month` $\in [-1, 1]$). Unscaled $L_2$ regularization unfairly penalized unit-circle trigonometric features while failing to penalize large-scale features.
- **Decision**: Implement a scikit-learn `Pipeline([('scaler', StandardScaler()), ('ridge', Ridge(alpha=10.0))])`. Fit the scaler strictly on the training partition ($t \le 2000$).
- **Justification**: Out-of-sample test RMSE improved from 1.708 °C down to **1.675 °C**, while MAE improved from 1.367 °C to **1.335 °C**. Strict separation prevents data leakage between training and held-out test periods.

---

### ADR-06: Strict Chronological Train/Test Partitioning
- **Date**: 2026-10-28
- **Status**: Approved & Superseded by ADR-11 (Target-Date Policy)
- **Context**: Standard machine learning practices often employ random $k$-fold cross-validation, which causes temporal data leakage in time-series forecasting.
- **Decision**: Enforce a strict chronological partition rather than random cross-validation. Refined in ADR-11 into the Target-Date Partition Policy (1,570 training months predicting target months 1870-02 to 2000-12; 309 held-out test months predicting target months 2001-01 to 2026-09).
- **Justification**: Completely prevents future information leakage into past model states, accurately assessing real-world forecast performance on genuinely unseen future climate regimes.

---

### ADR-07: Bounded Gap Interpolation and Proper Exclusion of Incomplete Months
- **Date**: 2026-10-28
- **Status**: Approved & Implemented
- **Context**: In May 1869, 7 consecutive days lacked observations. The previous code used pandas `interpolate(limit=3)`, which partially interpolated the first 3 days of the 7-day gap, artificially raising May 1869 from 24 to 27 valid days and bypassing the 25-day completeness threshold.
- **Decision**: Implement `interpolate_bounded_gaps()`, ensuring that gaps exceeding `max_gap_interpolation` (3 days) are strictly NOT interpolated.
- **Justification**: May 1869 properly fails the threshold ($24 < 25$) and is excluded from valid monthly records without fabricating artificial data inside a 7-day gap.

---

### ADR-08: Full Calendar Sequence Reindexing for Lag Alignment
- **Date**: 2026-10-28
- **Status**: Approved & Implemented
- **Context**: Dropping May 1869 directly from a DataFrame causes row-based shifts (`shift(12)`) to jump across the missing month, misaligning all future calendar lags by 1 month.
- **Decision**: Reindex the monthly summary onto the full continuous monthly calendar range (`1869-01-01` to `2026-09-01`), representing unobserved months as explicit `NaN` values.
- **Justification**: Ensures that `shift(12)` aligns strictly with the identical calendar month of the prior year, preventing calendar phase distortion across 157 years.

---

### ADR-09: Implementation of Newey-West HAC Standard Errors & Modified Mann-Kendall Test
- **Date**: 2026-10-28
- **Status**: Approved & Implemented
- **Context**: The annual anomaly series exhibits strong positive serial autocorrelation ($\rho_1 = 0.616$), which violates the i.i.d. assumption and artificially inflates nominal test statistics.
- **Decision**:
  1. Implement Newey-West Heteroskedasticity and Autocorrelation Consistent (HAC) standard error for the OLS trend slope using Bartlett kernel with automatic lag selection $L = 4$.
  2. Implement the Modified Mann-Kendall test (Yue & Wang 2004) applying variance inflation factor $\text{VIF} = (1 + \rho_1) / (1 - \rho_1) = 4.21$.
  3. Format extremely small $p$-values as scientific bounds (e.g. $p < 10^{-24}$ or $p = 3.56 \times 10^{-7}$) rather than truncating to `0.0000`.
- **Justification**: Provides rigorous, publication-grade statistical inference accounting for serial autocorrelation.

---

### ADR-10: Scientific Retraction of Constant 'Steady Warming' Claims
- **Date**: 2026-10-28
- **Status**: Approved & Implemented
- **Context**: Previous project documentation claimed that close numerical agreement between OLS slope (+0.162 °C/dec) and Sen's slope (+0.161 °C/dec) proved that warming occurred steadily throughout the 157-year record.
- **Decision**: Retract that claim. Clarify that slope agreement proves mathematical robustness against single-year outliers, but does not imply steady, linear warming.
- **Justification**: The historical record contains distinct multi-decadal phases: early warming (1870–1940), a mid-20th-century plateau/cooling (~1940–1970) driven by aerosol masking, and accelerated post-1970 warming (+0.36 °C/dec) dominated by greenhouse forcing and urban heat island effects.

### ADR-11: Adoption of Target-Date Split Policy for Out-of-Sample Forecasting
- **Date**: 2026-10-28
- **Status**: Approved & Implemented (Phase 5C)
- **Context**: Prior implementation partitioned by feature calendar year (`df["year"] <= 2000`). Because the forecasting target is one-month-ahead temperature ($T_{t+1}$), the December 2000 feature row predicted January 2001, meaning the training set contained a target in 2001 despite being labeled as ending in 2000.
- **Decision**: Formally adopt and enforce a **target-date split policy** (`target_year <= 2000` for training; `target_year > 2000` for testing).
- **Justification**: Under this policy, training targets terminate strictly in December 2000 (1,570 samples spanning target months February 1870 through December 2000), and held-out test targets begin strictly in January 2001 (309 samples spanning target months January 2001 through September 2026). The forecast origin for the first test prediction is December 2000, using strictly observed historical data up to that date to predict January 2001 with zero forward-looking data leakage.

---

### ADR-12: Mathematical Baseline Invariance Conditioning & 1869 Seasonal Leverage Reconciliation
- **Date**: 2026-10-29
- **Status**: Approved & Implemented (Phases 7A-R2 & 7A-R2-F1)
- **Context**: Statistical trends were reported to have small variations at the 5th and 6th decimal places across different climatological baselines on the full 157-year record (1869–2025), seemingly contradicting mathematical invariance of linear slopes under scalar shifts.
- **Decision**:
  1. Prove mathematically and test numerically that on complete 12-month calendar years ($N=156$, 1870–2025), baseline shifts are pure scalar translations, yielding **bit-for-bit identical statistics ($< 10^{-14}$)** for OLS slope, $R^2$, HAC SE, Sen's slope, and Mann-Kendall statistics.
  2. Prove that on the full 157-year operational record (1869–2025), year 1869 has 11 valid months (missing May due to an authentic 7-day observation gap). Because atmospheric warming is seasonally non-uniform across calendar months, 1869's baseline offset differs from complete years by $\delta$, producing an analytical OLS regression leverage perturbation $\Delta \hat{\beta} = 10 \cdot (1869 - \bar{t}) \cdot \delta / \sum (t - \bar{t})^2$ that predicts actual slope differences down to $10^{-8}$ °C/decade.
  3. Reconcile full-precision HAC SE span ($0.000017$ °C/dec), unrounded Sen's slope difference ($0.000235$ °C/dec), refute tied ranks in Mann-Kendall ($\text{var}(S) = 434,052.67$ is identical with zero ties), and prove the single pairwise sign flip `(1869, 1882)` accounting for $\Delta S = -2$.
- **Justification**: Distinguishes machine-precision invariance, unrounded analytical leverage effects, and universal 3-decimal dashboard display equality (`+0.162 °C / dec` OLS and `+0.161 °C / dec` Sen).

---

### ADR-13: Minimal Headless Browser Dashboard Viewport Verification
- **Date**: 2026-10-29
- **Status**: Approved & Implemented (Phase 7B)
- **Context**: Interactive UI verification required confirmation of responsive desktop and mobile layouts and real-time interactive filtering without overengineering heavy browser testing frameworks.
- **Decision**:
  1. Implement lightweight headless browser verification using system Chrome CLI (`--no-sandbox`, `--disable-gpu`, `--disable-dev-shm-usage`) to render the live Streamlit dashboard across desktop (1280x900) and mobile (375x812) viewports.
  2. Programmatically verify interactive control state transitions (filtering from Full Record $N=157$ to Post-1970 Era $N=56$, dynamically accelerating warming rate from $+0.162$ to $+0.216$ °C/decade without calculation errors).
  3. Validate exported CSV schemas and physical unit headers.
- **Justification**: Achieves complete end-to-end user experience and layout verification while strictly avoiding bloatware and unnecessary browser automation dependencies.

---

## 2. Summary of Key Modifications Across Modules

| Module File | Modification Performed | Reason for Change |
| :--- | :--- | :--- |
| `src/climate_analyzer/config.py` | Added NOAA URLs, default station `USW00094728`, 1951–1980 baseline. Removed simulation paths. | Complete transition to genuine public data. |
| `src/climate_analyzer/ingest.py` | Implemented NOAA GHCN-Daily downloader, unit conversions, derived $T_{\text{avg}}$. Removed synthetic fallback. | Fail-fast real-data ingestion. |
| `src/climate_analyzer/validation.py` | Converted $T_{\text{min}} > T_{\text{max}}$ assertion into logged quality warning. | Robust historical data ingestion. |
| `src/climate_analyzer/transform.py` | Added bounded gap interpolation ($\le 3$ days), monthly/annual aggregation thresholds, calendar reindexing. | Clean, standardized climate aggregates. |
| `src/climate_analyzer/features.py` | Built cyclical month encodings, decimal time, lags, and rolling features. | ML feature engineering. |
| `src/climate_analyzer/analysis.py` | Implemented Newey-West HAC standard error, Modified Mann-Kendall (Yue & Wang 2004), and scientific $p$-value formatting. | Autocorrelation-robust statistical inference. |
| `src/climate_analyzer/anomaly_detection.py` | Fixed `KeyError: 'annual_anomaly'` by dynamically retaining ranking columns. | Prevented pipeline ranking crashes. |
| `src/climate_analyzer/modeling.py` | Wrapped Ridge in `StandardScaler` pipeline; added Seasonal Climatology & Persistence baselines. | Prevented scale bias; enabled baseline benchmarking. |
| `src/climate_analyzer/visualization.py` | Replaced deprecated `matplotlib.cm.get_cmap()` with `matplotlib.colormaps["coolwarm"]`. | Matplotlib 3.8+ compatibility. |
| `src/climate_analyzer/reporting.py` | Enhanced markdown report with HAC OLS, Modified MK, and multi-decadal scientific notes. | Publication-quality reporting. |
| `run_pipeline.py` | Added HAC and Modified MK logging; pure real-data flow. | Windows CP1252 terminal compatibility. |
| `pyproject.toml` | Added `-p no:cacheprovider` to pytest `addopts`. | Prevented Windows sandbox pytest write hangs. |

