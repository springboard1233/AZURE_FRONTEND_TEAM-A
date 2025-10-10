from pathlib import Path
from typing import Tuple

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def load_data(csv_path: Path) -> pd.DataFrame:
	df = pd.read_csv(csv_path)
	required_cols = {"date", "region", "usage_cpu"}
	missing = required_cols.difference(df.columns)
	if missing:
		raise ValueError(f"Missing required columns in CSV: {missing}")
	df["date"] = pd.to_datetime(df["date"], errors="coerce")
	df = df.dropna(subset=["date", "usage_cpu", "region"]).copy()
	return df


def compute_average_daily_cpu_per_region(df: pd.DataFrame) -> pd.DataFrame:
	daily_region_mean = (
		df.groupby(["date", "region"], as_index=False)["usage_cpu"].mean()
		.rename(columns={"usage_cpu": "avg_cpu"})
	)
	return daily_region_mean


def compute_peak_demand_per_month(df: pd.DataFrame) -> pd.DataFrame:
	daily_total = (
		df.groupby("date", as_index=False)["usage_cpu"].sum()
		.rename(columns={"usage_cpu": "total_cpu"})
	)
	daily_total["month"] = daily_total["date"].dt.to_period("M").dt.to_timestamp()
	peak_monthly = (
		daily_total.groupby("month", as_index=False)["total_cpu"].max()
		.rename(columns={"total_cpu": "peak_daily_total_cpu"})
	)
	return peak_monthly


def compute_top5_regions_by_usage(df: pd.DataFrame) -> pd.DataFrame:
	region_totals = (
		df.groupby("region", as_index=False)["usage_cpu"].sum()
		.rename(columns={"usage_cpu": "total_cpu"})
		.sort_values("total_cpu", ascending=False)
	)
	return region_totals.head(5)


def plot_average_daily_cpu_per_region(daily_region_mean: pd.DataFrame, output_path: Path) -> None:
	plt.figure(figsize=(12, 6))
	sns.lineplot(
		data=daily_region_mean,
		x="date",
		y="avg_cpu",
		hue="region",
		marker=None,
		linewidth=1.5,
	)
	plt.title("Average Daily CPU Usage per Region")
	plt.xlabel("Date")
	plt.ylabel("Average CPU Usage")
	plt.legend(title="Region", loc="best", ncol=2, fontsize="small")
	plt.tight_layout()
	plt.savefig(output_path, dpi=150)
	plt.close()


def plot_peak_demand_per_month(peak_monthly: pd.DataFrame, output_path: Path) -> None:
	plt.figure(figsize=(10, 6))
	sns.barplot(data=peak_monthly, x="month", y="peak_daily_total_cpu", color="#4C78A8")
	plt.title("Peak Daily CPU Demand per Month (Total Across Regions)")
	plt.xlabel("Month")
	plt.ylabel("Peak Daily Total CPU Usage")
	plt.xticks(rotation=45, ha="right")
	plt.tight_layout()
	plt.savefig(output_path, dpi=150)
	plt.close()


def plot_top5_regions_by_usage(top5_regions: pd.DataFrame, output_path: Path) -> None:
	ordered = top5_regions.sort_values("total_cpu", ascending=True)
	plt.figure(figsize=(8, 5))
	sns.barplot(data=ordered, x="total_cpu", y="region", color="#F58518")
	plt.title("Top 5 Regions by Total CPU Usage")
	plt.xlabel("Total CPU Usage")
	plt.ylabel("Region")
	plt.tight_layout()
	plt.savefig(output_path, dpi=150)
	plt.close()


def main() -> Tuple[Path, Path, Path]:
	project_root = Path(__file__).resolve().parents[1]
	csv_path = project_root / "data" / "processed" / "cleaned_merged.csv"
	output_dir = project_root  

	if not csv_path.exists():
		raise FileNotFoundError(f"CSV not found at: {csv_path}")

	df = load_data(csv_path)

	daily_region_mean = compute_average_daily_cpu_per_region(df)
	peak_monthly = compute_peak_demand_per_month(df)
	top5_regions = compute_top5_regions_by_usage(df)

	avg_daily_png = output_dir / "avg_daily_cpu_usage_per_region.png"
	peak_monthly_png = output_dir / "peak_demand_per_month.png"
	top5_regions_png = output_dir / "top5_regions_by_usage.png"

	plot_average_daily_cpu_per_region(daily_region_mean, avg_daily_png)
	plot_peak_demand_per_month(peak_monthly, peak_monthly_png)
	plot_top5_regions_by_usage(top5_regions, top5_regions_png)

	print("Top 5 regions by usage")
	for _, row in top5_regions.iterrows():
		region = row["region"]
		total = int(row["total_cpu"]) if not pd.isna(row["total_cpu"]) else 0
		print(f"{region}: {total:,} total CPU")
	
	daily_total = df.groupby("date", as_index=False)["usage_cpu"].sum().rename(columns={"usage_cpu": "total_cpu"})
	daily_total["month"] = daily_total["date"].dt.to_period("M").dt.to_timestamp()
	idx = daily_total.groupby("month")["total_cpu"].idxmax()
	peak_with_day = daily_total.loc[idx, ["month", "date", "total_cpu"]].sort_values("month")
	print("Peak demand per month")
	for _, row in peak_with_day.iterrows():
		m = row["month"].strftime("%b %Y")
		peak_date = row["date"].date().isoformat()
		val = int(row["total_cpu"]) if not pd.isna(row["total_cpu"]) else 0
		print(f"{m}: peak {val:,} on {peak_date}")

	
	mean_per_region = (
		daily_region_mean.groupby("region", as_index=False)["avg_cpu"].mean().sort_values("avg_cpu", ascending=False)
	)
	print("Average daily CPU usage per region (mean of daily means)")
	for _, row in mean_per_region.iterrows():
		region = row["region"]
		avgv = float(row["avg_cpu"]) if not pd.isna(row["avg_cpu"]) else 0.0
		print(f"{region}: {avgv:.2f}")

	return avg_daily_png, peak_monthly_png, top5_regions_png


if __name__ == "__main__":
	paths = main()
	for p in paths:
		print(f"Saved: {p}")














































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
        "avg_daily_usage_per_region": avg_daily_list,
        "storage_efficiency_per_region": storage_eff_list,
        "cpu_utilization_ratios": cpu_util_list,
        "weekday_vs_weekend_cpu": {
            "weekday_mean": float(weekday_mean) if weekday_mean is not None else None,
            "weekend_mean": float(weekend_mean) if weekend_mean is not None else None,
        },
        "correlations_with_external_factors": ext_corr,
    }































# --- New Endpoints ---



