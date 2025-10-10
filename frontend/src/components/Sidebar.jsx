import React from 'react'
import { NavLink } from 'react-router-dom'
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChartLine, faChartBar, faFileAlt, faLightbulb, faTable, faScaleBalanced, faScaleUnbalanced, faComputer, faEye } from "@fortawesome/free-solid-svg-icons";

const Sidebar = () => {

  return (
    <div className='min-h-screen bg-white border-r border-gray-800'>
      <ul className='text-[#3d3d3d] mt-5 text-lg'>
        <NavLink className={({isActive})=>`flex items-center gap-2 py-3.5 px-3 md:min-w-60 cursor-pointer ${isActive ? 'bg-[#F2F3FF] border-r-4 border-[#a7aae9]' : ''}`} to={'/usage-trends'}>
          <FontAwesomeIcon icon={faChartLine} className='text-fuchsia-900'/>
          <p className='hidden md:block'>Usage Trends</p>
        </NavLink>
        <NavLink className={({isActive})=>`flex items-center gap-2 py-3 px-3 md:min-w-60 cursor-pointer ${isActive ? 'bg-[#F2F3FF] border-r-4 border-[#a7aae9]' : ''}`} to={'/forecasts'}>
          <FontAwesomeIcon icon={faChartBar} className='text-neutral-400'/>
          <p className='hidden md:block'>Forecasts</p>
        </NavLink>
        <NavLink className={({isActive})=>`flex items-center gap-2 py-3 px-3 md:min-w-60 cursor-pointer ${isActive ? 'bg-[#F2F3FF] border-r-4 border-[#a7aae9]' : ''}`} to={'/reports'}>
          <FontAwesomeIcon icon={faFileAlt} className='text-indigo-200'/>
          <p className='hidden md:block'>Reports</p>
        </NavLink>
         <NavLink className={({isActive})=>`flex items-center gap-2 py-3 px-3 md:min-w-60 cursor-pointer ${isActive ? 'bg-[#F2F3FF] border-r-4 border-[#a7aae9]' : ''}`} to={'/insights'}>
          <FontAwesomeIcon icon={faLightbulb} className="text-yellow-500"/>
          <p className='hidden md:block'>Insights</p>
        </NavLink>
        <NavLink className={({isActive})=>`flex items-center gap-2 py-3 px-3 md:min-w-60 cursor-pointer ${isActive ? 'bg-[#F2F3FF] border-r-4 border-[#a7aae9]' : ''}`} to={'/capacity-planning'}>
          <FontAwesomeIcon icon={faScaleUnbalanced} className="text-amber-800"/>
          <p className='hidden md:block'>Capacity planning</p>
        </NavLink>
        <NavLink className={({isActive})=>`flex items-center gap-2 py-3 px-3 md:min-w-60 cursor-pointer ${isActive ? 'bg-[#F2F3FF] border-r-4 border-[#a7aae9]' : ''}`} to={'/monitoring'}>
          <FontAwesomeIcon icon={faEye} className="text-blue-500"/>
          <p className='hidden md:block'>Monitoring</p>
        </NavLink>
        <NavLink className={({isActive})=>`flex items-center gap-2 py-3 px-3 md:min-w-60 cursor-pointer ${isActive ? 'bg-[#F2F3FF] border-r-4 border-[#a7aae9]' : ''}`} to={'/featuredata'}>
          <FontAwesomeIcon icon={faTable} className="text-emerald-600"/>
          <p className='hidden md:block'>Feature Data</p>
        </NavLink>

      </ul>
    </div>
  )
}

export default Sidebar
