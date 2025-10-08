// frontend/src/App.js
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from "chart.js";
import { Line } from "react-chartjs-2";
import Sidebar from "./components/Sidebar";
import Home from "./components/Home";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

function App() {
  const [usage, setUsage] = useState([]);
  const [forecast, setForecast] = useState([]);

  useEffect(() => {
    const API_BASE = process.env.REACT_APP_API_BASE || "http://127.0.0.1:5000";

    axios
      .get(`${API_BASE}/api/usage-trends`)
      .then((res) => {
        console.log("Usage API Response:", res.data);
        setUsage(res.data);
      })
      .catch((err) => console.error("usage error", err));

    axios
      .get(`${API_BASE}/api/forecast`)
      .then((res) => {
        console.log("Forecast API Response:", res.data);
        setForecast(res.data);
      })
      .catch((err) => console.error("forecast error", err));
  }, []);

  // -----------------------------
  // Chart 1: Raw Usage (CPU + Storage)
  // -----------------------------
  const usageData = {
    labels: usage.map((u) => u.date),
    datasets: [
      {
        label: "CPU Usage",
        data: usage.map((u) => u.usage_cpu || 0),
        borderColor: "rgba(75,192,192,1)",
        tension: 0.2,
      },
      {
        label: "Storage Usage",
        data: usage.map((u) => u.usage_storage || 0),
        borderColor: "rgba(153,102,255,1)",
        tension: 0.2,
      },
    ],
  };

  // -----------------------------
  // Chart 2: CPU Utilization
  // -----------------------------
  const utilizationData = {
    labels: usage.map((u) => u.date),
    datasets: [
      {
        label: "CPU Utilization",
        data: usage.map((u) => u.cpu_utilization || 0),
        borderColor: "rgba(255,99,132,1)",
        tension: 0.2,
      },
    ],
  };

  // -----------------------------
  // Chart 3: Storage Efficiency
  // -----------------------------
  const efficiencyData = {
    labels: usage.map((u) => u.date),
    datasets: [
      {
        label: "Storage Efficiency",
        data: usage.map((u) => u.storage_efficiency || 0),
        borderColor: "rgba(54,162,235,1)",
        tension: 0.2,
      },
    ],
  };

  // -----------------------------
  // Chart 4: Forecast (history + prediction)
  // -----------------------------
  const forecastData = {
    labels: [
      ...usage.map((u) => u.date),
      ...forecast.map((f) => f.date)
    ],
    datasets: [
      {
        label: "Historical CPU Usage",
        data: usage.map((u) => u.usage_cpu || 0),
        borderColor: "rgba(75,192,192,1)",
        tension: 0.2,
      },
      {
        label: "Forecast CPU",
        data: [
          ...Array(usage.length).fill(null), // align forecast after history
          ...forecast.map((f) => f.forecast_cpu || 0),
        ],
        borderColor: "rgba(255,99,132,1)",
        borderDash: [6, 4], // dashed line for forecast
        tension: 0.2,
      },
    ],
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main style={{ padding: 20, flex: 1 }}>
        <Home />

        {/* Usage Trends */}
        <section id="usage" style={{ marginTop: 20 }}>
          <h2>Usage Trends</h2>
          <Line data={usageData} />
        </section>

        {/* CPU Utilization */}
        <section id="utilization" style={{ marginTop: 40 }}>
          <h2>CPU Utilization</h2>
          <Line data={utilizationData} />
        </section>

        {/* Storage Efficiency */}
        <section id="efficiency" style={{ marginTop: 40 }}>
          <h2>Storage Efficiency</h2>
          <Line data={efficiencyData} />
        </section>

        {/* Forecast */}
        <section id="forecast" style={{ marginTop: 40 }}>
          <h2>Forecast (Historical + Prediction)</h2>
          <Line data={forecastData} />
        </section>
      </main>
    </div>
  );
}

export default App;
