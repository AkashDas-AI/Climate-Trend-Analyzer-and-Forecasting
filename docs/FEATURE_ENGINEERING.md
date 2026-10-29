# Feature Engineering, Target Alignment & Sample Reconciliation

This document details the feature engineering methodology, mathematical transformations, target construction, leakage-prevention guarantees, and exact sample reconciliation implemented in the **Climate Trend Analyzer**.

**Author**: Akash Das  
**Operational Status**: Fully Audited & Verified (Real Public Data)  

---

## 1. Forecast Origin & Information Boundary

A fundamental requirement in rigorous meteorological forecasting is ensuring that **all predictor features are genuinely observable at the exact moment a prediction is made**.

### 1.1 Operational Forecast Origin
- **Forecast Timestamp**: Exactly at the close of calendar month $t$ (e.g. December 31 at 23:59:59 UTC).
- **Target Variable**: The mean surface temperature of the subsequent calendar month $t+1$ (`target_next_tavg`, e.g. January mean temperature).
- **Information Boundary**:
  - Predictor features at row $t$ use only observations from month $t$ and prior ($s \le t$).
  - No information from month $t+1$ is accessed by any feature calculation.
  - The target column is generated strictly via `shift(-1)`:
    $$y_t = T_{t+1}$$

```
Observation History: ... [t-2] [t-1] [t] | Forecast Origin ────► Target: [t+1]
Features Used:       All data <= t       |                         To predict
```

### 1.2 Feature Availability Audit at Forecast Origin

| Feature Name | Information Used | Available at Forecast Origin? | Future Information Leakage? |
| :--- | :--- | :---: | :---: |
| `tavg_mean` | Current month $t$ mean temperature | **Yes** (Month $t$ has concluded) | None |
| `sin_month`, `cos_month` | Calendar month of month $t$ | **Yes** (Deterministic calendar position) | None |
| `time_fraction` | Decimal year of month $t$ | **Yes** (Calendar timestamp) | None |
| `tavg_lag_1` | Temperature of month $t-1$ | **Yes** (Concluded 1 month prior) | None |
| `tavg_lag_2` | Temperature of month $t-2$ | **Yes** (Concluded 2 months prior) | None |
| `tavg_lag_12` | Temperature of month $t-12$ | **Yes** (Concluded 12 months prior) | None |
| `rolling_tavg_3m` | Mean of months $t-2, t-1, t$ | **Yes** (Backward-looking rolling window) | None |
| `rolling_tavg_12m` | Mean of months $t-11 \dots t$ | **Yes** (Backward-looking rolling window) | None |
| `prcp_lag_1` | Precipitation of month $t-1$ | **Yes** (Prior month total) | None |

---

## 2. Mathematical Rationale for Cyclical Month Encoding

Standard calendar months are integers $m \in \{1, 2, \dots, 12\}$. Treating months as linear integers introduces an artificial numerical discontinuity:
- December ($m=12$) and January ($m=1$) are consecutive months (difference: 1 month).
- In a raw integer representation, $|12 - 1| = 11$, misleading linear models into treating December and January as maximally distant.

To preserve the circular continuity of Earth's orbit around the Sun, calendar months are mapped onto the 2D trigonometric unit circle:

$$\theta_t = \frac{2\pi \cdot m_t}{12}$$

$$x_{\text{sin}} = \sin(\theta_t), \quad x_{\text{cos}} = \cos(\theta_t)$$

Any seasonal phase shift can be represented as a linear combination of these two basis vectors:
$$A \sin(\theta_t + \phi) = \beta_1 \sin(\theta_t) + \beta_2 \cos(\theta_t)$$
where $\beta_1 = A\cos(\phi)$ and $\beta_2 = A\sin(\phi)$.

---

## 3. Sample Reconciliation: From Raw Records to Modeling Samples

An exhaustive row-by-row reconciliation traces the transformation from raw daily records to the final model evaluation matrix:

```
[Raw Observations: 57,640 Daily Records (1869-01-01 to 2026-10-24)]
                           │
                           ▼
[Monthly Aggregation: 1,892 Valid Complete Months (>= 25 valid days)]
   - Filtered out May 1869 (24 observed days < 25)
   - Filtered out October 2026 (24 observed days < 25)
                           │
                           ▼
[Calendar Reindexing: 1,893 Continuous Calendar Months (1869-01 to 2026-09)]
   - Preserves May 1869 as explicit NaN gap to prevent calendar lag phase distortion
                           │
                           ▼
[Feature Construction & Boundary Dropna: Exactly 14 Rows Excluded]
   - 12 rows in 1869: Lacks tavg_lag_12 (no prior records before 1869)
   - 1 row in 1870 (1870-05): Lacks tavg_lag_12 (May 1869 was unobserved)
   - 1 row in 2026 (2026-09): Lacks target_next_tavg (October 2026 incomplete)
                           │
                           ▼
[Valid Modeling Sample Matrix: Exactly 1,879 Samples]
                           │
         ┌─────────────────┴─────────────────┐
         ▼                                   ▼
[Training Partition: 1,570 Samples]   [Test Partition: 309 Samples]
   - Feature Months: 1870-01 to 2000-11  - Feature Months: 2000-12 to 2026-08
   - Target Months:  1870-02 to 2000-12  - Target Months:  2001-01 to 2026-09
   - Target-Date Split (<= 2000)         - Target-Date Split (> 2000)
   - Fits StandardScaler & Ridge         - Strictly held-out evaluation
```

### Mathematical Verification of Sample Totals
$$\text{Total Calendar Months (1869-01 to 2026-09)} = 1,893$$
$$\text{Dropped Rows} = 12 \text{ (1869 lags)} + 1 \text{ (1870-05 lag)} + 1 \text{ (2026-09 target)} = 14$$
$$\text{Eligible Modeling Rows} = 1,893 - 14 = 1,879$$
$$\text{Training Samples (Targets } \le 2000) = 1,570 \quad (\text{Feature: 1870-01 to 2000-11} \to \text{Target: 1870-02 to 2000-12})$$
$$\text{Held-Out Test Samples (Targets } > 2000) = 309 \quad (\text{Feature: 2000-12 to 2026-08} \to \text{Target: 2001-01 to 2026-09})$$
$$1,570 + 309 = 1,879 \quad \checkmark$$

> [!NOTE]
> **Target-Date Split Policy Resolution**: Under the target-date split policy, training targets strictly terminate at December 2000, and held-out test targets strictly span the 21st-century record from January 2001 through September 2026 (the final eligible observation month before the incomplete October 2026). Feature origins for the first test sample reside at December 2000, ensuring strictly historical observations are used to forecast January 2001 with zero forward-looking leakage.

---

## 4. Leakage Prevention Protocol

To strictly prevent data leakage between historical training and held-out test records:

1. **Chronological Partitioning**: Training records ($t \le 2000$) precede test records ($t > 2000$). No random k-fold shuffling or future lookback is permitted.
2. **Preprocessing Isolation**: Feature standardizers (`StandardScaler`) are fit exclusively on the training matrix $X_{\text{train}}$. The learned mean $\mu_{\text{train}}$ and standard deviation $\sigma_{\text{train}}$ are applied to transform $X_{\text{test}}$:
   $$X_{\text{test, scaled}} = \frac{X_{\text{test}} - \mu_{\text{train}}}{\sigma_{\text{train}}}$$
3. **Climatology Isolation**: The seasonal climatology baseline is calculated strictly as the mean of training records for each target month. Test target values are never used to compute baseline lookups.
4. **Boundary Truncation**: Missing future targets and unobserved prior lags are explicitly dropped rather than forward-filled or imputed, ensuring that no artificial data enters the model evaluation.
