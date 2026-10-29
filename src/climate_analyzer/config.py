"""Central Configuration and Path Management for Climate Trend Analyzer.

Author: Akash Das
"""

from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass(frozen=True)
class ProjectPaths:
    """Project directory topology rooted at the repository base."""
    root_dir: Path
    data_dir: Path
    raw_data_dir: Path
    processed_data_dir: Path
    outputs_dir: Path
    figures_dir: Path
    metrics_dir: Path
    reports_dir: Path
    docs_dir: Path


def get_project_paths(base_dir: Path | None = None) -> ProjectPaths:
    """Derive all project paths relative to the project root.

    Args:
        base_dir: Optional override for project root. Defaults to two levels up from this file.

    Returns:
        ProjectPaths dataclass with absolute paths.
    """
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[2]

    data_dir = base_dir / "data"
    outputs_dir = base_dir / "outputs"

    return ProjectPaths(
        root_dir=base_dir,
        data_dir=data_dir,
        raw_data_dir=data_dir / "raw",
        processed_data_dir=data_dir / "processed",
        outputs_dir=outputs_dir,
        figures_dir=outputs_dir / "figures",
        metrics_dir=outputs_dir / "metrics",
        reports_dir=outputs_dir / "reports",
        docs_dir=base_dir / "docs",
    )


@dataclass
class Config:
    """Global configuration settings for Climate Trend Analyzer (Real Public Data)."""
    paths: ProjectPaths = field(default_factory=get_project_paths)
    
    # Primary Real Public Dataset: NOAA GHCN-Daily
    default_station_id: str = "USW00094728"
    default_station_name: str = "NY City Central Park, NY US"
    noaa_ghcn_base_url: str = (
        "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/"
    )
    
    # Reference Baseline Period for Climatological Anomalies
    baseline_start: int = 1951
    baseline_end: int = 1980
    
    # Machine Learning Train/Test Chronological Split Year
    ml_split_year: int = 2000
    
    # Statistical Anomaly Detection Thresholds
    zscore_threshold: float = 2.0
    iqr_multiplier: float = 1.5

    def ensure_directories(self) -> None:
        """Create all necessary output and data directories if they do not exist."""
        for p in [
            self.paths.raw_data_dir,
            self.paths.processed_data_dir,
            self.paths.figures_dir,
            self.paths.metrics_dir,
            self.paths.reports_dir,
        ]:
            p.mkdir(parents=True, exist_ok=True)
