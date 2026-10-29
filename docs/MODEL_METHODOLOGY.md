# Machine Learning Methodology & Predictive Modeling

This document provides a comprehensive technical and mathematical specification of the machine learning architecture, feature scaling, baseline benchmarking, and out-of-sample evaluation implemented in the **Climate Trend Analyzer**.

**Project Author**: Akash Das  
**Module**: [`src/climate_analyzer/modeling.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/modeling.py)  
**Evaluated Data**: NOAA GHCN-Daily (`USW00094728`, NYC Central Park)  

---

## 1. Forecasting Task Definition

The forecasting task is structured as a **one-month-ahead monthly mean temperature prediction problem** on a long-term real-world meteorological series:

$$\text{Given observations up to month } t, \quad \text{Predict: } y_{t+1} = T_{\text{avg}}(t+1) \quad (^\circ\text{C})$$

### 1.1 Strict Temporal Split & Sample Reconciliation
To prevent temporal data leakage, standard random k-fold cross-validation is **strictly prohibited**. Instead, a chronological time-series partition is applied across the 1,893 continuous monthly intervals from January 1869 through September 2026:

#### Derivation of Modeling Samples (1,879 Valid Rows from 1,893 Continuous Months)
- **Continuous Calendar Span**: `1869-01-01` to `2026-09-01` = **1,893 continuous calendar months**.
- **Boundary Dropna Exclusions (14 rows dropped)**:
  1. **12 rows in 1869** (`1869-01` to `1869-12`): Missing multi-month lookback lags (`tavg_lag_1`, `tavg_lag_2`, `tavg_lag_12`, `rolling_tavg_12m`), as station observations began in January 1869.
  2. **1 row in 1870** (`1870-05`): Missing `tavg_lag_12` because May 1869 had an unobserved 7-day gap (only 24 valid days, below the 25-day threshold) and was correctly preserved as `NaN` without synthetic fabrication.
  3. **1 row in 2026** (`2026-09`): Missing `target_next_tavg` because the subsequent target month (October 2026) has only 24 observed days (data ends October 24, 2026) and was excluded by the 25-day validity threshold.
- **Total Valid Modeling Samples**: $1,893 - 14 = \mathbf{1,879 \text{ samples}}$.

#### Train and Held-Out Test Partitions (Target-Date Split Policy)
To ensure the training targets strictly conclude at or before the end of the year 2000 and the held-out test evaluation strictly spans the 21st-century record (2001–2026), a **Target-Date Partition Policy** is enforced:

| Dataset Partition | Feature Months ($t$) | Target Months ($t+1$) | Sample Count | Role in Modeling |
| :--- | :--- | :--- | :---: | :--- |
| **Training Set** | January 1870 – November 2000 | February 1870 – December 2000 | **1,570 months** | Parameter estimation, scaler fitting, baseline lookup |
| **Held-Out Test Set** | December 2000 – August 2026 | January 2001 – September 2026 | **309 months** | Unseen out-of-sample evaluation and baseline comparison |

> [!IMPORTANT]
> **Resolution of Boundary Target Dates & Zero-Leakage Verification**:
> 1. **Strict Target Alignment**:
>    - Every target in the training partition occurred between February 1870 and December 2000 ($t+1 \le \text{2000-12}$).
>    - Every target in the held-out test partition occurred in the 21st century between January 2001 and September 2026 ($t+1 \ge \text{2001-01}$).
> 2. **Information Boundary at Forecast Origin**:
>    - To forecast January 2001 (the first test target), the model is evaluated at the close of December 2000 ($t = \text{2000-12}$) using strictly observed historical data up to month $t$.
>    - Preprocessing transformations (`StandardScaler`) and historical seasonal averages (`climatology_lookup`) are fit strictly on the 1,570 training rows ($t+1 \le \text{2000-12}$) and applied downstream without refitting.
>    - Zero test-period observations are accessed during feature standardization, baseline creation, or model training.

---

## 2. Machine Learning Pipeline Architecture

The primary predictive model is an $L_2$-regularized linear regressor (**Ridge Regression**) wrapped in a scikit-learn `Pipeline` alongside a standardizer:

$$\text{Pipeline} = \left[ \text{StandardScaler}(), \; \text{Ridge}(\alpha = 10.0) \right]$$

### 2.1 Why Ridge Regression?
Meteorological lagged features (e.g., $T_t, T_{t-1}, T_{t-2}$, and rolling averages) exhibit substantial **multicollinearity**. In ordinary least squares (OLS), strong collinearity inflates the variance of estimated coefficients:

$$\mathbf{w}_{\text{OLS}} = (\mathbf{X}^T \mathbf{X})^{-1} \mathbf{X}^T \mathbf{y}$$

When columns of $\mathbf{X}$ are collinear, $\mathbf{X}^T \mathbf{X}$ is ill-conditioned (near-singular determinant). Ridge regression introduces a penalty on the squared magnitude of coefficients ($L_2$ regularization), conditioning the inversion:

$$\mathbf{w}_{\text{Ridge}} = (\mathbf{X}^T \mathbf{X} + \alpha \mathbf{I})^{-1} \mathbf{X}^T \mathbf{y}$$

The objective function minimized during training is:

$$J(\mathbf{w}, b) = \frac{1}{2N} \sum_{i=1}^N \left( y_i - (\mathbf{w}^T \mathbf{x}_i + b) \right)^2 + \frac{\alpha}{2} \|\mathbf{w}\|_2^2$$

where:
- $N = 1,570$ (number of training months)
- $\mathbf{x}_i \in \mathbb{R}^{10}$ (standardized feature vector for month $i$)
- $y_i \in \mathbb{R}$ (observed mean temperature for month $i+1$)
- $\alpha = 10.0$ (regularization hyperparameter)
- $\|\mathbf{w}\|_2^2 = \sum_{j=1}^{10} w_j^2$ (squared Euclidean norm)

### 2.2 Necessity of `StandardScaler`
Regularization penalties apply uniformly to all coefficient magnitudes $w_j$. If features are unstandardized:
- `time_fraction` spans values from $\approx 1870$ to $2000$ (scale $10^3$).
- `sin_month` and `cos_month` span $[-1.0, 1.0]$ (scale $10^0$).
- `prcp_lag_1` spans $[0.0, 350.0]$ mm (scale $10^2$).

Without scaling, the $L_2$ penalty would disproportionately suppress coefficients of small-scale variables while allowing large-scale variables to dominate. The `StandardScaler` maps each feature to zero mean and unit variance:

$$z_{ij} = \frac{x_{ij} - \mu_{j, \text{train}}}{\sigma_{j, \text{train}}}$$

---

## 3. Feature Set & Learned Model Coefficients

The model takes 10 physical and temporal features engineered from preceding months:

| Feature Name | Meteorological & Physical Meaning | Scaled Ridge Coefficient ($w_j$) | Learned Impact |
| :--- | :--- | :---: | :--- |
| `cos_month` | Cyclical month projection ($\cos(2\pi m / 12)$) | **-6.277** | Primary driver of seasonal heating/cooling cycle |
| `tavg_mean` | Current month's mean temperature ($T_t$) | **+2.010** | Autoregressive thermal persistence |
| `sin_month` | Cyclical month projection ($\sin(2\pi m / 12)$) | **+0.804** | Seasonal phase alignment (solstice vs. equinox) |
| `rolling_tavg_3m` | 3-month rolling average temperature | **+0.697** | Multi-month thermal inertia |
| `tavg_lag_12` | Same-month temperature from previous year ($T_{t-12}$) | **+0.588** | Interannual annual memory |
| `time_fraction` | Continuous decimal calendar year | **+0.355** | Secular long-term warming trend |
| `tavg_lag_1` | 1-month lookback temperature ($T_{t-1}$) | **+0.274** | Short-term thermal persistence |
| `rolling_tavg_12m` | 12-month rolling average temperature | **+0.042** | Annual climatic baseline level |
| `prcp_lag_1` | 1-month lookback precipitation ($P_{t-1}$) | **+0.030** | Soil moisture feedback proxy |
| `tavg_lag_2` | 2-month lookback temperature ($T_{t-2}$) | **-0.395** | Negative momentum correction |

---

## 4. Benchmark Models & Baselines

To rigorously evaluate the machine learning model, two standard climatological baselines are computed:

### 4.1 Baseline 1: Seasonal Climatology (Monthly Historical Mean)
This baseline reflects the historical expected value for calendar month $m$, calculated exclusively from the training dataset (1870–2000):

$$\hat{y}_{t+1}^{\text{Clim}} = \bar{T}_{\text{train}}(m_{t+1}) = \frac{1}{|\mathcal{S}_{m_{t+1}}|} \sum_{k \in \mathcal{S}_{m_{t+1}}} y_k$$

where $\mathcal{S}_{m}$ represents the set of all training months corresponding to calendar month $m \in \{1, 2, \dots, 12\}$.
- **Physical Interpretation**: "Next month's temperature will equal the long-term average temperature of that calendar month between 1870 and 2000."
- **Properties**: Captures 100% of the periodic seasonal climatology, but possesses zero sensitivity to current weather inertia, interannual modes, or secular warming trends.

### 4.2 Baseline 2: Persistence Baseline (Naive Lookback)
This naive baseline assumes the weather regime remains unchanged from the previous month:

$$\hat{y}_{t+1}^{\text{Pers}} = y_t$$

- **Physical Interpretation**: "Next month will have the exact same temperature as this month."
- **Properties**: While effective for hourly or daily weather where autocorrelation approaches $0.95$, monthly persistence suffers severely during transition seasons (e.g., September to October or March to April) where monthly temperatures shift by $6^\circ\text{C}$ to $8^\circ\text{C}$.

---

## 5. Out-of-Sample Empirical Results

All models were evaluated on the **exact same 309 held-out test months** (target dates: January 2001 – September 2026; feature origins: December 2000 – August 2026):

### 5.1 Absolute Temperature Forecasting Performance

| Model Architecture | Test RMSE ($^\circ\text{C}$) | Test MAE ($^\circ\text{C}$) | Out-of-Sample $R^2$ | Performance Relative to Climatology |
| :--- | :---: | :---: | :---: | :---: |
| **Ridge ML Regressor** | **1.674** | **1.335** | **0.963** | **21.92% Error Reduction** (Improvement) |
| **Seasonal Climatology** | 2.143 | 1.660 | 0.939 | Reference Baseline (0.0%) |
| **Persistence Baseline** | 4.847 | 4.257 | 0.686 | +126.14% Higher Error |

### 5.2 Deseasonalized Temperature Anomaly Forecasting Performance
When evaluated on temperature anomalies relative to the training climatological baseline (removing the astronomical solar cycle):

| Model Architecture | Anomaly RMSE ($^\circ\text{C}$) | Anomaly MAE ($^\circ\text{C}$) | Anomaly $R^2$ |
| :--- | :---: | :---: | :---: |
| **Ridge ML Regressor** | **1.674** | **1.335** | **+0.059** |
| **Seasonal Climatology (Anomaly = 0)** | 2.143 | 1.660 | -0.544 |
| **Persistence Baseline** | 4.847 | 4.257 | -6.883 |

---

## 6. Scientific Interpretation of High $R^2$ (0.963 vs. 0.939)

### 6.1 The Dominance of the Annual Solar Cycle
In mid-latitude terrestrial locations like New York City (Lat 40.8° N), surface air temperature is heavily dominated by the annual astronomical cycle of solar insolation:
- January monthly average: $\approx 0.5^\circ\text{C}$
- July monthly average: $\approx 25.0^\circ\text{C}$
- Total annual temperature range: $\approx 24.5^\circ\text{C}$

Because the periodic seasonal cycle is deterministic and massive, **the zero-intelligence Seasonal Climatology baseline alone achieves an $R^2$ of 0.939** on the test set:

$$R^2_{\text{Clim}} = 1 - \frac{\text{MSE}_{\text{Clim}}}{\text{Var}(y_{\text{test}})} = 1 - \frac{2.1434^2}{74.72} \approx 1 - \frac{4.594}{74.72} = 0.9385 \to 0.939$$

### 6.2 The Actual Added Value of Machine Learning
The machine learning model's achievement is that it **compresses the remaining unexplained variance by an additional 39.04%**:

$$\text{MSE}_{\text{Clim}} = 4.594 \; (^\circ\text{C})^2 \quad \longrightarrow \quad \text{MSE}_{\text{Ridge}} = 2.801 \; (^\circ\text{C})^2$$

This yields an absolute error reduction of **0.470 °C RMSE** (a 21.92% improvement in root mean squared error).
