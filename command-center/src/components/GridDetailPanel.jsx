import React from 'react';

export default function GridDetailPanel({ gridStates }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full overflow-y-auto">
      <h2 className="text-xl font-bold text-white mb-4">Grid Status</h2>
      
      <div className="space-y-3">
        {Object.entries(gridStates).map(([gridId, state]) => {
          const densityLevel = state.crowd_density?.level || 'normal';
          const peopleCount = state.people_count || 0;
          
          const densityColors = {
            low: 'text-green-400',
            normal: 'text-yellow-400',
            moderate: 'text-orange-400',
            high: 'text-red-400',
            critical: 'text-red-600'
          };

          return (
            <div key={gridId} className="bg-gray-700 rounded p-3">
              <div className="flex justify-between items-center">
                <span className="text-white font-semibold">{gridId}</span>
                <span className={`text-2xl font-bold ${densityColors[densityLevel]}`}>
                  {peopleCount}
                </span>
              </div>
              <div className="mt-2 flex justify-between text-sm">
                <span className="text-gray-400">Density:</span>
                <span className={densityColors[densityLevel]}>
                  {densityLevel.toUpperCase()}
                </span>
              </div>
              <div className="mt-1 w-full bg-gray-600 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${densityColors[densityLevel].replace('text-', 'bg-')}`}
                  style={{ width: `${Math.min(100, (peopleCount / 200) * 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}