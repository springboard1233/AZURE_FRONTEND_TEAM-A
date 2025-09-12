import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

function ForecastChart() {
  const [data, setData] = useState([]);
  const [region, setRegion] = useState('');
  const [metric, setMetric] = useState('usage_cpu');

  useEffect(() => {
    axios.get('http://127.0.0.1:5000/api/forecast').then((res) => {
      setData(res.data);
      if (res.data.length > 0) {
        setRegion(res.data[0].region); // default region
        setMetric(res.data[0].metric); // default metric
      }
    });
  }, []);

  // Unique regions and metrics for dropdowns
  const regions = Array.from(new Set(data.map((d) => d.region)));
  const metrics = Array.from(new Set(data.map((d) => d.metric)));

  // Filter data by selected region and metric
  const filteredData = data.filter((d) => d.region === region && d.metric === metric);

  const labels = filteredData.map((d) => d.date);
  const forecastData = filteredData.map((d) => d.forecast);

  const chartData = {
    labels,
    datasets: [
      {
        label: `Forecast (${region} - ${metric})`,
        data: forecastData,
        backgroundColor: 'orange',
      },
    ],
  };

  return (
    <div>
      <h2>Forecast Results</h2>

      <label>
        Select Region:&nbsp;
        <select value={region} onChange={(e) => setRegion(e.target.value)}>
          {regions.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </label>

      <label style={{ marginLeft: '1rem' }}>
        Select Metric:&nbsp;
        <select value={metric} onChange={(e) => setMetric(e.target.value)}>
          {metrics.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </label>

      {filteredData.length > 0 ? (
        <Bar data={chartData} />
      ) : (
        <p>No forecast data available for selected region and metric.</p>
      )}
    </div>
  );
}

export default ForecastChart;
