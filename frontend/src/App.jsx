import React from 'react'
import { Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import Sidebar from './components/Sidebar'
import UsageTrends from './pages/UsageTrends'
import Forecasts from './pages/Forecasts'
import Reports from './pages/Reports'
import Header from './components/Header'
import {Chart as ChartJS} from "chart.js/auto"
import Footer from './components/Footer'

const App = () => {
  return (
    <div className='bg-[#F8F9FD]'>
      <Header/>
      <div className='flex items-start'>
        <Sidebar/>
        <div className='flex-1 p-4'>
          <Routes>
            <Route path='/' element={<Home/>}/>
            <Route path='/usage-trends' element={<UsageTrends/>}/>
            <Route path='/forecasts' element={<Forecasts/>}/>
            <Route path='/reports' element={<Reports/>}/>
          </Routes>
        </div>
      </div>
      <Footer/>
    </div>
  )
}

export default App

