// src/pages/Monitoring.jsx
import React, { useEffect, useState } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

/**
 * Monitoring.jsx
 *
 * - Fetches /api/model-comparison and /api/model-metrics
 * - Uses model MAPE_mean -> accuracy = 100 - MAPE_mean
 * - Because model-metrices.json has no historical values, this component
 *   generates a small synthetic trend (replaceable by a real historical
 *   endpoint when you add one).
 *
 * Replace syntheticTrend() with a real API call to obtain true per-date metrics if available.
 */

// Helper: generate deterministic synthetic trend around baseAccuracy
const syntheticTrend = (baseAccuracy, volatility, points = 30) => {
  // volatility acts like std dev proxy (use MAE_std scaled)
  // We'll produce a small random-walk-like series but deterministic-ish (no seed here).
  const arr = [];
  let cur = baseAccuracy;
  for (let i = 0; i < points; i++) {
    // small step influenced by volatility
    const step = (Math.sin(i * 1.3) * 0.5 + Math.cos(i * 0.7) * 0.3) * (volatility / 10);
    cur = Math.max(0, Math.min(100, cur + step));
    arr.push(Number(cur.toFixed(2)));
  }
  return arr;
};

// Traffic light and label according to thresholds
const healthFromAccuracy = (acc) => {
  if (acc > 85) return { label: "Stable", color: "green" };
  if (acc >= 70) return { label: "Caution", color: "yellow" };
  return { label: "Retrain Needed", color: "red" };
};

const Monitoring = () => {
  const [comparison, setComparison] = useState([]); // array of models from /model-comparison
  const [bestModelInfo, setBestModelInfo] = useState(null); // from /model-metrics or comparison.best_model
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState(30); // 7/14/30
  const [lastRetrainDate, setLastRetrainDate] = useState(null); // set from backend if available
  const [alerts, setAlerts] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [backendAlerts, setBackendAlerts] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        // 1) fetch comparison (list of models + metrics)
        const compRes = await fetch("http://localhost:8000/api/model-comparison");
        const compJson = compRes.ok ? await compRes.json() : null;

        // 2) fetch best model metrics (single record)
        const topRes = await fetch("http://localhost:8000/api/model-metrics");
        const topJson = topRes.ok ? await topRes.json() : null;

        // 3) fetch system health and backend alerts
        const healthRes = await fetch("http://localhost:8000/api/monitoring/health");
        const healthJson = healthRes.ok ? await healthRes.json() : null;
        setSystemHealth(healthJson);
        setBackendAlerts(healthJson?.alerts || []);

        // 4) fetch historical accuracy data for each model
        const historyRes = await fetch("http://localhost:8000/api/model-history");
        const historyJson = historyRes.ok ? await historyRes.json() : null;

        // Prepare model metrics list
        const models = (compJson && compJson.comparison) ? compJson.comparison : [];
        const modelList = models.map((m) => {
          const mape = Number(m.MAPE) || Number(m.MAPE_mean) || null;
          const baseMape = mape ?? Number(m.MAPE_mean ?? NaN);
          const computedAccuracy = Number.isFinite(baseMape) ? Math.max(0, Math.min(100, 100 - baseMape)) : null;
          const volatility = Number(m.MAE_std ?? 0);
          return {
            model: m.model || m.Model || "Unknown",
            MAE_mean: Number(m.MAE ?? m.MAE_mean ?? NaN),
            MAE_std: volatility,
            RMSE_mean: Number(m.RMSE ?? m.RMSE_mean ?? NaN),
            MAPE_mean: Number(m.MAPE ?? m.MAPE_mean ?? NaN),
            accuracy: computedAccuracy,
          };
        });
        if (modelList.length === 0 && topJson && topJson.metrics) {
          const m = topJson.metrics;
          const baseMape = Number(m.MAPE ?? m.MAPE_mean ?? NaN);
          const computedAccuracy = Number.isFinite(baseMape) ? Math.max(0, Math.min(100, 100 - baseMape)) : null;
          modelList.push({
            model: topJson.model || "BestModel",
            MAE_mean: Number(m.MAE ?? m.MAE_mean ?? NaN),
            MAE_std: Number(m.MAE_std ?? 0),
            RMSE_mean: Number(m.RMSE ?? m.RMSE_mean ?? NaN),
            MAPE_mean: baseMape,
            accuracy: computedAccuracy,
          });
        }
        if (cancelled) return;
        // Remove duplicates by model name (keep first occurrence)
        const seen = new Set();
        const uniqueModels = [];
        for (const mm of modelList) {
          const key = (mm.model || "").toString();
          if (!seen.has(key)) {
            seen.add(key);
            uniqueModels.push(mm);
          }
        }
        // Use real historical accuracy data if available
        const series = uniqueModels.map((m) => {
          let trend = [];
          let labels = [];
          if (historyJson && historyJson[m.model]) {
            // historyJson[model] = [{date: 'YYYY-MM-DD', accuracy: 92.1}, ...]
            trend = historyJson[m.model].map((d) => d.accuracy);
            labels = historyJson[m.model].map((d) => d.date);
          } else {
            // fallback to synthetic trend if no history
            const points = 30;
            const baseAcc = Number.isFinite(m.accuracy) ? m.accuracy : 75;
            const volatility = Number.isFinite(m.MAE_std) ? m.MAE_std : 1;
            trend = syntheticTrend(baseAcc, volatility, points);
            const now = new Date();
            labels = [];
            for (let i = points - 1; i >= 0; i--) {
              const d = new Date(now);
              d.setDate(now.getDate() - i);
              labels.push(d.toISOString().split("T")[0]);
            }
          }
          return {
            model: m.model,
            trend,
            labels,
            color: getColorForModel(m.model),
            latestAccuracy: trend[trend.length - 1],
            raw: m,
          };
        });
        // Last retrain date: try to read from topJson.metrics if it contains a 'last_retrain' field
        const lastRetrain = (topJson && topJson.metrics && topJson.metrics.last_retrain) ? topJson.metrics.last_retrain : null;
        setComparison(series);
        setLastRetrainDate(lastRetrain ?? "Unknown");
        setBestModelInfo(topJson ?? null);
      } catch (err) {
        setError("Failed to load monitoring data");
        console.error("Monitoring load error:", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // small palette helper
  function getColorForModel(name) {
    const map = {
      ARIMA: "#0ea5e9",
      LSTM: "#8b5cf6",
      XGBoost: "#f59e0b",
    };
    return map[name] ?? stringToColor(name);
  }
  // fallback deterministic color by name
  function stringToColor(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) h = str.charCodeAt(i) + ((h << 5) - h);
    const c = (h & 0x00ffffff).toString(16).toUpperCase();
    return `#${"00000".substring(0, 6 - c.length)}${c}`;
  }

  // Chart dataset assembly
  const buildChartData = () => {
    if (comparison.length === 0) return { labels: [], datasets: [] };
    // Use labels from real data if available
    const labels = comparison[0].labels || [];
    const startIndex = Math.max(0, labels.length - dateRange);
    const slicedLabels = labels.slice(startIndex);

    const datasets = comparison.map((s) => ({
      label: s.model,
      data: s.trend.slice(startIndex),
      borderColor: s.color,
      backgroundColor: s.color + "33",
      tension: 0.25,
      fill: false,
      pointRadius: 3,
    }));
    return { labels: slicedLabels, datasets };
  };

  const chartData = buildChartData();

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: "top" },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y}%`,
        },
      },
    },
    scales: {
      y: {
        min: 0,
        max: 100,
        title: { display: true, text: "Accuracy (%)" },
      },
      x: {
        title: { display: true, text: "Date" },
      },
    },
  };

  const overallAccuracy = comparison.length > 0 ? comparison.reduce((acc, s) => acc + s.latestAccuracy, 0) / comparison.length : null;
  const overallHealth = overallAccuracy !== null ? healthFromAccuracy(overallAccuracy) : { label: "Unknown", color: "gray" };

  return (
    <div className="p-6 md:p-10 bg-gray-50 min-h-screen">
      <div className="max-w-6xl mx-auto">
        <header className="mb-6">
          <h1 className="text-2xl font-bold">Model Monitoring</h1>
          <p className="text-sm text-gray-600 mt-1">
            Live model health, accuracy trends, backend alerts, and recommendations.
          </p>
        </header>

        {/* Error/Loading States */}
        {loading && <div className="text-blue-500 text-center p-4">Loading...</div>}
        {error && <div className="text-red-500 text-center p-4">{error}</div>}

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="col-span-2 bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold">Model Accuracy Trend</h2>
              <div className="flex items-center gap-3">
                <label className="text-sm text-gray-600">Range</label>
                <select
                  value={dateRange}
                  onChange={(e) => setDateRange(Number(e.target.value))}
                  className="border rounded p-1 text-sm"
                >
                  <option value={7}>Last 7 days</option>
                  <option value={14}>Last 14 days</option>
                  <option value={30}>Last 30 days</option>
                </select>
              </div>
            </div>
            <div style={{ height: 360 }}>
              {!loading && chartData.labels && chartData.labels.length > 0 ? (
                <Line data={chartData} options={chartOptions} />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">Loading chart...</div>
              )}
            </div>
          </div>

          <aside className="bg-white p-4 rounded-lg shadow space-y-4">
            <div>
              <h3 className="text-sm text-gray-600">System Health</h3>
              {systemHealth ? (
                <div className="mt-2">
                  <div className="text-sm font-medium">Status: {systemHealth.system_status}</div>
                  <div className="text-xs text-gray-500">Models: {systemHealth.total_models}</div>
                  <div className="text-xs text-gray-500">Health Score: {systemHealth.health_score}</div>
                  <div className="text-xs text-gray-500">Last Updated: {systemHealth.last_updated}</div>
                </div>
              ) : (
                <div className="text-xs text-gray-500">No system health data.</div>
              )}
            </div>
            <div>
              <h3 className="text-sm text-gray-600">Best Model</h3>
              <div className="mt-2">
                <div className="text-sm font-medium">{bestModelInfo?.model ?? "Unknown"}</div>
                {bestModelInfo?.metrics && (
                  <div className="text-xs text-gray-500">
                    MAE: {bestModelInfo.metrics.MAE ?? "N/A"} &middot; RMSE: {bestModelInfo.metrics.RMSE ?? "N/A"} &middot; MAPE: {bestModelInfo.metrics.MAPE ?? "N/A"}
                  </div>
                )}
              </div>
            </div>
            <div>
              <h3 className="text-sm text-gray-600">Last Retrain</h3>
              <div className="mt-2 text-sm">{lastRetrainDate ?? "Unknown"}</div>
            </div>
          </aside>
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white p-4 rounded-lg shadow">
            <h3 className="font-semibold mb-3">Backend Alerts</h3>
            {backendAlerts.length === 0 ? (
              <div className="text-sm text-gray-500">No backend alerts detected.</div>
            ) : (
              <ul className="space-y-2">
                {backendAlerts.map((a, idx) => (
                  <li key={idx} className="border-l-4 pl-3 py-2" style={{ borderColor: a.level === "critical" ? "#ef4444" : "#f59e0b" }}>
                    <div className="text-sm font-medium">{a.model}</div>
                    <div className="text-xs text-gray-600">{a.message}</div>
                    <div className="text-xs text-gray-400 mt-1">Action: {a.action}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <h3 className="font-semibold mb-3">Model Summary</h3>
            <div className="text-sm text-gray-600 mb-3">Models</div>
            <div className="space-y-3">
              {comparison.map((m, i) => {
                const health = healthFromAccuracy(m.latestAccuracy);
                return (
                  <div key={i} className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">{m.model}</div>
                      <div className="text-xs text-gray-500">MAPE: {m.raw.MAPE_mean ?? "N/A"}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-sm font-semibold">{m.latestAccuracy?.toFixed(1)}%</div>
                      <div style={{
                        width: 12, height: 12, borderRadius: 4,
                        backgroundColor: health.color === "green" ? "#10b981" : health.color === "yellow" ? "#f59e0b" : "#ef4444"
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Monitoring;
