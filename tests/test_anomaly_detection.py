"""Unit Tests for Anomaly Detection Module.

Author: Akash Das
"""

import pytest
import pandas as pd
import numpy as np
from climate_analyzer.anomaly_detection import (
    detect_zscore_anomalies,
    detect_iqr_anomalies,
    get_top_extreme_records,
    detect_anomalies,
)


def test_detect_zscore_anomalies():
    years = list(range(1980, 2001))
    anomalies = [0.1] * 20 + [2.5]  # Outlier spike at index 20
    df = pd.DataFrame({"year": years, "monthly_anomaly": anomalies})

    res = detect_zscore_anomalies(df, column="monthly_anomaly", threshold=2.0)
    assert "z_score" in res.columns
    assert "is_anomaly_zscore" in res.columns
    assert res.loc[res["year"] == 2000, "is_anomaly_zscore"].iloc[0] == True
    assert res.loc[res["year"] == 1980, "is_anomaly_zscore"].iloc[0] == False


def test_detect_iqr_anomalies():
    years = list(range(1990, 2011))
    anomalies = [0.2] * 20 + [3.5]
    df = pd.DataFrame({"year": years, "monthly_anomaly": anomalies})

    res = detect_iqr_anomalies(df, column="monthly_anomaly", multiplier=1.5)
    assert res.loc[res["year"] == 2010, "is_anomaly_iqr"].iloc[0] == True


def test_get_top_extreme_records():
    df = pd.DataFrame({
        "year": [2015, 2016, 2017, 2018],
        "tavg_mean": [12.5, 14.2, 13.1, 12.8],
    })
    top = get_top_extreme_records(df, value_col="tavg_mean", top_n=2, warmest=True)
    assert len(top) == 2
    assert top.iloc[0]["year"] == 2016
    assert top.iloc[0]["tavg_mean"] == 14.2
    assert top.iloc[1]["year"] == 2017


def test_detect_anomalies_combined():
    df = pd.DataFrame({
        "year": [1990, 1991, 1992, 1993, 1994],
        "monthly_anomaly": [0.0, 0.1, 0.0, 0.1, 5.0],
    })
    res = detect_anomalies(df, column="monthly_anomaly")
    assert "is_anomaly_any" in res.columns
    assert res["is_anomaly_any"].iloc[-1] == True
