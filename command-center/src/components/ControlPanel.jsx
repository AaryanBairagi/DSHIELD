import React from 'react';

export default function ControlPanel({ systemHealth }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h2 className="text-xl font-bold text-white mb-4">System Health</h2>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-700 rounded p-3">
          <p className="text-gray-400 text-sm">Total Grids</p>
          <p className="text-3xl font-bold text-white">{systemHealth.total_grids || 0}</p>
        </div>
        
        <div className="bg-gray-700 rounded p-3">
          <p className="text-gray-400 text-sm">Online Grids</p>
          <p className="text-3xl font-bold text-green-400">{systemHealth.online_grids || 0}</p>
        </div>
        
        <div className="bg-gray-700 rounded p-3">
          <p className="text-gray-400 text-sm">Total People</p>
          <p className="text-3xl font-bold text-blue-400">{systemHealth.total_people || 0}</p>
        </div>
        
        <div className="bg-gray-700 rounded p-3">
          <p className="text-gray-400 text-sm">Critical Alerts</p>
          <p className="text-3xl font-bold text-red-400">{systemHealth.critical_alerts || 0}</p>
        </div>
      </div>
    </div>
  );
}