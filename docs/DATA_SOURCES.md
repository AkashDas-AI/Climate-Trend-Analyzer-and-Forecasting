# Data Sources & Attribution

This document details the authoritative public datasets evaluated and utilized by the **Climate Trend Analyzer**.

**Author**: Akash Das  
**Current Status**: Verified Real Public Data  

---

## 1. Primary Operational Dataset: NOAA GHCN-Daily

- **Organization**: National Oceanic and Atmospheric Administration (NOAA) National Centers for Environmental Information (NCEI).
- **Dataset Title**: Global Historical Climatology Network - Daily (GHCN-Daily), Version 3.
- **Official Portal**: [https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily](https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily)
- **Direct Access URL**: `https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/USW00094728.csv`
- **Selected Station**: `USW00094728` (New York City Central Park, NY, United States).
- **Station Coordinates**: Latitude 40.77898° N, Longitude -73.96925° W, Elevation 42.7 m.
- **Coverage**: January 1, 1869 to October 24, 2026 (57,640 daily records across 157 years).
- **File Format & Size**: CSV, ~17.0 MB.
- **Terms of Use**: U.S. Federal Government Open Data / Public Domain. Free and unrestricted public access with no login or API key required.
- **Scientific Attribution**:
  > Menne, M. J., I. Durre, R. S. Vose, B. E. Gleason, and T. G. Houston, 2012: An overview of the Global Historical Climatology Network-Daily database. *Journal of Atmospheric and Oceanic Technology*, 29, 897-910, doi:10.1175/JTECH-D-11-00103.1.

### 1.1 Column Schema and Physical Units in Raw NOAA File
The raw file `data/raw/USW00094728.csv` adheres to the official NOAA GHCN-Daily standard format:
- `TMAX`, `TMIN`, `TAVG`: Integers expressed in **tenths of degrees Celsius** ($0.1^\circ\text{C}$). Converted by dividing by 10.0 during ingestion in `load_noaa_ghcn_daily()`. E.g., raw value `150` represents $15.0^\circ\text{C}$.
- `PRCP`: Integer expressed in **tenths of millimeters** ($0.1\text{ mm}$). Converted by dividing by 10.0. E.g., raw value `25` represents $2.5\text{ mm}$.
- `SNOW`: Integer expressed in **millimeters** ($1\text{ mm}$).
- Missing values: Represented as empty fields (e.g. `,,` in CSV), which parse directly to `NaN`.

### 1.2 Verification of Raw Zero Values and Quality-Flagged Records
A targeted scientific audit was performed to resolve whether raw `0` in `TAVG` represents $0^\circ\text{C}$, $0^\circ\text{F}$ ($-17.8^\circ\text{C}$), or missing data:
1. **Raw 0 in TAVG (23 records)**:
   - Exactly 23 rows in `USW00094728.csv` contain raw `TAVG = 0.0` ($0.0^\circ\text{C}$).
   - All 23 records occur exclusively during winter months (December, January, February, and March).
   - On every such day, $T_{\text{max}} > 0^\circ\text{C}$ and $T_{\text{min}} < 0^\circ\text{C}$, and the midpoint $(T_{\text{max}} + T_{\text{min}}) / 2.0 \approx 0.0^\circ\text{C}$.
   - **Conclusion**: Raw 0 represents genuine physical $0.0^\circ\text{C}$ ($32.0^\circ\text{F}$, the freezing point of water). It is neither missing nor an erroneous placeholder.
2. **Summer Sensor Glitches and Quality Flag G (5 records)**:
   - On 5 dates during summer heat (`2001-07-05`, `2001-08-30`, `2002-08-13`, `2002-09-02`, and `2002-09-03`), raw `TAVG` literally contains `-178.0` (which is $-17.8^\circ\text{C} = 0.0^\circ\text{F}$).
   - All 5 records are accompanied by NOAA Quality Flag `G` ("Failed gap check"). This represents a known ASOS automated sensor failure where uncalibrated zero-voltage readings ($0^\circ\text{F}$) were erroneously written into the GHCN-Daily ingest pipeline.
3. **Unflagged Inconsistency (1 record)**:
   - On `2001-04-04`, raw `TAVG` is `256.0` ($25.6^\circ\text{C}$), but $T_{\text{max}} = 12.2^\circ\text{C}$ and $T_{\text{min}} = 3.3^\circ\text{C}$ ($T_{\text{avg}} > T_{\text{max}}$). This record was unflagged by NOAA QC.

### 1.3 Mean Temperature Standardization Policy
- **Native Availability**: Native NOAA `TAVG` is available for only **2,648 rows** (spanning 1998-04-01 to 2005-07-31), covering merely 4.6% of the 157-year record. 95.4% of rows (54,985 days) lack native `TAVG`.
- **Operational Series**: To preserve strict climatological homogeneity across 157 years and prevent contamination from the 6 corrupted ASOS records, the pipeline utilizes the standard meteorological midpoint estimate:
  $$T_{\text{avg}} = \frac{T_{\text{max}} + T_{\text{min}}}{2.0}$$
- **Auditability**: Source values are preserved in `tavg_native`, alongside `tavg_midpoint` and the boolean tracking flag `is_tavg_derived`, ensuring 100% transparency.

---

## 2. Dataset Evaluations & Comparison

### Candidate A: Copernicus ERA5 Reanalysis
- **Provider**: European Centre for Medium-Range Weather Forecasts (ECMWF) / Copernicus Climate Change Service (C3S).
- **Access Portal**: `https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels`
- **Evaluation**: ERA5 provides global gridded hourly and monthly reanalysis products from 1940 to present. However, downloading ERA5 requires registering a personal user account on the Copernicus Data Store, accepting legal terms online, and configuring an API key in a user-local `~/.cdsapirc` file. Since no pre-configured CDS credentials were present in this local environment, NOAA GHCN-Daily was selected to ensure full, transparent, automated reproducibility without external credential dependencies.

### Candidate B: NASA GISTEMP v4
- **Provider**: NASA Goddard Institute for Space Studies (GISS).
- **Access Portal**: `https://data.giss.nasa.gov/gistemp/data_v4.html`
- **Evaluation**: GISTEMP provides global and hemispheric monthly and annual surface temperature anomalies from 1880 to present. While highly valuable for global macro trends, the public endpoint experienced intermittent HTTP timeouts, and the dataset is a single scalar anomaly series rather than a multi-variable terrestrial weather dataset supporting predictive machine learning experiments.

---

## 3. Climatological Reference Baseline

- **Standard Reference Period**: **1951–1980 Mean** (World Meteorological Organization standard).
- **Rationale**: Represents a 30-year climatological baseline with widespread global station coverage prior to the rapid post-1980 warming acceleration.
- **Calculation**: For each of the 12 calendar months, the baseline temperature $\mu_{\text{baseline}, m}$ is computed as the 30-year average across 1951–1980:
  $$\mu_{\text{baseline}, m} = \frac{1}{30} \sum_{y=1951}^{1980} T_{\text{avg}, y, m}$$
  $$\text{Anomaly}_{y, m} = T_{\text{avg}, y, m} - \mu_{\text{baseline}, m}$$
