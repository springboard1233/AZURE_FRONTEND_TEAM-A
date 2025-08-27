import React from 'react'
import { Line } from 'react-chartjs-2'
import cpu_usage from "../data/cpu_usage.json"
import { defaults } from 'chart.js'
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

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
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

const MainArea = () => {
  return (

    <div className="flex justify-center items-center p-1">
      <div className="h-[40vh] w-full max-w-4xl bg-white shadow-lg rounded-2xl border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-700 text-center">
          CPU Usage Trends per Region
        </h2>
        <Line
          data={{
            labels: cpu_usage.map((data) => data.date),
            datasets: [
              {
                label: "East US",
                data: cpu_usage.map((data) => data.eastUS),
                backgroundColor: "rgba(167, 170, 233, 0.2)",
                borderColor: "#6366f1",
                borderWidth: 2,
                fill: true,
              },
              {
                label: "West US",
                data: cpu_usage.map((data) => data.westUS),
                backgroundColor: "rgba(151, 220, 247, 0.2)",
                borderColor: "#0ea5e9",
                borderWidth: 2,
                fill: true,
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
                titleColor: "#f9fafb", // gray-50
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

export default MainArea
