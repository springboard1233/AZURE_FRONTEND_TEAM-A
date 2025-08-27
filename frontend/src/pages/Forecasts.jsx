import React from "react";
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

import cpu_usage from "../data/cpu_usage.json";
import storage_usage from "../data/storage.json";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const Forecasts = () => {
  // Extend CPU data with dummy forecast values
  const cpuForecast = [
    ...cpu_usage,
    { date: "2023-01-07", eastUS: 90, westUS: 87 },
    { date: "2023-01-08", eastUS: 92, westUS: 85 },
  ];

  // Extend Storage data with dummy forecast values
  const storageForecast = [
    ...storage_usage,
    { date: "2023-01-07", eastUS: 1500, westUS: 1400 },
    { date: "2023-01-08", eastUS: 1600, westUS: 1700 },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800 text-center">Forecasts</h1>

      {/* CPU Forecast Line Chart */}
      <div className="h-[40vh] bg-white shadow-lg rounded-2xl border p-6">
        <h2 className="text-lg font-semibold text-gray-700 ">CPU Usage Forecast</h2>
        <Line
          data={{
            labels: cpuForecast.map((d) => d.date),
            datasets: [
              {
                label: "East US",
                data: cpuForecast.map((d) => d.eastUS),
                borderColor: "#6366f1",
                fill: false,
              },
              {
                label: "West US",
                data: cpuForecast.map((d) => d.westUS),
                borderColor: "#0ea5e9",
                fill: false,
              },
            ],
          }}
        />
      </div>

      {/* Storage Forecast Line Chart */}
      <div className="h-[40vh] bg-white shadow-lg rounded-2xl border p-6">
        <h2 className="text-lg font-semibold text-gray-700">Storage Usage Forecast</h2>
        <Line
          data={{
            labels: storageForecast.map((d) => d.date),
            datasets: [
              {
                label: "East US",
                data: storageForecast.map((d) => d.eastUS),
                borderColor: "#f59e0b",
                fill: false,
              },
              {
                label: "West US",
                data: storageForecast.map((d) => d.westUS),
                borderColor: "#10b981",
                fill: false,
              },
            ],
          }}
        />
      </div>
    </div>
  );
};

export default Forecasts;


