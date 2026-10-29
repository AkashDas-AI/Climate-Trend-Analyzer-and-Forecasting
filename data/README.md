# Data Directory Conventions & Provenance

This directory stores real meteorological observational assets for the **Climate Trend Analyzer** project. All substantive analysis and modeling are conducted strictly using genuine, publicly available climate records.

---

## 📁 Directory Structure

```
data/
├── raw/          # Immutable source data downloaded directly from NOAA NCEI (e.g. USW00094728.csv)
└── processed/    # Cleaned, aggregated, and feature-engineered observation tables
```

---

## 🔒 Directory Conventions

1. **`data/raw/`**:
   - Contains immutable original records as received from data providers (e.g., NOAA GHCN-Daily).
   - Files in this directory are never modified or overwritten in-place.
   - Primary station record: `USW00094728.csv` (New York City Central Park).

2. **`data/processed/`**:
   - Contains normalized datasets produced by `climate_analyzer.transform` and `climate_analyzer.features`.
   - Aggregated monthly summaries: `USW00094728_monthly_features.csv`.
   - Annual summaries: `USW00094728_annual_features.csv`.

---

## 🌐 Primary Data Provenance & Attribution

- **Data Provider**: National Oceanic and Atmospheric Administration (NOAA) National Centers for Environmental Information (NCEI).
- **Dataset**: Global Historical Climatology Network - Daily (GHCN-Daily), Version 3.
- **Station**: `USW00094728` (NY City Central Park, NY, US).
- **Geographic Coordinates**: Latitude 40.77898° N, Longitude -73.96925° W, Elevation 42.7 m.
- **Temporal Span**: January 1, 1869 to October 24, 2026 (>57,600 daily records).
- **Physical Variables**:
  - `TMAX`: Daily maximum surface temperature (recorded in tenths of °C, converted to °C).
  - `TMIN`: Daily minimum surface temperature (recorded in tenths of °C, converted to °C).
  - `TAVG`: Daily average temperature (midpoint `(TMAX + TMIN) / 2.0` in °C).
  - `PRCP`: Daily precipitation (recorded in tenths of mm, converted to mm).
  - `SNOW`: Daily snowfall (mm).
- **License / Terms**: U.S. Federal Government Public Domain / Open Data Policy.
- **Official Access URL**: [https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/USW00094728.csv](https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/USW00094728.csv)
