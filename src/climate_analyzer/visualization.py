"""Visualization and Chart Export Module for Real Climate Analysis.

Generates publication-quality charts using Matplotlib and Seaborn based strictly on genuine observations.

Author: Akash Das
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")  # Safe non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


sns.set_theme(style="whitegrid", palette="deep")


def plot_historical_temperature_trend(
    df: pd.DataFrame,
    trend_dict: dict[str, float] | None = None,
    output_path: str | Path | None = None,
    station_name: str = "NYC Central Park (NOAA GHCN)",
    baseline_label: str = "1951–1980 Baseline",
) -> plt.Figure:
    """Plot historical temperature anomaly timeline with 5-yr and 10-yr rolling smoothers.

    Args:
        df: Annual feature DataFrame with 'year', 'annual_anomaly', and rolling means.
        trend_dict: Optional OLS linear trend results.
        output_path: Optional path to save figure.
        station_name: Station label for the title.
        baseline_label: Description of climatological reference period.

    Returns:
        Matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = ["#d73027" if val >= 0 else "#4575b4" for val in df["annual_anomaly"]]
    ax.bar(df["year"], df["annual_anomaly"], color=colors, alpha=0.55, width=0.8, label="Annual Anomaly")

    # Dynamically find rolling columns
    rolling_cols = [c for c in df.columns if c.startswith("rolling_mean_")]
    if rolling_cols:
        palette = ["#fc8d59", "#7f0000", "#984ea3"]
        for idx, col in enumerate(rolling_cols[:2]):
            clean_label = col.replace("rolling_mean_", "").replace("yr", "-Year").title() + " Moving Avg"
            ax.plot(df["year"], df[col], color=palette[idx % len(palette)], linewidth=2.0 + 0.5 * idx, label=clean_label)
    else:
        if "rolling_mean_5yr" in df.columns:
            ax.plot(df["year"], df["rolling_mean_5yr"], color="#fc8d59", linewidth=2.0, label="5-Year Moving Avg")
        if "rolling_mean_10yr" in df.columns:
            ax.plot(df["year"], df["rolling_mean_10yr"], color="#7f0000", linewidth=2.5, label="10-Year Moving Avg")

    if trend_dict is not None and "slope_per_year" in trend_dict:
        x_vals = df["year"].values
        y_trend = trend_dict["intercept"] + trend_dict["slope_per_year"] * x_vals
        rate = trend_dict["decadal_rate"]
        p_bound = trend_dict.get("p_value_bound", f"p={trend_dict.get('p_value', 0):.1e}")
        ax.plot(
            x_vals,
            y_trend,
            color="black",
            linestyle="--",
            linewidth=1.8,
            label=f"OLS Trend ({rate:+.2f} °C/decade, {p_bound})",
        )

    ax.axhline(0, color="gray", linestyle="-", linewidth=0.8)
    ax.set_title(f"Observed Temperature Anomalies ({baseline_label}) - {station_name}", fontsize=13, fontweight="bold")
    ax.set_xlabel("Year", fontsize=11)
    ax.set_ylabel("Temperature Anomaly (°C)", fontsize=11)
    ax.legend(loc="upper left", frameon=True)
    fig.tight_layout()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=300)

    plt.close(fig)
    return fig


def plot_anomalies(
    df: pd.DataFrame,
    date_col: str = "date",
    val_col: str = "monthly_anomaly",
    output_path: str | Path | None = None,
    station_name: str = "NYC Central Park",
    z_threshold: float = 2.0,
    baseline_label: str = "1951–1980 Baseline",
) -> plt.Figure:
    """Plot anomaly time series highlighting genuine statistical outliers.

    Args:
        df: DataFrame containing anomaly flags.
        date_col: Column containing timestamp or year.
        val_col: Target anomaly column.
        output_path: Destination path for saved image.
        station_name: Station label.
        z_threshold: Cutoff used for outlier highlighting.
        baseline_label: Label for the reference period.

    Returns:
        Matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(df[date_col], df[val_col], color="#4575b4", linewidth=1.0, alpha=0.75, label="Observed Monthly Anomaly")

    anomaly_mask = df.get("is_anomaly_any", df.get("is_anomaly_zscore", pd.Series(False, index=df.index)))
    outliers = df[anomaly_mask]

    if not outliers.empty:
        ax.scatter(
            outliers[date_col],
            outliers[val_col],
            color="#d73027",
            s=45,
            zorder=5,
            label=f"Statistical Extremes (|z| > {z_threshold:.1f} or IQR)",
        )

    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_title(f"Statistical Anomaly & Extreme Event Distribution ({baseline_label}) - {station_name}", fontsize=13, fontweight="bold")
    ax.set_xlabel("Time", fontsize=11)
    ax.set_ylabel("Anomaly (°C)", fontsize=11)
    ax.legend(loc="upper left", frameon=True)
    fig.tight_layout()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=300)

    plt.close(fig)
    return fig


def plot_decadal_temperature_shifts(
    decadal_df: pd.DataFrame,
    val_col: str = "mean_annual_tavg",
    output_path: str | Path | None = None,
    station_name: str = "NYC Central Park",
) -> plt.Figure:
    """Plot mean observed temperature by decade.

    Args:
        decadal_df: Summary DataFrame from calculate_decadal_summary.
        val_col: Value column name.
        output_path: Destination path.
        station_name: Station name.

    Returns:
        Matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=(11, 5))

    decades = [f"{int(d)}s" for d in decadal_df["decade"]]
    values = decadal_df[val_col]

    norm = plt.Normalize(values.min(), values.max())
    cmap = matplotlib.colormaps["coolwarm"]
    colors = [cmap(norm(v)) for v in values]

    bars = ax.bar(decades, values, color=colors, width=0.7, edgecolor="gray")
    ax.set_title(f"Mean Observed Temperature by Decade - {station_name}", fontsize=13, fontweight="bold")
    ax.set_xlabel("Decade", fontsize=11)
    ax.set_ylabel("Mean Temperature (°C)", fontsize=11)
    ax.set_ylim(bottom=values.min() - 0.5, top=values.max() + 0.5)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=300)

    plt.close(fig)
    return fig


def plot_model_forecast_vs_actual(
    pred_df: pd.DataFrame,
    target_col: str = "target_next_tavg",
    pred_col: str = "pred_ml",
    output_path: str | Path | None = None,
    station_name: str = "NYC Central Park",
) -> plt.Figure:
    """Plot held-out test predictions vs. actual real observations.

    Args:
        pred_df: Test predictions DataFrame.
        target_col: True observation column.
        pred_col: Model prediction column.
        output_path: Destination path.
        station_name: Station identifier.

    Returns:
        Matplotlib Figure object.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1]})

    # Plot actual vs predicted on upper axis
    ax1.plot(pred_df["date"], pred_df[target_col], label="Actual Observed Temperature", color="black", linewidth=1.5)
    ax1.plot(pred_df["date"], pred_df[pred_col], label="Ridge ML Forecast (1-Month Ahead)", color="#e41a1c", linestyle="--", linewidth=1.2)
    if "pred_climatology" in pred_df.columns:
        ax1.plot(pred_df["date"], pred_df["pred_climatology"], label="Seasonal Climatology Baseline", color="#377eb8", linestyle=":", linewidth=1.1, alpha=0.8)

    ax1.set_title(f"Held-Out Out-of-Sample Temperature Forecast vs. Genuine Observations - {station_name}", fontsize=13, fontweight="bold")
    ax1.set_ylabel("Next Month Mean Temp (°C)", fontsize=11)
    ax1.legend(loc="upper left", frameon=True)

    # Plot prediction residuals on lower axis
    residuals = pred_df[target_col] - pred_df[pred_col]
    ax2.plot(pred_df["date"], residuals, color="#4daf4a", linewidth=1.0, label="Forecast Residual (Actual - ML)")
    ax2.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax2.set_xlabel("Date", fontsize=11)
    ax2.set_ylabel("Residual (°C)", fontsize=11)
    ax2.legend(loc="upper left", frameon=True)

    fig.tight_layout()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=300)

    plt.close(fig)
    return fig
