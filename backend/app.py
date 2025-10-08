# backend/app.py
from flask import Flask, jsonify
from flask_cors import CORS
import pandas as pd
import os
import joblib
import numpy as np

app = Flask(__name__)
CORS(app)

# ------------------------------
# Paths
# ------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "cleaned_merged.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "cpu_forecast.pkl")

# ------------------------------
# Helpers
# ------------------------------
def load_data():
    if os.path.exists(DATA_PATH):
        return pd.read_csv(DATA_PATH, parse_dates=["date"])
    return None

def load_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None

# ------------------------------
# Health check
# ------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# ------------------------------
# Usage Trends API (Milestone 2 enriched)
# ------------------------------
@app.route("/api/usage-trends", methods=["GET"])
def usage_trends():
    df = load_data()
    if df is None or df.empty:
        # fallback dummy data
        return jsonify([
            {"date": "2025-09-15", "usage_cpu": 150, "usage_storage": 2000,
             "cpu_utilization": 0.65, "storage_efficiency": 0.72},
            {"date": "2025-09-16", "usage_cpu": 170, "usage_storage": 2200,
             "cpu_utilization": 0.70, "storage_efficiency": 0.75}
        ])

    # Ensure date is datetime
    df["date"] = pd.to_datetime(df["date"])

    # Aggregate daily metrics
    agg = df.groupby(df["date"].dt.strftime("%Y-%m-%d")).agg({
        "usage_cpu": "sum",
        "usage_storage": "sum",
        "cpu_utilization": "mean",
        "storage_efficiency": "mean"
    }).reset_index()

    return jsonify(agg.to_dict(orient="records"))

# ------------------------------
# Forecast API (always returns data)
# ------------------------------
@app.route("/api/forecast", methods=["GET"])
def forecast():
    df = load_data()
    model = load_model()

    # ------------------------------
    # Case 1: No data available
    # ------------------------------
    if df is None or df.empty:
        return jsonify([
            {"date": "2025-09-18", "forecast_cpu": 500},
            {"date": "2025-09-19", "forecast_cpu": 520},
            {"date": "2025-09-20", "forecast_cpu": 540}
        ])

    # Ensure sorted by date
    df = df.sort_values("date")
    last_date = df["date"].max()

    # ------------------------------
    # Case 2: Model available → real forecast
    # ------------------------------
    if model is not None:
        feature_cols = [
            "cpu_utilization",
            "storage_efficiency",
            "month",
            "day_of_week",
            "is_weekend",
            "cpu_lag_1",
            "cpu_lag_7",
            "cpu_rolling_7",
            "cpu_rolling_30",
            "econ_index",
            "market_trend",
            "holiday_flag"
        ]
        feature_cols = [c for c in feature_cols if c in df.columns]

        X_future = df.tail(14)[feature_cols].fillna(method="ffill").fillna(0)
        preds = model.predict(X_future)

        future_dates = [last_date + pd.Timedelta(days=i) for i in range(1, len(preds) + 1)]
        results = [{"date": d.strftime("%Y-%m-%d"), "forecast_cpu": float(round(p, 2))}
                   for d, p in zip(future_dates, preds)]

        return jsonify(results)

    # ------------------------------
    # Case 3: Model missing → simple dummy forecast
    # ------------------------------
    else:
        last_usage = df["usage_cpu"].iloc[-1] if "usage_cpu" in df.columns else 500
        results = []
        for i in range(1, 8):  # 7-day forecast
            results.append({
                "date": (last_date + pd.Timedelta(days=i)).strftime("%Y-%m-%d"),
                "forecast_cpu": float(last_usage * (1 + 0.02 * i))  # +2% growth each day
            })
        return jsonify(results)

# ------------------------------
# Run app
# ------------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
