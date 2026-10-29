"""Unit Tests for Real Climate Data Ingestion.

Author: Akash Das
"""

import pytest
import pandas as pd
from pathlib import Path
from climate_analyzer.ingest import load_noaa_ghcn_daily, load_climate_dataset


def test_load_noaa_ghcn_daily_parsing(tmp_path: Path):
    """Verify correct parsing and unit conversions (tenths of deg C to deg C, tenths of mm to mm)."""
    csv_content = (
        '"STATION","DATE","LATITUDE","LONGITUDE","ELEVATION","NAME","PRCP","TMAX","TMIN"\n'
        '"USW00094728","1900-01-01","40.78","-73.97","42.7","NY CITY CENTRAL PARK, NY US","100","200","-50"\n'
        '"USW00094728","1900-01-02","40.78","-73.97","42.7","NY CITY CENTRAL PARK, NY US","0","150","-20"\n'
    )
    test_file = tmp_path / "test_station.csv"
    test_file.write_text(csv_content, encoding="utf-8")

    df = load_noaa_ghcn_daily(test_file)
    assert len(df) == 2
    assert "tmax" in df.columns
    assert "tmin" in df.columns
    assert "tavg" in df.columns
    assert "prcp" in df.columns

    # 200 tenths of °C -> 20.0 °C
    assert df["tmax"].iloc[0] == 20.0
    # -50 tenths of °C -> -5.0 °C
    assert df["tmin"].iloc[0] == -5.0
    # Average of 20.0 and -5.0 is 7.5 °C
    assert df["tavg"].iloc[0] == 7.5
    assert df["tavg_midpoint"].iloc[0] == 7.5
    assert df["is_tavg_derived"].iloc[0] == True
    # 100 tenths of mm -> 10.0 mm
    assert df["prcp"].iloc[0] == 10.0


def test_load_noaa_ghcn_missing_file_raises():
    """Verify clear FileNotFoundError when file is not found."""
    non_existent = Path("non_existent_climate_file.csv")
    with pytest.raises(FileNotFoundError, match="not found"):
        load_noaa_ghcn_daily(non_existent)


def test_load_noaa_ghcn_missing_columns_raises(tmp_path: Path):
    """Verify ValueError when required climate observation columns are absent."""
    malformed_csv = tmp_path / "malformed.csv"
    malformed_csv.write_text('"DATE","TMAX"\n"1900-01-01","200"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="missing essential columns"):
        load_noaa_ghcn_daily(malformed_csv)


def test_offline_mode_fails_explicitly_when_file_missing(tmp_path: Path):
    """Verify that pipeline fails explicitly without synthetic fallback when offline and file is absent."""
    with pytest.raises(FileNotFoundError, match="Real climate data file"):
        load_climate_dataset(station_id="NON_EXISTENT_STATION", raw_dir=tmp_path, allow_download=False)
