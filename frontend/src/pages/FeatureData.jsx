import React, { useEffect, useState } from "react";
import { FaSearch, FaCalendarAlt, FaGlobe } from "react-icons/fa";

const FeatureData = () => {
  const [data, setData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [columns, setColumns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchDate, setSearchDate] = useState("");
  const [selectedRegion, setSelectedRegion] = useState("All");
  const [regions, setRegions] = useState([]);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/features")
      .then((res) => res.json())
      .then((result) => {
        const fetchedData = result.data || [];
        setData(fetchedData);
        setFilteredData(fetchedData);
        setColumns(result.columns || []);
        
        // Extract unique regions
        const uniqueRegions = [...new Set(fetchedData.map(row => row.region).filter(Boolean))];
        setRegions(uniqueRegions);
        
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to fetch feature data");
        setLoading(false);
      });
  }, []);

  // Filter data based on search criteria
  useEffect(() => {
    let filtered = data;

    // Filter by date
    if (searchDate) {
      filtered = filtered.filter(row => {
        const rowDate = row.date;
        if (rowDate) {
          // Handle different date formats
          const formattedRowDate = new Date(rowDate).toISOString().split('T')[0];
          return formattedRowDate === searchDate;
        }
        return false;
      });
    }

    // Filter by region
    if (selectedRegion !== "All") {
      filtered = filtered.filter(row => row.region === selectedRegion);
    }

    setFilteredData(filtered);
  }, [data, searchDate, selectedRegion]);

  if (loading) return <div className="text-center py-8">Loading feature data...</div>;
  if (error) return <div className="text-red-600 text-center py-8">{error}</div>;

  return (
    <div className="max-w-[1500px] border rounded-xl shadow-lg bg-white p-4">
      <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">Feature Engineered Dataset</h2>
      
      {/* Filter Controls */}
      <div className="mb-6 bg-gray-50 p-4 rounded-lg border">
        <div className="flex flex-wrap gap-4 items-center justify-center">
          {/* Date Search */}
          <div className="flex items-center gap-2">
            <FaCalendarAlt className="text-blue-600" />
            <label className="font-medium text-gray-700">Filter by Date:</label>
            <input
              type="date"
              value={searchDate}
              onChange={(e) => setSearchDate(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          {/* Region Dropdown */}
          <div className="flex items-center gap-2">
            <FaGlobe className="text-green-600" />
            <label className="font-medium text-gray-700">Filter by Region:</label>
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="All">All Regions</option>
              {regions.map(region => (
                <option key={region} value={region}>{region}</option>
              ))}
            </select>
          </div>
          
          {/* Clear Filters */}
          <button
            onClick={() => {
              setSearchDate("");
              setSelectedRegion("All");
            }}
            className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-md font-medium transition-colors flex items-center gap-2"
          >
            <FaSearch />
            Clear Filters
          </button>
        </div>
        
        {/* Results Count */}
        <div className="mt-3 text-center">
          <span className="text-sm text-gray-600">
            Showing <span className="font-bold text-blue-600">{filteredData.length}</span> of <span className="font-bold">{data.length}</span> records
          </span>
        </div>
      </div>

      {/* Data Table */}
      <div className="overflow-auto max-h-[600px] border rounded-lg">
        <table className="min-w-[600px] w-full border-collapse">
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-3 py-2 bg-blue-50 text-blue-700 font-semibold border-b border-gray-200 sticky top-0 z-10"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredData.map((row, i) => (
              <tr
                key={i}
                className="hover:bg-blue-100 transition-colors duration-150"
              >
                {columns.map((col) => (
                  <td
                    key={col}
                    className="px-3 py-2 border-b border-gray-100 text-sm whitespace-nowrap"
                  >
                    {col === "holiday"
                      ? row[col] === true || row[col] === 1
                        ? "true"
                        : row[col] === false || row[col] === 0
                          ? "false"
                          : row[col]
                      : row[col]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default FeatureData;
