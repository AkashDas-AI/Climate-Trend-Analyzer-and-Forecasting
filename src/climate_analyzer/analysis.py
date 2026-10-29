"""Statistical Trend Analysis and Hypothesis Testing Module.

Implements OLS Linear Trends with Newey-West HAC Standard Errors,
Non-Parametric Mann-Kendall Test with Autocorrelation Variance Correction,
and Sen's Slope Estimator.

Scientific Interpretation & Attribution Boundary:
1. Empirical Findings: The station record at NYC Central Park demonstrates a statistically
   significant monotonic warming trend (+0.162 °C/decade over 1869–2025).
2. Robustness: Agreement between OLS slope and Sen's slope establishes mathematical robustness
   against single-year outlier extremes, but does NOT imply uniform or 'steady warming'
   across the 157-year record.
3. Multi-Decadal Dynamics: Historical observations exhibit non-linear phases: early-century
   warming (1870–1940), mid-century plateau/cooling (~1940–1970), and accelerated post-1970
   warming (+0.36 °C/decade).
4. Physical Hypotheses vs. Causal Attribution: In peer-reviewed literature, such decadal
   patterns are typically linked to combinations of greenhouse gas radiative forcing,
   tropospheric sulfate aerosols, ocean-atmosphere circulation modes, and urban heat island effects.
   However, empirical analysis of a single weather station cannot perform formal causal
   attribution or partition the relative contributions of these mechanisms, and a single
   terrestrial station record is not equivalent to a global temperature index.

Author: Akash Das
"""

from typing import Any
import numpy as np
import pandas as pd
from scipy import stats


def _format_p_value_bound(p: float) -> str:
    """Format very small p-values as scientific bounds rather than naive 0.0000."""
    if p < 1e-24:
        return "< 1e-24"
    elif p < 1e-10:
        power = int(np.floor(np.log10(p))) if p > 0 else 24
        return f"< 1e{power}"
    elif p < 0.001:
        return f"{p:.2e}"
    else:
        return f"{p:.4f}"


def _newey_west_hac_stderr(
    x: np.ndarray,
    y: np.ndarray,
    slope: float,
    intercept: float,
    max_lags: int | None = None,
) -> tuple[float, float, float, float, float, float, int]:
    """Calculate Newey-West Heteroskedasticity and Autocorrelation Consistent (HAC) standard error.

    Uses a Bartlett triangular kernel with automatic lag selection L = floor(4 * (n / 100)^(2/9)).
    Computes both asymptotic SE and finite-sample corrected SE (multiplier n / (n - k) with k = 2).
    Computes p-values using Student's t-distribution with df = n - 2.

    Returns:
        (hac_se_asymp, t_asymp, p_asymp, hac_se_fs, t_fs, p_fs, degrees_of_freedom)
    """
    n = len(y)
    if n < 4:
        return 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, max(1, n - 2)

    df = n - 2
    X = np.column_stack([np.ones(n), x - np.mean(x)])
    e = y - (intercept + slope * x)

    if max_lags is None:
        L = int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    else:
        L = max_lags
    L = max(1, min(L, n - 2))

    XtX_inv = np.linalg.inv(X.T @ X)
    S = (X.T * (e**2)) @ X
    for lag in range(1, L + 1):
        w = 1.0 - (lag / (L + 1.0))
        gamma = (X[lag:].T * e[lag:]) @ (e[:-lag, None] * X[:-lag])
        S += w * (gamma + gamma.T)

    # 1. Asymptotic covariance matrix (standard Newey-West)
    V_asymp = XtX_inv @ S @ XtX_inv
    hac_se_asymp = float(np.sqrt(max(0.0, V_asymp[1, 1])))

    # 2. Finite-sample corrected covariance matrix (n / (n - k) with k = 2)
    V_fs = V_asymp * (n / df)
    hac_se_fs = float(np.sqrt(max(0.0, V_fs[1, 1])))

    if hac_se_asymp > 0:
        t_asymp = float(slope / hac_se_asymp)
        p_asymp = float(2.0 * (1.0 - stats.t.cdf(abs(t_asymp), df=df)))
    else:
        t_asymp = 0.0
        p_asymp = 1.0

    if hac_se_fs > 0:
        t_fs = float(slope / hac_se_fs)
        p_fs = float(2.0 * (1.0 - stats.t.cdf(abs(t_fs), df=df)))
    else:
        t_fs = 0.0
        p_fs = 1.0

    return hac_se_asymp, t_asymp, p_asymp, hac_se_fs, t_fs, p_fs, df


def calculate_linear_trend(
    time_series: np.ndarray | pd.Series,
    values: np.ndarray | pd.Series,
) -> dict[str, Any]:
    """Fit an Ordinary Least Squares (OLS) linear trend line with HAC standard errors.

    Args:
        time_series: 1D array of times (calendar years or fractional years).
        values: 1D array of climate observations.

    Returns:
        Dictionary with slope (°C/year), decadal_rate (°C/decade), intercept,
        r_squared, nominal p_value, Newey-West HAC standard errors (both asymptotic
        and finite-sample corrected, in °C/year and °C/decade), HAC t-statistics,
        degrees of freedom, and formatted scientific p-value bounds.
    """
    x = np.asarray(time_series, dtype=float)
    y = np.asarray(values, dtype=float)

    mask = ~np.isnan(x) & ~np.isnan(y)
    x_clean = x[mask]
    y_clean = y[mask]

    if len(x_clean) < 2:
        raise ValueError("At least 2 valid points required to compute linear trend.")

    res = stats.linregress(x_clean, y_clean)
    slope = float(res.slope)
    intercept = float(res.intercept)
    decadal_rate = float(slope * 10.0)
    std_err = float(res.stderr) if res.stderr is not None else 0.0

    # Compute Newey-West HAC standard error to account for serial autocorrelation
    (
        hac_se_asymp,
        t_asymp,
        p_asymp,
        hac_se_fs,
        t_fs,
        p_fs,
        hac_df,
    ) = _newey_west_hac_stderr(x_clean, y_clean, slope, intercept)

    return {
        "slope_per_year": slope,
        "decadal_rate": decadal_rate,
        "intercept": intercept,
        "r_value": float(res.rvalue),
        "r_squared": float(res.rvalue ** 2),
        "p_value": float(res.pvalue),
        "p_value_bound": _format_p_value_bound(float(res.pvalue)),
        "std_err": std_err,
        "decadal_std_err": std_err * 10.0,
        "hac_std_err": hac_se_asymp,
        "hac_decadal_std_err": hac_se_asymp * 10.0,
        "hac_t_stat": t_asymp,
        "hac_p_value": p_asymp,
        "hac_p_value_bound": _format_p_value_bound(p_asymp),
        "hac_std_err_fs": hac_se_fs,
        "hac_decadal_std_err_fs": hac_se_fs * 10.0,
        "hac_t_stat_fs": t_fs,
        "hac_p_value_fs": p_fs,
        "hac_p_value_fs_bound": _format_p_value_bound(p_fs),
        "hac_df": hac_df,
    }


def mann_kendall_test(
    series: np.ndarray | pd.Series,
    adjust_autocorr: bool = True,
) -> dict[str, Any]:
    """Perform the non-parametric Mann-Kendall test for monotonic trends.

    Includes nominal test statistics, Yue & Wang (2004) AR(1) variance correction
    (conservative upper-bound penalty on raw series), and detrended residual
    autocorrelation diagnostics.

    Args:
        series: 1D numerical array of observations ordered chronologically.
        adjust_autocorr: Whether to compute autocorrelation-adjusted variance and Z-score.

    Returns:
        Dict with test statistic S, nominal variance Var(S), adjusted variance Var*(S),
        nominal and adjusted Z scores, p-values, lag-1 autocorrelation rho1, VIF,
        detrended diagnostics, and trend classification.
    """
    x = np.asarray(series, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)

    if n < 3:
        raise ValueError("At least 3 observations are required for Mann-Kendall test.")

    # Calculate S statistic: sum(sgn(x_j - x_i)) for i < j
    s = 0
    for i in range(n - 1):
        s += int(np.sum(np.sign(x[i + 1:] - x[i])))

    # Compute variance accounting for ties
    unique_vals, counts = np.unique(x, return_counts=True)
    tie_adjustment = np.sum(counts * (counts - 1) * (2 * counts + 5))

    var_s = float((n * (n - 1) * (2 * n + 5) - tie_adjustment) / 18.0)

    # Compute standardized test statistic Z (nominal)
    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0

    # Two-tailed nominal p-value
    p_value = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))

    # 1. Raw series lag-1 serial autocorrelation & conservative AR(1) VIF (Yue & Wang 2004)
    x_mean = np.mean(x)
    denom = np.sum((x - x_mean) ** 2)
    if denom > 0 and n > 1:
        rho1 = float(np.sum((x[:-1] - x_mean) * (x[1:] - x_mean)) / denom)
    else:
        rho1 = 0.0

    if adjust_autocorr and 0.0 < rho1 < 0.99:
        vif = float((1.0 + rho1) / (1.0 - rho1))
    else:
        vif = 1.0

    var_s_adj = float(var_s * vif)

    if s > 0:
        z_adj = float((s - 1) / np.sqrt(var_s_adj))
    elif s < 0:
        z_adj = float((s + 1) / np.sqrt(var_s_adj))
    else:
        z_adj = 0.0

    p_value_adj = float(2.0 * (1.0 - stats.norm.cdf(abs(z_adj))))

    # 2. Detrended residual autocorrelation (removes secular Sen's slope first)
    slopes: list[float] = []
    for i in range(n - 1):
        dx = np.arange(i + 1, n) - i
        dy = x[i + 1:] - x[i]
        valid = dx != 0
        if np.any(valid):
            slopes.extend((dy[valid] / dx[valid]).tolist())
    beta = float(np.median(slopes)) if slopes else 0.0
    x_detrended = x - beta * np.arange(n)
    xd_mean = np.mean(x_detrended)
    xd_denom = np.sum((x_detrended - xd_mean) ** 2)
    if xd_denom > 0 and n > 1:
        rho1_detrended = float(np.sum((x_detrended[:-1] - xd_mean) * (x_detrended[1:] - xd_mean)) / xd_denom)
    else:
        rho1_detrended = 0.0

    if adjust_autocorr and 0.0 < rho1_detrended < 0.99:
        vif_detrended = float((1.0 + rho1_detrended) / (1.0 - rho1_detrended))
    else:
        vif_detrended = 1.0

    var_s_adj_det = float(var_s * vif_detrended)
    z_adj_det = float((s - 1) / np.sqrt(var_s_adj_det)) if s > 0 else (float((s + 1) / np.sqrt(var_s_adj_det)) if s < 0 else 0.0)
    p_value_adj_det = float(2.0 * (1.0 - stats.norm.cdf(abs(z_adj_det))))

    trend = "no trend"
    if p_value < 0.05:
        trend = "increasing" if z > 0 else "decreasing"

    trend_adj = "no trend"
    if p_value_adj < 0.05:
        trend_adj = "increasing" if z_adj > 0 else "decreasing"

    return {
        "s": s,
        "var_s": var_s,
        "var_s_adj": var_s_adj,
        "z": float(z),
        "z_adj": z_adj,
        "p_value": p_value,
        "p_value_adj": p_value_adj,
        "p_value_bound": _format_p_value_bound(p_value),
        "p_value_adj_bound": _format_p_value_bound(p_value_adj),
        "rho1": rho1,
        "vif": vif,
        "rho1_detrended": rho1_detrended,
        "vif_detrended": vif_detrended,
        "var_s_adj_detrended": var_s_adj_det,
        "z_adj_detrended": z_adj_det,
        "p_value_adj_detrended_bound": _format_p_value_bound(p_value_adj_det),
        "trend": trend,
        "trend_adj": trend_adj,
        "is_significant": bool(p_value < 0.05),
        "is_significant_adj": bool(p_value_adj < 0.05),
    }


def sens_slope(
    time_series: np.ndarray | pd.Series,
    values: np.ndarray | pd.Series,
) -> dict[str, float]:
    """Calculate Sen's non-parametric slope estimator (median of pairwise slopes).

    Args:
        time_series: 1D array of observation times.
        values: 1D array of values.

    Returns:
        Dict with slope (°C/year), decadal_rate (°C/decade), and intercept.
    """
    x = np.asarray(time_series, dtype=float)
    y = np.asarray(values, dtype=float)
    mask = ~np.isnan(x) & ~np.isnan(y)
    x = x[mask]
    y = y[mask]
    n = len(x)

    if n < 2:
        raise ValueError("At least 2 points required for Sen's slope calculation.")

    # Subsample if n is very large to maintain computational tractability
    if n > 2000:
        step = int(np.ceil(n / 1000))
        x = x[::step]
        y = y[::step]
        n = len(x)

    slopes: list[float] = []
    for i in range(n - 1):
        dx = x[i + 1:] - x[i]
        dy = y[i + 1:] - y[i]
        valid = dx != 0
        if np.any(valid):
            slopes.extend((dy[valid] / dx[valid]).tolist())

    median_slope = float(np.median(slopes))
    intercept = float(np.median(y - median_slope * x))

    return {
        "sens_slope_per_year": median_slope,
        "sens_decadal_rate": median_slope * 10.0,
        "sens_intercept": intercept,
    }


def calculate_decadal_summary(
    df: pd.DataFrame,
    value_col: str = "annual_tavg",
) -> pd.DataFrame:
    """Group climate observations by decade and compute statistical aggregates.

    Args:
        df: DataFrame with 'year' and the target value column.
        value_col: Column name to aggregate.

    Returns:
        Decade-level summary DataFrame.
    """
    temp_df = df.copy()
    temp_df["decade"] = (temp_df["year"] // 10) * 10

    summary = (
        temp_df.groupby("decade")
        .agg(
            mean_val=(value_col, "mean"),
            min_val=(value_col, "min"),
            max_val=(value_col, "max"),
            std_val=(value_col, "std"),
            record_count=("year", "count"),
        )
        .reset_index()
    )
    summary.rename(
        columns={
            "mean_val": f"mean_{value_col}",
            "min_val": f"min_{value_col}",
            "max_val": f"max_{value_col}",
            "std_val": f"std_{value_col}",
        },
        inplace=True,
    )
    return summary
