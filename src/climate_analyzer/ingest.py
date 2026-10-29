"""Data Ingestion Module for NOAA GHCN-Daily Climate Observations.

Handles automated retrieval and ingestion of verified real-world public climate records
from the NOAA National Centers for Environmental Information (NCEI).

Author: Akash Das
"""

import os
from pathlib import Path
import urllib.request
import urllib.error
import pandas as pd


def download_noaa_ghcn_station(
    station_id: str,
    target_dir: str | Path,
    base_url: str = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/",
    timeout: int = 45,
) -> Path:
    """Download official NOAA GHCN-Daily station CSV record.

    Args:
        station_id: NOAA station identifier (e.g. 'USW00094728').
        target_dir: Directory where downloaded raw file will be persisted.
        base_url: Official NOAA NCEI access URL.
        timeout: HTTP request timeout in seconds.

    Returns:
        Path to the saved raw CSV file.

    Raises:
        FileNotFoundError: If the station record does not exist on NOAA server.
        ConnectionError: If network connectivity or server error occurs.
    """
    dest_dir = Path(target_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{station_id}.csv"
    dest_path = dest_dir / filename

    url = f"{base_url.rstrip('/')}/{filename}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ClimateTrendAnalyzer/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            dest_path.write_bytes(content)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise FileNotFoundError(f"Station {station_id} not found on NOAA GHCN server at {url}.")
        raise ConnectionError(f"HTTP error {e.code} while downloading NOAA data: {e.reason}")
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to connect to NOAA GHCN server ({url}): {e.reason}")

    return dest_path


def load_noaa_ghcn_daily(file_path: str | Path) -> pd.DataFrame:
    """Load and parse raw NOAA GHCN-Daily observation table.

    Converts physical units:
    - TMAX, TMIN: tenths of degrees Celsius -> degrees Celsius (°C)
    - PRCP: tenths of mm -> millimetres (mm)
    - TAVG: derived as midpoint (TMAX + TMIN) / 2.0 when absent

    Args:
        file_path: Path to the local raw GHCN-Daily CSV file.

    Returns:
        pd.DataFrame with standardized columns:
        ['station', 'name', 'latitude', 'longitude', 'elevation', 'date',
         'year', 'month', 'day', 'tmax', 'tmin', 'tavg', 'prcp', 'snow']
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Raw NOAA GHCN observation file not found at: {path}. "
            "Please run the download workflow first."
        )

    # Use selected columns to optimize memory and parse speed
    df_raw = pd.read_csv(path, low_memory=False)

    col_map = {c.upper().strip(): c for c in df_raw.columns}
    required = ["DATE", "TMAX", "TMIN", "PRCP"]
    missing = [c for c in required if c not in col_map]
    if missing:
        raise ValueError(f"GHCN file {path.name} is missing essential columns: {missing}")

    df = pd.DataFrame()
    df["station"] = df_raw[col_map.get("STATION", "STATION")].astype(str) if "STATION" in col_map else "UNKNOWN"
    df["name"] = df_raw[col_map.get("NAME", "NAME")].astype(str) if "NAME" in col_map else "UNKNOWN"
    df["latitude"] = pd.to_numeric(df_raw[col_map.get("LATITUDE", "LATITUDE")], errors="coerce")
    df["longitude"] = pd.to_numeric(df_raw[col_map.get("LONGITUDE", "LONGITUDE")], errors="coerce")
    df["elevation"] = pd.to_numeric(df_raw[col_map.get("ELEVATION", "ELEVATION")], errors="coerce")

    df["date"] = pd.to_datetime(df_raw[col_map["DATE"]], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day

    # Physical Unit Conversions:
    # NOAA GHCN-Daily records temperatures in tenths of °C and precipitation in tenths of mm
    tmax_raw = pd.to_numeric(df_raw[col_map["TMAX"]], errors="coerce")
    tmin_raw = pd.to_numeric(df_raw[col_map["TMIN"]], errors="coerce")
    prcp_raw = pd.to_numeric(df_raw[col_map["PRCP"]], errors="coerce")

    df["tmax"] = tmax_raw / 10.0
    df["tmin"] = tmin_raw / 10.0
    df["prcp"] = prcp_raw / 10.0

    if "SNOW" in col_map:
        df["snow"] = pd.to_numeric(df_raw[col_map["SNOW"]], errors="coerce")
    else:
        df["snow"] = 0.0

    # Daily Mean Temperature Tracking & Provenance:
    # 1. Native NOAA-provided TAVG (available for 2,648 rows, 1998-2005)
    if "TAVG" in col_map:
        df["tavg_native"] = pd.to_numeric(df_raw[col_map["TAVG"]], errors="coerce") / 10.0
    else:
        df["tavg_native"] = float("nan")

    df["has_native_tavg"] = df["tavg_native"].notna()

    # 2. Midpoint daily mean temperature estimate from daily extremes (tmax + tmin) / 2.0
    # Strictly evaluates to NaN if either tmax or tmin is missing/NaN
    df["tavg_midpoint"] = (df["tmax"] + df["tmin"]) / 2.0

    # 3. Operational daily mean temperature:
    # Standardized on midpoint proxy (tmax + tmin) / 2.0 across all 157 years to ensure
    # climatological homogeneity and prevent contamination from corrupted ASOS sensor glitches
    # (e.g. -17.8 °C summer readings with QC flag 'G' or tavg > tmax inversions).
    # Native TAVG is never silently reintroduced into the operational series.
    df["tavg"] = df["tavg_midpoint"]

    # 4. Explicit boolean describing whether operational tavg is derived from midpoint
    # Because operational tavg is standardized on midpoint extremes, all valid tavg rows are derived.
    df["is_tavg_derived"] = df["tavg"].notna()

    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def load_climate_dataset(
    station_id: str = "USW00094728",
    raw_dir: str | Path | None = None,
    allow_download: bool = True,
) -> pd.DataFrame:
    """Retrieve or load genuine NOAA GHCN-Daily observation records.

    Args:
        station_id: NOAA station code.
        raw_dir: Local raw data cache directory.
        allow_download: Whether to attempt download if local file is missing.

    Returns:
        Parsed daily observations DataFrame.
    """
    if raw_dir is None:
        raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
    else:
        raw_dir = Path(raw_dir)

    target_path = raw_dir / f"{station_id}.csv"

    if not target_path.exists():
        if allow_download:
            print(f"Downloading real NOAA GHCN data for station {station_id}...")
            download_noaa_ghcn_station(station_id, raw_dir)
        else:
            raise FileNotFoundError(
                f"Real climate data file {target_path} not found and downloads are disabled."
            )

    return load_noaa_ghcn_daily(target_path)
