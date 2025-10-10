import React, { useEffect, useState } from "react";
import { Bar, Line, Pie } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from "chart.js";
import cpu_usage from "../data/cpu_usage.json";
import storage_usage from "../data/storage.json";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

const FeatureReport = () => {
  // --- State ---
  const [rawData, setRawData] = useState([]);
  const [feData, setFeData] = useState([]);
  const [monthlyUsage, setMonthlyUsage] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFeature, setSelectedFeature] = useState("time");

  const scaleFactor = 10000;

  // --- Fetch Backend Data ---
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [rawRes, feRes, insightsRes] = await Promise.all([
          fetch("http://127.0.0.1:8000/api/raw-data").then((r) => r.json()),
          fetch("http://127.0.0.1:8000/api/features").then((r) => r.json()),
          fetch("http://127.0.0.1:8000/api/insights").then((r) => r.json()),
        ]);

        setRawData(rawRes.data || []);
        setFeData(feRes.data || []);
        setMonthlyUsage(insightsRes.monthly_usage || []);
        setLoading(false);
      } catch {
        setError("Failed to fetch report data");
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // --- Compute Summaries from Local JSON ---
  const avgCPU_East = (cpu_usage.reduce((a, b) => a + b.eastUS, 0) / cpu_usage.length).toFixed(1);
  const avgCPU_West = (cpu_usage.reduce((a, b) => a + b.westUS, 0) / cpu_usage.length).toFixed(1);
  const totalStorage_East = storage_usage.reduce((a, b) => a + b.eastUS, 0);
  const totalStorage_West = storage_usage.reduce((a, b) => a + b.westUS, 0);

  // --- Chart Data ---
  const timeLabels = feData.map((d) => d.date);
  const timeData = feData.map((d) => d.usage_cpu / scaleFactor);
  const timeColors = feData.map((d) => (d.is_weekend ? "#F59E42" : "#4F8A8B"));

  const rollingRaw = feData.map((d) => d.usage_cpu / scaleFactor);
  const rollingMean = rollingRaw.map((val, idx, arr) => {
    const start = Math.max(0, idx - 6);
    const slice = arr.slice(start, idx + 1);
    return slice.length ? slice.reduce((a, b) => a + b, 0) / slice.length : val;
  });

  const derivedRegions = [...new Set(feData.map((d) => d.region))];
  const derivedData = {
    labels: derivedRegions,
    datasets: [
      {
        label: "CPU Utilization",
        data: derivedRegions.map((region) => {
          const rows = feData.filter((d) => d.region === region);
          return rows.length ? rows.reduce((a, b) => a + (b.cpu_utilization_ratio || 0), 0) / rows.length : 0;
        }),
        backgroundColor: "#4F8A8B",
      },
      {
        label: "Storage Efficiency",
        data: derivedRegions.map((region) => {
          const rows = feData.filter((d) => d.region === region);
          return rows.length ? rows.reduce((a, b) => a + (b.storage_efficiency || 0), 0) / rows.length : 0;
        }),
        backgroundColor: "#F59E42",
      },
    ],
  };

  const lagData = {
    labels: feData.map((d) => d.date),
    datasets: [
      {
        label: "CPU vs Lag 1",
        data: feData.map((d) => ({ x: d.cpu_usage_lag_1, y: d.usage_cpu })),
        backgroundColor: "#4F8A8B",
        pointRadius: 4,
      },
      {
        label: "Storage vs Lag 1",
        data: feData.map((d) => ({ x: d.storage_usage_lag_1, y: d.usage_storage })),
        backgroundColor: "#F59E42",
        pointRadius: 4,
      },
    ],
  };

  const rollingData = {
    labels: feData.map((d) => d.date),
    datasets: [
      {
        label: "Raw CPU Usage",
        data: rollingRaw,
        borderColor: "rgba(245,158,66,0.5)", // semi-transparent orange
        backgroundColor: "rgba(245,158,66,0.2)",
        fill: false,
        tension: 0.3,
        pointRadius: 1,          // make points smaller
        borderWidth: 1,          // thinner line
      },
      {
        label: "7-day Rolling Mean",
        data: rollingMean,
        borderColor: "#4F8A8B",
        fill: false,
        tension: 0.3,
        pointRadius: 1,
        borderWidth: 1,          // thicker line to stand out
      },
    ],
  };

  // --- Reusable Chart Container ---
  const ChartCard = ({ title, children }) => (
    <div className="bg-white shadow-lg rounded-2xl p-6 w-full max-w-4xl mb-6">
      <h2 className="text-lg font-semibold text-gray-700 mb-4 text-center">{title}</h2>
      {children}
    </div>
  );

  // --- Render ---
  if (loading) return <div className="text-center py-10">Loading...</div>;
  if (error) return <div className="text-center py-10 text-red-600">{error}</div>;

  return (
    <div className="flex flex-col items-center space-y-8 p-4">
      <h1 className="text-3xl font-bold text-gray-800 text-center">Feature Engineering Reports</h1>

      {/* Feature Dropdown */}
      <div className="flex justify-center mb-4">
        <select
          value={selectedFeature}
          onChange={(e) => setSelectedFeature(e.target.value)}
          className="border px-3 py-2 rounded-lg shadow"
        >
          <option value="time">Time-based Features</option>
          <option value="lag">Lag Features</option>
          <option value="rolling">Rolling Features</option>
          <option value="derived">Derived Metrics</option>
        </select>
      </div>

      {/* Charts with Fixed Height */}
      {selectedFeature === "time" && (
        <ChartCard title="CPU Usage Over Time (Weekday vs Weekend)">
          <div className="h-[400px]">
            <Line
              data={{
                labels: timeLabels,
                datasets: [
                  {
                    label: "CPU Usage",
                    data: timeData,
                    borderColor: "#4F8A8B",
                    pointBackgroundColor: timeColors,
                    fill: false,
                    tension: 0.3,
                  },
                ],
              }}
              options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "top" } } }}
            />
          </div>
        </ChartCard>
      )}

      {selectedFeature === "lag" && (
        <ChartCard title="CPU & Storage vs Lag Features">
          <div className="h-[400px]">
            <Bar
              data={lagData}
              options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "top" } } }}
            />
          </div>
        </ChartCard>
      )}

      {selectedFeature === "rolling" && (
        <ChartCard title="CPU Usage with 7-day Rolling Mean">
          <div className="h-[400px]">
            <Line
              data={rollingData}
              options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "top" } } }}
            />
          </div>
        </ChartCard>
      )}

      {selectedFeature === "derived" && (
        <ChartCard title="Region-wise Metrics">
          <div className="h-[400px]">
            <Bar
              data={derivedData}
              options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "top" } } }}
            />
          </div>
        </ChartCard>
      )}
    </div>
  );
};

export default FeatureReport;






