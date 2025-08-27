import React from "react";
import { Bar, Pie } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from "chart.js";

import cpu_usage from "../data/cpu_usage.json";
import storage_usage from "../data/storage.json";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);

const Reports = () => {
  // Compute summaries
  const avgCPU_East = (cpu_usage.reduce((a, b) => a + b.eastUS, 0) / cpu_usage.length).toFixed(1);
  const avgCPU_West = (cpu_usage.reduce((a, b) => a + b.westUS, 0) / cpu_usage.length).toFixed(1);

  const totalStorage_East = storage_usage.reduce((a, b) => a + b.eastUS, 0);
  const totalStorage_West = storage_usage.reduce((a, b) => a + b.westUS, 0);

  return (
    <div className="space-y-6 ">
      <h1 className="text-2xl font-bold text-gray-800 text-center">Reports</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white shadow rounded-2xl p-4 text-center">
          <p className="text-gray-500 text-sm">Avg CPU (East US)</p>
          <p className="text-xl font-bold">{avgCPU_East}%</p>
        </div>
        <div className="bg-white shadow rounded-2xl p-4 text-center">
          <p className="text-gray-500 text-sm">Avg CPU (West US)</p>
          <p className="text-xl font-bold">{avgCPU_West}%</p>
        </div>
        <div className="bg-white shadow rounded-2xl p-4 text-center">
          <p className="text-gray-500 text-sm">Total Storage (East US)</p>
          <p className="text-xl font-bold">{totalStorage_East} GB</p>
        </div>
        <div className="bg-white shadow rounded-2xl p-4 text-center">
          <p className="text-gray-500 text-sm">Total Storage (West US)</p>
          <p className="text-xl font-bold">{totalStorage_West} GB</p>
        </div>
      </div>

      {/* CPU Usage Comparison - Pie */}
      <div className="w-full h-[40vh] bg-white shadow-lg rounded-2xl border p-6 flex flex-col justify-center items-center">
        <h2 className="text-lg font-semibold text-gray-700 ">CPU Usage Share</h2>
        <div className="w-full h-full flex justify-center items-center">
          <Pie
            data={{
              labels: ["East US", "West US"],
              datasets: [
                {
                  data: [avgCPU_East, avgCPU_West],
                  backgroundColor: ["#C0C9EE", "#898AC4"],
                },
              ],
            }}
            options={{
              maintainAspectRatio: false,
              responsive: true,
              plugins: {
                legend: {
                  position: "bottom",
                },
              },
            }}
          />
        </div>
      </div>

      {/* Storage Usage Comparison - Bar */}
      <div className="w-full h-[40vh] bg-white shadow-lg rounded-2xl border p-6">
        <h2 className="text-lg font-semibold text-gray-700 ">Storage Usage Comparison</h2>
        <Bar
          data={{
            labels: storage_usage.map((d) => d.date),
            datasets: [
              {
                label: "East US",
                data: storage_usage.map((d) => d.eastUS),
                backgroundColor: "#C0C9EE",
              },
              {
                label: "West US",
                data: storage_usage.map((d) => d.westUS),
                backgroundColor: "#898AC4",
              },
            ],
          }}
          options={{
            maintainAspectRatio: false,
            responsive: true,
            plugins: {
              legend: { position: "top" },
            },
          }}
        />
      </div>
    </div>
  );
};

export default Reports;




