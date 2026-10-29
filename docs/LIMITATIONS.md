# Scientific Limitations & Analytical Boundaries

This document articulates the constraints, caveats, and theoretical boundaries of the analytical routines in the **Climate Trend Analyzer**.

**Author**: Akash Das  
**Current Status**: Active  

---

## 1. Statistical Forecasting vs. Physical General Circulation Models (GCMs)

> [!CAUTION]
> **Fundamental Distinction**:
> The machine learning models and regression routines implemented in this project are purely **empirical time-series tools**. They are **not** General Circulation Models (GCMs) or Earth System Models (ESMs).

- **Omission of Physical Thermodynamics**: Statistical models do not resolve Navier-Stokes fluid dynamics, radiative transfer equations, ocean-atmosphere energy exchanges, cloud microphysics, or greenhouse gas radiative forcing curves.
- **Stationarity Assumption**: Empirical models assume statistical continuity of historical relationships. They cannot predict non-linear tipping points or shifts driven by future emissions scenarios (e.g., SSP pathways).
- **Intended Use**: Historical trend quantification, climate monitoring, and diagnostic modeling—not long-range climate policy projection.

---

## 2. Station-Level Observational Caveats

- **Urban Heat Island (UHI) Effect**:
  - The primary station analyzed (`USW00094728`, NYC Central Park) is situated in a major urban metropolitan area that grew dramatically between 1869 and 2026.
  - While Central Park provides a relatively stable parkland microclimate, surrounding urban development contributes to an elevated local warming signal compared to rural stations.
- **Historical Instrumentation Changes & Observer Artifacts**:
  - Across a 157-year record, thermometer types, sheltering (e.g., Cotton Region Shelter adoption in the late 19th century), and observation schedules shifted.
  - Minor observer transcription artifacts (such as two 1890s days where TMIN was transcribed above TMAX) are preserved as recorded, flagged with `is_inverted_temp = True`, and evaluated without introducing artificial data mutations.
- **Single Station Geographic Scope**:
  - An analysis of New York City Central Park reflects local and regional climatology. Global mean surface temperature anomalies cannot be directly inferred from an individual station record without integrating hemispheric or global station networks.

---

## 3. Daily Mean Temperature ($T_{\text{avg}}$) Midpoint Proxy

- In the absence of continuous 24-hour electronic temperature logging (which NOAA provides for only 4.59% of records at this station), daily mean temperature is calculated as:
  $$T_{\text{avg}} = \frac{T_{\text{max}} + T_{\text{min}}}{2.0}$$
- **Asymmetric Diurnal Profiles**: Real diurnal temperature curves are rarely perfect sinusoids. Prolonged cloud cover, nocturnal inversions, or midday cold front passages cause the true 24-hour time-integrated mean temperature to deviate slightly from the midpoint proxy (typically within $\pm 0.3^\circ\text{C}$).
- **Corrupted Native Placeholders**: Native NOAA TAVG contains known QC-flagged anomalies (such as -17.8 °C in July/August with flag 'G'), making the midpoint proxy essential for a homogeneous, uncorrupted series.

---

## 4. One-Month Forecast Horizon Boundary

- The machine learning model is engineered specifically for a **one-month-ahead ($t+1$) horizon**.
- Attempting to recursively iterate the model for multi-year or decadal projections without coupling to full physical ocean-atmosphere models leads to rapid variance collapse toward climatological mean values.

---

## 5. Serial Autocorrelation & Hypothesis Testing

- **Serial Dependence**: Annual mean anomalies exhibit strong positive lag-1 autocorrelation ($\rho_1 = 0.616$), driven by oceanic thermal inertia and persistent multi-year climate modes (e.g., AMO, PDO).
- **Impact on Significance**: Ordinary Least Squares standard error formulas assume serially independent residuals ($\epsilon_t \sim \text{i.i.d.}$). With $\rho_1 = 0.616$, the effective sample size is reduced from 157 to $N_{\text{eff}} \approx 37$, causing nominal OLS standard errors ($0.0113$ °C/decade) and nominal $p$-values ($2.55 \times 10^{-30}$) to be overconfident.
- **Implemented Mitigations**:
  1. **Newey-West HAC Covariance Estimator**: Accounts for serial autocorrelation in the OLS regression residuals. The HAC standard error is **0.0129 °C/decade** ($t = 12.58, p_{\text{HAC}} < 10^{-24}$), establishing that the warming rate (+0.162 °C/decade) remains overwhelmingly statistically significant.
  2. **Modified Mann-Kendall Test (Yue & Wang 2004)**: Computes the variance inflation factor $\text{VIF} = (1 + \rho_1) / (1 - \rho_1) = 4.21$, adjusting the variance from $434,052.7$ to $1,826,500.0$. The adjusted statistic is $Z^* = +5.09$, yielding an adjusted two-sided $p^* = 3.56 \times 10^{-7} < 10^{-6}$, confirming a monotonic warming trend beyond statistical doubt.
- **Retraction of 'Steady Warming' Claims**:
  - Close agreement between OLS slope (+0.162 °C/dec) and Sen's slope (+0.161 °C/dec) demonstrates mathematical robustness against outlier years, but does **not** prove steady or uniform warming across the historical record.
  - The record contains distinct multi-decadal phases: early warming (1870–1940), mid-century plateau/cooling (~1940–1970) linked to aerosol masking, and accelerated post-1970 warming (+0.36 °C/decade) dominated by greenhouse forcing and urban heat island effects.
