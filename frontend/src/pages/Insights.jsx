import React, { useEffect, useState } from "react";
import { FaServer, FaChartLine, FaCloud, FaCalendarAlt, FaCheckCircle, FaExclamationCircle, FaArrowUp, FaArrowRight } from "react-icons/fa";

const Card = ({ title, icon, children }) => (
  <div className="bg-white shadow-lg rounded-2xl p-6 mb-6 hover:shadow-2xl transition-all">
    <div className="flex items-center mb-4">
      <span className="text-2xl mr-2 text-blue-600">{icon}</span>
      <h2 className="text-xl font-semibold text-gray-800">{title}</h2>
    </div>
    {children}
  </div>
);

const Insights = () => {
  const [insights, setInsights] = useState(null);
  const [modelComparison, setModelComparison] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch model comparison data first
    fetch("http://127.0.0.1:8000/api/model-comparison")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch model comparison");
        return res.json();
      })
      .then((data) => setModelComparison(data))
      .catch((err) => setError(err.message));

    // Fetch insights data
    fetch("http://127.0.0.1:8000/api/insights")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch insights");
        return res.json();
      })
      .then((data) => setInsights(data))
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <p className="text-red-600 text-center mt-8">{error}</p>;
  if (!modelComparison || !insights) return <p className="text-center mt-8">Loading Insights...</p>;

  // Data keys from backend
  const {
    top_regions_by_cpu = [],
    monthly_peak_demand,
    quarterly_peak_demand,
    avg_daily_usage_per_region = [],
    storage_efficiency_per_region = [],
    cpu_utilization_ratios = [],
    weekday_vs_weekend_cpu = {},
    correlations_with_external_factors = {},
  } = insights;

  return (
    <div className="max-w-6xl mx-auto py-10 px-4">
      <h1 className="text-3xl font-bold text-blue-800 text-center mb-10 tracking-tight">Azure Demand Forecasting Insights</h1>

      {/* Model Comparison Table - First Section */}
      <Card title="Model Performance Comparison" icon={<FaChartLine />}>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse bg-white">
            <thead>
              <tr className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
                <th className="p-4 text-left font-semibold">Model</th>
                <th className="p-4 text-left font-semibold">MAE</th>
                <th className="p-4 text-left font-semibold">RMSE</th>
                <th className="p-4 text-left font-semibold">MAPE</th>
                <th className="p-4 text-left font-semibold">MAE Std</th>
                <th className="p-4 text-left font-semibold">Rank</th>
              </tr>
            </thead>
            <tbody>
              {modelComparison && modelComparison.comparison ? modelComparison.comparison.map((model, idx) => (
                <tr 
                  key={idx} 
                  className="border-b border-gray-200 hover:bg-gradient-to-r hover:from-blue-50 hover:to-purple-50 transition-all duration-300 cursor-pointer transform hover:scale-[1.02]"
                >
                  <td className="p-4 font-bold text-gray-800">{model.model}</td>
                  <td className="p-4">
                    <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
                      {model.MAE?.toFixed(4) || 'N/A'}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-medium">
                      {model.RMSE?.toFixed(4) || 'N/A'}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
                      {model.MAPE?.toFixed(4) || 'N/A'}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm font-medium">
                      {model.MAE_std?.toFixed(4) || 'N/A'}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className="bg-indigo-100 text-indigo-800 px-3 py-1 rounded-full text-sm font-medium">
                      {model.rank || 'N/A'}
                    </span>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="6" className="p-4 text-center text-gray-500">No model comparison data available</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {modelComparison && modelComparison.best_model && (
          <div className="mt-6 p-4 bg-gradient-to-r from-green-100 to-blue-100 rounded-lg border-l-4 border-green-500">
            <div className="flex items-center">
              <FaCheckCircle className="text-green-600 mr-2" />
              <span className="font-semibold text-green-800">Best Performing Model: </span>
              <span className="ml-2 bg-green-200 text-green-800 px-3 py-1 rounded-full font-bold">
                {modelComparison.best_model}
              </span>
            </div>
          </div>
        )}
      </Card>

      {/* Top Regions by CPU Usage */}
      <Card title="Top Regions by CPU Usage" icon={<FaServer />}>
        {top_regions_by_cpu.length === 0 ? (
          <p className="text-gray-500">No data available.</p>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-blue-50">
                <th className="p-2 text-left">Region</th>
                <th className="p-2 text-left">Total CPU Usage</th>
              </tr>
            </thead>
            <tbody>
              {top_regions_by_cpu.map((r, i) => (
                <tr key={i} className="border-t">
                  <td className="p-2 font-medium">{r.region}</td>
                  <td className="p-2">{r.cpu_usage_total.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* Monthly & Quarterly Peak Demand */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="Monthly Peak Demand" icon={<FaChartLine />}>
          <div className="flex items-center text-lg">
            <FaCalendarAlt className="mr-2 text-blue-400" />
            <span>Month: <b>{monthly_peak_demand ?? "N/A"}</b></span>
          </div>
        </Card>
        <Card title="Quarterly Peak Demand" icon={<FaChartLine />}>
          <div className="flex items-center text-lg">
            <FaCalendarAlt className="mr-2 text-blue-400" />
            <span>Quarter: <b>{quarterly_peak_demand ?? "N/A"}</b></span>
          </div>
        </Card>
      </div>

      {/* Average Daily Usage per Region */}
      <Card title="Average Daily CPU Usage per Region" icon={<FaCloud />}>
        {avg_daily_usage_per_region.length === 0 ? (
          <p className="text-gray-500">No data available.</p>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-blue-50">
                <th className="p-2 text-left">Region</th>
                <th className="p-2 text-left">Avg Daily CPU</th>
              </tr>
            </thead>
            <tbody>
              {avg_daily_usage_per_region.map((r, i) => (
                <tr key={i} className="border-t">
                  <td className="p-2 font-medium">{r.region}</td>
                  <td className="p-2">{r.avg_daily_cpu.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* Storage Efficiency per Region */}
      <Card title="Storage Efficiency per Region" icon={<FaCheckCircle />}>
        {storage_efficiency_per_region.length === 0 ? (
          <p className="text-gray-500">No data available.</p>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-blue-50">
                <th className="p-2 text-left">Region</th>
                <th className="p-2 text-left">Storage Efficiency</th>
              </tr>
            </thead>
            <tbody>
              {storage_efficiency_per_region.map((r, i) => (
                <tr key={i} className="border-t">
                  <td className="p-2 font-medium">{r.region}</td>
                  <td className="p-2">{r.storage_efficiency.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* CPU Utilization Ratios per Region */}
      <Card title="CPU Utilization Ratios per Region" icon={<FaArrowUp />}>
        {cpu_utilization_ratios.length === 0 ? (
          <p className="text-gray-500">No data available.</p>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-blue-50">
                <th className="p-2 text-left">Region</th>
                <th className="p-2 text-left">CPU Utilization Ratio</th>
              </tr>
            </thead>
            <tbody>
              {cpu_utilization_ratios.map((r, i) => (
                <tr key={i} className="border-t">
                  <td className="p-2 font-medium">{r.region}</td>
                  <td className="p-2">{r.cpu_utilization_ratio.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* Weekday vs Weekend CPU Usage */}
      <Card title="Weekday vs Weekend CPU Usage" icon={<FaCalendarAlt />}>
        <div className="flex flex-col md:flex-row gap-4">
          <div className="bg-blue-50 rounded-lg p-4 flex-1 text-center">
            <span className="font-semibold text-blue-700">Weekday Mean</span>
            <div className="text-2xl mt-2">{weekday_vs_weekend_cpu.weekday_mean?.toFixed(2) ?? "N/A"}</div>
          </div>
          <div className="bg-blue-50 rounded-lg p-4 flex-1 text-center">
            <span className="font-semibold text-blue-700">Weekend Mean</span>
            <div className="text-2xl mt-2">{weekday_vs_weekend_cpu.weekend_mean?.toFixed(2) ?? "N/A"}</div>
          </div>
        </div>
      </Card>

      {/* Correlations with External Factors */}
      <Card title="Correlations with External Factors" icon={<FaArrowRight />}>
        {Object.keys(correlations_with_external_factors).length === 0 ? (
          <p className="text-gray-500">No data available.</p>
        ) : (
          <ul className="list-disc ml-6 space-y-2">
            {Object.entries(correlations_with_external_factors).map(([factor, value], i) => (
              <li key={i} className="flex items-center">
                <span className="font-medium mr-2">{factor.replace(/_/g, " ")}</span>
                <span className="bg-blue-100 px-2 py-1 rounded text-blue-700">{value?.toFixed(3) ?? "N/A"}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
};

export default Insights;

