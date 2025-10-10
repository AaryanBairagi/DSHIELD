import React, { useState, useEffect, useRef } from 'react';
import StadiumDashboard from './components/StadiumDashboard';
import GridDetailPanel from './components/GridDetailPanel';
import AlertsList from './components/AlertsList';
import ControlPanel from './components/ControlPanel';
import WebSocketClient from './services/websocket-client';
import ApiClient from './services/api-client';

export default function App() {
  const [gridStates, setGridStates] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [systemHealth, setSystemHealth] = useState({});
  const [connected, setConnected] = useState(false);
  const wsClient = useRef(null);
  const apiClient = useRef(new ApiClient());

  useEffect(() => {
    // Initialize WebSocket connection
    wsClient.current = new WebSocketClient('ws://localhost:8080');
    
    wsClient.current.on('connected', () => {
      console.log('✓ Connected to WebSocket server');
      setConnected(true);
    });

    wsClient.current.on('disconnected', () => {
      console.log('✗ Disconnected from WebSocket server');
      setConnected(false);
    });

    wsClient.current.on('grid_status', (data) => {
      setGridStates(prev => ({
        ...prev,
        [data.grid_id]: data
      }));
    });

    wsClient.current.on('alert', (data) => {
      setAlerts(prev => [data, ...prev].slice(0, 50));
    });

    wsClient.current.connect();

    // Fetch initial data from API
    loadInitialData();

    // Fetch system health periodically
    const healthInterval = setInterval(() => {
      fetchSystemHealth();
    }, 10000);

    return () => {
      wsClient.current?.disconnect();
      clearInterval(healthInterval);
    };
  }, []);

  const loadInitialData = async () => {
    try {
      const grids = await apiClient.current.getGrids();
      if (grids.success) {
        setGridStates(grids.grids);
      }

      const alertsData = await apiClient.current.getAlerts();
      if (alertsData.success) {
        setAlerts(alertsData.alerts);
      }

      await fetchSystemHealth();
    } catch (error) {
      console.error('Error loading initial data:', error);
    }
  };

  const fetchSystemHealth = async () => {
    try {
      const health = await apiClient.current.getSystemHealth();
      if (health.success) {
        setSystemHealth(health);
      }
    } catch (error) {
      console.error('Error fetching system health:', error);
    }
  };

  const handleAcknowledgeAlert = async (alertId) => {
    try {
      await apiClient.current.acknowledgeAlert(alertId);
      setAlerts(prev => 
        prev.map(alert => 
          alert.id === alertId 
            ? { ...alert, acknowledged: true }
            : alert
        )
      );
    } catch (error) {
      console.error('Error acknowledging alert:', error);
    }
  };

  return (
    <div className="w-screen h-screen bg-gray-900 flex flex-col">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-white">DHSILED Command Center</h1>
            <div className={`flex items-center space-x-2 ${connected ? 'text-green-400' : 'text-red-400'}`}>
              <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'} animate-pulse`}></div>
              <span className="text-sm font-semibold">
                {connected ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="text-gray-400 text-sm">Last Update</p>
              <p className="text-white font-mono">{new Date().toLocaleTimeString()}</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Alerts */}
        <div className="w-80 border-r border-gray-700 p-4">
          <AlertsList alerts={alerts} onAcknowledge={handleAcknowledgeAlert} />
        </div>

        {/* Center - 3D Visualization */}
        <div className="flex-1 relative">
          <StadiumDashboard gridStates={gridStates} />
        </div>

        {/* Right Sidebar - Grid Status & Health */}
        <div className="w-80 border-l border-gray-700 p-4 space-y-4 overflow-y-auto">
          <ControlPanel systemHealth={systemHealth} />
          <GridDetailPanel gridStates={gridStates} />
        </div>
      </div>
    </div>
  );
}