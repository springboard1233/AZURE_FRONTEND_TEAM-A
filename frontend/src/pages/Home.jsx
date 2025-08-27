import React from 'react'
import { Line } from 'react-chartjs-2'
import cpu_usage from "../data/cpu_usage.json"

const Home = () => {
  return (
    <div className="p-6">
      {/* Title + Intro */}
      

      {/* Stat Cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white shadow-md rounded-xl p-4">
          <h2 className="text-lg font-semibold">Avg CPU Usage</h2>
          <p className="text-2xl text-blue-600">78%</p>
        </div>
        <div className="bg-white shadow-md rounded-xl p-4">
          <h2 className="text-lg font-semibold">Total Storage</h2>
          <p className="text-2xl text-green-600">120 TB</p>
        </div>
        <div className="bg-white shadow-md rounded-xl p-4">
          <h2 className="text-lg font-semibold">Top Region</h2>
          <p className="text-2xl text-purple-600">East US</p>
        </div>
      </div>

      {/* Small Chart */}
      <div className= "h-[40vh] bg-white shadow-md rounded-xl p-6">
        <h2 className="text-xl font-semibold">Last 7 Days CPU Usage</h2>
        <Line
          data={{
            labels: cpu_usage.map((d) => d.date),
            datasets: [
              {
                label: "East US",
                data: cpu_usage.map((d) => d.eastUS),
                borderColor: "#064FF0",
              },
              {
                label: "West US",
                data: cpu_usage.map((d) => d.westUS),
                borderColor: "#FF3030",
              },
            ],
          }}
        />
      </div>
    </div>
  )
}

export default Home
