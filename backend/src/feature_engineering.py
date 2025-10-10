"""
Feature Engineering Script for Azure Demand Forecasting

This script reads the processed Azure usage data and external factors, performs feature engineering (time-based, lag, rolling, derived, and merges external features), and saves the enriched dataset to data/processed/feature_engineered.csv.
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "cleaned_merged.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "feature_engineered.csv"

# Read processed data
if not PROCESSED_PATH.exists():
    raise FileNotFoundError(f"Processed data not found at {PROCESSED_PATH}")

df = pd.read_csv(PROCESSED_PATH, parse_dates=["date"])

# --- 1. Time-Based Features ---
df["day_of_week"] = df["date"].dt.dayofweek  # 0=Monday

df["month"] = df["date"].dt.month

df["quarter"] = df["date"].dt.quarter

df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

# --- 2. Lag and Rolling Features ---
# We'll do this per region/resource_type
lag_days = [1, 3, 7]
rolling_windows = [3, 7]

for region in df["region"].unique():
    for resource in df["resource_type"].unique():
        mask = (df["region"] == region) & (df["resource_type"] == resource)
        group = df.loc[mask].sort_values("date")
        for lag in lag_days:
            df.loc[mask, f"cpu_usage_lag_{lag}"] = group["usage_cpu"].shift(lag)
            df.loc[mask, f"storage_usage_lag_{lag}"] = group["usage_storage"].shift(lag)
        for win in rolling_windows:
            df.loc[mask, f"cpu_usage_rollmean_{win}"] = group["usage_cpu"].rolling(win).mean()
            df.loc[mask, f"cpu_usage_rollmax_{win}"] = group["usage_cpu"].rolling(win).max()
            df.loc[mask, f"cpu_usage_rollmin_{win}"] = group["usage_cpu"].rolling(win).min()
            df.loc[mask, f"storage_usage_rollmean_{win}"] = group["usage_storage"].rolling(win).mean()
            df.loc[mask, f"storage_usage_rollmax_{win}"] = group["usage_storage"].rolling(win).max()
            df.loc[mask, f"storage_usage_rollmin_{win}"] = group["usage_storage"].rolling(win).min()

# --- 3. Derived Metrics ---
# Assume CPU_Total and Storage_Allocated are not present, so use max observed per region/resource_type as proxy
for region in df["region"].unique():
    for resource in df["resource_type"].unique():
        mask = (df["region"] == region) & (df["resource_type"] == resource)
        cpu_total = df.loc[mask, "usage_cpu"].max()
        storage_alloc = df.loc[mask, "usage_storage"].max()
        df.loc[mask, "cpu_utilization_ratio"] = df.loc[mask, "usage_cpu"] / cpu_total if cpu_total else np.nan
        df.loc[mask, "storage_efficiency"] = df.loc[mask, "usage_storage"] / storage_alloc if storage_alloc else np.nan

# --- 4. External Factors ---
# Already merged in cleaned_merged.csv (econ_index, cloud_market_demand, holiday)
# If you want to add more, merge here.

# --- Save the feature engineered dataset ---
df.sort_values(["region", "resource_type", "date"], inplace=True)
df.reset_index(drop=True, inplace=True)
df.to_csv(OUTPUT_PATH, index=False)

print(f"Feature engineered dataset saved to {OUTPUT_PATH}")
