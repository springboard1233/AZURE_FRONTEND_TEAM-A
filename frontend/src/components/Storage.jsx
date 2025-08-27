import React from 'react'
import { Bar } from 'react-chartjs-2'
import storage from "../data/storage.json"
import { defaults } from 'chart.js'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

defaults.maintainAspectRatio = false;
defaults.responsive = true;

defaults.plugins.title.display = true;
defaults.plugins.title.align = "center";
defaults.plugins.title.font.size = 20;
defaults.plugins.title.color = "black";

const StorageUsage = () => {
  return (
    <div className="flex justify-center items-center p-1">
      <div className="h-[40vh] w-full max-w-4xl bg-white shadow-lg rounded-2xl border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-700 text-center">
          Storage Usage per Region
        </h2>
        <Bar
          data={{
            labels: storage.map((data) => data.date),
            datasets: [
              {
                label: "East US",
                data: storage.map((data) => data.eastUS),
                backgroundColor: "rgba(167, 170, 233, 0.5)", // Indigo
                borderColor: "#6366f1",
                borderWidth: 1,
              },
              {
                label: "West US",
                data: storage.map((data) => data.westUS),
                backgroundColor: "rgba(151, 220, 247, 0.5)", // Sky blue
                borderColor: "#0ea5e9",
                borderWidth: 1,
              },
            ],
          }}
          options={{
            responsive: true,
            plugins: {
              legend: {
                display: true,
                position: "top",
                labels: {
                  color: "#374151", // gray-700
                  font: {
                    size: 14,
                  },
                },
              },
              tooltip: {
                backgroundColor: "#1f2937", // gray-800
                titleColor: "#f9fafb",
                bodyColor: "#f9fafb",
              },
            },
            scales: {
              x: {
                grid: {
                  color: "rgba(209, 213, 219, 0.3)", // gray-300
                },
                ticks: {
                  color: "#4b5563", // gray-600
                },
              },
              y: {
                grid: {
                  color: "rgba(209, 213, 219, 0.3)",
                },
                ticks: {
                  color: "#4b5563",
                },
              },
            },
          }}
        />
      </div>
    </div>
  )
}

export default StorageUsage

