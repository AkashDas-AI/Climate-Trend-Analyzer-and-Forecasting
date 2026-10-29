"""Quality Assurance and Schema Validation Module for Real Climate Data.

Author: Akash Das
"""

from typing import Any
import numpy as np
import pandas as pd


class ClimateDataValidationError(ValueError):
    """Raised when climate records violate schema or integrity constraints."""
    pass


def validate_ghcn_dataframe(
    df: pd.DataFrame,
    min_year: int = 1850,
    max_year: int = 2100,
    min_temp: float = -60.0,
    max_temp: float = 60.0,
    raise_on_error: bool = True,
) -> dict[str, Any]:
    """Validate daily NOAA GHCN meteorological observation series.

    Ensures physical plausibility, temporal continuity, and column schema
    without automatically deleting extreme genuine meteorological events.

    Args:
        df: Daily observations DataFrame.
        min_year: Minimum expected calendar year.
        max_year: Maximum expected calendar year.
        min_temp: Minimum physically plausible temperature (°C).
        max_temp: Maximum physically plausible temperature (°C).
        raise_on_error: Whether to raise ClimateDataValidationError on fatal errors.

    Returns:
        Dictionary of validation findings and data quality statistics.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Essential Columns Check
    required_cols = {"date", "year", "month", "tmax", "tmin", "tavg", "prcp"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        errors.append(f"Missing required columns: {sorted(missing_cols)}")
        if raise_on_error:
            raise ClimateDataValidationError("; ".join(errors))
        return {"is_valid": False, "errors": errors, "warnings": warnings}

    # 2. Date Monotonicity and Duplication
    if not df["date"].is_monotonic_increasing:
        warnings.append("Date series is not strictly sorted chronologically.")

    dup_dates = df["date"].duplicated().sum()
    if dup_dates > 0:
        errors.append(f"Found {dup_dates} duplicate date timestamps.")

    # 3. Calendar Year Boundaries
    invalid_years = df[(df["year"] < min_year) | (df["year"] > max_year)]
    if not invalid_years.empty:
        errors.append(f"Found observations outside acceptable year range [{min_year}, {max_year}].")

    # 4. Temperature Physical Sanity Assertions
    # Tmin vs Tmax: Flag any historical records where Tmin exceeds Tmax
    inverted_temps = df[(df["tmax"].notna()) & (df["tmin"].notna()) & (df["tmin"] > df["tmax"])]
    if not inverted_temps.empty:
        warnings.append(
            f"Detected {len(inverted_temps)} historical records where TMIN > TMAX "
            "(known observer/transcription anomalies in 19th-century records)."
        )

    # Temperature bounds
    extreme_temps = df[
        ((df["tmax"] < min_temp) | (df["tmax"] > max_temp)) |
        ((df["tmin"] < min_temp) | (df["tmin"] > max_temp))
    ]
    if not extreme_temps.empty:
        warnings.append(
            f"Detected {len(extreme_temps)} records exceeding typical physical bounds "
            f"[{min_temp}, {max_temp}] °C (meteorological extremes)."
        )

    # 5. Precipitation Non-negativity
    negative_prcp = df[df["prcp"] < 0]
    if not negative_prcp.empty:
        errors.append(f"Found {len(negative_prcp)} records with negative precipitation.")

    # 6. Null Counts
    null_tavg = df["tavg"].isna().sum()
    null_prcp = df["prcp"].isna().sum()
    if null_tavg > 0:
        warnings.append(f"{null_tavg} missing values in daily average temperature (TAVG).")
    if null_prcp > 0:
        warnings.append(f"{null_prcp} missing values in daily precipitation (PRCP).")

    is_valid = len(errors) == 0
    if not is_valid and raise_on_error:
        raise ClimateDataValidationError("; ".join(errors))

    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "total_records": len(df),
        "start_date": str(df["date"].min().date()) if not df.empty else None,
        "end_date": str(df["date"].max().date()) if not df.empty else None,
        "missing_tavg_count": int(null_tavg),
        "missing_prcp_count": int(null_prcp),
    }
