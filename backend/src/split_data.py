"""
Time-based Train/Validation/Test Split Script

Splits feature_engineered.csv into train, val, and test sets by date for Milestone 3.
"""
import pandas as pd
import matplotlib.pyplot as plt
import json
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "feature_engineered.csv"
SPLITS_DIR = PROJECT_ROOT / "data" / "splits"
SPLITS_DIR.mkdir(exist_ok=True)

# Load data
print("Loading data...")
df = pd.read_csv(DATA_PATH, parse_dates=["date"])
df = df.sort_values("date").reset_index(drop=True)

# Confirm date range
date_min, date_max = df["date"].min(), df["date"].max()
print(f"Date range: {date_min} to {date_max}")

# Split ranges
train_start, train_end = pd.Timestamp("2023-01-01"), pd.Timestamp("2023-02-28")
val_start, val_end = pd.Timestamp("2023-03-01"), pd.Timestamp("2023-03-15")
test_start, test_end = pd.Timestamp("2023-03-16"), pd.Timestamp("2023-03-31")

# Perform splits
train_df = df[(df["date"] >= train_start) & (df["date"] <= train_end)]
val_df = df[(df["date"] >= val_start) & (df["date"] <= val_end)]
test_df = df[(df["date"] >= test_start) & (df["date"] <= test_end)]

# Validation checks
assert train_df["date"].max() < val_df["date"].min(), "Train/Val split overlap!"
assert val_df["date"].max() < test_df["date"].min(), "Val/Test split overlap!"

# Save splits
train_df.to_csv(SPLITS_DIR / "train.csv", index=False)
val_df.to_csv(SPLITS_DIR / "val.csv", index=False)
test_df.to_csv(SPLITS_DIR / "test.csv", index=False)

# Metadata
metadata = {
    "train_range": [str(train_start.date()), str(train_end.date())],
    "val_range": [str(val_start.date()), str(val_end.date())],
    "test_range": [str(test_start.date()), str(test_end.date())],
    "train_rows": len(train_df),
    "val_rows": len(val_df),
    "test_rows": len(test_df),
    "frequency": "daily",  # adjust if needed
    "target_column": "usage_cpu"
}
with open(SPLITS_DIR / "metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

# Print row counts
print(f"Train rows: {len(train_df)}")
print(f"Val rows: {len(val_df)}")
print(f"Test rows: {len(test_df)}")

# Plot demand curves for Jan, Feb, Mar
plt.figure(figsize=(12, 6))
for month, color in zip([1, 2, 3], ["blue", "orange", "green"]):
    month_df = df[df["date"].dt.month == month]
    plt.plot(month_df["date"], month_df["usage_cpu"], label=f"Month {month}", color=color)
plt.title("CPU Usage Demand Curves (Jan–Mar)")
plt.xlabel("Date")
plt.ylabel("CPU Usage")
plt.legend()
plt.tight_layout()
plt.savefig(SPLITS_DIR / "demand_curves.png", dpi=150)
plt.close()

print(f"Splits and metadata saved in {SPLITS_DIR}")
