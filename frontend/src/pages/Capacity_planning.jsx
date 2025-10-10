import React, { useEffect, useState } from "react";
import { Line, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const COLORS = {
  cpu: {
    main: "#0ea5e9",
    ci: "rgba(14, 165, 233, 0.1)",
  },
};

// Utility function for CI bounds
const calculateBounds = (value) => {
  const error = value * 0.1; // ±10%
  return {
    forecast: value,
    upper: value + error,
    lower: value - error,
  };
};

const CapacityPlanning = () => {

  const [selectedRegion, setSelectedRegion] = useState("EastUS");
  const [selectedService, setSelectedService] = useState("Storage");
  const [dateRange, setDateRange] = useState(7);
  const [scaleFactor, setScaleFactor] = useState(1);

  const [cpuForecast, setCpuForecast] = useState({ labels: [], datasets: [] });
  const [capacityData, setCapacityData] = useState({ labels: [], datasets: [] });
  const [riskIndicators, setRiskIndicators] = useState([]);
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Fetch data
  useEffect(() => {
    setLoading(true);
    setError("");
    const region = selectedRegion.toLowerCase();
    const service = selectedService;
    // Fetch capacity planning recommendation
    fetch(`http://127.0.0.1:8000/api/capacity-planning/${region}/${service}?horizon_days=${dateRange}&target=usage_cpu`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch recommendation");
        return res.json();
      })
      .then((data) => {
        setRecommendation(data);
        // Chart data from additional_metrics
        const metrics = data.additional_metrics || {};
        const labels = ["Forecast Min", "Forecast Mean", "Forecast Max", "Required Capacity", "Available Capacity"];
        const values = [metrics.forecast_min, metrics.forecast_mean, metrics.forecast_max, data.required_capacity, data.available_capacity];
        setCpuForecast({
          labels,
          datasets: [
            {
              label: "Capacity Metrics",
              data: values,
              backgroundColor: [COLORS.cpu.main, COLORS.cpu.ci, COLORS.cpu.main, "#6EE7B7", "#93C5FD"],
            },
          ],
        });
        setCapacityData({
          labels: ["Required", "Available"],
          datasets: [
            {
              label: "Capacity",
              data: [data.required_capacity, data.available_capacity],
              backgroundColor: ["#6EE7B7", "#93C5FD"],
            },
          ],
        });
        setRiskIndicators([
          {
            date: data.forecast_period,
            forecast: data.forecast_peak_demand,
            capacity: data.available_capacity,
            status: data.risk_level,
            color:
              data.risk_level === "critical"
                ? "#ef4444"
                : data.risk_level === "high"
                ? "#f59e0b"
                : data.risk_level === "medium"
                ? "#fbbf24"
                : "#10b981",
            action: data.action_type,
            adjustment: data.recommended_adjustment,
            cost: data.cost_impact_monthly,
            reason: data.reason,
          },
        ]);
      })
      .catch((err) => {
        setError(err.message || "Error fetching data");
        setRecommendation(null);
      })
      .finally(() => setLoading(false));
  }, [selectedRegion, selectedService, dateRange, scaleFactor]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: "top" } },
    scales: {
      y: {
        title: { display: true, text: "Usage (%)" },
        min: 0,
        max: 120 / scaleFactor,
      },
    },
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen font-sans">
      <div className="bg-white shadow-xl rounded-xl p-6">
        <h1 className="text-2xl font-bold mb-6 border-b text-gray-800">
          Capacity Forecast Dashboard
        </h1>

        {/* Filter Controls */}
        <div className="flex flex-wrap gap-4 mb-6 bg-gray-100 p-4 rounded-lg shadow-inner">
          <div>
            <label className="mr-2 font-medium text-gray-600">Region:</label>
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              className="border rounded-lg p-2"
            >
              <option>EastUS</option>
              <option>WestUS</option>
              <option>NorthEurope</option>
              <option>SoutheastAsia</option>
            </select>
          </div>
          <div>
            <label className="mr-2 font-medium text-gray-600">Service:</label>
            <select
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              className="border rounded-lg p-2"
            >
              <option>Storage</option>
              <option>Container</option>
              <option>VM</option>
            </select>
          </div>
          <div>
            <label className="mr-2 font-medium text-gray-600">Date Range:</label>
            <select
              value={dateRange}
              onChange={(e) => setDateRange(Number(e.target.value))}
              className="border rounded-lg p-2"
            >
              <option value={7}>7</option>
              <option value={14}>14</option>
              <option value={30}>30</option>
            </select>
          </div>
        </div>

        {/* Error/Loading States */}
        {loading && <div className="text-blue-500 text-center p-4">Loading...</div>}
        {error && <div className="text-red-500 text-center p-4">{error}</div>}

        {/* CPU Forecast Chart */}
        <div className="h-[45vh] w-full bg-white shadow-lg rounded-2xl border p-6 mb-10">
          <h2 className="text-xl font-semibold text-gray-700 ">Capacity Metrics</h2>
          {cpuForecast.labels.length > 0 ? (
            <Bar data={cpuForecast} options={chartOptions} />
          ) : (
            <div className="text-gray-400 text-center p-12">No metrics data available.</div>
          )}
        </div>

        {/* Capacity vs Forecast Chart */}
        <div className="h-[45vh] w-full bg-white shadow-lg rounded-2xl border p-6 mb-10">
          <h2 className="text-xl font-semibold text-gray-700 ">Required vs Available Capacity</h2>
          {capacityData.labels.length > 0 ? (
            <Bar data={capacityData} options={chartOptions} />
          ) : (
            <div className="text-gray-400 text-center p-12">No comparison data available.</div>
          )}
        </div>

        {/* Recommendation & Risk Table */}
        <div className="bg-white shadow-lg rounded-2xl border p-6">
          <h2 className="text-xl font-semibold text-gray-700 ">Capacity Recommendation & Risk Assessment</h2>
          {recommendation ? (
            <div className="mb-6">
              <div className="mb-2 text-lg font-bold text-gray-800">{recommendation.recommended_adjustment}</div>
              <div className="mb-2 text-gray-700">{recommendation.reason}</div>
              <div className="mb-2 text-gray-700">Risk Level: <span style={{color: riskIndicators[0]?.color}}>{recommendation.risk_level}</span></div>
              <div className="mb-2 text-gray-700">Action: <span className="font-semibold">{recommendation.action_type}</span></div>
              <div className="mb-2 text-gray-700">Cost Impact (Monthly): <span className="font-semibold">${recommendation.cost_impact_monthly}</span></div>
              <div className="mb-2 text-gray-700">Confidence Score: <span className="font-semibold">{recommendation.confidence_score}</span></div>
            </div>
          ) : (
            <div className="text-center text-gray-500 p-8">No recommendation data available.</div>
          )}

          {/* Risk Table */}
          {riskIndicators.length > 0 && (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Forecast Peak</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Available Capacity</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Risk Level</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Adjustment</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cost Impact</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {riskIndicators.map((r, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">{r.date}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{r.forecast}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{r.capacity}</td>
                      <td className="px-6 py-4">
                        <span className="px-3 py-1 inline-flex text-xs font-semibold rounded-full" style={{backgroundColor: `${r.color}22`, color: r.color}}>{r.status}</span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{r.action}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{r.adjustment}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">${r.cost}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CapacityPlanning;