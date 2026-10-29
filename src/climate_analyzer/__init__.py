"""Climate Trend Analyzer.

A modular Python framework for real-world climate data ingestion, quality validation,
trend analysis, anomaly detection, and predictive modeling using genuine public datasets.

Author: Akash Das
License: MIT
"""

__version__ = "0.2.0"
__author__ = "Akash Das"

from climate_analyzer.config import Config, get_project_paths
from climate_analyzer.ingest import (
    download_noaa_ghcn_station,
    load_noaa_ghcn_daily,
    load_climate_dataset,
)
from climate_analyzer.validation import (
    validate_ghcn_dataframe,
    ClimateDataValidationError,
)
from climate_analyzer.transform import (
    clean_daily_observations,
    aggregate_to_monthly,
    compute_climatological_anomalies,
    aggregate_to_annual,
)
from climate_analyzer.features import (
    engineer_monthly_features,
    engineer_annual_features,
)
from climate_analyzer.analysis import (
    calculate_linear_trend,
    mann_kendall_test,
    sens_slope,
    calculate_decadal_summary,
)
from climate_analyzer.anomaly_detection import (
    detect_zscore_anomalies,
    detect_iqr_anomalies,
    get_top_extreme_records,
    detect_anomalies,
)
from climate_analyzer.modeling import (
    temporal_train_test_split,
    compute_forecast_metrics,
    train_and_evaluate_climate_model,
)
from climate_analyzer.visualization import (
    plot_historical_temperature_trend,
    plot_anomalies,
    plot_decadal_temperature_shifts,
    plot_model_forecast_vs_actual,
)
from climate_analyzer.reporting import (
    generate_markdown_report,
    export_metrics,
)

__all__ = [
    "Config",
    "get_project_paths",
    "download_noaa_ghcn_station",
    "load_noaa_ghcn_daily",
    "load_climate_dataset",
    "validate_ghcn_dataframe",
    "ClimateDataValidationError",
    "clean_daily_observations",
    "aggregate_to_monthly",
    "compute_climatological_anomalies",
    "aggregate_to_annual",
    "engineer_monthly_features",
    "engineer_annual_features",
    "calculate_linear_trend",
    "mann_kendall_test",
    "sens_slope",
    "calculate_decadal_summary",
    "detect_zscore_anomalies",
    "detect_iqr_anomalies",
    "get_top_extreme_records",
    "detect_anomalies",
    "temporal_train_test_split",
    "compute_forecast_metrics",
    "train_and_evaluate_climate_model",
    "plot_historical_temperature_trend",
    "plot_anomalies",
    "plot_decadal_temperature_shifts",
    "plot_model_forecast_vs_actual",
    "generate_markdown_report",
    "export_metrics",
]
