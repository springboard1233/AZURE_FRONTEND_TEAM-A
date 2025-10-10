import React from 'react';
import { FaRocket, FaBrain, FaDatabase, FaLightbulb, FaGem, FaCube } from 'react-icons/fa';

const Header = () => {
  return (
    <div className="relative overflow-hidden bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white">
      {/* Geometric Background Pattern */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute top-0 left-0 w-full h-full">
          {/* Grid Pattern */}
          <div className="grid grid-cols-12 grid-rows-8 h-full w-full">
            {Array.from({ length: 96 }).map((_, i) => (
              <div key={i} className="border border-gray-700 opacity-20"></div>
            ))}
          </div>
        </div>
      </div>

      {/* Floating Tech Elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-10 left-12 w-3 h-3 bg-cyan-400 rounded-full animate-pulse"></div>
        <div className="absolute top-20 right-20 w-2 h-2 bg-emerald-400 rounded-full animate-ping"></div>
        <div className="absolute bottom-16 left-1/4 w-4 h-4 bg-amber-400 rounded-full animate-bounce"></div>
        <div className="absolute bottom-24 right-1/3 w-2 h-2 bg-pink-400 rounded-full animate-pulse"></div>
        <div className="absolute top-1/2 left-8 w-1 h-1 bg-violet-400 rounded-full animate-ping"></div>
        <div className="absolute top-1/3 right-12 w-3 h-3 bg-rose-400 rounded-full animate-bounce"></div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 py-1 px-4">
        <div className="max-w-7xl mx-auto">
          {/* Header Top Section */}
          <div className="flex flex-col lg:flex-row items-center justify-between mb-4">
            {/* Logo & Branding */}
            <div className="flex items-center space-x-4 mb-6 lg:mb-0">
              <div className="relative">
                <div className="w-16 h-16 bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-2xl transform rotate-3 hover:rotate-0 transition-transform duration-300">
                  <FaRocket className="text-2xl text-white" />
                </div>
                <div className="absolute -top-1 -right-1 w-6 h-6 bg-gradient-to-r from-emerald-400 to-cyan-400 rounded-full flex items-center justify-center">
                  <FaGem className="text-xs text-white" />
                </div>
              </div>
              <div className="text-left">
                <h1 className="text-3xl lg:text-4xl font-black tracking-tight">
                  <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
                    AZURE
                  </span>
                  <span className="text-white ml-2">DEMAND</span>
                </h1>
                <p className="text-gray-400 text-sm font-medium tracking-widest uppercase">
                  Forecasting Platform
                </p>
              </div>
            </div>

            {/* Status Indicators */}
            <div className="flex items-center space-x-6">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse"></div>
                <span className="text-emerald-400 text-sm font-medium">LIVE</span>
              </div>
              <div className="flex items-center space-x-2">
                <FaBrain className="text-purple-400" />
                <span className="text-gray-300 text-sm">AI Active</span>
              </div>
            </div>
          </div>

          {/* Main Description */}
          <div className="text-center mb-1">
            <h2 className="text-xl lg:text-2xl text-gray-300 font-light mb-4 max-w-4xl mx-auto leading-relaxed">
              Next-Generation Cloud Intelligence & 
              <span className="text-cyan-400 font-medium"> Predictive Analytics </span>
              Ecosystem
            </h2>
          </div>



         

        </div>
      </div>

      {/* Bottom Accent Line */}
      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-cyan-400 via-purple-500 to-orange-500"></div>
    </div>
  );
};

export default Header
