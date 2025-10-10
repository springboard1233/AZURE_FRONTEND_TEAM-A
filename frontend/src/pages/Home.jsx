import React, { useState, useEffect } from 'react';
import { 
  FaCloud, FaServer, FaChartLine, FaGlobe, FaArrowUp, 
  FaDatabase, FaShieldAlt, FaRocket, FaBolt, FaEye, FaCalendarAlt 
} from 'react-icons/fa';

const Home = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [modelComparison, setModelComparison] = useState(null);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('http://127.0.0.1:8000/api/usage-trends').then(res => res.json()),
      fetch('http://127.0.0.1:8000/api/model-comparison').then(res => res.json()),
      fetch('http://127.0.0.1:8000/api/insights').then(res => res.json())
    ])
    .then(([usageData, modelData, insightsData]) => {
      console.log("Usage Data:", usageData); // debug
      setDashboardData(usageData);
      setModelComparison(modelData);
      setInsights(insightsData);
      setLoading(false);
    })
    .catch(err => {
      console.error('Error fetching dashboard data:', err);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-xl text-gray-600">Loading Azure Demand Analytics...</p>
        </div>
      </div>
    );
  }

  // ✅ Extract all data points correctly
  const allDataPoints = dashboardData?.series?.flatMap(s => s.data) || [];

  // ✅ Key Metrics
  const totalRegions = dashboardData?.regions ? dashboardData.regions.length : 0;
  const totalDataPoints = allDataPoints.length;

  const avgCpuUsage = totalDataPoints > 0
    ? (allDataPoints.reduce((sum, d) => sum + (d.cpu_percent || 0), 0) / totalDataPoints).toFixed(2)
    : '0';

  const totalStorageCapacity = totalDataPoints > 0
    ? allDataPoints.reduce((sum, d) => sum + (d.storage_percent || 0), 0).toLocaleString()
    : '0';

  const bestModel = modelComparison?.best_model || 'ARIMA';
  const modelAccuracy = modelComparison?.comparison?.find(m => m.model === bestModel)?.MAE?.toFixed(3) || 'N/A';

  const topRegion = insights?.top_regions_by_cpu?.[0]?.region || 'East US';
  const peakMonth = insights?.monthly_peak_demand || 'December';

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-700 text-white">
        <div className="absolute inset-0 bg-black opacity-10"></div>
        <div className="relative max-w-7xl mx-auto px-6 py-16">
          <div className="text-center">
            <div className="flex justify-center mb-6">
              <div className="p-4 bg-white bg-opacity-20 rounded-full">
                <FaCloud className="text-6xl text-amber-200" />
              </div>
            </div>
            <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
              Azure Demand Forecasting Platform
            </h1>
            <p className="text-xl text-blue-100 mb-8 max-w-3xl mx-auto">
              Advanced AI-Powered Cloud Resource Optimization & Predictive Analytics
            </p>
            <div className="flex justify-center gap-4">
              <div className="flex items-center gap-2 bg-white bg-opacity-20 px-4 py-2 rounded-full">
                <FaBolt className="text-yellow-300" />
                <span className="font-semibold text-black">Real-time Analytics</span>
              </div>
              <div className="flex items-center gap-2 bg-white bg-opacity-20 px-4 py-2 rounded-full">
                <FaRocket className="text-green-300" />
                <span className="font-semibold text-black">ML-Powered Forecasts</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics Dashboard */}
      <div className="max-w-7xl mx-auto px-6 -mt-12 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {/* Active Regions */}
          <div className="bg-white shadow-xl rounded-2xl p-6 border-l-4 border-blue-500 hover:shadow-2xl transition-all transform hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Regions</p>
                <p className="text-3xl font-bold text-blue-600">{totalRegions}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <FaGlobe className="text-2xl text-blue-600" />
              </div>
            </div>
          </div>

          {/* Data Points */}
          <div className="bg-white shadow-xl rounded-2xl p-6 border-l-4 border-green-500 hover:shadow-2xl transition-all transform hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Data Points</p>
                <p className="text-3xl font-bold text-green-600">{totalDataPoints.toLocaleString()}</p>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <FaDatabase className="text-2xl text-green-600" />
              </div>
            </div>
          </div>

          {/* Best Model */}
          <div className="bg-white shadow-xl rounded-2xl p-6 border-l-4 border-purple-500 hover:shadow-2xl transition-all transform hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Best Model</p>
                <p className="text-2xl font-bold text-purple-600">{bestModel}</p>
                <p className="text-xs text-green-600 mt-1">
                  <FaShieldAlt className="inline mr-1" /> MAE: {modelAccuracy}
                </p>
              </div>
              <div className="p-3 bg-purple-100 rounded-full">
                <FaChartLine className="text-2xl text-purple-600" />
              </div>
            </div>
          </div>

          {/* Top Region */}
          <div className="bg-white shadow-xl rounded-2xl p-6 border-l-4 border-orange-500 hover:shadow-2xl transition-all transform hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Top Region</p>
                <p className="text-xl font-bold text-orange-600">{topRegion}</p>
              </div>
              <div className="p-3 bg-orange-100 rounded-full">
                <FaServer className="text-2xl text-orange-600" />
              </div>
            </div>
          </div>
        </div>

        {/* System Performance Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
          <div className="bg-white shadow-xl rounded-2xl p-8 hover:shadow-2xl transition-all">
            <div className="flex items-center mb-6">
              <div className="p-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full mr-4">
                <FaServer className="text-2xl text-white" />
              </div>
              <h3 className="text-2xl font-bold text-gray-800">System Performance</h3>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-4 bg-blue-50 rounded-lg">
                <span className="font-semibold text-gray-700">Average CPU Utilization</span>
                <span className="text-2xl font-bold text-blue-600">{avgCpuUsage}%</span>
              </div>
              <div className="flex justify-between items-center p-4 bg-green-50 rounded-lg">
                <span className="font-semibold text-gray-700">Total Storage Capacity</span>
                <span className="text-2xl font-bold text-green-600">{totalStorageCapacity} GB</span>
              </div>
              <div className="flex justify-between items-center p-4 bg-purple-50 rounded-lg">
                <span className="font-semibold text-gray-700">Peak Demand Month</span>
                <span className="text-2xl font-bold text-purple-600">{peakMonth}</span>
              </div>
            </div>
          </div>

          {/* AI Model Intelligence */}
          <div className="bg-white shadow-xl rounded-2xl p-8 hover:shadow-2xl transition-all">
            <div className="flex items-center mb-6">
              <div className="p-3 bg-gradient-to-r from-green-500 to-blue-600 rounded-full mr-4">
                <FaRocket className="text-2xl text-white" />
              </div>
              <h3 className="text-2xl font-bold text-gray-800">AI Intelligence</h3>
            </div>
            <div className="space-y-4">
              <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
                <div className="flex items-center mb-2">
                  <FaEye className="text-blue-600 mr-2" />
                  <span className="font-semibold text-gray-700">Predictive Models</span>
                </div>
                <p className="text-sm text-gray-600">ARIMA, LSTM, XGBoost algorithms deployed for demand forecasting</p>
              </div>
              <div className="p-4 bg-gradient-to-r from-green-50 to-blue-50 rounded-lg border border-green-200">
                <div className="flex items-center mb-2">
                  <FaBolt className="text-green-600 mr-2" />
                  <span className="font-semibold text-gray-700">Real-time Processing</span>
                </div>
                <p className="text-sm text-gray-600">Live data ingestion and analysis with sub-second response times</p>
              </div>
              <div className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg border border-purple-200">
                <div className="flex items-center mb-2">
                  <FaCalendarAlt className="text-purple-600 mr-2" />
                  <span className="font-semibold text-gray-700">Automated Insights</span>
                </div>
                <p className="text-sm text-gray-600">Intelligent anomaly detection and capacity planning recommendations</p>
              </div>
            </div>
          </div>
        </div>

        {/* Technology Stack */}
        <div className="bg-white shadow-xl rounded-2xl p-8 mb-12 hover:shadow-2xl transition-all">
          <div className="text-center mb-8">
            <h3 className="text-3xl font-bold text-gray-800 mb-4">Technology Stack</h3>
            <p className="text-gray-600 max-w-3xl mx-auto">
              Built with cutting-edge technologies for enterprise-grade performance and scalability
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="text-center p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl">
              <div className="bg-blue-600 text-white rounded-full p-3 w-16 h-16 mx-auto mb-3 flex items-center justify-center">
                <FaRocket className="text-2xl" />
              </div>
              <h4 className="font-bold text-gray-800">FastAPI</h4>
              <p className="text-sm text-gray-600">High-performance backend</p>
            </div>
            <div className="text-center p-4 bg-gradient-to-br from-green-50 to-green-100 rounded-xl">
              <div className="bg-green-600 text-white rounded-full p-3 w-16 h-16 mx-auto mb-3 flex items-center justify-center">
                <FaChartLine className="text-2xl" />
              </div>
              <h4 className="font-bold text-gray-800">React</h4>
              <p className="text-sm text-gray-600">Modern UI framework</p>
            </div>
            <div className="text-center p-4 bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl">
              <div className="bg-purple-600 text-white rounded-full p-3 w-16 h-16 mx-auto mb-3 flex items-center justify-center">
                <FaDatabase className="text-2xl" />
              </div>
              <h4 className="font-bold text-gray-800">ML Models</h4>
              <p className="text-sm text-gray-600">Advanced algorithms</p>
            </div>
            <div className="text-center p-4 bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl">
              <div className="bg-orange-600 text-white rounded-full p-3 w-16 h-16 mx-auto mb-3 flex items-center justify-center">
                <FaCloud className="text-2xl" />
              </div>
              <h4 className="font-bold text-gray-800">Azure</h4>
              <p className="text-sm text-gray-600">Cloud infrastructure</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;



