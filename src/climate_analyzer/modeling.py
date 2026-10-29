"""Machine Learning Modeling and Out-of-Sample Evaluation Module.

Implements next-period temperature forecasting using genuine historical observations,
strictly enforced chronological train/test splitting, feature standardization,
and rigorous baseline benchmarking.

Author: Akash Das
"""

from typing import Any
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


def temporal_train_test_split(
    df: pd.DataFrame,
    split_year: int = 2000,
    time_col: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chronologically partition DataFrame without forward-looking leakage.

    Adopted Split Policy (Target-Date Split):
        Partitions by target year when 'target_year' is available, ensuring training targets
        end strictly at or before split_year (e.g. December 2000 for split_year=2000), while
        held-out test targets begin strictly in split_year + 1 (e.g. January 2001).
        Falls back to 'year' if 'target_year' is absent.

    Args:
        df: Input DataFrame.
        split_year: Dividing calendar year.
        time_col: Optional column indicating time. If None, checks for 'target_year'
            before falling back to 'year'.

    Returns:
        (train_df, test_df) tuple.
    """
    if time_col is not None:
        col = time_col
    elif "target_year" in df.columns:
        col = "target_year"
    elif "year" in df.columns:
        col = "year"
    else:
        col = df.columns[0]

    train_df = df[df[col] <= split_year].copy()
    test_df = df[df[col] > split_year].copy()

    if train_df.empty or test_df.empty:
        raise ValueError(
            f"Split year {split_year} on column '{col}' resulted in an empty partition: "
            f"train size={len(train_df)}, test size={len(test_df)}"
        )

    return train_df, test_df


def compute_forecast_metrics(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
) -> dict[str, float]:
    """Compute standard error metrics on held-out observations.

    Args:
        y_true: Ground truth observations.
        y_pred: Predicted values.

    Returns:
        Dict with RMSE, MAE, and R2.
    """
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)

    mask = ~np.isnan(yt) & ~np.isnan(yp)
    yt = yt[mask]
    yp = yp[mask]

    if len(yt) == 0:
        return {"rmse": float("nan"), "mae": float("nan"), "r2": float("nan")}

    rmse = float(np.sqrt(mean_squared_error(yt, yp)))
    mae = float(mean_absolute_error(yt, yp))
    r2 = float(r2_score(yt, yp)) if len(yt) > 1 else float("nan")

    return {
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
    }


def train_and_evaluate_climate_model(
    monthly_features_df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    target_col: str = "target_next_tavg",
    split_year: int = 2000,
) -> dict[str, Any]:
    """Train next-month temperature model and evaluate against baselines on held-out real data.

    Evaluation compares:
    1. Seasonal Climatology Baseline (mean of target month in historical train set)
    2. Persistence Baseline (current month's temperature)
    3. Regularized Machine Learning Model (Ridge Regression with StandardScaler)

    Args:
        monthly_features_df: Enriched monthly climate features DataFrame.
        feature_cols: Predictor column names.
        target_col: Target variable column name.
        split_year: Boundary year for chronological hold-out.

    Returns:
        Dictionary containing comparative test metrics, test predictions,
        and model coefficients.
    """
    if feature_cols is None:
        feature_cols = [
            "sin_month", "cos_month", "time_fraction",
            "tavg_mean", "tavg_lag_1", "tavg_lag_2", "tavg_lag_12",
            "rolling_tavg_3m", "rolling_tavg_12m", "prcp_lag_1"
        ]

    # Filter to rows where features and target are present
    valid_data = monthly_features_df.dropna(subset=feature_cols + [target_col]).copy()

    # Ensure target_year and target_month are present for target-date split policy
    if "target_year" not in valid_data.columns and "year" in valid_data.columns and "month" in valid_data.columns:
        valid_data["target_year"] = np.where(valid_data["month"] == 12, valid_data["year"] + 1, valid_data["year"])
    if "target_month" not in valid_data.columns and "month" in valid_data.columns:
        valid_data["target_month"] = (valid_data["month"] % 12) + 1

    train_df, test_df = temporal_train_test_split(valid_data, split_year=split_year)

    x_train = train_df[feature_cols].values
    y_train = train_df[target_col].values
    x_test = test_df[feature_cols].values
    y_test = test_df[target_col].values

    # 1. Fit ML Model: StandardScaler + Ridge Regressor pipeline (fit strictly on train)
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=10.0)),
    ])
    pipeline.fit(x_train, y_train)
    y_pred_ml = pipeline.predict(x_test)
    ml_metrics = compute_forecast_metrics(y_test, y_pred_ml)

    # 2. Climatology Seasonal Baseline:
    # Target month is next month: (current_month % 12) + 1
    target_m_col = "target_month" if "target_month" in train_df.columns else "target_m_temp"
    if target_m_col not in train_df.columns:
        train_df["target_m_temp"] = (train_df["month"] % 12) + 1
        test_df["target_m_temp"] = (test_df["month"] % 12) + 1

    climatology_lookup = (
        train_df.groupby(target_m_col)[target_col]
        .mean()
        .to_dict()
    )
    y_pred_climatology = test_df[target_m_col].map(climatology_lookup).values
    climatology_metrics = compute_forecast_metrics(y_test, y_pred_climatology)

    # 3. Persistence Baseline (predict next month using current tavg_mean)
    y_pred_persistence = test_df["tavg_mean"].values
    persistence_metrics = compute_forecast_metrics(y_test, y_pred_persistence)

    # Compile Predictions DataFrame
    pred_cols = [c for c in ["date", "target_date", "year", "month", "target_year", "target_month", "tavg_mean", target_col] if c in test_df.columns]
    pred_df = test_df[pred_cols].copy()
    if "target_date" not in pred_df.columns and "date" in pred_df.columns:
        pred_df["target_date"] = pd.to_datetime(pred_df["date"]) + pd.DateOffset(months=1)
    pred_df["pred_ml"] = y_pred_ml
    pred_df["pred_climatology"] = y_pred_climatology
    pred_df["pred_persistence"] = y_pred_persistence
    pred_df["residual_ml"] = pred_df[target_col] - pred_df["pred_ml"]

    # Model Feature Coefficients from unscaled space
    ridge_model: Ridge = pipeline.named_steps["ridge"]
    feature_importance = dict(zip(feature_cols, [float(c) for c in ridge_model.coef_]))

    train_period_min = int(train_df["year"].min())
    train_period_max = int(train_df["target_year"].max()) if "target_year" in train_df.columns else int(train_df["year"].max())
    test_period_min = int(test_df["target_year"].min()) if "target_year" in test_df.columns else int(test_df["year"].min())
    test_period_max = int(test_df["target_year"].max()) if "target_year" in test_df.columns else int(test_df["year"].max())

    train_feat_start = str(train_df["date"].min())[:7] if "date" in train_df.columns else str(train_period_min)
    train_feat_end = str(train_df["date"].max())[:7] if "date" in train_df.columns else str(train_period_max)
    test_feat_start = str(test_df["date"].min())[:7] if "date" in test_df.columns else str(test_period_min)
    test_feat_end = str(test_df["date"].max())[:7] if "date" in test_df.columns else str(test_period_max)

    if "target_date" in train_df.columns and train_df["target_date"].notna().any():
        train_target_start = str(train_df["target_date"].dropna().min())[:7]
        train_target_end = str(train_df["target_date"].dropna().max())[:7]
    elif "date" in train_df.columns:
        dt_train = pd.to_datetime(train_df["date"]) + pd.DateOffset(months=1)
        train_target_start = str(dt_train.min())[:7]
        train_target_end = str(dt_train.max())[:7]
    else:
        train_target_start = str(train_period_min)
        train_target_end = str(train_period_max)

    if "target_date" in test_df.columns and test_df["target_date"].notna().any():
        test_target_start = str(test_df["target_date"].dropna().min())[:7]
        test_target_end = str(test_df["target_date"].dropna().max())[:7]
    elif "date" in test_df.columns:
        dt_test = pd.to_datetime(test_df["date"]) + pd.DateOffset(months=1)
        test_target_start = str(dt_test.min())[:7]
        test_target_end = str(dt_test.max())[:7]
    else:
        test_target_start = str(test_period_min)
        test_target_end = str(test_period_max)

    return {
        "metrics": {
            "ml_model": ml_metrics,
            "climatology_baseline": climatology_metrics,
            "persistence_baseline": persistence_metrics,
        },
        "predictions": pred_df,
        "feature_coefficients": feature_importance,
        "train_period": (train_period_min, train_period_max),
        "test_period": (test_period_min, test_period_max),
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "train_feature_range": (train_feat_start, train_feat_end),
        "train_target_range": (train_target_start, train_target_end),
        "test_feature_range": (test_feat_start, test_feat_end),
        "test_target_range": (test_target_start, test_target_end),
        "feature_cols": feature_cols,
        "target_col": target_col,
    }
