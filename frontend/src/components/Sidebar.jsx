import React from 'react'
import { NavLink } from 'react-router-dom'

const Sidebar = () => {

  return (
    <div className='min-h-screen bg-white border-r border-gray-800'>
      <ul className='text-[#3d3d3d] mt-5 text-lg'>
        <NavLink className={({isActive})=>`flex items-center gap-2 py-3.5 px-3 md:min-w-60 cursor-pointer ${isActive ? 'bg-[#F2F3FF] border-r-4 border-[#a7aae9]' : ''}`} to={'/usage-trends'}>
          <p className='hidden md:block'>Usage Trends</p>
        </NavLink>
        <NavLink className={({isActive})=>`flex items-center gap-2 py-3 px-3 md:min-w-60 cursor-pointer ${isActive ? 'bg-[#F2F3FF] border-r-4 border-[#a7aae9]' : ''}`} to={'/forecasts'}>
          <p className='hidden md:block'>Forecasts</p>
        </NavLink>
        <NavLink className={({isActive})=>`flex items-center gap-2 py-3 px-3 md:min-w-60 cursor-pointer ${isActive ? 'bg-[#F2F3FF] border-r-4 border-[#a7aae9]' : ''}`} to={'/reports'}>
          <p className='hidden md:block'>Reports</p>
        </NavLink>
      </ul>
    </div>
  )
}

export default Sidebar
