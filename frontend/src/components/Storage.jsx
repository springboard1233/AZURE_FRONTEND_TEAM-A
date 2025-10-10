import React,{useState,useEffect} from 'react'
import { Bar } from 'react-chartjs-2'
import { defaults } from 'chart.js'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
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

const StorageUsage = () => {

  const [storageData, setStorageData] = useState([])
  const [region, setRegion] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/usage-trends")
      .then((res) => res.json())
      .then((data) => {
        setStorageData(data.series);
        if (data.regions && data.regions.length) setRegion(data.regions[0]);
      })
      .catch((err) => console.error("Error fetching Storage usage: ", err));
  }, []);

  const regions = storageData.map(d => d.region);
  const allData = storageData.find(d => d.region === region)?.data || [];
  
  // Filter by date range if both are selected
  const filtered = allData.filter((d) => {
    if (!startDate && !endDate) return true;
    const dDate = new Date(d.date);
    const start = startDate ? new Date(startDate) : null;
    const end = endDate ? new Date(endDate) : null;

    if (start && dDate < start) return false;
    if (end && dDate > end) return false;
    return true;
  });


  return (
    <div className="flex flex-col items-center p-4">
      <div className='mb-4 flex gap-4 items-center'>
        <div>
          <label className='mr-2 font-medium'>Choose Region:</label>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className='border rounded-md p-1'
          >
            {regions.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>
        <div>
          <label className='mr-2 font-medium'>Start Date:</label>
          <input 
            type="date" 
            value={startDate} 
            onChange={(e) => setStartDate(e.target.value)}
            className='border rounded-md p-1'
          />
        </div>
        <div>
          <label className='mr-2 font-medium'>End Date:</label>
          <input 
            type="date" 
            value={endDate} 
            onChange={(e) => setEndDate(e.target.value)}
            className='border rounded-md p-1'
          />
        </div>
      </div>

      <div className="h-[40vh] w-full max-w-4xl bg-white shadow-lg rounded-2xl border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-700 text-center">
          ({region}) Storage Usage Trends
        </h2>
        <Bar
          data={{
            labels: filtered.map((d) => d.date),
            datasets: [
              {
                label: `${region} Storage Usage`,
                data: filtered.map((d) => d.storage_percent ?? 0), // fallback 0 if null
                backgroundColor: "rgba(151, 220, 247, 0.5)",
                borderColor: "#0ea5e9",
                borderWidth: 1,
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
                  font: { size: 14 },
                },
              },
              tooltip: {
                backgroundColor: "#1f2937",
                titleColor: "#f9fafb",
                bodyColor: "#f9fafb",
              },
            },
            scales: {
              x: {
                grid: { color: "rgba(209, 213, 219, 0.3)" },
                ticks: { color: "#4b5563" },
              },
              y: {
                grid: { color: "rgba(209, 213, 219, 0.3)" },
                ticks: { color: "#4b5563" },
              },
            },
          }}
        />
      </div>
    </div>
  )
}

export default StorageUsage

