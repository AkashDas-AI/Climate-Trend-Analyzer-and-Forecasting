# Unit Testing & Verification Framework

This document specifies the test architecture, test philosophy, fixture conventions, and test suite execution for the **Climate Trend Analyzer**.

**Project Author**: Akash Das  
**Test Directory**: [`tests/`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/tests)  
**Configuration**: Defined in [`pyproject.toml`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/pyproject.toml)  

---

## 1. Testing Philosophy & Core Principles

The test suite is built on four core principles to ensure complete reproducibility and scientific integrity:

1. **Small, Deterministic In-Memory Fixtures**:
   - All tests run against compact synthetic in-memory fixtures generated dynamically in RAM.
   - **Strict Isolation**: Test fixtures are never mixed with real product data and are never used to train production models or produce reported climate metrics.
2. **Zero Network Calls During Tests**:
   - Tests do not make network requests to NOAA or external servers. All unit tests run completely offline.
3. **Sandbox Compliance**:
   - Pytest is configured with `-p no:cacheprovider` to avoid creating `.pytest_cache/` directories, ensuring tests execute seamlessly within sandboxed CI/CD and developer environments.
4. **Comprehensive Algorithmic Coverage**:
   - Every core module (`ingest`, `transform`, `analysis`, `anomaly_detection`, `modeling`) has dedicated test coverage validating nominal behavior, mathematical exactness, and edge-case resilience.
5. **Clean CI Environment Adaptability**:
   - In clean CI/CD environments where raw data (`data/raw/USW00094728.csv`, 17.8 MB) is excluded via `.gitignore`, 36 core unit tests run and pass deterministically in under 10 seconds while data-dependent integration tests cleanly skip, ensuring zero network flakiness. When raw observations are present locally, all 43 tests pass 100%.

---

## 2. Test Suite Organization

The test suite comprises **43 unit and integration tests** across 6 modules:

```
tests/
├── __init__.py                   # Test package initialization
├── test_ingest.py                # Ingestion, column parsing, derived TAVG (4 tests)
├── test_transform.py             # Cleaning, bounded gaps, inversion flags, aggregation (7 tests)
├── test_analysis.py              # OLS regression, HAC standard errors, Mann-Kendall, Sen's slope, scalar invariance (9 tests)
├── test_anomaly_detection.py     # Z-score, IQR filters, and extreme ranking (4 tests)
├── test_modeling.py              # Target-date chronological split, scaler pipeline, baselines (6 tests)
└── test_dashboard.py             # Streamlit AST, baselines, leverage, tolerances, exports, isolation (13 tests)
```

### 2.1 Detailed Module Test Matrix

| Test Module | Test Function | Target Functionality Tested |
| :--- | :--- | :--- |
| `test_ingest.py` | `test_load_noaa_ghcn_daily_parsing` | Verifies DataFrame schema, column types, and parsing. |
| | `test_load_noaa_ghcn_missing_file_raises` | Verifies explicit `FileNotFoundError` when a non-existent file path is provided. |
| | `test_load_noaa_ghcn_missing_columns_raises` | Verifies explicit `ValueError` when required columns are absent. |
| | `test_offline_mode_fails_explicitly_when_file_missing` | Verifies fail-fast behavior in offline mode with zero synthetic fallback. |
| `test_transform.py` | `test_validate_ghcn_dataframe_valid` | Verifies validation logic on compliant observations. |
| | `test_validate_ghcn_dataframe_inverted_temps` | Verifies identification of inverted temperature records. |
| | `test_validate_ghcn_dataframe_negative_prcp` | Verifies detection of unphysical negative precipitation values. |
| | `test_clean_daily_observations` | Tests short gap interpolation ($\le 3$ days) on isolated missing days. |
| | `test_clean_daily_bounded_gap_preservation` | Verifies that gaps exceeding `max_gap_interpolation` are NOT interpolated. |
| | `test_clean_daily_inversion_flagging_without_mutation` | Verifies that $T_{\text{min}} > T_{\text{max}}$ records are flagged and source values preserved. |
| | `test_aggregate_to_monthly_and_baseline` | Verifies the $\ge 25$ days/month completeness threshold and baseline subtraction. |
| `test_analysis.py` | `test_linear_trend_exact_line` | Validates OLS slope, intercept, decadal rate, and $p$-value on known linear data. |
| | `test_mann_kendall_strictly_increasing` | Validates positive monotonic trend identification ($S > 0, Z > 0$). |
| | `test_mann_kendall_strictly_decreasing` | Validates negative monotonic trend identification ($S < 0, Z < 0$). |
| | `test_sens_slope_robustness` | Validates Theil-Sen median pairwise slope calculation. |
| | `test_calculate_decadal_summary` | Verifies decade binning and mean anomaly computations with float tolerance. |
| | `test_linear_trend_hac_standard_error` | Validates Newey-West HAC standard errors (asymptotic and finite-sample). |
| | `test_mann_kendall_autocorrelation_adjustment` | Tests Modified Mann-Kendall variance inflation factor adjustments. |
| | `test_mann_kendall_ties_and_constant` | Verifies $S = 0$ and tie correction on flat, constant time series. |
| | `test_linear_trend_and_sens_constant_shift_invariance` | Tests pure mathematical invariance of OLS slope, residuals, R², and Sen slope under scalar shifts. |
| `test_anomaly_detection.py` | `test_detect_zscore_anomalies` | Tests standard score thresholding ($|z| \ge 2.0$). |
| | `test_detect_iqr_anomalies` | Tests IQR non-parametric boundary detection ($1.5 \times \text{IQR}$). |
| | `test_get_top_extreme_records` | Verifies sorting and retention of `annual_anomaly` and `annual_tavg` columns. |
| | `test_detect_anomalies_combined` | Verifies the composite anomaly detection pipeline function. |
| `test_modeling.py` | `test_temporal_train_test_split_no_leakage` | Verifies chronological partitioning without random shuffling. |
| | `test_temporal_train_test_split_empty_raises` | Verifies that empty or insufficient data raises a descriptive error. |
| | `test_compute_forecast_metrics` | Verifies RMSE, MAE, and $R^2$ calculation routines. |
| | `test_temporal_train_test_split_target_date_boundary` | Verifies strict Target-Date Split Policy ($\le 2000$ train, $\ge 2001$ test). |
| | `test_train_and_evaluate_climate_model_baselines` | Verifies Ridge pipeline execution, metric dictionaries, and baselines. |
| | `test_real_data_boundary_dates_and_leakage` | Verifies 1,570 train / 309 test sample counts and boundary dates on real data. |
| `test_dashboard.py` | `test_streamlit_app_ast_syntax` | Verifies `app/streamlit_app.py` AST syntax and module compilation. |
| | `test_dynamic_baseline_recalculation` | Verifies that shifting baselines recalculates anomalies accurately. |
| | `test_interactive_date_range_filtering` | Verifies that year range slider recalculates trends dynamically on active eras. |
| | `test_csv_export_schema_and_units` | Verifies CSV headers include required physical units (`degC`, `mm`). |
| | `test_dashboard_ml_benchmark_reconciliation` | Verifies dashboard default metrics match official pipeline metrics. |
| | `test_missing_data_fail_fast_behavior` | Verifies dashboard fail-fast when station file missing without synthetic fallback. |
| | `test_baseline_invariance_for_ols_and_sens_slope` | Verifies bit-for-bit invariance (< 1e-14) on complete 12-month series (N=156) and display invariance on full series. |
| | `test_1869_incomplete_year_leverage_reconciliation` | Verifies quantitative analytical leverage equation predicting 1869 11-month seasonal deviation down to 1e-8. |
| | `test_full_record_statistical_tolerances_and_mk_mechanism` | Verifies HAC SE span ($0.000017$ °C/dec), unrounded Sen's slope difference ($0.000235$ °C/dec), refutes MK ties, and proves exact (1869, 1882) pairwise sign flip. |
| | `test_dashboard_pathway_invariance_and_display_agreement` | Verifies dashboard pathway computes identical displayed KPIs and sample sizes across all baselines. |
| | `test_moving_average_window_configurations_and_export_schema` | Verifies multiple moving average window pairs and dynamic CSV header schema. |
| | `test_forecast_export_partitioning_and_metadata` | Verifies benchmark export has 309 rows, target dates 2001-01 to 2026-09, and protocol metadata. |
| | `test_exploratory_split_labeling_and_isolation` | Verifies exploratory split mode is labeled `exploratory_scenario` and isolated. |

---

## 3. Running the Test Suite

Always execute tests using the project's local virtual environment:

### Standard Pytest Execution
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### Verbose Execution with Test Names
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### Execution with Print Output Captured
```powershell
.\.venv\Scripts\python.exe -m pytest -v -s
```

### Expected Output
```text
..........................................                               [100%]
42 passed in 5.76s
```

---

## 4. Continuous Integration (CI) Workflow

The automated test suite runs on every pull request and push to `main` via GitHub Actions ([`.github/workflows/tests.yml`](file:///d:/Projects/Data%20Science/Climate%20Trend%20Analyzer/.github/workflows/tests.yml)):
- Matrix testing across Python **3.10** and **3.11**.
- Runs on `ubuntu-latest` and `windows-latest`.
- Validates clean package installation (`pip install -e .`) and execution of `pytest`.

