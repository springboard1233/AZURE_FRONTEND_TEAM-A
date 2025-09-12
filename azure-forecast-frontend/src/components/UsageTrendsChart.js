import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

function UsageTrendsChart() {
  const [data, setData] = useState([]);
  const [region, setRegion] = useState('');

  useEffect(() => {
    axios.get('http://127.0.0.1:5000/api/usage-trends').then(res => {
      setData(res.data);
      if (res.data.length > 0) {
        setRegion(res.data[0].region); // default to first region
      }
    });
  }, []);

  const regions = Array.from(new Set(data.map(d => d.region)));

  const filteredData = data.filter(d => d.region === region);
  const labels = filteredData.map(d => d.date);
  const usageCpuData = filteredData.map(d => d.usage_cpu);

  const chartData = {
    labels,
    datasets: [
      {
        label: `CPU Usage (${region})`,
        data: usageCpuData,
        borderColor: 'blue',
        fill: false,
        tension: 0.1,
      },
    ],
  };

  return (
    <div>
      <h2>Historical Usage Trends</h2>

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

      {filteredData.length > 0 ? (
        <Line data={chartData} />
      ) : (
        <p>No data available for region: {region}</p>
      )}
    </div>
  );
}

export default UsageTrendsChart;
