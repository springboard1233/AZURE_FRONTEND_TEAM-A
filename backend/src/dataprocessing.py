from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from dateutil import parser as dateparser


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR_RAW = PROJECT_ROOT / "data" / "raw"
DATA_DIR_PROCESSED = PROJECT_ROOT / "data" / "processed"


@dataclass
class PipelineResult:
    raw_usage_path: Path
    raw_external_path: Path
    output_path: Path
    rows_input_usage: int
    rows_input_external: int
    rows_output: int


def _standardize_region(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip().lower().replace(" ", "")
    normalized = normalized.replace("-", "").replace("_", "")
    aliases = {
        "eastus": "eastus",
        "eastus2": "eastus2",
        "westus": "westus",
        "westeurope": "westeurope",
        "southeastasia": "southeastasia",
        "northeurope": "northeurope",
    }
    return aliases.get(normalized, normalized)


def _parse_date(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.to_datetime(value)
    try:
        return pd.to_datetime(dateparser.parse(str(value)))
    except Exception:
        return pd.NaT


def _clean_usage_df(df: pd.DataFrame) -> pd.DataFrame:
    column_map = {
        "cpu": "cpu_usage",
        "cpu_percent": "cpu_usage",
        "cpu_usage_percent": "cpu_usage",
        "storage_usage": "storage",
        "storage_percent": "storage",
        "vm": "vm_type",
        "vmcategory": "vm_type",
        "location": "region",
    }
    df = df.rename(columns={c: column_map.get(c, c) for c in df.columns})

    for required in ["date", "region"]:
        if required not in df.columns:
            df[required] = np.nan

    df["date"] = df["date"].apply(_parse_date)
    df["region"] = df["region"].apply(_standardize_region)

    for col in ["cpu_usage", "storage"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["date"]).copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isna().any():
            df[col] = df[col].fillna(df[col].median())

    df = df.sort_values(["date", "region"]).reset_index(drop=True)
    return df


def _clean_external_df(df: pd.DataFrame) -> pd.DataFrame:
    column_map = {
        "economic_index": "econ_index",
        "econ": "econ_index",
        "market": "market_trend",
        "trend": "market_trend",
        "location": "region",
    }
    df = df.rename(columns={c: column_map.get(c, c) for c in df.columns})

    if "date" not in df.columns:
        df["date"] = np.nan

    df["date"] = df["date"].apply(_parse_date)
    if "region" in df.columns:
        df["region"] = df["region"].apply(_standardize_region)

    if "holiday" in df.columns:
        df["holiday"] = (
            df["holiday"].map({"yes": True, "no": False}).fillna(df["holiday"]).astype("boolean")
        )

    for col in ["econ_index", "market_trend"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["date"]).copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isna().any():
            df[col] = df[col].fillna(df[col].median())

    df = df.sort_values(["date"] + (["region"] if "region" in df.columns else [])).reset_index(drop=True)
    return df


def run() -> PipelineResult:
    usage_path = DATA_DIR_RAW / "azure_usage.csv"
    external_path = DATA_DIR_RAW / "external_factors.csv"
    output_path = DATA_DIR_PROCESSED / "cleaned_merged.csv"

    DATA_DIR_PROCESSED.mkdir(parents=True, exist_ok=True)

    usage_df = pd.read_csv(usage_path)
    external_df = pd.read_csv(external_path)

    rows_input_usage = len(usage_df)
    rows_input_external = len(external_df)

    usage_df = _clean_usage_df(usage_df)
    external_df = _clean_external_df(external_df)

    if "region" in usage_df.columns and "region" in external_df.columns:
        on_keys: Tuple[str, ...] = ("date", "region")
    else:
        on_keys = ("date",)

    merged = pd.merge(usage_df, external_df, on=list(on_keys), how="left")
    merged = merged.sort_values(list(on_keys)).reset_index(drop=True)
    merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)

    return PipelineResult(
        raw_usage_path=usage_path,
        raw_external_path=external_path,
        output_path=output_path,
        rows_input_usage=rows_input_usage,
        rows_input_external=rows_input_external,
        rows_output=len(merged),
    )


if __name__ == "__main__":
    result = run()
    print(
        {
            "message": "Data processed successfully",
            "raw_usage": str(result.raw_usage_path),
            "raw_external": str(result.raw_external_path),
            "output": str(result.output_path),
            "rows": {
                "usage": result.rows_input_usage,
                "external": result.rows_input_external,
                "output": result.rows_output,
            },
        }
    )


