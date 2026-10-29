# Statistical Trend Analysis & Extreme Event Detection

This document provides a rigorous mathematical and scientific specification of the statistical methods implemented in the **Climate Trend Analyzer** for trend quantification, monotonic hypothesis testing, non-parametric slope estimation, serial autocorrelation assessment, and meteorological anomaly detection.

**Project Author**: Akash Das  
**Modules**:  
- [`src/climate_analyzer/analysis.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/analysis.py)  
- [`src/climate_analyzer/anomaly_detection.py`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/src/climate_analyzer/anomaly_detection.py)  
**Evaluated Data**: NOAA GHCN-Daily (`USW00094728`, NYC Central Park, 1869–2025, 157 complete annual records)  

---

## 1. Parametric Trend Quantification: Ordinary Least Squares (OLS)

Ordinary Least Squares regression models the annual mean temperature anomaly as a linear function of time:

$$y_t = \beta_0 + \beta_1 t + \epsilon_t, \quad \epsilon_t \sim \mathcal{N}(0, \sigma^2)$$

where $t$ represents the calendar year, $y_t$ is the annual mean temperature anomaly (°C relative to 1951–1980 baseline), $\beta_1$ is the annual rate of change, and $\beta_0$ is the intercept.

### 1.1 Closed-Form Formulas
$$\beta_1 = \frac{\sum_{i=1}^n (t_i - \bar{t})(y_i - \bar{y})}{\sum_{i=1}^n (t_i - \bar{t})^2}$$

$$\beta_0 = \bar{y} - \beta_1 \bar{t}$$

$$\text{Decadal Warming Rate} = \beta_1 \times 10.0 \quad (^\circ\text{C / decade})$$

Nominal standard error of the slope:

$$\text{SE}(\beta_1) = \sqrt{\frac{\sum_{i=1}^n (y_i - \hat{y}_i)^2}{(n - 2) \sum_{i=1}^n (t_i - \bar{t})^2}}$$

#### Newey-West Heteroskedasticity and Autocorrelation Consistent (HAC) Standard Error
Because climate anomaly series exhibit positive serial correlation ($\rho_1 \approx 0.616$), nominal OLS standard errors underestimate variance. We compute the Newey-West HAC covariance estimator using a Bartlett triangular kernel with automatic lag selection $L = \lfloor 4 (n / 100)^{2/9} \rfloor = 4$:

$$\hat{\Omega} = \hat{\Gamma}_0 + \sum_{j=1}^L \left(1 - \frac{j}{L + 1}\right) (\hat{\Gamma}_j + \hat{\Gamma}_j^T)$$

$$\text{Var}_{\text{HAC}}(\hat{\beta}) = (X^T X)^{-1} X^T \hat{\Omega} X (X^T X)^{-1}$$

$$\text{SE}_{\text{HAC}}(\beta_1) = \sqrt{\text{Var}_{\text{HAC}}(\hat{\beta})_{1,1}}$$

**HAC Reporting Conventions**:
- **Default Convention (Asymptotic)**: The unadjusted Newey-West (1987) asymptotic covariance estimator $\text{SE}_{\text{HAC, asymp}}$, evaluated with Student's $t$-distribution ($\text{df} = n - k = 155$).
- **Finite-Sample Corrected Convention**: Scaled by the degrees-of-freedom multiplier $\sqrt{n / (n - k)} = \sqrt{157 / 155} \approx 1.00643$. Both conventions are reported side-by-side to guarantee full transparency across econometric standards.

### 1.2 Empirical OLS Findings (1869–2025)
- **Slope ($\beta_1$)**: $+0.016183$ °C / year
- **Decadal Warming Rate**: **+0.162 °C / decade** (+0.16183 °C / decade)
- **Intercept ($\beta_0$)**: $-31.75$ °C
- **Coefficient of Determination ($R^2$)**: $0.5714$ ($r = 0.7559$)
- **Degrees of Freedom**: $\text{df} = n - 2 = 155$
- **Nominal Standard Error**: $0.001126$ °C / year ($0.01126$ °C / decade)
- **Nominal $p$-Value**: $< 10^{-24}$ ($2.55 \times 10^{-30}$)
- **Newey-West HAC Standard Error ($L=4$, Default Asymptotic)**: $0.001286$ °C / year (**0.01286 °C / decade**)
  - Asymptotic $t$-Statistic: **12.58**
  - Asymptotic $p$-Value (Student's $t$, $\text{df}=155$): **$< 10^{-24}$** ($2.92 \times 10^{-25}$)
- **Newey-West HAC Standard Error ($L=4$, Finite-Sample Corrected)**: $0.001295$ °C / year (**0.01295 °C / decade**)
  - Finite-sample scaling factor: $\sqrt{n / (n - k)} = \sqrt{157 / 155} \approx 1.00643$
  - Finite-Sample $t$-Statistic: **12.50**
  - Finite-Sample $p$-Value (Student's $t$, $\text{df}=155$): **$< 10^{-24}$** ($4.45 \times 10^{-25}$)

### 1.3 Newey-West Lag Sensitivity Analysis
To confirm that the inference does not depend arbitrarily on the lag choice $L = 4$, a sensitivity analysis was executed across $L \in [0, 10]$ using the exact same implementation:

| Truncation Lag $L$ | Kernel Weights | Asymptotic HAC SE (°C/dec) | Finite-Sample SE (°C/dec) | $t$-Statistic (Asymp / FS) | $p$-Value (Student's $t$, $\text{df}=155$) |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **0** (White HC) | No lag terms | 0.01136 | 0.01143 | 14.25 / 14.15 | $< 10^{-24}$ |
| **1** | Bartlett (0.50) | 0.01237 | 0.01245 | 13.09 / 13.00 | $< 10^{-24}$ |
| **2** | Bartlett (0.67, 0.33) | 0.01264 | 0.01272 | 12.80 / 12.72 | $< 10^{-24}$ |
| **3** | Bartlett (0.75, 0.50, 0.25) | 0.01272 | 0.01280 | 12.72 / 12.64 | $< 10^{-24}$ |
| **4** (Default) | Bartlett (0.80, 0.60, 0.40, 0.20) | **0.01286** | **0.01295** | **12.58 / 12.50** | **$< 10^{-24}$** |
| **5** | Bartlett (0.83 to 0.17) | 0.01282 | 0.01290 | 12.62 / 12.54 | $< 10^{-24}$ |
| **6** | Bartlett (0.86 to 0.14) | 0.01268 | 0.01276 | 12.76 / 12.68 | $< 10^{-24}$ |
| **8** | Bartlett (0.89 to 0.11) | 0.01264 | 0.01272 | 12.81 / 12.72 | $< 10^{-24}$ |
| **10** | Bartlett (0.91 to 0.09) | 0.01262 | 0.01271 | 12.82 / 12.74 | $< 10^{-24}$ |

**Conclusion**: The standard error is **relatively stable over the tested lags** ($0.0124$ to $0.0130$ °C/decade for $L \ge 1$), and the $t$-statistic consistently exceeds $12.5$, demonstrating that the finding of statistical significance does not hinge on lag parameter tuning.

---

## 2. Non-Parametric Hypothesis Testing: Mann-Kendall Test

While OLS provides an intuitive slope, geophysical time series frequently violate classical Gauss-Markov assumptions:
1. Annual climate observations may not follow a strictly Gaussian distribution.
2. Extreme weather events create high-leverage outliers.

To rigorously confirm whether warming is genuine without assuming normality, the **Mann-Kendall test** (Mann 1945; Kendall 1975) is implemented.

### 2.1 Hypotheses
- **Null Hypothesis ($H_0$)**: The data $x_1, x_2, \dots, x_n$ are independent and identically distributed. There is no monotonic trend over time.
- **Alternative Hypothesis ($H_1$)**: A monotonic increasing or decreasing trend exists.

### 2.2 Test Statistic $S$
The Mann-Kendall statistic $S$ evaluates the signs of all $n(n-1)/2$ pairwise differences across the chronological sequence:

$$S = \sum_{k=1}^{n-1} \sum_{j=k+1}^n \text{sgn}(x_j - x_k)$$

where the sign function is defined as:

$$\text{sgn}(\theta) = \begin{cases} +1 & \text{if } \theta > 0 \\ 0 & \text{if } \theta = 0 \\ -1 & \text{if } \theta < 0 \end{cases}$$

A positive $S$ indicates that later observations are systematically warmer than earlier observations.

### 2.3 Variance with Tie Correction
When identical values exist in the time series (ties), the variance of $S$ is adjusted:

$$\text{Var}(S) = \frac{n(n-1)(2n+5) - \sum_{p=1}^g t_p(t_p-1)(2t_p+5)}{18}$$

where $g$ is the number of tied groups and $t_p$ is the number of data points in group $p$.

### 2.4 Standardized Test Statistic $Z$ and Significance
For sample sizes $n > 10$, $S$ is asymptotically normal. The continuity-corrected test statistic $Z$ is computed as:

$$Z = \begin{cases} \frac{S-1}{\sqrt{\text{Var}(S)}} & \text{if } S > 0 \\ 0 & \text{if } S = 0 \\ \frac{S+1}{\sqrt{\text{Var}(S)}} & \text{if } S < 0 \end{cases}$$

The two-tailed $p$-value is evaluated from the standard normal cumulative distribution function $\Phi(Z)$:

$$p = 2 \cdot \left( 1 - \Phi(|Z|) \right)$$

### 2.5 Modified Mann-Kendall Test for Autocorrelated Data (Published Methodologies)
When a time series exhibits positive serial autocorrelation ($\rho_k > 0$), observations violate the independence assumption of the classical Mann-Kendall test. Positive serial persistence inflates the probability of falsely rejecting the null hypothesis (inflated Type I error rate).

To account for serial autocorrelation, hydrological and climatological literature defines several approaches:
1. **Yue & Wang (2004)** (*Water Resources Management*, 18(3), 201–218):
   Approximates the effective sample size and variance inflation factor (VIF) under an AR(1) autoregressive process:
   $$\text{VIF} = 1 + 2 \sum_{k=1}^{n-1} \left(1 - \frac{k}{n}\right) \rho_k \approx \frac{1 + \rho_1}{1 - \rho_1}$$
   where $\rho_1$ is the lag-1 autocorrelation coefficient.
   $$\text{Var}^*(S) = \text{Var}(S) \times \text{VIF}$$
   The adjusted standardized test statistic $Z^*$ and two-tailed p-value are:
   $$Z^* = \begin{cases} \frac{S - 1}{\sqrt{\text{Var}^*(S)}} & \text{if } S > 0 \\ 0 & \text{if } S = 0 \\ \frac{S + 1}{\sqrt{\text{Var}^*(S)}} & \text{if } S < 0 \end{cases}, \quad p^* = 2 \cdot \left( 1 - \Phi(|Z^*|) \right)$$

2. **Trend Removal Prior to Autocorrelation Assessment (Bayazit & Önöz 2007; Yue et al. 2002)**:
   A deterministic trend inflates the sample autocorrelation coefficient $\rho_1$ calculated on raw anomalies. Therefore, standard procedure detrends the series by subtracting Sen's median slope ($y_t' = y_t - \beta \cdot t$) prior to computing the residual lag-1 autocorrelation $r_1$.

3. **Hamed & Rao (1998)** (*Journal of Hydrology*, 204(1-4), 182–196):
   Computes variance correction from ranks rather than values, summing only those autocorrelation coefficients whose magnitudes are statistically distinguishable from white noise at the 5% level ($\alpha = 0.05$):
   $$\text{White-Noise Band} = \pm \frac{1.96}{\sqrt{n}}$$

### 2.6 Empirical Mann-Kendall Findings (1869–2025, $n=157$)
- **Sample Size ($n$)**: 157 complete annual records (1869–2025)
- **Pairwise Comparisons**: $157 \times 156 / 2 = 12,246$ pairs
- **Mann-Kendall Statistic ($S$)**: **+6,882**
- **Nominal Variance ($\text{Var}(S)$)**: $434,052.67$ (accounting for ties)
- **Primary Non-Parametric Test (Nominal Mann-Kendall)**:
  - Nominal $Z$ Score: **+10.44**
  - Nominal $p$-Value Bound: **$< 10^{-24}$** (exact normal CDF tail $1.64 \times 10^{-25}$)
- **Provisional Detrended Residual AR(1) Diagnostic (Yue & Wang 2004 post-detrending)**:
  - Detrended Residual Lag-1 Autocorrelation ($r_1$): **0.1228**
  - Residual VIF: **1.2799**
  - Adjusted Variance ($\text{Var}^*(S)$): **555,534.5**
  - Adjusted $Z^*$ Score: **+9.23**
  - Adjusted $p^*$-Value Bound: **$< 10^{-19}$** ($2.65 \times 10^{-20}$)
- **Provisional Raw AR(1) Diagnostic (Yue & Wang 2004 on raw anomalies)**:
  - Raw Lag-1 Autocorrelation ($\rho_1$): **0.6160**
  - Raw AR(1) VIF: **4.2087**
  - Adjusted Variance ($\text{Var}^*(S)$): **1,826,777.6**
  - Adjusted $Z^*$ Score: **+5.09**
  - Adjusted $p^*$-Value Bound: **$3.56 \times 10^{-7} < 10^{-6}$**
- **Trend Conclusion**: **INCREASING** (Statistically significant beyond $\alpha = 0.0001$ under nominal variance, detrended residual variance, and raw AR(1) penalized variance)

---

## 3. Non-Parametric Slope Estimation: Sen's Slope (Theil-Sen)

To determine the magnitude of the trend without sensitivity to outlier extremes, **Sen's Slope Estimator** (Theil 1950; Sen 1968) is computed.

### 3.1 Mathematical Definition
Sen's slope is the median of all pairwise slopes across all distinct time steps $(i, j)$ with $j > i$:

$$Q_{ij} = \frac{x_j - x_i}{j - i} \quad \forall \; 1 \le i < j \le n$$

$$\text{Sen's Slope} = \text{median}\left( \{ Q_{ij} \} \right)$$

$$\text{Decadal Sen's Rate} = \text{Sen's Slope} \times 10.0 \quad (^\circ\text{C / decade})$$

Sen's slope has a breakdown point of approximately 29%, meaning nearly a third of the dataset can be arbitrary outliers without distorting the slope.

### 3.2 Empirical Sen's Slope Findings
- **Sen's Slope**: $+0.016103$ °C / year
- **Decadal Sen's Rate**: **+0.161 °C / decade** (+0.16103 °C / decade)
- **Sen's Intercept**: $-31.58$ °C

---

## 4. Serial Autocorrelation & Scientific Interpretation

### 4.1 Serial Persistence & Provisional Autoregressive Diagnostics
An empirical assessment of the annual anomaly series reveals positive serial autocorrelation:

$$\rho_1 = \text{Corr}(y_t, y_{t-1}) = \mathbf{0.6160}$$

- **Conflation of Deterministic Trend and Stochastic Persistence**:
  Computing lag-1 autocorrelation directly on the raw annual anomaly series yields $\rho_1 = 0.6160$. In non-stationary climate series, an underlying secular warming trend artificially inflates sample autocorrelation because earlier years are systematically cooler and later years warmer, producing low-frequency coherence even if stochastic noise is independent.
- **Detrended Residual Autocorrelation**:
  When the series is detrended by subtracting Sen's median slope ($y_t' = y_t - \beta \cdot t$, Bayazit & Önöz 2007), the residual lag-1 autocorrelation drops to:
  $$r_1 = \text{Corr}(y_t', y_{t-1}') = \mathbf{0.1228}$$
- **Sample White-Noise Confidence Limit & Its Interpretation**:
  For an independent and identically distributed sequence of sample size $n = 157$, sample autocorrelation coefficients have an asymptotic standard error of $1/\sqrt{n} \approx 0.0798$, giving an approximate 95% two-tailed Gaussian critical band:
  $$\text{Critical Band} = \pm \frac{1.96}{\sqrt{n}} = \pm \frac{1.96}{\sqrt{157}} \approx \pm 0.1564$$
  The detrended residual correlation $|r_1| = 0.1228$ falls within this band ($|r_1| < 0.1564$). However, **this sample white-noise band alone does not prove that the underlying stochastic process is pure white noise**, nor does it definitively validate the modified test against higher-order autoregressive processes ($\text{AR}(p)$), ARMA structures, or fractionally integrated long-memory persistence ($I(d)$).
- **Provisional Status of Modified Mann–Kendall Formulations**:
  Because peer-reviewed climatological and hydrological literature features conflicting methodologies regarding autocorrelation correction (e.g., variance inflation factors vs. trend-free pre-whitening vs. rank-based adjustments), **all modified Mann–Kendall calculations are classified as provisional sensitivity diagnostics**:
  1. **Primary Headline Result**: Ordinary Mann–Kendall with tie adjustment ($S = +6,882, Z = +10.44, p < 10^{-24}$).
  2. **Provisional Detrended AR(1) Diagnostic (Yue & Wang 2004 post-detrending)**: $r_1 = 0.1228 \to \text{VIF} = 1.2799, Z^* = +9.23, p < 10^{-19}$.
  3. **Provisional Raw AR(1) Diagnostic (Yue & Wang 2004 without detrending)**: $\rho_1 = 0.6160 \to \text{VIF} = 4.2087, Z^* = +5.09, p = 3.56 \times 10^{-7} < 10^{-6}$.
  *Note on Upper Bounds*: The raw-series VIF ($\text{VIF} = 4.21$) reflects an aggressive un-detrended AR(1) diagnostic heavily penalized by deterministic trend inflation. It must **not** be interpreted as a mathematically universal upper bound for arbitrary stochastic families (such as long-memory processes), but rather as an un-detrended AR(1) heuristic. Under all specifications, the null hypothesis of no monotonic trend is rejected at $p < 10^{-6}$.

### 4.2 Distinguishing Long-Term Trends from Steady Warming & Attribution Boundaries
> [!WARNING]
> **Scientific Interpretation & Attribution Boundary**:
> The close agreement between OLS (+0.162 °C/decade) and Sen's slope (+0.161 °C/decade) summarizes the net secular change over 157 years. It **must not** be interpreted as evidence that warming occurred steadily or linearly across the full record.
>
> In reality, the observational record exhibits substantial multi-decadal variability:
> 1. **Late 19th-Century Cold Regime**: The 1880s was the coldest decade on record (-1.77 °C anomaly).
> 2. **Mid-20th Century Plateau**: The 1950s–1970s saw a temporary cooling/plateau (-0.35 °C to -0.16 °C), which external literature frequently associates with regional sulfate aerosol masking and Atlantic Multidecadal Variability (AMV).
> 3. **Post-1980 Acceleration**: A pronounced acceleration occurred after 1980 (+0.12 °C in 1980s $\to$ +1.17 °C in 2010s $\to$ +1.47 °C in 2020s), consistent with global greenhouse gas forcing literature.
> 4. **Urban Microclimate Influence**: Central Park's surrounding metropolitan footprint grew from ~1 million residents in 1870 to over 8 million today, introducing a localized Urban Heat Island (UHI) component.
>
> **Attribution Limit**: Statistical analysis of a single station cannot isolate or quantify the specific fractional contribution of each causal mechanism, and one urban station is not a global temperature record.

---

## 5. Decadal Temperature Shifts

Aggregating annual observations into 10-year decadal bins highlights the non-linear chronological progression of temperature anomalies:

| Decade | Mean Annual Temperature (°C) | Mean Anomaly vs. 1951–1980 Baseline (°C) | Decadal Shift |
| :---: | :---: | :---: | :--- |
| **1870s** | 10.88 °C | -1.63 °C | Late 19th-century baseline |
| **1880s** | 10.74 °C | -1.77 °C | Coldest decade on record |
| **1890s** | 11.41 °C | -1.10 °C | Gradual rise |
| **1900s** | 11.19 °C | -1.32 °C | Early 20th century |
| **1910s** | 11.23 °C | -1.28 °C | Stable cold period |
| **1920s** | 11.36 °C | -1.15 °C | Moderate warming |
| **1930s** | 11.87 °C | -0.64 °C | Dust Bowl era warmth |
| **1940s** | 12.01 °C | -0.50 °C | Mid-century warming |
| **1950s** | 12.28 °C | -0.23 °C | Reference baseline period start |
| **1960s** | 12.16 °C | -0.35 °C | Regional aerosol cooling |
| **1970s** | 12.35 °C | -0.16 °C | Transition decade |
| **1980s** | 12.63 °C | +0.12 °C | Transition to positive anomalies |
| **1990s** | 13.08 °C | +0.57 °C | Rapid warming acceleration |
| **2000s** | 13.25 °C | +0.74 °C | Modern warming regime |
| **2010s** | 13.68 °C | +1.17 °C | Warmest complete decade |
| **2020s (to 2025)** | **13.98 °C** | **+1.47 °C** | Highest decadal average on record |

---

## 6. Meteorological Anomaly & Extreme Event Detection

### 6.1 Standardized Score ($Z$-Score) Filter
Identifies observations that deviate significantly from the long-term monthly mean in units of standard deviations:

$$z_t = \frac{x_t - \mu_m}{\sigma_m}$$

An observation is flagged as an extreme event if $|z_t| \ge 2.0$.

### 6.2 Interquartile Range (IQR) Non-Parametric Filter
A robust dispersion filter resistant to extreme value contamination:

$$\text{IQR}_m = Q_3(m) - Q_1(m)$$

$$\text{Thresholds} = [Q_1(m) - 1.5 \cdot \text{IQR}_m, \; Q_3(m) + 1.5 \cdot \text{IQR}_m]$$

### 6.3 Warmest Recorded Years in Station History (1869–2026)

| Historical Rank | Calendar Year | Annual Mean Temperature (°C) | Anomaly vs. 1951–1980 Baseline (°C) |
| :---: | :---: | :---: | :---: |
| **1** | **2024** | **14.40 °C** | **+1.89 °C** |
| **2** | **2023** | **14.39 °C** | **+1.88 °C** |
| **3** | **2012** | **14.06 °C** | **+1.55 °C** |
| **4** | **2020** | **14.05 °C** | **+1.54 °C** |
| **5** | **1991** | **14.00 °C** | **+1.48 °C** |

> [!NOTE]
> **Key Finding**: 4 out of the 5 warmest years in 157 years of records occurred in the last 15 years (2012, 2020, 2023, 2024). 2024 stands as the single warmest year in station history.
