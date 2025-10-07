import React, { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment } from '@react-three/drei';
import * as THREE from 'three';
import WebSocketClient from './services/websocket-client';
import ApiClient from './services/api-client';

// Stadium 3D Model Component
function StadiumModel({ gridStates }) {
    const groupRef = useRef();

    return (
    <group ref={groupRef}>
      {/* Stadium base structure */}
      <mesh position={[0, -2, 0]} receiveShadow>
        <cylinderGeometry args={[100, 100, 1, 64]} />
        <meshStandardMaterial color="#2a5934" />
      </mesh>

      {/* Grid zones */}
      {Object.entries(gridStates).map(([gridId, state]) => {
        const pos = state.position || { x: 0, y: 0, z: 0 };
        const densityLevel = state.crowd_density?.level || 'normal';
        
        // Color based on density
        const colors = {
          low: '#4ade80',
          normal: '#fbbf24',
          moderate: '#fb923c',
          high: '#f87171',
          critical: '#dc2626'
        };
        
        const color = colors[densityLevel] || colors.normal;
        const height = Math.max(2, (state.people_count || 0) / 10);

        return (
          <mesh 
            key={gridId} 
            position={[pos.x, pos.y + height/2, pos.z]}
            castShadow
          >
            <boxGeometry args={[25, height, 30]} />
            <meshStandardMaterial 
              color={color}
              transparent
              opacity={0.7}
            />
          </mesh>
        );
      })}
    </group>
  );
}

// Alert Panel Component
function AlertPanel({ alerts, onAcknowledge }) {
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

// Grid Status Panel Component
function GridStatusPanel({ gridStates }) {
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

// System Health Component
function SystemHealth({ health }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h2 className="text-xl font-bold text-white mb-4">System Health</h2>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-700 rounded p-3">
          <p className="text-gray-400 text-sm">Total Grids</p>
          <p className="text-3xl font-bold text-white">{health.total_grids || 0}</p>
        </div>
        
        <div className="bg-gray-700 rounded p-3">
          <p className="text-gray-400 text-sm">Online Grids</p>
          <p className="text-3xl font-bold text-green-400">{health.online_grids || 0}</p>
        </div>
        
        <div className="bg-gray-700 rounded p-3">
          <p className="text-gray-400 text-sm">Total People</p>
          <p className="text-3xl font-bold text-blue-400">{health.total_people || 0}</p>
        </div>
        
        <div className="bg-gray-700 rounded p-3">
          <p className="text-gray-400 text-sm">Critical Alerts</p>
          <p className="text-3xl font-bold text-red-400">{health.critical_alerts || 0}</p>
        </div>
      </div>
    </div>
  );
}

// Main App Component
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
          <AlertPanel alerts={alerts} onAcknowledge={handleAcknowledgeAlert} />
        </div>

        {/* Center - 3D Visualization */}
        <div className="flex-1 relative">
          <Canvas shadows>
            <PerspectiveCamera makeDefault position={[0, 100, 150]} />
            <OrbitControls 
              enableDamping
              dampingFactor={0.05}
              minDistance={50}
              maxDistance={300}
            />
            
            {/* Lighting */}
            <ambientLight intensity={0.5} />
            <directionalLight 
              position={[50, 100, 50]} 
              intensity={1}
              castShadow
            />
            <hemisphereLight intensity={0.5} />

            {/* Stadium Model */}
            <StadiumModel gridStates={gridStates} />

            {/* Environment */}
            <Environment preset="night" />
          </Canvas>

          {/* Overlay Info */}
          <div className="absolute top-4 left-4 bg-gray-800 bg-opacity-90 rounded-lg p-4 text-white">
            <h3 className="font-bold mb-2">Controls</h3>
            <p className="text-sm text-gray-300">🖱️ Left Click + Drag: Rotate</p>
            <p className="text-sm text-gray-300">🖱️ Right Click + Drag: Pan</p>
            <p className="text-sm text-gray-300">🖱️ Scroll: Zoom</p>
          </div>
        </div>

        {/* Right Sidebar - Grid Status & Health */}
        <div className="w-80 border-l border-gray-700 p-4 space-y-4 overflow-y-auto">
          <SystemHealth health={systemHealth} />
          <GridStatusPanel gridStates={gridStates} />
        </div>
      </div>
    </div>
  );
}