import React, { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment } from '@react-three/drei';
import * as THREE from 'three';

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
        const pos = state.location?.position || { x: 0, y: 0, z: 0 };
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

// Main Dashboard Component
export default function StadiumDashboard({ gridStates }) {
  return (
    <div className="w-full h-full relative">
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
  );
}