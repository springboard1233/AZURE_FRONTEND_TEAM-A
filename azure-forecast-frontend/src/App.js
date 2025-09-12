import React from 'react';
import UsageTrendsChart from './components/UsageTrendsChart';
import ForecastChart from './components/ForecastChart';
import './styles/Dashboard.css';
import UploadData from './components/UploadData';

function App() {
  return (
    <div className="dashboard-container">
      <h1>Azure Demand Forecast Dashboard</h1>
      <UsageTrendsChart />
      <ForecastChart />
      <UploadData />
    </div>
  );
}
export default App;
