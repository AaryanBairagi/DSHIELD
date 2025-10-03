# edge-computing/src/main.py
#!/usr/bin/env python3
"""
DSHIELD Edge Processor - Main Application
Handles crowd monitoring, behavior analysis, and emergency detection
"""

import asyncio
import cv2
import json
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

from processors.edge_processor import EdgeProcessor
from processors.mqtt_client import MQTTClient
from processors.device_monitor import DeviceMonitor
from models.people_counter import PeopleCounter
from models.behavior_analyzer import BehaviorAnalyzer
from models.emergency_detector import EmergencyDetector
from utils.config import Config
from utils.logging import setup_logging
from utils.helpers import ensure_directories

class DHSILEDEdgeApp:
    def __init__(self, config_path="config/grid_config.yaml"):
        # Load configuration
        self.config = Config(config_path)
        self.grid_id = self.config.get('grid.id', 'G01')
        
        # Setup logging
        self.logger = setup_logging(self.grid_id)
        self.logger.info(f"Initializing DSHIELD Edge Processor for Grid {self.grid_id}")
        
        # Ensure directories exist
        ensure_directories([
            'data/video_buffer',
            'data/logs',
            'data/analytics',
            'models'
        ])
        
        # Initialize components
        self.camera = None
        self.mqtt_client = None
        self.device_monitor = None
        self.edge_processor = None
        
        # Control flags
        self.running = False
        self.processing_enabled = True
        
        # Performance metrics
        self.frame_count = 0
        self.last_fps_update = time.time()
        self.current_fps = 0
        
    async def initialize(self):
        """Initialize all system components"""
        try:
            # Initialize camera
            await self.setup_camera()
            
            # Initialize MQTT client
            self.mqtt_client = MQTTClient(self.config, self.logger)
            await self.mqtt_client.connect()
            
            # Setup command handler
            self.mqtt_client.set_message_handler(self.handle_mqtt_command)
            
            # Initialize device monitor
            self.device_monitor = DeviceMonitor(self.config, self.logger)
            
            # Initialize edge processor
            self.edge_processor = EdgeProcessor(
                grid_id=self.grid_id,
                config=self.config,
                logger=self.logger,
                mqtt_client=self.mqtt_client
            )
            await self.edge_processor.initialize()
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            raise
    
    async def setup_camera(self):
        """Initialize camera with optimal settings"""
        try:
            # Try different camera indices
            for camera_index in [0, 1, 2]:
                self.camera = cv2.VideoCapture(camera_index)
                if self.camera.isOpened():
                    break
            else:
                raise RuntimeError("No camera found")
            
            # Configure camera settings
            camera_config = self.config.get('camera', {})
            width = camera_config.get('width', 1920)
            height = camera_config.get('height', 1080)
            fps = camera_config.get('fps', 30)
            
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.camera.set(cv2.CAP_PROP_FPS, fps)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
            
            # Verify settings
            actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
            
            self.logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            # Test frame capture
            ret, frame = self.camera.read()
            if not ret or frame is None:
                raise RuntimeError("Failed to capture test frame")
                
        except Exception as e:
            self.logger.error(f"Camera setup failed: {e}")
            raise
    
    async def handle_mqtt_command(self, topic, payload):
        """Handle incoming MQTT commands"""
        try:
            command_data = json.loads(payload.decode())
            command = command_data.get('command')
            
            if command == 'start_processing':
                self.processing_enabled = True
                self.logger.info("Processing enabled via MQTT command")
                
            elif command == 'stop_processing':
                self.processing_enabled = False
                self.logger.info("Processing disabled via MQTT command")
                
            elif command == 'restart':
                self.logger.info("Restart requested via MQTT command")
                await self.restart()
                
            elif command == 'health_check':
                health_data = await self.device_monitor.get_health_status()
                await self.mqtt_client.publish(
                    f"dhsiled/grids/{self.grid_id}/health",
                    json.dumps(health_data)
                )
                
            elif command == 'update_config':
                config_updates = command_data.get('config', {})
                self.config.update(config_updates)
                self.logger.info(f"Configuration updated: {config_updates}")
                
        except Exception as e:
            self.logger.error(f"Error handling MQTT command: {e}")
    
    def update_fps_counter(self):
        """Update FPS calculation"""
        self.frame_count += 1
        current_time = time.time()
        
        if current_time - self.last_fps_update >= 1.0:  # Update every second
            self.current_fps = self.frame_count / (current_time - self.last_fps_update)
            self.frame_count = 0
            self.last_fps_update = current_time
    
    async def process_video_stream(self):
        """Main video processing loop"""
        self.logger.info("Starting video processing loop")
        frame_buffer = []
        buffer_size = 16  # For temporal analysis
        
        try:
            while self.running:
                # Capture frame
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    self.logger.warning("Failed to capture frame, retrying...")
                    await asyncio.sleep(0.1)
                    continue
                
                # Update FPS counter
                self.update_fps_counter()
                
                if self.processing_enabled:
                    # Add frame to buffer for temporal analysis
                    frame_buffer.append(frame.copy())
                    if len(frame_buffer) > buffer_size:
                        frame_buffer.pop(0)
                    
                    # Process current frame
                    try:
                        grid_status = await self.edge_processor.process_frame(
                            frame, 
                            frame_buffer if len(frame_buffer) == buffer_size else None
                        )
                        
                        # Add system metrics to status
                        grid_status.update({
                            'fps': round(self.current_fps, 2),
                            'processing_enabled': self.processing_enabled,
                            'frame_timestamp': datetime.now(timezone.utc).isoformat()
                        })
                        
                        # Publish status via MQTT
                        await self.mqtt_client.publish(
                            f"dhsiled/grids/{self.grid_id}/status",
                            json.dumps(grid_status)
                        )
                        
                    except Exception as e:
                        self.logger.error(f"Frame processing error: {e}")
                
                # Control processing rate (target: 30 FPS)
                await asyncio.sleep(0.033)
                
        except Exception as e:
            self.logger.error(f"Video processing loop error: {e}")
            raise
    
    async def monitor_device_health(self):
        """Monitor device health in background"""
        while self.running:
            try:
                health_data = await self.device_monitor.get_health_status()
                
                # Check for critical issues
                if health_data['cpu_temperature'] > 80:
                    self.logger.warning(f"High CPU temperature: {health_data['cpu_temperature']}°C")
                
                if health_data['memory_usage'] > 90:
                    self.logger.warning(f"High memory usage: {health_data['memory_usage']}%")
                
                if health_data['disk_usage'] > 85:
                    self.logger.warning(f"High disk usage: {health_data['disk_usage']}%")
                
                # Publish health status
                await self.mqtt_client.publish(
                    f"dhsiled/grids/{self.grid_id}/health",
                    json.dumps(health_data)
                )
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
            
            # Wait 30 seconds before next check
            await asyncio.sleep(30)
    
    async def run(self):
        """Main application loop"""
        self.running = True
        
        try:
            # Start background tasks
            tasks = [
                asyncio.create_task(self.process_video_stream()),
                asyncio.create_task(self.monitor_device_health()),
                asyncio.create_task(self.mqtt_client.run())
            ]
            
            self.logger.info("DHSILED Edge Processor started successfully")
            
            # Wait for all tasks
            await asyncio.gather(*tasks)
            
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested by user")
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Shutting down DHSILED Edge Processor...")
        self.running = False
        
        # Cleanup resources
        if self.camera:
            self.camera.release()
        
        if self.mqtt_client:
            await self.mqtt_client.disconnect()
        
        if self.edge_processor:
            await self.edge_processor.cleanup()
        
        self.logger.info("Shutdown complete")
    
    async def restart(self):
        """Restart the application"""
        self.logger.info("Restarting application...")
        await self.shutdown()
        await asyncio.sleep(2)
        await self.initialize()

async def main():
    """Application entry point"""
    app = DHSILEDEdgeApp()
    
    try:
        await app.initialize()
        await app.run()
    except Exception as e:
        print(f"Application failed to start: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))