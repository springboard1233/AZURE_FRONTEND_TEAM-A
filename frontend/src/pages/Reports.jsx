import React, { useEffect, useState } from "react";
import { Bar, Pie } from "react-chartjs-2";
import FeatureReport from "../components/FeatureReport";
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
import { motion } from "framer-motion";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);

const Reports = () => {
  const [forecast, setForecast] = useState({ forecasts: {} });
  const [usageTrends, setUsageTrends] = useState({ regions: [], series: [] });
  const [topRegions, setTopRegions] = useState([]);
  const [insights, setInsights] = useState({});
  const [selectedRegion, setSelectedRegion] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const scaleFactor = 10;

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [fRes, uRes, tRes, iRes] = await Promise.all([
          fetch("http://127.0.0.1:8000/api/forecast"),
          fetch("http://127.0.0.1:8000/api/usage-trends"),
          fetch("http://127.0.0.1:8000/api/top-regions"),
          fetch("http://127.0.0.1:8000/api/insights"),
        ]);

        const [forecastData, usageData, topData, insightData] = await Promise.all([
          fRes.json(),
          uRes.json(),
          tRes.json(),
          iRes.json(),
        ]);

        setForecast(forecastData);
        setUsageTrends(usageData);
        setTopRegions(topData.top_regions || []);
        setInsights(insightData);
        if (usageData.regions?.length) setSelectedRegion(usageData.regions[0]);
      } catch (err) {
        console.error(err);
        setError("Failed to load reports data. Please try again later.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading)
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-lg font-semibold animate-pulse text-blue-600">
          Loading reports...
        </div>
      </div>
    );

  if (error)
    return (
      <div className="text-center text-red-600 mt-10 font-semibold">
        {error}
      </div>
    );

  // Data calculations
  const regionSeries =
    usageTrends.series.find((s) => s.region === selectedRegion)?.data || [];
  const forecastSeries = forecast.forecasts[selectedRegion] || [];

  const actualDates = regionSeries.map((d) => d.date);
  const forecastDates = forecastSeries.map((d) => d.date);
  const allDates = [...actualDates, ...forecastDates];

  const actualCpuData = allDates.map((date) => {
    const found = regionSeries.find((d) => d.date === date);
    return found ? (found.cpu_percent / scaleFactor).toFixed(2) : null;
  });

  const forecastCpuData = allDates.map((date) => {
    const found = forecastSeries.find((d) => d.date === date);
    return found ? (found.cpu_percent / scaleFactor).toFixed(2) : null;
  });

  const avgCpuRegion = regionSeries.length
    ? (
        regionSeries.reduce((a, b) => a + b.cpu_percent, 0) /
        regionSeries.length
      ).toFixed(2)
    : 0;

  const totalStorageLatest = regionSeries.length
    ? regionSeries[regionSeries.length - 1].storage_percent
    : 0;

  const avgCpuByRegion = topRegions.map((r) => ({
    region: r.region,
    avg: (r.cpu_usage_total / scaleFactor).toFixed(2),
  }));

  const monthlyLabels = insights.monthly_usage?.map((d) => d.month) || [];
  const monthlyValues =
    insights.monthly_usage?.map((d) => (d.cpu_usage / scaleFactor).toFixed(2)) ||
    [];

  const StatCard = ({ title, value, unit }) => (
    <motion.div
      whileHover={{ scale: 1.05 }}
      className="bg-white shadow-lg rounded-2xl p-5 text-center hover:shadow-2xl transition-all duration-200"
    >
      <p className="text-gray-500 text-sm">{title}</p>
      <p className="text-2xl font-bold text-blue-700">
        {value} {unit}
      </p>
    </motion.div>
  );

  return (
    <div className="p-4 space-y-8">
      <h1 className="text-3xl font-extrabold text-center text-blue-800 mb-4">
        📈 Reports Dashboard
      </h1>

      {/* Region Selector */}
      <div className="flex justify-center">
        <select
          value={selectedRegion}
          onChange={(e) => setSelectedRegion(e.target.value)}
          className="border border-blue-400 px-4 py-2 rounded-xl shadow focus:ring focus:ring-blue-300 outline-none"
        >
          {usageTrends.regions.map((region) => (
            <option key={region} value={region}>
              {region}
            </option>
          ))}
        </select>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-6 text-center">
        <StatCard
          title={`Avg CPU (${selectedRegion})`}
          value={avgCpuRegion}
          unit="%"
        />
        <StatCard
          title={`Storage (Latest Day)`}
          value={totalStorageLatest}
          unit="GB"
        />
        <StatCard
          title="Forecast Days"
          value={forecastDates.length}
          unit="days"
        />
      </div>

      {/* Actual vs Forecasted Chart */}
      <motion.div
        whileHover={{ scale: 1.01 }}
        className="bg-white shadow-xl rounded-2xl p-6 mx-auto max-w-5xl"
      >
        <h2 className="text-lg font-semibold text-gray-700 mb-4">
          Actual vs Forecasted CPU Usage ({selectedRegion})
        </h2>
        <div className="h-[400px]">
          <Bar
            data={{
              labels: allDates,
              datasets: [
                {
                  label: "Actual CPU Usage (x" + scaleFactor + ")",
                  data: actualCpuData,
                  backgroundColor: "rgba(59,130,246,0.7)",
                  borderRadius: 6,
                },
                {
                  label: "Forecasted CPU Usage (x" + scaleFactor + ")",
                  data: forecastCpuData,
                  backgroundColor: "rgba(245,158,66,0.7)",
                  borderRadius: 6,
                },
              ],
            }}
            options={{
              maintainAspectRatio: false,
              responsive: true,
              plugins: {
                legend: { position: "top" },
                tooltip: {
                  callbacks: {
                    label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y}`,
                  },
                },
              },
              scales: {
                x: {
                  title: { display: true, text: "Date" },
                },
                y: {
                  title: { display: true, text: "CPU Usage (x" + scaleFactor + ")" },
                },
              },
            }}
          />
        </div>
      </motion.div>

      {/* Two Side-by-Side Charts */}
      <div className="flex flex-col md:flex-row gap-6 h-[40vh]">
        {/* Pie Chart */}
        <motion.div
          whileHover={{ scale: 1.03 }}
          className="flex-1 bg-white shadow-lg rounded-2xl border p-6"
        >
          <h2 className="text-lg font-semibold text-gray-700 text-center">
            Top Regions by CPU Usage (x{scaleFactor})
          </h2>
          {avgCpuByRegion.length ? (
            <Pie
              data={{
                labels: avgCpuByRegion.map((d) => d.region),
                datasets: [
                  {
                    data: avgCpuByRegion.map((d) => d.avg),
                    backgroundColor: [
                      "#3b82f6",
                      "#6366f1",
                      "#22c55e",
                      "#f59e0b",
                      "#ef4444",
                    ],
                    borderWidth: 2,
                  },
                ],
              }}
              options={{
                maintainAspectRatio: false,
                responsive: true,
                plugins: {
                  legend: {position: "bottom", labels: { boxWidth: 20 }} ,
                },
              }}
              height={250}
            />
          ) : (
            <p className="text-gray-500 text-center">No data available</p>
          )}
        </motion.div>

        {/* Bar Chart */}
        <motion.div
          whileHover={{ scale: 1.03 }}
          className="flex-1 bg-white shadow-lg rounded-2xl border p-6"
        >
          <h2 className="text-lg font-semibold text-gray-700 text-center">
            Monthly CPU Usage (x{scaleFactor})
          </h2>
          {monthlyValues.length ? (
            <Bar
              data={{
                labels: monthlyLabels,
                datasets: [
                  {
                    label: "CPU Usage",
                    data: monthlyValues,
                    backgroundColor: "#60a5fa",
                    borderRadius: 6,
                  },
                ],
              }}
              options={{
                maintainAspectRatio: false,
                responsive: true,
                plugins: { legend: { display: false } },
              }}
              height={250}
            />
          ) : (
            <p className="text-gray-500 text-center">No data available</p>
          )}
        </motion.div>
      </div>

      {/* Additional Reports */}
      <FeatureReport />
    </div>
  );
};

export default Reports;

