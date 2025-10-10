
# Endpoint: /model-comparison

import json

from datetime import date, timedelta, datetime
from typing import List, Dict, Any
import statistics


from fastapi import APIRouter, HTTPException
from pathlib import Path
import pandas as pd
import random
import math






import joblib
import pickle
import numpy as np
from fastapi import Query

api_router = APIRouter()
# ...existing code...
@api_router.get("/model-history")
def api_model_history(days_back: int = 30, metrics: List[str] = None) -> Dict[str, Any]:
    """
    Returns historical accuracy data for each model for the last N days.
    Output format:
    {
        "ARIMA": [ {"date": "YYYY-MM-DD", "accuracy": 92.1, "mape": 7.9, "rmse": 3.2, ...}, ... ],
        "LSTM": [ ... ],
        ...
    }
    """
    import pandas as pd
    from pathlib import Path
    import numpy as np
    # Load processed data
    fe_path = Path(__file__).parent.parent / "data" / "processed" / "feature_engineered.csv"
    if not fe_path.exists():
        raise HTTPException(status_code=404, detail="Feature engineered dataset not found.")
    df = pd.read_csv(fe_path, parse_dates=["date"])

    # Only use models present in model-metrices.json
    metrics_path = Path(__file__).parent.parent / "data" / "model-metrices.json"
    model_names = []
    if metrics_path.exists():
        with open(metrics_path, "r") as f:
            metrics_json = json.load(f)
        model_names = [m.get("Model", "Unknown") for m in metrics_json]
    else:
        model_names = ["ARIMA", "LSTM", "XGBoost"]

    # Default metrics to return
    if not metrics:
        metrics = ["accuracy", "mape", "rmse", "mae"]

    # Get last N days
    max_date = df["date"].max()
    min_date = max_date - pd.Timedelta(days=days_back)
    df_recent = df[df["date"] >= min_date]

    # For each model, simulate historical metrics (replace with real per-model metrics if available)
    history = {}
    for model in model_names:
        # For demo: assign each model to a resource_type (customize as needed)
        if model.upper() == "ARIMA":
            model_df = df_recent[df_recent["resource_type"].str.lower().str.contains("vm")]
        elif model.upper() == "LSTM":
            model_df = df_recent[df_recent["resource_type"].str.lower().str.contains("container")]
        elif model.upper() == "XGBOOST":
            model_df = df_recent[df_recent["resource_type"].str.lower().str.contains("storage")]
        else:
            model_df = df_recent

        # Group by date
        daily = model_df.groupby("date").agg({
            "usage_cpu": ["mean", "std"],
            "usage_storage": ["mean", "std"],
        }).reset_index()
        daily.columns = ["date", "cpu_mean", "cpu_std", "storage_mean", "storage_std"]

        # Simulate accuracy metrics (replace with real metrics if available)
        records = []
        for _, row in daily.iterrows():
            # Simulate MAPE, RMSE, MAE (replace with real calculation if available)
            mape = np.abs(np.random.normal(8, 2))  # Simulate MAPE around 8% ±2
            rmse = np.abs(np.random.normal(3, 1))  # Simulate RMSE around 3 ±1
            mae = np.abs(np.random.normal(2, 0.5)) # Simulate MAE around 2 ±0.5
            accuracy = max(0, min(100, 100 - mape))
            record = {
                "date": row["date"].strftime("%Y-%m-%d"),
                "accuracy": round(accuracy, 2),
                "mape": round(mape, 2),
                "rmse": round(rmse, 2),
                "mae": round(mae, 2),
                "cpu_mean": round(row["cpu_mean"], 2),
                "cpu_std": round(row["cpu_std"], 2),
                "storage_mean": round(row["storage_mean"], 2),
                "storage_std": round(row["storage_std"], 2)
            }
            records.append(record)
        history[model] = records

    return history

# Helper: Load model (mock, replace with real logic as needed)
def load_model(model_name: str):
    model_path = Path(__file__).parent.parent / "models"
    if model_name.lower() == "arima":
        pkl = model_path / "arima_model.pkl"
        if pkl.exists():
            return joblib.load(pkl)
    elif model_name.lower() == "xgboost":
        pkl = model_path / "xgboost_model.pkl"
        if pkl.exists():
            return joblib.load(pkl)
    elif model_name.lower() == "lstm":
        h5 = model_path / "lstm_model.h5"
        if h5.exists():
            from tensorflow.keras.models import load_model as keras_load_model
            return keras_load_model(h5)
    return None

# Helper: Get best model name (from notebook or config, here hardcoded)





@api_router.get("/model-comparison")
def api_model_comparison():
    metrics_path = Path(__file__).parent.parent / "data" / "model-metrices.json"
    comparison = []
    best_model = None
    best_rank = float("inf")
    if metrics_path.exists():
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
        for m in metrics:
            comparison.append({
                "model": m.get("Model", "Unknown"),
                "MAE": m.get("MAE_mean"),
                "RMSE": m.get("RMSE_mean"),
                "MAPE": m.get("MAPE_mean"),
                "MAE_std": m.get("MAE_std"),
                "rank": m.get("rank")
            })
            if m.get("rank", float("inf")) < best_rank:
                best_rank = m["rank"]
                best_model = m.get("Model", "Unknown")
    return {
        "comparison": comparison,
        "best_model": best_model
    }



# Endpoint: /api/model-metrics
@api_router.get("/model-metrics")
def api_model_metrics():
    import json
    metrics_path = Path(__file__).parent.parent / "data" / "model-metrices.json"
    if metrics_path.exists():
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
        if isinstance(metrics, list) and metrics:
            best = min(metrics, key=lambda m: m.get("rank", float("inf")))
            return {
                "model": best.get("Model", "Unknown"),
                "metrics": {
                    "MAE": best.get("MAE_mean", None),
                    "RMSE": best.get("RMSE_mean", None),
                    "MAPE": best.get("MAPE_mean", None),
                    "Bias": best.get("Bias", None)
                }
            }
    # Fallback if file missing or error
    return {
        "model": "Unknown",
        "metrics": {}
    }



# Endpoint: /api/forecast/{region}/{service}
@api_router.get("/forecast/{region}/{service}")
def api_forecast(region: str, service: str, horizon_days: int = 30):
    """
    Returns a forecast of CPU% and Storage% for the requested region and service using trained ARIMA models.
    
    Args:
        region: Azure region (e.g., eastus, westus, northeurope, southeastasia)
        service: Service type (e.g., Container, Storage, VM)
        horizon_days: Number of days to forecast (default: 30)
    
    Returns:
        JSON with forecast data, confidence intervals, and model metadata
    """
    from .model_manager import get_model_manager
    from datetime import datetime, timedelta
    
    # Validate inputs
    if horizon_days < 1 or horizon_days > 90:
        raise HTTPException(status_code=400, detail="horizon_days must be between 1 and 90")
    
    # Get model manager
    model_manager = get_model_manager()
    
    # Check if we have models for both CPU and storage
    cpu_available = model_manager.is_model_available(region, service, "usage_cpu")
    storage_available = model_manager.is_model_available(region, service, "usage_storage")
    
    if not cpu_available and not storage_available:
        # Check if the combination exists in the data
        fe_path = Path(__file__).parent.parent / "data" / "processed" / "feature_engineered.csv" 
        if fe_path.exists():
            df = pd.read_csv(fe_path)
            if not ((df["region"] == region) & (df["resource_type"] == service)).any():
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid region/service combination: {region}/{service}"
                )
        
        raise HTTPException(
            status_code=404, 
            detail=f"No trained models available for region={region}, service={service}"
        )
    
    # Get forecast data from model_manager
    cpu_forecast_data = model_manager.get_forecast(region, service, "usage_cpu", horizon_days) if cpu_available else None
    storage_forecast_data = model_manager.get_forecast(region, service, "usage_storage", horizon_days) if storage_available else None

    # Get the latest date from the data for date generation
    fe_path = Path(__file__).parent.parent / "data" / "processed" / "feature_engineered.csv"
    last_date = None
    if fe_path.exists():
        df = pd.read_csv(fe_path, parse_dates=["date"])
        df_filtered = df[(df["region"] == region) & (df["resource_type"] == service)]
        if not df_filtered.empty:
            last_date = df_filtered["date"].max()
    if last_date is None:
        last_date = datetime.now().date()

    # Build forecast response with zigzag noise
    import random
    forecast = []
    for i in range(horizon_days):
        forecast_date = (pd.to_datetime(last_date) + pd.Timedelta(days=i+1)).date().isoformat()
        entry = {"date": forecast_date}

        # Add CPU forecast with zigzag noise
        if cpu_forecast_data:
            base = float(cpu_forecast_data["forecast"][i])
            # Add ±7% random noise, alternating sign for zigzag
            noise = (random.uniform(-0.07, 0.07) * base) * ((-1) ** i)
            entry["cpu_percent"] = round(base + noise, 2)
            ci = cpu_forecast_data.get("confidence_intervals")
            if ci is not None:
                if isinstance(ci, dict) and "lower" in ci and "upper" in ci:
                    lo = ci["lower"][i]
                    hi = ci["upper"][i]
                else:
                    try:
                        lo = ci[i][0]
                        hi = ci[i][1]
                    except Exception:
                        lo = None
                        hi = None
                if lo is not None:
                    entry["cpu_lo"] = round(float(lo), 2)
                if hi is not None:
                    entry["cpu_hi"] = round(float(hi), 2)

        # Add storage forecast with zigzag noise
        if storage_forecast_data:
            base = float(storage_forecast_data["forecast"][i])
            noise = (random.uniform(-0.07, 0.07) * base) * ((-1) ** (i+1))
            entry["storage_percent"] = round(base + noise, 2)
            ci = storage_forecast_data.get("confidence_intervals")
            if ci is not None:
                if isinstance(ci, dict) and "lower" in ci and "upper" in ci:
                    lo = ci["lower"][i]
                    hi = ci["upper"][i]
                else:
                    try:
                        lo = ci[i][0]
                        hi = ci[i][1]
                    except Exception:
                        lo = None
                        hi = None
                if lo is not None:
                    entry["storage_lo"] = round(float(lo), 2)
                if hi is not None:
                    entry["storage_hi"] = round(float(hi), 2)

        forecast.append(entry)

    # Prepare model metadata
    models_used = []
    if cpu_forecast_data and cpu_forecast_data.get("model_metadata"):
        models_used.append({
            "target": "usage_cpu",
            "metadata": cpu_forecast_data["model_metadata"]
        })
    if storage_forecast_data and storage_forecast_data.get("model_metadata"):
        models_used.append({
            "target": "usage_storage", 
            "metadata": storage_forecast_data["model_metadata"]
        })

    return {
        "region": region,
        "service": service,
        "horizon_days": horizon_days,
        "forecast": forecast,
        "models_used": models_used,
        "forecast_generated_at": datetime.now().isoformat(),
        "data_last_updated": last_date.isoformat() if hasattr(last_date, 'isoformat') else str(last_date)
    }

# Endpoint: /api/models/available
@api_router.get("/models/available")
def api_available_models():
    """
    Get list of all available trained models and their metadata.
    """
    from .model_manager import get_model_manager
    
    model_manager = get_model_manager()
    available_combinations = model_manager.get_available_combinations()
    
    models = []
    for region, service, target in available_combinations:
        metadata = model_manager.get_model_metadata(region, service, target)
        models.append({
            "region": region,
            "service": service,
            "target": target,
            "metadata": metadata
        })
    
    summary = model_manager.get_model_summary()
    
    return {
        "available_models": models,
        "summary": summary
    }

# Endpoint: /api/models/summary
@api_router.get("/models/summary")
def api_models_summary():
    """
    Get summary statistics of available models.
    """
    from .model_manager import get_model_manager
    
    model_manager = get_model_manager()
    return model_manager.get_model_summary()

# Endpoint: /api/models/{region}/{service}/{target}/metadata
@api_router.get("/models/{region}/{service}/{target}/metadata")
def api_get_model_metadata(region: str, service: str, target: str):
    """
    Get metadata for a specific model.
    
    Args:
        region: Azure region (e.g., eastus, westus)
        service: Service type (e.g., VirtualMachine, Container, Storage)
        target: Target metric (usage_cpu or usage_storage)
    
    Returns:
        JSON with model metadata including training details, performance metrics
    """
    from .model_manager import get_model_manager
    
    model_manager = get_model_manager()
    
    # Check if model is available
    if not model_manager.is_model_available(region, service, target):
        raise HTTPException(
            status_code=404, 
            detail=f"No model available for {region}/{service}/{target}"
        )
    
    # Get metadata
    metadata = model_manager.get_model_metadata(region, service, target)
    
    if not metadata:
        raise HTTPException(
            status_code=404,
            detail=f"No metadata available for {region}/{service}/{target}"
        )
    
    return {
        "region": region,
        "service": service,
        "target": target,
        "metadata": metadata,
        "retrieved_at": datetime.now().isoformat()
    }




















































#mile 1:
@api_router.get("/usage-trends")
def get_usage_trends() -> Dict[str, Any]:
    # Load real data from cleaned_merged.csv
    csv_path = Path(__file__).parent.parent / "data" / "processed" / "cleaned_merged.csv"
    df = pd.read_csv(csv_path)

    # Only use VM resource_type for CPU usage aggregation (can be changed if needed)
    df_vm = df[df["resource_type"] == "VM"]

    # Get all regions
    regions = sorted(df_vm["region"].unique())

    # Get all dates (sorted)
    dates = sorted(df_vm["date"].unique())

    series = []
    for region in regions:
        region_data = df_vm[df_vm["region"] == region]
        region_series = []
        for d in dates:
            day_data = region_data[region_data["date"] == d]
            # Aggregate CPU and storage usage for the day (sum over all VMs)
            cpu_percent = float(day_data["usage_cpu"].sum())
            storage_percent = float(day_data["usage_storage"].sum())
            region_series.append({
                "date": d,
                "cpu_percent": round(cpu_percent, 2),
                "storage_percent": round(storage_percent, 2)
            })
        series.append({"region": region, "data": region_series})

    return {"regions": regions, "series": series}



@api_router.get("/forecast")
def get_forecast() -> Dict[str, Any]:
    # Load real data from cleaned_merged.csv
    csv_path = Path(__file__).parent.parent / "data" / "processed" / "cleaned_merged.csv"
    df = pd.read_csv(csv_path)

    # Only use VM resource_type for CPU usage aggregation (can be changed if needed)
    df_vm = df[df["resource_type"] == "VM"]

    regions = sorted(df_vm["region"].unique())
    horizon_days = 14
    last_date = pd.to_datetime(df_vm["date"].max())

    forecasts = {}
    for region in regions:
        region_data = df_vm[df_vm["region"] == region].copy()
        region_data["date_dt"] = pd.to_datetime(region_data["date"])
        region_data = region_data.sort_values("date_dt")
        # Use last 14 days for regression
        last_n = region_data.tail(14)
        if len(last_n) < 2:
            # fallback to mean if not enough data
            mean_cpu = float(last_n["usage_cpu"].mean()) if len(last_n) > 0 else 0.0
            mean_storage = float(last_n["usage_storage"].mean()) if len(last_n) > 0 else 0.0
            region_forecast = []
            for offset in range(1, horizon_days + 1):
                forecast_date = (last_date + pd.Timedelta(days=offset)).date().isoformat()
                region_forecast.append({
                    "date": forecast_date,
                    "cpu_percent": round(mean_cpu, 2),
                    "storage_percent": round(mean_storage, 2)
                })
            forecasts[region] = region_forecast
            continue

        # Linear regression for CPU and storage
        import numpy as np
        x = np.arange(len(last_n))
        cpu_y = last_n["usage_cpu"].values
        storage_y = last_n["usage_storage"].values
        cpu_coef = np.polyfit(x, cpu_y, 1)
        storage_coef = np.polyfit(x, storage_y, 1)
        cpu_trend = np.poly1d(cpu_coef)
        storage_trend = np.poly1d(storage_coef)

        region_forecast = []
        for offset in range(1, horizon_days + 1):
            forecast_date = (last_date + pd.Timedelta(days=offset)).date().isoformat()
            # Predict next values
            next_x = len(last_n) + offset - 1
            cpu_pred = float(cpu_trend(next_x))
            storage_pred = float(storage_trend(next_x))
            region_forecast.append({
                "date": forecast_date,
                "cpu_percent": round(cpu_pred, 2),
                "storage_percent": round(storage_pred, 2)
            })
        forecasts[region] = region_forecast

    return {"horizon_days": horizon_days, "forecasts": forecasts}


def _project_root() -> Path:
    current_path = Path(__file__).resolve()
    while current_path.parent != current_path:  
        if (current_path / "data" / "processed" / "cleaned_merged.csv").exists():
            return current_path
        current_path = current_path.parent
    return Path(__file__).resolve().parents[3]


def _load_processed(limit: int | None = None) -> pd.DataFrame:
    processed_csv = _project_root() / "data" / "processed" / "cleaned_merged.csv"
    if not processed_csv.exists():
        raise HTTPException(status_code=404, detail="Processed dataset not found. Run dataprocessing.py first.")
    df = pd.read_csv(processed_csv, nrows=limit if limit and limit > 0 else None)
    rename_map = {
        "usage_cpu": "cpu_usage",
        "usage_storage": "storage",
        "resource_type": "vm_type",
        "cloud_market_demand": "market_trend",
    }
    for old, new in rename_map.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})
    return df


@api_router.get("/top-regions")
def get_top_regions(limit: int = 5) -> Dict[str, Any]:
    try:
        df = _load_processed()
        if "cpu_usage" not in df.columns or "region" not in df.columns:
            raise HTTPException(status_code=500, detail="Required columns not found in processed dataset.")
        grouped = (
            df.groupby("region")["cpu_usage"].sum().sort_values(ascending=False).head(max(1, limit))
        )
        return {
            "limit": max(1, limit),
            "top_regions": [{"region": r, "cpu_usage_total": float(v)} for r, v in grouped.items()],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)})


@api_router.get("/raw-data")
def get_raw_data(limit: int | None = None) -> Dict[str, Any]:
    try:
        df = _load_processed(limit=limit)
        return {
            "rows": len(df),
            "columns": list(df.columns),
            "data": df.to_dict(orient="records"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)})
    
@api_router.get("/features")
def get_feature_engineered_dataset(limit: int | None = None) -> Dict[str, Any]:
    """
    Returns the full feature_engineered.csv dataset as JSON.
    """
    project_root = Path(__file__).resolve().parents[1]
    fe_path = project_root / "data" / "processed" / "feature_engineered.csv"
    if not fe_path.exists():
        raise HTTPException(status_code=404, detail="Feature engineered dataset not found. Run feature_engineering.py first.")
    df = pd.read_csv(fe_path, nrows=limit if limit and limit > 0 else None)
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "data": df.to_dict(orient="records"),
    }








@api_router.get("/insights")
def get_summary_insights() -> Dict[str, Any]:
    """
    Returns pre-computed summary insights for dashboard visualization.
    """
    project_root = Path(__file__).resolve().parents[1]
    fe_path = project_root / "data" / "processed" / "feature_engineered.csv"
    if not fe_path.exists():
        raise HTTPException(status_code=404, detail="Feature engineered dataset not found. Run feature_engineering.py first.")
    df = pd.read_csv(fe_path, parse_dates=["date"])

    # Top 5 regions by CPU usage
    top_regions = (
        df.groupby("region")["usage_cpu"].sum().sort_values(ascending=False).head(5)
    )
    top_regions_list = [{"region": r, "cpu_usage_total": float(v)} for r, v in top_regions.items()]

    # Month/quarter with peak demand
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    monthly_peak = df.groupby(["month"])["usage_cpu"].sum().idxmax()
    quarterly_peak = df.groupby(["quarter"])["usage_cpu"].sum().idxmax()

    # Monthly usage for chart
    df["month_str"] = df["date"].dt.strftime('%Y-%m')
    monthly_usage = df.groupby("month_str")["usage_cpu"].sum().reset_index()
    monthly_usage_list = [
        {"month": row["month_str"], "cpu_usage": float(row["usage_cpu"])} for _, row in monthly_usage.iterrows()
    ]

    # Average daily usage per region
    avg_daily = (
        df.groupby(["region", "date"])["usage_cpu"].sum().groupby("region").mean()
    )
    avg_daily_list = [{"region": r, "avg_daily_cpu": float(v)} for r, v in avg_daily.items()]

    # Storage efficiency per region
    storage_eff = (
        df.groupby("region")["storage_efficiency"].mean()
    ) if "storage_efficiency" in df.columns else None
    storage_eff_list = (
        [{"region": r, "storage_efficiency": float(v)} for r, v in storage_eff.items()] if storage_eff is not None else []
    )

    # CPU utilization ratios per region
    cpu_util = (
        df.groupby("region")["cpu_utilization_ratio"].mean()
    ) if "cpu_utilization_ratio" in df.columns else None
    cpu_util_list = (
        [{"region": r, "cpu_utilization_ratio": float(v)} for r, v in cpu_util.items()] if cpu_util is not None else []
    )

    # Weekday vs weekend demand patterns
    if "is_weekend" in df.columns:
        weekday_mean = df[df["is_weekend"] == 0]["usage_cpu"].mean()
        weekend_mean = df[df["is_weekend"] == 1]["usage_cpu"].mean()
    else:
        weekday_mean = weekend_mean = None

    # Key correlations with external factors
    corr = df.corr(numeric_only=True)
    ext_corr = {}
    for ext in ["econ_index", "cloud_market_demand"]:
        if ext in corr.index and "usage_cpu" in corr.columns:
            ext_corr[ext] = float(corr.at[ext, "usage_cpu"])

    return {
        "top_regions_by_cpu": top_regions_list,
        "monthly_peak_demand": int(monthly_peak),
        "quarterly_peak_demand": int(quarterly_peak),
        "monthly_usage": monthly_usage_list,
        "avg_daily_usage_per_region": avg_daily_list,
        "storage_efficiency_per_region": storage_eff_list,
        "cpu_utilization_ratios": cpu_util_list,
        "weekday_vs_weekend_cpu": {
            "weekday_mean": float(weekday_mean) if weekday_mean is not None else None,
            "weekend_mean": float(weekend_mean) if weekend_mean is not None else None,
        },
        "correlations_with_external_factors": ext_corr,
    }

# =============================================================================
# CAPACITY PLANNING ENDPOINTS
# =============================================================================

# Endpoint: /api/capacity-planning/{region}/{service}
@api_router.get("/capacity-planning/{region}/{service}")
def api_capacity_planning(region: str, service: str, 
                         horizon_days: int = 30, 
                         target: str = "usage_cpu",
                         strategy: str = None):
    """
    Get capacity planning recommendations for a specific region/service.
    
    Args:
        region: Azure region (e.g., eastus, westus)
        service: Service type (e.g., Container, VM, Storage)
        horizon_days: Forecast horizon in days (default: 30)
        target: Target metric (usage_cpu or usage_storage)
        strategy: Capacity planning strategy (peak_based, p95_based, average_plus_buffer)
    
    Returns:
        JSON with capacity recommendation including gaps, risks, and actions
    """
    from .model_manager import get_model_manager
    from .capacity_planning import get_capacity_engine
    
    # Validate inputs
    if horizon_days < 1 or horizon_days > 90:
        raise HTTPException(status_code=400, detail="horizon_days must be between 1 and 90")
    
    if target not in ["usage_cpu", "usage_storage"]:
        raise HTTPException(status_code=400, detail="target must be 'usage_cpu' or 'usage_storage'")
    
    # Get forecast data
    model_manager = get_model_manager()
    if not model_manager.is_model_available(region, service, target):
        raise HTTPException(
            status_code=404, 
            detail=f"No forecast model available for {region}/{service}/{target}"
        )
    
    forecast_result = model_manager.get_forecast(region, service, target, horizon_days)
    if not forecast_result:
        raise HTTPException(
            status_code=500, 
            detail="Failed to generate forecast for capacity planning"
        )
    
    # Generate capacity recommendation
    capacity_engine = get_capacity_engine()
    
    # Generate forecast dates
    from datetime import datetime, timedelta
    start_date = datetime.now().date() + timedelta(days=1)
    forecast_dates = [(start_date + timedelta(days=i)).isoformat() for i in range(horizon_days)]
    
    recommendation = capacity_engine.create_capacity_recommendation(
        region=region,
        service=service,
        target=target,
        forecast_data=forecast_result["forecast"],
        forecast_dates=forecast_dates,
        strategy=strategy
    )
    
    if not recommendation:
        raise HTTPException(
            status_code=404,
            detail=f"No capacity configuration available for {region}/{service}"
        )
    
    # Convert to JSON-serializable format
    return {
        "region": recommendation.region,
        "service": recommendation.service,
        "target": recommendation.target,
        "forecast_period": recommendation.forecast_period,
        "forecast_peak_demand": round(recommendation.forecast_peak_demand, 2),
        "forecast_avg_demand": round(recommendation.forecast_avg_demand, 2),
        "available_capacity": round(recommendation.available_capacity, 2),
        "required_capacity": round(recommendation.required_capacity, 2),
        "gap_absolute": round(recommendation.gap_absolute, 2),
        "gap_percentage": round(recommendation.gap_percentage, 2),
        "risk_level": recommendation.risk_level.value,
        "action_type": recommendation.action_type.value,
        "recommended_adjustment": recommendation.recommended_adjustment,
        "reason": recommendation.reason,
        "cost_impact_monthly": round(recommendation.cost_impact_monthly, 2),
        "confidence_score": round(recommendation.confidence_score, 2),
        "additional_metrics": recommendation.additional_metrics,
        "generated_at": datetime.now().isoformat()
    }

# Endpoint: /api/capacity/current
@api_router.get("/capacity/current")
def api_current_capacity():
    """
    Get current capacity inventory across all regions and services.
    
    Returns:
        JSON with capacity summary including units, costs, and utilization
    """
    from .capacity_planning import get_capacity_engine
    
    capacity_engine = get_capacity_engine()
    summary = capacity_engine.get_all_capacity_summary()
    
    return summary

# Endpoint: /api/capacity/risks
@api_router.get("/capacity/risks")
def api_capacity_risks(risk_threshold: str = "medium"):
    """
    Get list of regions/services with capacity risks above threshold.
    
    Args:
        risk_threshold: Minimum risk level to include (low, medium, high, critical)
    
    Returns:
        JSON with list of high-risk capacity situations
    """
    from .model_manager import get_model_manager
    from .capacity_planning import get_capacity_engine, RiskLevel
    from datetime import datetime, timedelta
    
    # Validate risk threshold
    risk_levels = {"low": RiskLevel.LOW, "medium": RiskLevel.MEDIUM, 
                  "high": RiskLevel.HIGH, "critical": RiskLevel.CRITICAL}
    
    if risk_threshold.lower() not in risk_levels:
        raise HTTPException(
            status_code=400, 
            detail="risk_threshold must be one of: low, medium, high, critical"
        )
    
    threshold_level = risk_levels[risk_threshold.lower()]
    
    # Get available models and assess risks
    model_manager = get_model_manager()
    capacity_engine = get_capacity_engine()
    available_combinations = model_manager.get_available_combinations()
    
    risks = []
    forecast_dates = [(datetime.now().date() + timedelta(days=i+1)).isoformat() for i in range(30)]
    
    for region, service, target in available_combinations:
        # Get forecast
        forecast_result = model_manager.get_forecast(region, service, target, 30)
        if not forecast_result:
            continue
        
        # Generate recommendation
        recommendation = capacity_engine.create_capacity_recommendation(
            region=region,
            service=service,
            target=target,
            forecast_data=forecast_result["forecast"],
            forecast_dates=forecast_dates
        )
        
        if not recommendation:
            continue
        
        # Check if risk level meets threshold
        risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        if risk_order.index(recommendation.risk_level) >= risk_order.index(threshold_level):
            risks.append({
                "region": recommendation.region,
                "service": recommendation.service,
                "target": recommendation.target,
                "risk_level": recommendation.risk_level.value,
                "gap_percentage": round(recommendation.gap_percentage, 2),
                "recommended_adjustment": recommendation.recommended_adjustment,
                "cost_impact_monthly": round(recommendation.cost_impact_monthly, 2),
                "urgency_score": risk_order.index(recommendation.risk_level)
            })
    
    # Sort by urgency (highest risk first)
    risks.sort(key=lambda x: x["urgency_score"], reverse=True)
    
    return {
        "risk_threshold": risk_threshold,
        "total_risks_found": len(risks),
        "risks": risks,
        "generated_at": datetime.now().isoformat()
    }

# Endpoint: /api/capacity/recommendations
@api_router.get("/capacity/recommendations")
def api_capacity_recommendations(include_low_risk: bool = False):
    """
    Get capacity recommendations for all regions/services.
    
    Args:
        include_low_risk: Whether to include low-risk items (default: False)
    
    Returns:
        JSON with comprehensive capacity recommendations
    """
    from .model_manager import get_model_manager
    from .capacity_planning import get_capacity_engine, RiskLevel
    from datetime import datetime, timedelta
    
    model_manager = get_model_manager()
    capacity_engine = get_capacity_engine()
    available_combinations = model_manager.get_available_combinations()
    
    recommendations = []
    forecast_dates = [(datetime.now().date() + timedelta(days=i+1)).isoformat() for i in range(30)]
    
    for region, service, target in available_combinations:
        # Get forecast
        forecast_result = model_manager.get_forecast(region, service, target, 30)
        if not forecast_result:
            continue
        
        # Generate recommendation
        recommendation = capacity_engine.create_capacity_recommendation(
            region=region,
            service=service,
            target=target,
            forecast_data=forecast_result["forecast"],
            forecast_dates=forecast_dates
        )
        
        if not recommendation:
            continue
        
        # Filter low-risk items if requested
        if not include_low_risk and recommendation.risk_level == RiskLevel.LOW:
            continue
        
        recommendations.append({
            "region": recommendation.region,
            "service": recommendation.service,
            "target": recommendation.target,
            "risk_level": recommendation.risk_level.value,
            "action_type": recommendation.action_type.value,
            "gap_percentage": round(recommendation.gap_percentage, 2),
            "recommended_adjustment": recommendation.recommended_adjustment,
            "cost_impact_monthly": round(recommendation.cost_impact_monthly, 2),
            "confidence_score": round(recommendation.confidence_score, 2),
            "reason": recommendation.reason
        })
    
    # Group by region for easier consumption
    by_region = {}
    total_cost_impact = 0.0
    
    for rec in recommendations:
        region = rec["region"]
        if region not in by_region:
            by_region[region] = []
        by_region[region].append(rec)
        total_cost_impact += rec["cost_impact_monthly"]
    
    return {
        "total_recommendations": len(recommendations),
        "total_cost_impact_monthly": round(total_cost_impact, 2),
        "recommendations_by_region": by_region,
        "recommendations": recommendations,
        "generated_at": datetime.now().isoformat()
    }

# =============================================================================
# REPORTING & AUTOMATION ENDPOINTS
# =============================================================================

# Endpoint: /api/scheduler/run
@api_router.post("/scheduler/run")
def api_run_scheduled_forecast():
    """
    Manually trigger scheduled forecast generation.
    
    Returns:
        JSON with forecast run results and statistics
    """
    from .scheduler import get_scheduler
    
    try:
        scheduler = get_scheduler()
        result = scheduler.run_scheduled_forecast()
        
        return {
            "status": result["status"],
            "run_id": result.get("run_id"),
            "duration_seconds": result.get("duration_seconds", 0),
            "successful_forecasts": result.get("successful_forecasts", 0),
            "failed_forecasts": result.get("failed_forecasts", 0),
            "total_forecast_records": result.get("total_forecast_records", 0),
            "errors": result.get("errors", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduler run failed: {str(e)}")

# Endpoint: /api/scheduler/status
@api_router.get("/scheduler/status")
def api_scheduler_status():
    """
    Get status of recent forecast runs.
    
    Returns:
        JSON with recent run information
    """
    from .scheduler import get_scheduler
    
    try:
        scheduler = get_scheduler()
        latest_run = scheduler.get_latest_run_status()
        recent_runs = scheduler.get_recent_runs(limit=5)
        
        return {
            "latest_run": latest_run,
            "recent_runs": recent_runs,
            "total_recent_runs": len(recent_runs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")

# Endpoint: /api/forecasts/history
@api_router.get("/forecasts/history")
def api_forecast_history(region: str = None, service: str = None, target: str = None,
                        days_back: int = 30, limit: int = 100):
    """
    Get historical forecast data from database.
    
    Args:
        region: Filter by region (optional)
        service: Filter by service (optional)
        target: Filter by target metric (optional)
        days_back: Number of days back to retrieve (default: 30)
        limit: Maximum records to return (default: 100)
    
    Returns:
        JSON with historical forecast records
    """
    from .database import get_database_manager, Forecast
    from sqlalchemy import and_, desc
    from datetime import datetime, timedelta
    
    db_manager = get_database_manager()
    session = db_manager.get_session()
    
    try:
        # Build query filters
        filters = []
        
        if region:
            filters.append(Forecast.region == region)
        if service:
            filters.append(Forecast.service == service)
        if target:
            filters.append(Forecast.target == target)
        
        # Date filter
        cutoff_date = datetime.now() - timedelta(days=days_back)
        filters.append(Forecast.generated_at >= cutoff_date)
        
        # Execute query
        query = session.query(Forecast)
        if filters:
            query = query.filter(and_(*filters))
        
        forecasts = query.order_by(desc(Forecast.generated_at)).limit(limit).all()
        
        # Convert to JSON-serializable format
        forecast_data = []
        for forecast in forecasts:
            forecast_data.append({
                "id": forecast.id,
                "run_id": forecast.run_id,
                "region": forecast.region,
                "service": forecast.service,
                "target": forecast.target,
                "forecast_date": forecast.forecast_date.isoformat(),
                "predicted_value": forecast.predicted_value,
                "lower_ci": forecast.lower_ci,
                "upper_ci": forecast.upper_ci,
                "model_version": forecast.model_version,
                "generated_at": forecast.generated_at.isoformat(),
                "horizon_days": forecast.horizon_days,
                "confidence_score": forecast.confidence_score
            })
        
        return {
            "forecasts": forecast_data,
            "total_records": len(forecast_data),
            "filters_applied": {
                "region": region,
                "service": service,
                "target": target,
                "days_back": days_back
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve forecast history: {str(e)}")
    finally:
        db_manager.close_session(session)

# Endpoint: /api/accuracy/metrics
@api_router.get("/accuracy/metrics")
def api_accuracy_metrics(region: str = None, service: str = None, target: str = None,
                        days_back: int = 30):
    """
    Get forecast accuracy metrics.
    
    Args:
        region: Filter by region (optional)
        service: Filter by service (optional)
        target: Filter by target metric (optional)
        days_back: Number of days back to analyze (default: 30)
    
    Returns:
        JSON with accuracy metrics and summary
    """
    from .accuracy_tracker import get_accuracy_tracker
    
    try:
        tracker = get_accuracy_tracker()
        
        if region and service and target:
            # Get accuracy for specific combination
            result = tracker.calculate_accuracy_for_combination(region, service, target, days_back)
            if result:
                return {
                    "region": result.region,
                    "service": result.service,
                    "target": result.target,
                    "mae": result.mae,
                    "mape": result.mape,
                    "rmse": result.rmse,
                    "accuracy_score": result.accuracy_score,
                    "sample_size": result.sample_size,
                    "period_start": result.period_start.isoformat(),
                    "period_end": result.period_end.isoformat()
                }
            else:
                raise HTTPException(status_code=404, detail="No accuracy data available for specified combination")
        else:
            # Get summary across all combinations
            summary = tracker.get_accuracy_summary(days_back)
            return summary
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get accuracy metrics: {str(e)}")

# Endpoint: /api/accuracy/calculate
@api_router.post("/accuracy/calculate")
def api_calculate_accuracy(days_back: int = 30):
    """
    Trigger accuracy calculation for all model combinations.
    
    Args:
        days_back: Number of days back to analyze (default: 30)
    
    Returns:
        JSON with calculation results
    """
    from .accuracy_tracker import get_accuracy_tracker
    
    try:
        tracker = get_accuracy_tracker()
        results = tracker.calculate_all_accuracy_metrics(days_back)
        
        return {
            "status": "completed",
            "accuracy_results": len(results),
            "period_days": days_back,
            "results": [
                {
                    "region": result.region,
                    "service": result.service,
                    "target": result.target,
                    "accuracy_score": result.accuracy_score,
                    "mae": result.mae,
                    "sample_size": result.sample_size
                }
                for result in results
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Accuracy calculation failed: {str(e)}")

# Endpoint: /api/reports/daily
@api_router.get("/reports/daily")
def api_daily_report(target_date: str = None):
    """
    Generate and retrieve daily capacity planning report.
    
    Args:
        target_date: Date in YYYY-MM-DD format (default: yesterday)
    
    Returns:
        JSON with daily summary report
    """
    from .report_generator import get_report_generator
    from datetime import datetime
    
    try:
        generator = get_report_generator()
        
        # Parse target date if provided
        if target_date:
            try:
                target_datetime = datetime.fromisoformat(target_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            target_datetime = None
        
        # Generate daily summary
        summary = generator.generate_daily_summary(target_datetime)
        
        # Convert to JSON-serializable format
        return {
            "date": summary.date,
            "total_forecasts_generated": summary.total_forecasts_generated,
            "regions_with_shortages": summary.regions_with_shortages,
            "urgent_capacity_actions": summary.urgent_capacity_actions,
            "top_risks": summary.top_risks,
            "recommended_adjustments": summary.recommended_adjustments,
            "system_health": summary.system_health
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate daily report: {str(e)}")

# Endpoint: /api/reports/weekly
@api_router.get("/reports/weekly")
def api_weekly_report(week_start: str = None):
    """
    Generate and retrieve weekly accuracy and performance report.
    
    Args:
        week_start: Week start date in YYYY-MM-DD format (default: last Monday)
    
    Returns:
        JSON with weekly report
    """
    from .report_generator import get_report_generator
    from datetime import datetime
    
    try:
        generator = get_report_generator()
        
        # Parse week start date if provided
        if week_start:
            try:
                week_start_datetime = datetime.fromisoformat(week_start)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            week_start_datetime = None
        
        # Generate weekly report
        report = generator.generate_weekly_report(week_start_datetime)
        
        # Convert to JSON-serializable format
        return {
            "week_start": report.week_start,
            "week_end": report.week_end,
            "forecast_accuracy_trends": report.forecast_accuracy_trends,
            "capacity_changes_executed": report.capacity_changes_executed,
            "cost_impact_summary": report.cost_impact_summary,
            "model_performance": report.model_performance,
            "recommendations_summary": report.recommendations_summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate weekly report: {str(e)}")

# Endpoint: /api/reports/generate
@api_router.post("/reports/generate")
def api_generate_reports(report_type: str = "daily"):
    """
    Generate and export reports to files.
    
    Args:
        report_type: Type of report ("daily" or "weekly")
    
    Returns:
        JSON with generation results and file paths
    """
    from .report_generator import get_report_generator
    
    try:
        generator = get_report_generator()
        
        if report_type.lower() == "daily":
            result = generator.run_daily_report_generation()
        elif report_type.lower() == "weekly":
            result = generator.run_weekly_report_generation()
        else:
            raise HTTPException(status_code=400, detail="report_type must be 'daily' or 'weekly'")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

# Endpoint: /api/database/init
@api_router.post("/database/init")
def api_init_database():
    """
    Initialize database tables for forecast storage and tracking.
    
    Returns:
        JSON with initialization status
    """
    from .database import init_database
    
    try:
        init_database()
        return {
            "status": "success",
            "message": "Database initialized successfully",
            "tables_created": [
                "forecast_runs",
                "forecasts", 
                "actuals",
                "accuracy_metrics",
                "capacity_actions"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")

# Endpoint: /api/actuals/add
@api_router.post("/actuals/add")
def api_add_actual_values(actuals_data: List[Dict[str, Any]]):
    """
    Add actual observed values for accuracy tracking.
    
    Args:
        actuals_data: List of dictionaries with actual values
        Format: [{"region": "eastus", "service": "Container", "target": "usage_cpu", 
                 "date": "2024-01-01", "actual_value": 75.5}]
    
    Returns:
        JSON with number of records added
    """
    from .accuracy_tracker import get_accuracy_tracker
    
    try:
        tracker = get_accuracy_tracker()
        records_added = tracker.add_actual_values(actuals_data)
        
        return {
            "status": "success",
            "records_added": records_added,
            "total_submitted": len(actuals_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add actual values: {str(e)}")

# Endpoint: /api/actuals/simulate
@api_router.post("/actuals/simulate")
def api_simulate_actual_data(days_back: int = 30, noise_factor: float = 0.1):
    """
    Generate simulated actual data for testing accuracy tracking.
    
    Args:
        days_back: Number of days back to generate data for
        noise_factor: Amount of noise to add (0.0-1.0)
    
    Returns:
        JSON with number of simulated records created
    """
    from .accuracy_tracker import get_accuracy_tracker
    
    try:
        if not (0.0 <= noise_factor <= 1.0):
            raise HTTPException(status_code=400, detail="noise_factor must be between 0.0 and 1.0")
        
        tracker = get_accuracy_tracker()
        records_created = tracker.simulate_actual_data(days_back, noise_factor)
        
        return {
            "status": "success",
            "simulated_records": records_created,
            "days_back": days_back,
            "noise_factor": noise_factor
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to simulate actual data: {str(e)}")

# =============================================================================
# MONITORING & RETRAINING ENDPOINTS
# =============================================================================

# Endpoint: /api/monitoring
@api_router.get("/monitoring")
def api_monitoring_overview():
    """
    Get comprehensive monitoring overview for all models.
    
    Returns:
        JSON with system health, model statuses, and recommendations
    """
    from .model_monitor import get_model_monitor
    
    try:
        monitor = get_model_monitor()
        summary = monitor.get_monitoring_summary()
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monitoring overview failed: {str(e)}")

# Endpoint: /api/monitoring/{region}/{service}/{target}
@api_router.get("/monitoring/{region}/{service}/{target}")
def api_monitoring_specific(region: str, service: str, target: str):
    """
    Get detailed monitoring information for a specific model.
    
    Args:
        region: Azure region
        service: Service type
        target: Target metric (usage_cpu or usage_storage)
    
    Returns:
        JSON with detailed model monitoring status
    """
    from .model_monitor import get_model_monitor
    from datetime import datetime
    
    try:
        monitor = get_model_monitor()
        status = monitor.monitor_model(region, service, target)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"No monitoring data available for {region}/{service}/{target}"
            )
        
        # Convert to JSON-serializable format
        return {
            "model_version": status.model_version,
            "current_mae": round(status.performance_metrics.current_mae, 2),
            "mae_30day_avg": round(status.performance_metrics.mae_30day_avg, 2),
            "mae_7day_avg": round(status.performance_metrics.mae_7day_avg, 2),
            "baseline_mae": round(status.performance_metrics.baseline_mae, 2),
            "mae_trend": status.performance_metrics.mae_trend,
            "drift_flag": status.drift_metrics.drift_flag if status.drift_metrics else False,
            "drift_score": round(status.drift_metrics.drift_score, 4) if status.drift_metrics else None,
            "days_since_last_retrain": status.days_since_last_retrain,
            "last_retrain_date": status.last_retrain_date.isoformat() if status.last_retrain_date else None,
            "health_status": status.health_status.value,
            "recommended_action": status.recommended_action.value,
            "alert_level": status.alert_level,
            "data_coverage": round(status.performance_metrics.data_coverage, 3),
            "sample_size": status.performance_metrics.sample_size,
            "monitoring_summary": status.monitoring_summary,
            "action": status.recommended_action.value.replace("_", " "),
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model monitoring failed: {str(e)}")

# Endpoint: /api/monitoring/health
@api_router.get("/monitoring/health")
def api_monitoring_health():
    """
    Get system health summary for monitoring dashboards.
    
    Returns:
        JSON with health metrics and alerts
    """
    from .model_monitor import get_model_monitor
    
    try:
        monitor = get_model_monitor()
        results = monitor.monitor_all_models()
        
        if not results:
            return {
                "system_status": "unknown",
                "total_models": 0,
                "health_score": 0.0,
                "alerts": []
            }
        
        # Calculate health metrics
        total_models = len(results)
        critical_count = len([r for r in results if r.health_status.value == "critical"])
        warning_count = len([r for r in results if r.health_status.value == "warning"])
        healthy_count = total_models - critical_count - warning_count
        
        health_score = healthy_count / total_models if total_models > 0 else 0.0
        
        # Determine system status
        if critical_count > 0:
            system_status = "critical"
        elif warning_count > total_models * 0.3:  # More than 30% warnings
            system_status = "warning"
        elif health_score > 0.8:
            system_status = "healthy"
        else:
            system_status = "degraded"
        
        # Generate alerts
        alerts = []
        for result in results:
            if result.health_status.value in ["critical", "warning"]:
                alerts.append({
                    "level": result.alert_level,
                    "model": f"{result.region}/{result.service}/{result.target}",
                    "message": result.monitoring_summary,
                    "action": result.recommended_action.value
                })
        
        return {
            "system_status": system_status,
            "total_models": total_models,
            "health_score": round(health_score, 3),
            "models_by_status": {
                "healthy": healthy_count,
                "warning": warning_count,
                "critical": critical_count
            },
            "alerts": alerts[:10],  # Limit to top 10 alerts
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health monitoring failed: {str(e)}")

# Endpoint: /api/monitoring/drift
@api_router.get("/monitoring/drift")
def api_monitoring_drift(threshold: float = 0.05):
    """
    Get models with detected data drift.
    
    Args:
        threshold: Drift detection threshold (default: 0.05)
    
    Returns:
        JSON with models showing data drift
    """
    from .model_monitor import get_model_monitor
    
    try:
        monitor = get_model_monitor()
        results = monitor.monitor_all_models()
        
        drift_models = []
        for result in results:
            if result.drift_metrics and result.drift_metrics.drift_flag:
                drift_models.append({
                    "region": result.region,
                    "service": result.service,
                    "target": result.target,
                    "drift_score": round(result.drift_metrics.drift_score, 4),
                    "p_value": round(result.drift_metrics.p_value, 6) if result.drift_metrics.p_value else None,
                    "drift_method": result.drift_metrics.drift_method,
                    "reference_period": f"{result.drift_metrics.reference_period_start.date()} to {result.drift_metrics.reference_period_end.date()}",
                    "current_period": f"{result.drift_metrics.current_period_start.date()} to {result.drift_metrics.current_period_end.date()}",
                    "recommended_action": result.recommended_action.value
                })
        
        return {
            "drift_threshold": threshold,
            "total_models_checked": len(results),
            "models_with_drift": len(drift_models),
            "drift_detected": drift_models,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drift monitoring failed: {str(e)}")

# Endpoint: /api/monitoring/performance
@api_router.get("/monitoring/performance")
def api_monitoring_performance():
    """
    Get performance metrics summary across all models.
    
    Returns:
        JSON with performance statistics and trends
    """
    from .model_monitor import get_model_monitor
    
    try:
        monitor = get_model_monitor()
        results = monitor.monitor_all_models()
        
        if not results:
            return {
                "message": "No models available for performance monitoring",
                "total_models": 0
            }
        
        # Aggregate performance metrics
        mae_values = [r.performance_metrics.current_mae for r in results]
        mae_30day_values = [r.performance_metrics.mae_30day_avg for r in results]
        coverage_values = [r.performance_metrics.data_coverage for r in results]
        
        # Trend analysis
        trend_counts = {}
        for result in results:
            trend = result.performance_metrics.mae_trend
            trend_counts[trend] = trend_counts.get(trend, 0) + 1
        
        # Models needing attention
        degrading_models = [
            {
                "region": r.region,
                "service": r.service,
                "target": r.target,
                "current_mae": round(r.performance_metrics.current_mae, 2),
                "baseline_mae": round(r.performance_metrics.baseline_mae, 2),
                "degradation_ratio": round(r.performance_metrics.current_mae / r.performance_metrics.baseline_mae, 2),
                "trend": r.performance_metrics.mae_trend
            }
            for r in results
            if r.performance_metrics.current_mae > r.performance_metrics.baseline_mae * 1.1
        ]
        
        return {
            "total_models": len(results),
            "performance_summary": {
                "average_mae": round(statistics.mean(mae_values), 2),
                "median_mae": round(statistics.median(mae_values), 2),
                "average_30day_mae": round(statistics.mean(mae_30day_values), 2),
                "average_data_coverage": round(statistics.mean(coverage_values), 3)
            },
            "trend_distribution": trend_counts,
            "models_above_baseline": len(degrading_models),
            "degrading_models": degrading_models[:10],  # Top 10 worst performers
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance monitoring failed: {str(e)}")

# =============================================================================
# RETRAINING ENDPOINTS
# =============================================================================

# Endpoint: /api/retrain
@api_router.post("/retrain")
def api_retrain_all_models():
    """
    Check all models and start retraining for those that need it.
    
    Returns:
        JSON with started retraining jobs
    """
    from .auto_retrainer import get_auto_retrainer
    
    try:
        retrainer = get_auto_retrainer()
        job_ids = retrainer.check_all_models_for_retraining()
        
        return {
            "message": f"Automatic retraining check completed",
            "jobs_started": len(job_ids),
            "job_ids": job_ids,
            "initiated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Automatic retraining failed: {str(e)}")

# Endpoint: /api/retrain/{region}/{service}/{target}
@api_router.post("/retrain/{region}/{service}/{target}")
def api_retrain_specific_model(region: str, service: str, target: str):
    """
    Start retraining for a specific model.
    
    Args:
        region: Azure region
        service: Service type
        target: Target metric (usage_cpu or usage_storage)
    
    Returns:
        JSON with job information
    """
    from .auto_retrainer import get_auto_retrainer, RetrainTrigger
    
    try:
        retrainer = get_auto_retrainer()
        job_id = retrainer.retrain_model(region, service, target, RetrainTrigger.MANUAL)
        
        return {
            "message": f"Retraining started for {region}/{service}/{target}",
            "job_id": job_id,
            "region": region,
            "service": service,
            "target": target,
            "trigger": "manual",
            "initiated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manual retraining failed: {str(e)}")

# Endpoint: /api/retrain/status/{job_id}
@api_router.get("/retrain/status/{job_id}")
def api_retrain_job_status(job_id: str):
    """
    Get status of a retraining job.
    
    Args:
        job_id: Job identifier
    
    Returns:
        JSON with job status
    """
    from .auto_retrainer import get_auto_retrainer
    
    try:
        retrainer = get_auto_retrainer()
        job_status = retrainer.get_job_status(job_id)
        
        if not job_status:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return {
            "job_id": job_id,
            "status": job_status,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving job status: {str(e)}")

# Endpoint: /api/retrain/jobs
@api_router.get("/retrain/jobs")
def api_retrain_jobs_list(limit: int = 50, status_filter: str = None):
    """
    Get list of retraining jobs.
    
    Args:
        limit: Maximum number of jobs to return
        status_filter: Filter by job status (optional)
    
    Returns:
        JSON with job list
    """
    from .auto_retrainer import get_auto_retrainer
    
    try:
        retrainer = get_auto_retrainer()
        
        # Get all job files
        job_files = list(retrainer.jobs_path.glob("*.json"))
        job_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)  # Sort by modification time, newest first
        
        jobs = []
        for job_file in job_files[:limit]:
            job_id = job_file.stem
            job_status = retrainer.get_job_status(job_id)
            if job_status:
                # Apply status filter if provided
                if status_filter is None or job_status.get('status') == status_filter:
                    jobs.append(job_status)
        
        return {
            "total_jobs": len(jobs),
            "jobs": jobs,
            "limit": limit,
            "status_filter": status_filter,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving job list: {str(e)}")

# Endpoint: /api/retrain/cleanup
@api_router.post("/retrain/cleanup")
def api_retrain_cleanup():
    """
    Clean up old backup files and completed jobs.
    
    Returns:
        JSON with cleanup results
    """
    from .auto_retrainer import get_auto_retrainer
    
    try:
        retrainer = get_auto_retrainer()
        cleaned_backups = retrainer.cleanup_old_backups()
        
        return {
            "message": "Cleanup completed",
            "backups_cleaned": cleaned_backups,
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

# Endpoint: /api/retrain/check
@api_router.get("/retrain/check")
def api_retrain_check():
    """
    Check which models need retraining without starting the process.
    
    Returns:
        JSON with models that need retraining
    """
    from .auto_retrainer import get_auto_retrainer
    from .model_manager import get_model_manager
    
    try:
        retrainer = get_auto_retrainer()
        model_manager = get_model_manager()
        available_combinations = model_manager.get_available_combinations()
        
        retrain_recommendations = []
        
        for region, service, target in available_combinations:
            should_retrain, triggers = retrainer.should_retrain(region, service, target)
            
            retrain_recommendations.append({
                "region": region,
                "service": service,
                "target": target,
                "should_retrain": should_retrain,
                "triggers": [t.value for t in triggers] if triggers else [],
                "trigger_count": len(triggers)
            })
        
        # Separate models that need retraining
        models_needing_retrain = [r for r in retrain_recommendations if r['should_retrain']]
        
        return {
            "total_models_checked": len(retrain_recommendations),
            "models_needing_retrain": len(models_needing_retrain),
            "recommendations": retrain_recommendations,
            "models_to_retrain": models_needing_retrain,
            "checked_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrain check failed: {str(e)}")

# =============================================================================
# MODEL VERSIONING ENDPOINTS
# =============================================================================

# Endpoint: /api/versions
@api_router.get("/versions")
def api_list_all_versions():
    """
    List all model versions across all models.
    
    Returns:
        JSON with all model versions
    """
    from .model_versioning import get_version_manager
    
    try:
        version_manager = get_version_manager()
        all_versions = version_manager.list_all_versions()
        
        # Calculate summary statistics
        total_versions = sum(len(versions) for versions in all_versions.values())
        active_count = len(version_manager.active_versions)
        
        return {
            "total_model_families": len(all_versions),
            "total_versions": total_versions,
            "active_versions": active_count,
            "versions_by_model": all_versions,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing versions: {str(e)}")

# Endpoint: /api/versions/{region}/{service}/{target}
@api_router.get("/versions/{region}/{service}/{target}")
def api_get_model_versions(region: str, service: str, target: str):
    """
    Get version history for a specific model.
    
    Args:
        region: Azure region
        service: Service type
        target: Target metric (usage_cpu or usage_storage)
    
    Returns:
        JSON with model version history
    """
    from .model_versioning import get_version_manager
    
    try:
        version_manager = get_version_manager()
        versions = version_manager.get_version_history(region, service, target)
        active_version = version_manager.get_active_version(region, service, target)
        
        # Convert versions to dictionaries
        version_list = []
        for version in versions:
            version_dict = version.__dict__.copy()
            
            # Convert datetime objects to strings
            for key, value in version_dict.items():
                if isinstance(value, datetime):
                    version_dict[key] = value.isoformat() if value else None
                elif hasattr(value, 'value'):  # Enum
                    version_dict[key] = value.value
            
            version_list.append(version_dict)
        
        return {
            "region": region,
            "service": service,
            "target": target,
            "total_versions": len(versions),
            "active_version": active_version.version_id if active_version else None,
            "versions": version_list,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting model versions: {str(e)}")

# Endpoint: /api/versions/{version_id}
@api_router.get("/versions/{version_id}")
def api_get_version_info(version_id: str):
    """
    Get detailed information about a specific version.
    
    Args:
        version_id: Version identifier
    
    Returns:
        JSON with version details
    """
    from .model_versioning import get_version_manager
    
    try:
        version_manager = get_version_manager()
        version_info = version_manager.get_version_info(version_id)
        
        if not version_info:
            raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
        
        return {
            "version_id": version_id,
            "version_info": version_info,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting version info: {str(e)}")

# Endpoint: /api/versions/{version_id}/deploy
@api_router.post("/versions/{version_id}/deploy")
def api_deploy_version(version_id: str, deployment_notes: str = None):
    """
    Deploy a specific model version to production.
    
    Args:
        version_id: Version identifier
        deployment_notes: Optional deployment notes
    
    Returns:
        JSON with deployment status
    """
    from .model_versioning import get_version_manager
    
    try:
        version_manager = get_version_manager()
        success = version_manager.deploy_version(
            version_id=version_id,
            deployment_notes=deployment_notes,
            deployed_by="api"
        )
        
        if success:
            return {
                "message": f"Version {version_id} deployed successfully",
                "version_id": version_id,
                "deployment_notes": deployment_notes,
                "deployed_at": datetime.now().isoformat(),
                "success": True
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to deploy version {version_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

# Endpoint: /api/versions/rollback/{region}/{service}/{target}
@api_router.post("/versions/rollback/{region}/{service}/{target}")
def api_rollback_model(region: str, service: str, target: str, 
                      target_version: str = None, rollback_reason: str = "Manual rollback via API"):
    """
    Rollback model to a previous version.
    
    Args:
        region: Azure region
        service: Service type
        target: Target metric (usage_cpu or usage_storage)
        target_version: Specific version to rollback to (optional)
        rollback_reason: Reason for rollback
    
    Returns:
        JSON with rollback status
    """
    from .model_versioning import get_version_manager
    
    try:
        version_manager = get_version_manager()
        success = version_manager.rollback_to_version(
            region=region,
            service=service,
            target=target,
            target_version=target_version,
            rollback_reason=rollback_reason,
            deployed_by="api"
        )
        
        if success:
            # Get the version that was rolled back to
            active_version = version_manager.get_active_version(region, service, target)
            
            return {
                "message": f"Successfully rolled back {region}/{service}/{target}",
                "region": region,
                "service": service,
                "target": target,
                "rolled_back_to": active_version.version_id if active_version else "unknown",
                "rollback_reason": rollback_reason,
                "rolled_back_at": datetime.now().isoformat(),
                "success": True
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to rollback {region}/{service}/{target}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")

# Endpoint: /api/versions/deployments
@api_router.get("/versions/deployments")
def api_get_deployment_history(region: str = None, service: str = None, 
                              target: str = None, limit: int = 50):
    """
    Get deployment history with optional filtering.
    
    Args:
        region: Filter by Azure region (optional)
        service: Filter by service type (optional)
        target: Filter by target metric (optional)
        limit: Maximum number of deployments to return
    
    Returns:
        JSON with deployment history
    """
    from .model_versioning import get_version_manager
    
    try:
        version_manager = get_version_manager()
        deployments = version_manager.get_deployment_history(
            region=region,
            service=service, 
            target=target,
            limit=limit
        )
        
        return {
            "total_deployments": len(deployments),
            "filters": {
                "region": region,
                "service": service,
                "target": target,
                "limit": limit
            },
            "deployments": deployments,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting deployment history: {str(e)}")

# Endpoint: /api/versions/cleanup
@api_router.post("/versions/cleanup")
def api_cleanup_versions(keep_versions: int = 10, keep_days: int = 90):
    """
    Clean up old model versions.
    
    Args:
        keep_versions: Number of versions to keep per model
        keep_days: Keep versions created within this many days
    
    Returns:
        JSON with cleanup results
    """
    from .model_versioning import get_version_manager
    
    try:
        version_manager = get_version_manager()
        cleaned_count = version_manager.cleanup_old_versions(
            keep_versions=keep_versions,
            keep_days=keep_days
        )
        
        return {
            "message": "Version cleanup completed",
            "versions_cleaned": cleaned_count,
            "cleanup_parameters": {
                "keep_versions": keep_versions,
                "keep_days": keep_days
            },
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Version cleanup failed: {str(e)}")

# Endpoint: /api/versions/create
@api_router.post("/versions/create/{region}/{service}/{target}")
def api_create_version(region: str, service: str, target: str, 
                      model_path: str = None, created_by: str = "api"):
    """
    Create a new model version from existing model file.
    
    Args:
        region: Azure region
        service: Service type
        target: Target metric (usage_cpu or usage_storage)
        model_path: Path to model file (optional, defaults to current production model)
        created_by: Who is creating this version
    
    Returns:
        JSON with new version information
    """
    from .model_versioning import get_version_manager
    from pathlib import Path
    
    try:
        version_manager = get_version_manager()
        
        # Use current production model if no path specified
        if not model_path:
            model_path = str(version_manager.models_path / "arima" / f"{region}_{service}_{target}_arima.pkl")
        
        # Check if model file exists
        if not Path(model_path).exists():
            raise HTTPException(status_code=404, detail=f"Model file not found: {model_path}")
        
        # Create new version
        version = version_manager.create_new_version(
            region=region,
            service=service,
            target=target,
            model_path=model_path,
            created_by=created_by
        )
        
        # Convert to dictionary
        version_dict = version.__dict__.copy()
        for key, value in version_dict.items():
            if isinstance(value, datetime):
                version_dict[key] = value.isoformat() if value else None
            elif hasattr(value, 'value'):  # Enum
                version_dict[key] = value.value
        
        return {
            "message": f"New version created for {region}/{service}/{target}",
            "version": version_dict,
            "created_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Version creation failed: {str(e)}")

# =============================================================================
# MONITORING SCHEDULER ENDPOINTS
# =============================================================================

# Endpoint: /api/monitoring/scheduled
@api_router.post("/monitoring/scheduled")
def api_run_scheduled_monitoring():
    """
    Run comprehensive scheduled monitoring checks.
    
    Returns:
        JSON with monitoring results and alerts
    """
    from .scheduler import get_scheduler
    
    try:
        scheduler = get_scheduler()
        monitoring_results = scheduler.run_monitoring_checks()
        
        return {
            "message": "Scheduled monitoring completed",
            "results": monitoring_results,
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduled monitoring failed: {str(e)}")

# Endpoint: /api/monitoring/drift/scheduled
@api_router.post("/monitoring/drift/scheduled")
def api_run_scheduled_drift_detection():
    """
    Run scheduled drift detection across all models.
    
    Returns:
        JSON with drift detection results
    """
    from .scheduler import get_scheduler
    
    try:
        scheduler = get_scheduler()
        drift_results = scheduler.run_drift_detection()
        
        return {
            "message": "Scheduled drift detection completed",
            "results": drift_results,
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduled drift detection failed: {str(e)}")

# Endpoint: /api/monitoring/performance/scheduled
@api_router.post("/monitoring/performance/scheduled")
def api_run_scheduled_performance_monitoring():
    """
    Run scheduled performance monitoring across all models.
    
    Returns:
        JSON with performance monitoring results
    """
    from .scheduler import get_scheduler
    
    try:
        scheduler = get_scheduler()
        performance_results = scheduler.run_performance_monitoring()
        
        return {
            "message": "Scheduled performance monitoring completed",
            "results": performance_results,
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduled performance monitoring failed: {str(e)}")

# Endpoint: /api/monitoring/health/scheduled
@api_router.post("/monitoring/health/scheduled")
def api_run_scheduled_health_checks():
    """
    Run scheduled system health checks.
    
    Returns:
        JSON with health check results
    """
    from .scheduler import get_scheduler
    
    try:
        scheduler = get_scheduler()
        health_results = scheduler.run_health_checks()
        
        return {
            "message": "Scheduled health checks completed",
            "results": health_results,
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduled health checks failed: {str(e)}")

# Endpoint: /api/retrain/scheduled
@api_router.post("/retrain/scheduled")
def api_run_scheduled_retraining():
    """
    Run scheduled automated retraining for models that need it.
    
    Returns:
        JSON with retraining results
    """
    from .scheduler import get_scheduler
    
    try:
        scheduler = get_scheduler()
        retraining_results = scheduler.run_automated_retraining()
        
        return {
            "message": "Scheduled automated retraining completed",
            "results": retraining_results,
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduled retraining failed: {str(e)}")

# =============================================================================
# ALERTING ENDPOINTS
# =============================================================================

# Endpoint: /api/alerts
@api_router.get("/alerts")
def api_get_active_alerts(level: str = None):
    """
    Get active alerts with optional level filtering.
    
    Args:
        level: Filter by alert level (info, warning, critical, error)
    
    Returns:
        JSON with active alerts
    """
    from .alerting import get_alert_manager, AlertLevel
    
    try:
        alert_manager = get_alert_manager()
        
        # Parse level filter
        level_filter = None
        if level:
            try:
                level_filter = AlertLevel(level.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid alert level: {level}")
        
        alerts = alert_manager.get_active_alerts(level=level_filter)
        summary = alert_manager.get_alert_summary()
        
        return {
            "alerts": alerts,
            "summary": summary,
            "filter": {"level": level},
            "retrieved_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")

# Endpoint: /api/alerts/summary
@api_router.get("/alerts/summary")
def api_get_alerts_summary():
    """
    Get summary of alert status.
    
    Returns:
        JSON with alert summary statistics
    """
    from .alerting import get_alert_manager
    
    try:
        alert_manager = get_alert_manager()
        summary = alert_manager.get_alert_summary()
        
        return {
            "summary": summary,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alert summary: {str(e)}")

# Endpoint: /api/alerts/{alert_id}/acknowledge
@api_router.post("/alerts/{alert_id}/acknowledge")  
def api_acknowledge_alert(alert_id: str, acknowledged_by: str = "api_user"):
    """
    Acknowledge an active alert.
    
    Args:
        alert_id: Alert identifier
        acknowledged_by: Who is acknowledging the alert
    
    Returns:
        JSON with acknowledgment status
    """
    from .alerting import get_alert_manager
    
    try:
        alert_manager = get_alert_manager()
        success = alert_manager.acknowledge_alert(alert_id, acknowledged_by)
        
        if success:
            return {
                "message": f"Alert {alert_id} acknowledged successfully",
                "alert_id": alert_id,
                "acknowledged_by": acknowledged_by,
                "acknowledged_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error acknowledging alert: {str(e)}")

# Endpoint: /api/alerts/{alert_id}/resolve
@api_router.post("/alerts/{alert_id}/resolve")
def api_resolve_alert(alert_id: str, resolved_by: str = "api_user"):
    """
    Resolve an active alert.
    
    Args:
        alert_id: Alert identifier
        resolved_by: Who is resolving the alert
    
    Returns:
        JSON with resolution status
    """
    from .alerting import get_alert_manager
    
    try:
        alert_manager = get_alert_manager()
        success = alert_manager.resolve_alert(alert_id, resolved_by)
        
        if success:
            return {
                "message": f"Alert {alert_id} resolved successfully",
                "alert_id": alert_id,
                "resolved_by": resolved_by,
                "resolved_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving alert: {str(e)}")

# Endpoint: /api/alerts/create
@api_router.post("/alerts/create")
def api_create_alert(level: str, alert_type: str, message: str,
                    region: str = None, service: str = None, target: str = None,
                    details: Dict[str, Any] = None):
    """
    Create a manual alert.
    
    Args:
        level: Alert level (info, warning, critical, error)
        alert_type: Type of alert
        message: Alert message
        region: Azure region (optional)
        service: Service type (optional)
        target: Target metric (optional)
        details: Additional alert details (optional)
    
    Returns:
        JSON with created alert information
    """
    from .alerting import get_alert_manager, AlertLevel
    
    try:
        # Parse alert level
        try:
            alert_level = AlertLevel(level.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid alert level: {level}")
        
        alert_manager = get_alert_manager()
        alert = alert_manager.create_alert(
            level=alert_level,
            alert_type=alert_type,
            message=message,
            details=details,
            region=region,
            service=service,
            target=target
        )
        
        if alert:
            # Convert alert to dict for response
            alert_dict = {
                "alert_id": alert.alert_id,
                "level": alert.level.value,
                "type": alert.type,
                "message": alert.message,
                "region": alert.region,
                "service": alert.service,
                "target": alert.target,
                "created_at": alert.created_at.isoformat(),
                "status": alert.status.value
            }
            
            return {
                "message": "Alert created successfully",
                "alert": alert_dict,
                "created_at": datetime.now().isoformat()
            }
        else:
            return {
                "message": "Alert was suppressed (duplicate or maintenance mode)",
                "suppressed": True,
                "created_at": datetime.now().isoformat()
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating alert: {str(e)}")

# Endpoint: /api/alerts/process-monitoring
@api_router.post("/alerts/process-monitoring")
def api_process_monitoring_alerts(monitoring_results: Dict[str, Any]):
    """
    Process monitoring results and create alerts.
    
    Args:
        monitoring_results: Results from monitoring checks
    
    Returns:
        JSON with created alerts
    """
    from .alerting import get_alert_manager
    
    try:
        alert_manager = get_alert_manager()
        created_alerts = alert_manager.process_monitoring_alerts(monitoring_results)
        
        # Convert alerts to dicts for response
        alert_list = []
        for alert in created_alerts:
            alert_dict = {
                "alert_id": alert.alert_id,
                "level": alert.level.value,
                "type": alert.type,
                "message": alert.message,
                "created_at": alert.created_at.isoformat(),
                "status": alert.status.value
            }
            alert_list.append(alert_dict)
        
        return {
            "message": f"Processed monitoring results and created {len(created_alerts)} alerts",
            "alerts_created": len(created_alerts),
            "alerts": alert_list,
            "processed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing monitoring alerts: {str(e)}")

# Endpoint: /api/alerts/cleanup
@api_router.post("/alerts/cleanup")
def api_cleanup_alerts(days_old: int = 7):
    """
    Clean up old resolved alerts.
    
    Args:
        days_old: Remove alerts older than this many days
    
    Returns:
        JSON with cleanup results
    """
    from .alerting import get_alert_manager
    
    try:
        alert_manager = get_alert_manager()
        cleaned_count = alert_manager.cleanup_resolved_alerts(days_old)
        
        return {
            "message": "Alert cleanup completed",
            "alerts_cleaned": cleaned_count,
            "days_threshold": days_old,
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert cleanup failed: {str(e)}")