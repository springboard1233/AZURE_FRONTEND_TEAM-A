import React, { useState, useMemo } from 'react';
import { Line, Pie } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Legend, Filler } from 'chart.js';
import { BarChart3, PieChart, AreaChart, FileText } from 'lucide-react';

// Register Chart.js components we will use
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler // Register the Filler plugin for gradient backgrounds
);

// --- REAL DATA SAMPLE ---
// This is a sample from your 'cleaned_merged.csv' data.
const rawData = [
    { date: '2023-01-01', region: 'East US', resource_type: 'VM', usage_cpu: 88, usage_storage: 1959, users_active: 470, economic_index: 104.97, cloud_market_demand: 0.99, holiday: 1 },
    { date: '2023-01-01', region: 'Southeast Asia', resource_type: 'Container', usage_cpu: 77, usage_storage: 1199, users_active: 470, economic_index: 104.97, cloud_market_demand: 0.99, holiday: 1 },
    { date: '2023-01-01', region: 'North Europe', resource_type: 'Storage', usage_cpu: 51, usage_storage: 1715, users_active: 476, economic_index: 104.97, cloud_market_demand: 0.99, holiday: 1 },
    { date: '2023-01-01', region: 'West US', resource_type: 'VM', usage_cpu: 95, usage_storage: 1215, users_active: 214, economic_index: 104.97, cloud_market_demand: 0.99, holiday: 1 },
    { date: '2023-01-02', region: 'East US', resource_type: 'VM', usage_cpu: 92, usage_storage: 1800, users_active: 480, economic_index: 106.48, cloud_market_demand: 1.15, holiday: 0 },
    { date: '2023-01-02', region: 'Southeast Asia', resource_type: 'Container', usage_cpu: 85, usage_storage: 1300, users_active: 460, economic_index: 106.48, cloud_market_demand: 1.15, holiday: 0 },
    { date: '2023-01-03', region: 'North Europe', resource_type: 'VM', usage_cpu: 70, usage_storage: 1600, users_active: 450, economic_index: 97.66, cloud_market_demand: 0.98, holiday: 0 },
    { date: '2023-01-03', region: 'West US', resource_type: 'Storage', usage_cpu: 60, usage_storage: 1400, users_active: 300, economic_index: 97.66, cloud_market_demand: 0.98, holiday: 0 },
    { date: '2023-01-04', region: 'East US', resource_type: 'Storage', usage_cpu: 85, usage_storage: 2100, users_active: 490, economic_index: 115.79, cloud_market_demand: 1.08, holiday: 0 },
    { date: '2023-01-05', region: 'Southeast Asia', resource_type: 'VM', usage_cpu: 52, usage_storage: 1100, users_active: 410, economic_index: 95.31, cloud_market_demand: 1.05, holiday: 0 },
    { date: '2023-01-06', region: 'North Europe', resource_type: 'Container', usage_cpu: 78, usage_storage: 1550, users_active: 430, economic_index: 98.12, cloud_market_demand: 1.02, holiday: 0 },
    { date: '2023-01-07', region: 'West US', resource_type: 'VM', usage_cpu: 65, usage_storage: 1350, users_active: 350, economic_index: 102.42, cloud_market_demand: 0.81, holiday: 1 },
    { date: '2023-01-08', region: 'East US', resource_type: 'Container', usage_cpu: 89, usage_storage: 1900, users_active: 500, economic_index: 82.75, cloud_market_demand: 0.94, holiday: 1 },
    { date: '2023-01-09', region: 'Southeast Asia', resource_type: 'Storage', usage_cpu: 75, usage_storage: 1250, users_active: 440, economic_index: 89.87, cloud_market_demand: 1.03, holiday: 0 },
    { date: '2023-01-10', region: 'North Europe', resource_type: 'VM', usage_cpu: 91, usage_storage: 1850, users_active: 470, economic_index: 90.92, cloud_market_demand: 0.86, holiday: 0 }
];

// --- Data Processing Hook ---
const useProcessedData = (data) => {
    return useMemo(() => {
        // 1. Process for Usage Trends (CPU)
        const dailyCpuUsage = data.reduce((acc, curr) => {
            acc[curr.date] = (acc[curr.date] || 0) + curr.usage_cpu;
            return acc;
        }, {});
        const usageTrendsData = {
            labels: Object.keys(dailyCpuUsage).sort(),
            cpuUsage: Object.values(dailyCpuUsage),
        };

        // 2. Process for Storage Consumption
        const regionalStorage = data.reduce((acc, curr) => {
            acc[curr.region] = (acc[curr.region] || 0) + curr.usage_storage;
            return acc;
        }, {});
        const storageConsumptionData = {
            labels: Object.keys(regionalStorage),
            datasets: [{
                label: 'Storage (GB)',
                data: Object.values(regionalStorage),
                backgroundColor: ['#0078D4', '#50E3C2', '#F5A623', '#D0021B'],
                borderColor: '#ffffff',
                borderWidth: 2,
            }]
        };

        // 3. Process for External Factors Table
        const externalFactorsData = [...new Map(data.map(item => [item['date'], item])).values()]
            .slice(0, 10);

        return { usageTrendsData, storageConsumptionData, externalFactorsData };
    }, [data]);
};


// --- Reusable Components ---
const Sidebar = ({ activeView, setActiveView }) => {
  const navItems = [
    { name: 'Usage Trends', icon: <BarChart3 size={20} /> },
    { name: 'Storage', icon: <PieChart size={20} /> },
    { name: 'Forecast', icon: <AreaChart size={20} /> },
    { name: 'Reports', icon: <FileText size={20} /> },
  ];
  return (
    <div className="w-64 h-screen bg-[#1e293b] text-white flex flex-col fixed shadow-lg">
      <div className="p-5 text-2xl font-bold border-b border-gray-700 flex items-center gap-3">
        <svg className="w-8 h-8 text-blue-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M1.5 13.5h1.938c.323 0 .633-.135.855-.371l2.42-2.584a3.5 3.5 0 014.574 0l2.42 2.584c.222.236.532.371.855.371H22.5v1.5h-1.938a2.001 2.001 0 01-1.562-.79L16.58 10.5a2 2 0 00-2.616 0l-2.42 2.584a2 2 0 01-1.562.79H1.5v-1.5zM1.5 9h1.938c.323 0 .633-.135.855-.371l2.42-2.584a3.5 3.5 0 014.574 0l2.42 2.584c.222.236.532.371.855.371H22.5V10.5h-1.938a2.001 2.001 0 01-1.562-.79L16.58 6a2 2 0 00-2.616 0l-2.42 2.584a2 2 0 01-1.562.79H1.5V9z"/></svg>
        <span>Azure Demand</span>
      </div>
      <nav className="mt-6 flex-1">
        {navItems.map(item => (
          <a
            key={item.name}
            href="#"
            onClick={() => setActiveView(item.name)}
            className={`flex items-center gap-4 py-3 px-5 mx-3 my-1 rounded-lg text-lg transition-all duration-200 ease-in-out ${
              activeView === item.name
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-gray-300 hover:bg-gray-700/50 hover:text-white'
            }`}
          >
            {item.icon}
            <span>{item.name}</span>
          </a>
        ))}
      </nav>
    </div>
  );
};

const Header = () => (
  <header className="py-5 px-8 bg-white border-b border-gray-200">
    <h1 className="text-3xl font-bold text-gray-800">Azure Demand Forecasting & Capacity Optimization</h1>
    <p className="mt-1 text-sm text-green-600 font-semibold flex items-center">
        <span className="inline-block w-2.5 h-2.5 mr-2 bg-green-500 rounded-full animate-pulse"></span>
        Status: ready
    </p>
  </header>
);

const Card = ({ children, title, className }) => (
    <div className={`bg-white rounded-xl shadow-md p-6 mt-6 transition-shadow hover:shadow-lg ${className}`}>
        {title && <h2 className="text-2xl font-bold text-gray-700 mb-4">{title}</h2>}
        {children}
    </div>
);


// --- Page Components ---
const UsageTrends = ({ data }) => {
    const lineChartData = {
        labels: data.labels,
        datasets: [
            {
                label: 'CPU Usage',
                data: data.cpuUsage,
                borderColor: '#0078D4',
                backgroundColor: (context) => {
                    const ctx = context.chart.ctx;
                    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
                    gradient.addColorStop(0, 'rgba(0, 120, 212, 0.3)');
                    gradient.addColorStop(1, 'rgba(0, 120, 212, 0)');
                    return gradient;
                },
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#0078D4',
                pointBorderColor: '#fff',
                pointHoverRadius: 7,
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: '#0078D4',
            },
        ],
    };

    return (
        <div>
            <Card title="CPU Usage Trends">
                <div className="h-80">
                    <Line data={lineChartData} options={{ maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } } } }} />
                </div>
            </Card>
            <Card title="Detailed Daily Usage">
                 <table className="w-full text-left">
                    <thead>
                        <tr className="border-b">
                            <th className="p-3 font-semibold text-gray-600">Date</th>
                            <th className="p-3 font-semibold text-gray-600">Total CPU Usage</th>
                            <th className="p-3 font-semibold text-gray-600">Usage Bar</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.labels.map((date, i) => (
                            <tr key={date} className="border-b border-gray-100 hover:bg-gray-50">
                                <td className="p-3">{date}</td>
                                <td className="p-3 font-medium">{data.cpuUsage[i]}</td>
                                <td className="p-3">
                                    <div className="w-full bg-gray-200 rounded-full h-4">
                                        <div className="bg-blue-500 h-4 rounded-full" style={{ width: `${data.cpuUsage[i]/2}%` }}></div>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </Card>
        </div>
    );
};

const Storage = ({ data }) => {
    const pieChartData = {
        labels: data.labels,
        datasets: data.datasets,
    };

    return (
        <Card title="Storage Consumption by Region">
            <p className="text-gray-500 mb-6">(Data processed from dummy dataset)</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
                <div className="h-80 w-80 mx-auto">
                    <Pie data={pieChartData} options={{ maintainAspectRatio: false, plugins: { legend: { position: 'top' } } }} />
                </div>
                <div>
                    <ul className="text-lg space-y-3">
                        {data.labels.map((region, i) => (
                            <li key={region} className="flex items-center p-2 rounded-md hover:bg-gray-100">
                                <span className="inline-block w-4 h-4 mr-3 rounded-full" style={{backgroundColor: data.datasets[0].backgroundColor[i]}}></span>
                                {region}: <strong className="ml-auto">{data.datasets[0].data[i]} GB</strong>
                            </li>
                        ))}
                    </ul>
                </div>
            </div>
        </Card>
    );
};

const Forecast = ({ data }) => (
    <Card title="External Factors Influencing Demand">
        <table className="w-full text-left">
            <thead className="bg-gray-50">
                <tr className="border-b">
                    <th className="p-3 font-semibold text-gray-600">Date</th>
                    <th className="p-3 font-semibold text-gray-600">Economic Index</th>
                    <th className="p-3 font-semibold text-gray-600">Cloud Market Demand</th>
                    <th className="p-3 font-semibold text-gray-600">Holiday</th>
                </tr>
            </thead>
            <tbody>
                {data.map((row, i) => (
                    <tr key={i} className="border-b hover:bg-gray-50">
                        <td className="p-3">{row.date}</td>
                        <td className="p-3">{row.economic_index}</td>
                        <td className="p-3">{row.cloud_market_demand}</td>
                        <td className="p-3">{row.holiday === 1 ? 'Yes' : 'No'}</td>
                    </tr>
                ))}
            </tbody>
        </table>
    </Card>
);

const Reports = () => (
    <div className="mt-6 border-2 border-dashed border-gray-300 rounded-xl p-16 text-center bg-gray-50">
        <FileText size={48} className="mx-auto text-gray-400 mb-4" />
        <p className="text-xl font-semibold text-gray-700">Capacity recommendations and export features are coming soon.</p>
        <p className="text-gray-500 mt-2">You will be able to generate insights and download reports in the next milestone.</p>
    </div>
);


// --- Main App Component ---
function App() {
  const [activeView, setActiveView] = useState('Usage Trends');
  const { usageTrendsData, storageConsumptionData, externalFactorsData } = useProcessedData(rawData);

  const renderView = () => {
    switch (activeView) {
      case 'Usage Trends': return <UsageTrends data={usageTrendsData} />;
      case 'Storage': return <Storage data={storageConsumptionData} />;
      case 'Forecast': return <Forecast data={externalFactorsData} />;
      case 'Reports': return <Reports />;
      default: return <UsageTrends data={usageTrendsData} />;
    }
  };

  return (
    <div className="flex bg-gray-50 font-sans min-h-screen">
      <Sidebar activeView={activeView} setActiveView={setActiveView} />
      <main className="flex-1 ml-64">
        <Header />
        <div className="p-8">
          {renderView()}
        </div>
      </main>
    </div>
  );
}

export default App;
