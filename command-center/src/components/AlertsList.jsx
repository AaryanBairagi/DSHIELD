import React from 'react';

export default function AlertsList({ alerts, onAcknowledge }) {
  const severityColors = {
    critical: 'bg-red-600',
    high: 'bg-orange-500',
    medium: 'bg-yellow-500',
    low: 'bg-blue-500'
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full overflow-y-auto">
      <h2 className="text-xl font-bold text-white mb-4">Active Alerts</h2>
      
      {alerts.length === 0 ? (
        <p className="text-gray-400">No active alerts</p>
      ) : (
        <div className="space-y-2">
          {alerts.map(alert => (
            <div 
              key={alert.id}
              className={`p-3 rounded ${severityColors[alert.severity]} bg-opacity-20 border border-current`}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <span className={`text-xs font-semibold px-2 py-1 rounded ${severityColors[alert.severity]}`}>
                    {alert.severity.toUpperCase()}
                  </span>
                  <p className="text-white font-semibold mt-2">{alert.message}</p>
                  <p className="text-gray-300 text-sm mt-1">Grid: {alert.grid_id}</p>
                  <p className="text-gray-400 text-xs mt-1">
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </p>
                </div>
                {!alert.acknowledged && (
                  <button
                    onClick={() => onAcknowledge(alert.id)}
                    className="ml-2 px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded"
                  >
                    ACK
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}