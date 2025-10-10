"""
Exploratory Data Analysis (EDA) Script for Azure Demand Forecasting

This script loads the feature-engineered dataset, performs EDA, generates plots, and writes summary insights to the EDA report.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "feature_engineered.csv"
PLOTS_DIR = PROJECT_ROOT / "reports" / "plots"
EDA_REPORT_PATH = PROJECT_ROOT / "reports" / "eda_report.md"

# Load data
df = pd.read_csv(DATA_PATH, parse_dates=["date"])

# 1. Correlation Analysis & Heatmap
corr = df.corr(numeric_only=True)
plt.figure(figsize=(12, 8))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm")
plt.title("Feature Correlation Heatmap")
plt.tight_layout()
plt.savefig(PLOTS_DIR / "correlation_heatmap.png", dpi=150)
plt.close()

# 2. Boxplots: Region-wise variation in CPU and Storage usage
plt.figure(figsize=(10, 6))
sns.boxplot(data=df, x="region", y="usage_cpu")
plt.title("CPU Usage Distribution by Region")
plt.tight_layout()
plt.savefig(PLOTS_DIR / "cpu_usage_boxplot.png", dpi=150)
plt.close()

plt.figure(figsize=(10, 6))
sns.boxplot(data=df, x="region", y="usage_storage")
plt.title("Storage Usage Distribution by Region")
plt.tight_layout()
plt.savefig(PLOTS_DIR / "storage_usage_boxplot.png", dpi=150)
plt.close()

# 3. Time-Series Line Graphs: CPU/Storage usage over time (by region)
for metric in ["usage_cpu", "usage_storage"]:
    plt.figure(figsize=(14, 7))
    sns.lineplot(data=df, x="date", y=metric, hue="region")
    plt.title(f"{metric.replace('_', ' ').title()} Over Time by Region")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"{metric}_timeseries.png", dpi=150)
    plt.close()

# 4. Histograms: Usage distribution
plt.figure(figsize=(10, 6))
sns.histplot(df["usage_cpu"], bins=30, kde=True)
plt.title("CPU Usage Distribution")
plt.tight_layout()
plt.savefig(PLOTS_DIR / "cpu_usage_histogram.png", dpi=150)
plt.close()

plt.figure(figsize=(10, 6))
sns.histplot(df["usage_storage"], bins=30, kde=True)
plt.title("Storage Usage Distribution")
plt.tight_layout()
plt.savefig(PLOTS_DIR / "storage_usage_histogram.png", dpi=150)
plt.close()

# 5. Rolling Averages: Trend smoothing (7-day window)
for metric in ["usage_cpu", "usage_storage"]:
    plt.figure(figsize=(14, 7))
    for region in df["region"].unique():
        region_df = df[df["region"] == region].sort_values("date")
        roll = region_df[metric].rolling(7).mean()
        plt.plot(region_df["date"], roll, label=region)
    plt.title(f"7-Day Rolling Average of {metric.replace('_', ' ').title()} by Region")
    plt.xlabel("Date")
    plt.ylabel(f"{metric.replace('_', ' ').title()}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / f"{metric}_rolling_avg.png", dpi=150)
    plt.close()

# 6. Scatter Plots: Usage vs External Factors
plt.figure(figsize=(10, 6))
sns.scatterplot(data=df, x="econ_index", y="usage_cpu", hue="region")
plt.title("CPU Usage vs Economic Index")
plt.tight_layout()
plt.savefig(PLOTS_DIR / "cpu_vs_econ_index.png", dpi=150)
plt.close()

plt.figure(figsize=(10, 6))
sns.scatterplot(data=df, x="cloud_market_demand", y="usage_cpu", hue="region")
plt.title("CPU Usage vs Cloud Market Demand")
plt.tight_layout()
plt.savefig(PLOTS_DIR / "cpu_vs_market_demand.png", dpi=150)
plt.close()

# 7. Peak Usage Detection: Highlight top 5 peak days per region
peak_days = df.groupby(["region", "date"])["usage_cpu"].sum().reset_index()
peak_summary = peak_days.groupby("region").apply(lambda x: x.nlargest(5, "usage_cpu")).reset_index(drop=True)

# Save peak summary to EDA report
with open(EDA_REPORT_PATH, "w") as f:
    f.write("# Exploratory Data Analysis (EDA) Report\n\n")
    f.write("## Key Insights\n\n")
    f.write("### Feature Correlations\n")
    f.write("- See correlation_heatmap.png for details.\n\n")
    f.write("### Region-wise Variation\n")
    f.write("- See cpu_usage_boxplot.png and storage_usage_boxplot.png.\n\n")
    f.write("### Time-Series Trends\n")
    f.write("- See *_timeseries.png and *_rolling_avg.png for demand cycles.\n\n")
    f.write("### Usage Distributions\n")
    f.write("- See cpu_usage_histogram.png and storage_usage_histogram.png.\n\n")
    f.write("### Usage vs External Factors\n")
    f.write("- See cpu_vs_econ_index.png and cpu_vs_market_demand.png.\n\n")
    f.write("### Peak Usage Days (Top 5 per Region)\n")
    for region in peak_summary["region"].unique():
        f.write(f"- {region}:\n")
        region_peaks = peak_summary[peak_summary["region"] == region]
        for _, row in region_peaks.iterrows():
            f.write(f"    - {row['date'].date()}: {row['usage_cpu']} CPU\n")
    f.write("\n## Features Added\n")
    f.write("- Time-based: day_of_week, month, quarter, is_weekend\n")
    f.write("- Lag features: cpu_usage_lag_1, cpu_usage_lag_3, cpu_usage_lag_7, etc.\n")
    f.write("- Rolling features: cpu_usage_rollmean_3, cpu_usage_rollmean_7, etc.\n")
    f.write("- Derived metrics: cpu_utilization_ratio, storage_efficiency\n")
    f.write("- External factors: econ_index, cloud_market_demand, holiday\n\n")
    f.write("## Features Dropped\n")
    f.write("- None explicitly dropped; all original and engineered features retained for modeling.\n\n")
    f.write("## Justification for Changes\n")
    f.write("- Added features to capture time cycles, trends, and external influences.\n")
    f.write("- Lag and rolling features help model temporal dependencies.\n")
    f.write("- Derived metrics provide business-level insights.\n")
    f.write("- External factors add contextual intelligence.\n")
    f.write("- No features dropped to preserve modeling flexibility.\n")

print(f"EDA complete. Plots saved to {PLOTS_DIR} and report written to {EDA_REPORT_PATH}")
