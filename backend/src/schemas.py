from typing import List, Dict
from pydantic import BaseModel


class UsagePoint(BaseModel):
    date: str
    cpu_percent: float
    storage_percent: float


class RegionSeries(BaseModel):
    region: str
    data: List[UsagePoint]


class UsageTrendsResponse(BaseModel):
    regions: List[str]
    series: List[RegionSeries]


class ForecastPoint(BaseModel):
    date: str
    cpu_percent: float
    storage_percent: float


class ForecastResponse(BaseModel):
    horizon_days: int
    forecasts: Dict[str, List[ForecastPoint]]


