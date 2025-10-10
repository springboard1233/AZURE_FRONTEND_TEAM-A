# Exploratory Data Analysis (EDA) Report

## Key Insights

### Feature Correlations
- See correlation_heatmap.png for details.

### Region-wise Variation
- See cpu_usage_boxplot.png and storage_usage_boxplot.png.

### Time-Series Trends
- See *_timeseries.png and *_rolling_avg.png for demand cycles.

### Usage Distributions
- See cpu_usage_histogram.png and storage_usage_histogram.png.

### Usage vs External Factors
- See cpu_vs_econ_index.png and cpu_vs_market_demand.png.

### Peak Usage Days (Top 5 per Region)
- eastus:
    - 2023-02-24: 290 CPU
    - 2023-03-29: 278 CPU
    - 2023-01-02: 275 CPU
    - 2023-03-08: 268 CPU
    - 2023-01-12: 267 CPU
- northeurope:
    - 2023-03-27: 279 CPU
    - 2023-03-02: 274 CPU
    - 2023-02-21: 258 CPU
    - 2023-01-06: 257 CPU
    - 2023-01-13: 256 CPU
- southeastasia:
    - 2023-01-14: 272 CPU
    - 2023-02-10: 267 CPU
    - 2023-01-20: 265 CPU
    - 2023-02-06: 265 CPU
    - 2023-03-04: 265 CPU
- westus:
    - 2023-01-24: 289 CPU
    - 2023-03-16: 288 CPU
    - 2023-02-10: 284 CPU
    - 2023-03-13: 284 CPU
    - 2023-03-12: 267 CPU

## Features Added
- Time-based: day_of_week, month, quarter, is_weekend
- Lag features: cpu_usage_lag_1, cpu_usage_lag_3, cpu_usage_lag_7, etc.
- Rolling features: cpu_usage_rollmean_3, cpu_usage_rollmean_7, etc.
- Derived metrics: cpu_utilization_ratio, storage_efficiency
- External factors: econ_index, cloud_market_demand, holiday

## Features Dropped
- None explicitly dropped; all original and engineered features retained for modeling.

## Justification for Changes
- Added features to capture time cycles, trends, and external influences.
- Lag and rolling features help model temporal dependencies.
- Derived metrics provide business-level insights.
- External factors add contextual intelligence.
- No features dropped to preserve modeling flexibility.
