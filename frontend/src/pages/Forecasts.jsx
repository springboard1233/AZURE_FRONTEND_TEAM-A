import React, { useEffect, useState } from "react";
import { Line,Bar } from "react-chartjs-2";
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
import { FaDownload } from "react-icons/fa";

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

const Forecasts = () => {
  const [cpuForecast, setCpuForecast] = useState({ labels: [], datasets: [] });
  const [storageForecast, setStorageForecast] = useState({ labels: [], datasets: [] });
  const [cpuModelForecast, setCpuModelForecast] = useState({ labels: [], datasets: [] });
  const [storageModelForecast, setStorageModelForecast] = useState({ labels: [], datasets: [] });
  const [scaleFactor, setScaleFactor] = useState(10);
  const [selectedRegion, setSelectedRegion] = useState("All");
  const [dateRange, setDateRange] = useState(30);
  const [selectedService, setSelectedService] = useState("All");
  const [selectedRegionModel, setSelectedRegionModel] = useState("All");
  const [selectedServiceModel, setSelectedServiceModel] = useState("All");
  const [dateRangeModel, setDateRangeModel] = useState(30);

  // Download functions
  const downloadCSV = (data, filename) => {
    const csvContent = convertToCSV(data);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const downloadExcel = (data, filename) => {
    const csvContent = convertToCSV(data);
    const blob = new Blob([csvContent], { type: 'application/vnd.ms-excel' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename.replace('.csv', '.xls'));
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const convertToCSV = (data) => {
    if (!data.labels || !data.datasets) return '';
    
    // Header row
    const headers = ['Date', ...data.datasets.map(ds => ds.label)];
    let csvContent = headers.join(',') + '\n';
    
    // Data rows
    data.labels.forEach((label, index) => {
      const row = [label, ...data.datasets.map(ds => ds.data[index] || '')];
      csvContent += row.join(',') + '\n';
    });
    
    return csvContent;
  };

  const downloadLinearRegressionData = (format) => {
    const combinedData = {
      labels: cpuForecast.labels,
      datasets: [
        ...cpuForecast.datasets.map(ds => ({ ...ds, label: `CPU - ${ds.label}` })),
        ...storageForecast.datasets.map(ds => ({ ...ds, label: `Storage - ${ds.label}` }))
      ]
    };
    
    const filename = `linear_regression_forecast.${format === 'csv' ? 'csv' : 'xls'}`;
    if (format === 'csv') {
      downloadCSV(combinedData, filename);
    } else {
      downloadExcel(combinedData, filename);
    }
  };

  const downloadPredictiveModelsData = (format) => {
    const combinedData = {
      labels: cpuModelForecast.labels.length > 0 ? cpuModelForecast.labels : storageModelForecast.labels,
      datasets: [
        ...cpuModelForecast.datasets.map(ds => ({ ...ds, label: `CPU - ${ds.label}` })),
        ...storageModelForecast.datasets.map(ds => ({ ...ds, label: `Storage - ${ds.label}` }))
      ]
    };
    
    const filename = `predictive_models_forecast.${format === 'csv' ? 'csv' : 'xls'}`;
    if (format === 'csv') {
      downloadCSV(combinedData, filename);
    } else {
      downloadExcel(combinedData, filename);
    }
  };

  useEffect(() => {
    // Linear Regression forecast from backend
    fetch("http://127.0.0.1:8000/api/forecast")
      .then((res) => res.json())
      .then((data) => {
        // Get all regions and dates
        const regions = Object.keys(data.forecasts);
        const allDates = Array.from(new Set(Object.values(data.forecasts).flat().map(d => d.date))).sort();

        // Prepare region-wise datasets for CPU and Storage
        const regionColors = [
          '#6366f1', '#0ea5e9', '#f59e42', '#4F8A8B', '#647FBC', '#91ADC8', '#AED6CF', '#7A85C1', '#3b82f6'
        ];
        const cpuDatasets = regions.map((region, idx) => ({
          label: `${region} (x${scaleFactor})`,
          data: allDates.map(date => {
            const found = data.forecasts[region].find(d => d.date === date);
            return found ? (found.cpu_percent / scaleFactor).toFixed(2) : null;
          }),
          borderColor: regionColors[idx % regionColors.length],
          backgroundColor: regionColors[idx % regionColors.length] + '33',
          borderWidth: 2,
          fill: false,
        }));
        const storageDatasets = regions.map((region, idx) => ({
          label: `${region} (x${scaleFactor})`,
          data: allDates.map(date => {
            const found = data.forecasts[region].find(d => d.date === date);
            return found ? (found.storage_percent / scaleFactor).toFixed(2) : null;
          }),
          backgroundColor: regionColors[idx % regionColors.length] + '66',
          borderColor: regionColors[idx % regionColors.length],
          borderWidth: 1,
        }));
        setCpuForecast({ labels: allDates, datasets: cpuDatasets });
        setStorageForecast({ labels: allDates, datasets: storageDatasets });
        // Dynamic scale factor for large datasets
        if (allDates.length > 50) setScaleFactor(1000);
        else if (allDates.length > 20) setScaleFactor(100);
        else setScaleFactor(10);
      })
      .catch((err) => console.error("Error fetching linear regression forecast:", err));
  }, []);

  // Fetch model-based forecasts with filters
  useEffect(() => {
   const region = selectedRegionModel === "All" ? "all" : selectedRegionModel.toLowerCase();    
   const service = selectedServiceModel === "All" ? "All" : selectedServiceModel.charAt(0).toUpperCase() + selectedServiceModel.slice(1).toLowerCase();
    
    fetch(`http://127.0.0.1:8000/api/forecast/${region}/${service}`)
      .then((res) => res.json())
      .then((data) => {
        const regionColors = [
          '#6366f1', '#0ea5e9', '#f59e42', '#4F8A8B', '#647FBC', '#91ADC8', '#AED6CF', '#7A85C1', '#3b82f6'
        ];
        
        // Process the data based on the actual API response format
        if (data.forecast && data.forecast.length > 0) {
          // CPU Forecast Dataset
          const cpuDatasets = [{
            label: `${selectedRegionModel} - ${selectedServiceModel} CPU`,
            data: data.forecast.map(d => (d.cpu_percent / scaleFactor).toFixed(2)),
            borderColor: regionColors[0],
            backgroundColor: regionColors[0] + '33',
            borderWidth: 2,
            fill: false,
          }];
          setCpuModelForecast({ 
            labels: data.forecast.map(d => d.date), 
            datasets: cpuDatasets 
          });

          // Storage Forecast Dataset
          const storageDatasets = [{
            label: `${selectedRegionModel} - ${selectedServiceModel} Storage`,
            data: data.forecast.map(d => (d.storage_percent / scaleFactor).toFixed(2)),
            backgroundColor: regionColors[1] + '66',
            borderColor: regionColors[1],
            borderWidth: 1,
          }];
          setStorageModelForecast({ 
            labels: data.forecast.map(d => d.date), 
            datasets: storageDatasets 
          });
        }
      })
      .catch((err) => console.error("Error fetching model forecast:", err));
  }, [selectedRegionModel, selectedServiceModel, scaleFactor]);

  // Apply filters (region + date range)
  const filterData = (data) => {
    let { labels, datasets } = data;

    // Filter dates (last 7/14/30 days)
    labels = labels.slice(-dateRange);

    // Filter datasets by region
    if (selectedRegion !== "All") {
      datasets = datasets.filter(ds => ds.label.startsWith(selectedRegion));
    }

    // Filter datasets by service type
    if (selectedService !== "All") {
      datasets = datasets.filter(ds => ds.label.toLowerCase().includes(selectedService.toLowerCase()));
    }

    // Update datasets to match filtered labels
    datasets = datasets.map(ds => ({
      ...ds,
      data: ds.data.slice(-dateRange)
    }));

    return { labels, datasets };
  };

  return (
    <div className="space-y-6 p-2 ">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Forecasts</h1>
        
        {/* Download Buttons */}
        <div className="flex gap-2">
          {/* Linear Regression Downloads */}
          <div className="flex gap-1">
            <button
              onClick={() => downloadLinearRegressionData('csv')}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              title="Download Linear Regression Data as CSV"
            >
              <FaDownload size={14} />
              Linear CSV
            </button>
            <button
              onClick={() => downloadLinearRegressionData('excel')}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              title="Download Linear Regression Data as Excel"
            >
              <FaDownload size={14} />
              Linear Excel
            </button>
          </div>
          
          {/* Predictive Models Downloads */}
          <div className="flex gap-1">
            <button
              onClick={() => downloadPredictiveModelsData('csv')}
              className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              title="Download Predictive Models Data as CSV"
            >
              <FaDownload size={14} />
              Models CSV
            </button>
            <button
              onClick={() => downloadPredictiveModelsData('excel')}
              className="flex items-center gap-2 bg-orange-600 hover:bg-orange-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              title="Download Predictive Models Data as Excel"
            >
              <FaDownload size={14} />
              Models Excel
            </button>
          </div>
        </div>
      </div>
      
      {/* Filter Controls */}
      <div className="flex gap-4 items-center justify-center mb-4">
        <div>
          <label className="mr-2 font-medium">Region:</label>
          <select 
            value={selectedRegion} 
            onChange={(e) => setSelectedRegion(e.target.value)}
            className="border rounded-md p-2"
          >
            <option value="All">All Regions</option>
            {cpuForecast.datasets.map(ds => ds.label.split(' ')[0]).filter((region, idx, arr) => arr.indexOf(region) === idx).map(region => (
              <option key={region} value={region}>{region}</option>
            ))}
          </select>
        </div>
        
        <div>
          <label className="mr-2 font-medium">Date Range:</label>
          <select 
            value={dateRange} 
            onChange={(e) => setDateRange(Number(e.target.value))}
            className="border rounded-md p-2"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            
          </select>
        </div>
      </div>

      {/* CPU Forecast (Using Linear Regression) */}
      <div className="h-[40vh] w-full bg-white shadow-lg rounded-2xl border p-6">
        <h2 className="text-lg font-semibold text-gray-700 ">CPU Usage Forecast (Using Linear Regression)</h2>
        {cpuForecast.labels.length > 0 && cpuForecast.datasets.length > 0 ? (
          <Line
            data={filterData(cpuForecast)}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                tooltip: {
                  callbacks: {
                    label: (ctx) => `${ctx.dataset.label}: ${ctx.raw} (x${scaleFactor})`,
                  },
                },
                legend: { position: 'top' },
              },
              scales: {
                y: {
                  ticks: {
                    callback: (val) => `${val} (x${scaleFactor})`,
                  },
                },
              },
            }}
          />
        ) : (
          <div className="text-gray-400 text-center">No forecast data available.</div>
        )}
      </div>




      

      {/* Storage Forecast (Using Linear Regression) */}
      <div className="h-[40vh] w-full bg-white shadow-lg rounded-2xl border p-6">
        <h2 className="text-lg font-semibold text-gray-700 ">Storage Usage Forecast (Using Linear Regression)</h2>
        {storageForecast.labels.length > 0 && storageForecast.datasets.length > 0 ? (
          <Bar
            data={filterData(storageForecast)}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                tooltip: {
                  callbacks: {
                    label: (ctx) => `${ctx.dataset.label}: ${ctx.raw} (x${scaleFactor})`,
                  },
                },
                legend: { position: 'top' },
              },
              scales: {
                y: {
                  ticks: {
                    callback: (val) => `${val} (x${scaleFactor})`,
                  },
                },
              },
            }}
          />
        ) : (
          <div className="text-gray-400 text-center">No forecast data available.</div>
        )}
      </div>








      {/* Using Predictive Models Section */}
      <div className="mt-12 pt-8 border-t-2 border-gray-200">
        <h2 className="text-xl font-bold text-gray-800 text-center mb-6">Using Predictive Models(Select Region, Service to display the data)</h2>
        
        {/* Filter Controls for Model-based Forecasts */}
        <div className="flex gap-4 items-center justify-center mb-4">
          <div>
            <label className="mr-2 font-medium">Region:</label>
            <select 
              value={selectedRegionModel} 
              onChange={(e) => setSelectedRegionModel(e.target.value)}
              className="border rounded-md p-2"
            >
              <option value="All">All Regions</option>
              <option value="EastUS">East US</option>
              <option value="WestUS">West US</option>
              
              <option value="NorthEurope">North Europe</option>
              <option value="SoutheastAsia">Southeast Asia</option>
            </select>
          </div>
          <div>
            <label className="mr-2 font-medium">Service:</label>
            <select 
              value={selectedServiceModel} 
              onChange={(e) => setSelectedServiceModel(e.target.value)}
              className="border rounded-md p-2"
            >
              <option value="All">All Services</option>
              <option value="Storage">Storage</option>
              <option value="Container">Container</option>
              <option value="VM">Virtual Machine</option>
            </select>
          </div>
          <div>
            <label className="mr-2 font-medium">Date Range:</label>
            <select 
              value={dateRangeModel} 
              onChange={(e) => setDateRangeModel(Number(e.target.value))}
              className="border rounded-md p-2"
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
            </select>
          </div>
        </div>
      </div>      


      {/* CPU Forecast (Using Predictive Models) */}
      <div className="h-[40vh] w-full bg-white shadow-lg rounded-2xl border p-6">
        <h2 className="text-lg font-semibold text-gray-700">CPU Usage Forecast (Using Predictive Models)</h2>
        {cpuModelForecast.labels.length > 0 && cpuModelForecast.datasets.length > 0 ? (
          <Line
            data={{
              labels: cpuModelForecast.labels.slice(-dateRangeModel),
              datasets: cpuModelForecast.datasets.map(ds => ({
                ...ds,
                data: ds.data.slice(-dateRangeModel)
              }))
            }}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                tooltip: {
                  callbacks: {
                    label: (ctx) => `${ctx.dataset.label}: ${ctx.raw} (x${scaleFactor})`,
                  },
                },
                legend: { position: 'top' },
              },
              scales: {
                y: {
                  ticks: {
                    callback: (val) => `${val} (x${scaleFactor})`,
                  },
                },
              },
            }}
          />
        ) : (
          <div className="text-gray-400 text-center">No model forecast data available.</div>
        )}
      </div>

      {/* Storage Forecast (Using Predictive Models) */}
      <div className="h-[40vh] w-full bg-white shadow-lg rounded-2xl border p-6">
        <h2 className="text-lg font-semibold text-gray-700">Storage Usage Forecast (Using Predictive Models)</h2>
        {storageModelForecast.labels.length > 0 && storageModelForecast.datasets.length > 0 ? (
          <Bar
            data={{
              labels: storageModelForecast.labels.slice(-dateRangeModel),
              datasets: storageModelForecast.datasets.map(ds => ({
                ...ds,
                data: ds.data.slice(-dateRangeModel)
              }))
            }}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                tooltip: {
                  callbacks: {
                    label: (ctx) => `${ctx.dataset.label}: ${ctx.raw} (x${scaleFactor})`,
                  },
                },
                legend: { position: 'top' },
              },
              scales: {
                y: {
                  ticks: {
                    callback: (val) => `${val} (x${scaleFactor})`,
                  },
                },
              },
            }}
          />
        ) : (
          <div className="text-gray-400 text-center">No model forecast data available.</div>
        )}
      </div>



    </div>
  );
};

export default Forecasts;