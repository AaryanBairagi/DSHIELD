#!/usr/bin/env python3
"""
Configuration management for DHSILED Edge Computing
"""

import yaml
import os
from pathlib import Path
from typing import Any, Dict, Optional
import json

class Config:
    """Configuration manager for DHSILED edge processor"""
    
    def __init__(self, config_path: str = "config/grid_config.yaml"):
        self.config_path = config_path
        self.config_data = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            if not os.path.exists(self.config_path):
                print(f"Warning: Config file not found at {self.config_path}")
                print("Using default configuration")
                self.config_data = self._get_default_config()
                return
            
            with open(self.config_path, 'r') as f:
                self.config_data = yaml.safe_load(f)
            
            print(f"Configuration loaded from {self.config_path}")
            
            # Load environment variable overrides
            self._load_env_overrides()
            
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print("Using default configuration")
            self.config_data = self._get_default_config()
    
    def _load_env_overrides(self):
        """Load configuration overrides from environment variables"""
        # MQTT host override
        if mqtt_host := os.getenv('DHSILED_MQTT_HOST'):
            self.config_data.setdefault('mqtt', {})['host'] = mqtt_host
        
        # MQTT port override
        if mqtt_port := os.getenv('DHSILED_MQTT_PORT'):
            self.config_data.setdefault('mqtt', {})['port'] = int(mqtt_port)
        
        # Grid ID override
        if grid_id := os.getenv('DHSILED_GRID_ID'):
            self.config_data.setdefault('grid', {})['id'] = grid_id
        
        # Log level override
        if log_level := os.getenv('DHSILED_LOG_LEVEL'):
            self.config_data.setdefault('logging', {})['level'] = log_level
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        Example: config.get('mqtt.host', 'localhost')
        """
        keys = key.split('.')
        value = self.config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation
        Example: config.set('mqtt.host', '192.168.1.100')
        """
        keys = key.split('.')
        config = self.config_data
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
    
    def update(self, updates: Dict):
        """Update multiple configuration values"""
        self._deep_update(self.config_data, updates)
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """Recursively update nested dictionaries"""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def save_config(self, filepath: str = None):
        """Save current configuration to file"""
        if filepath is None:
            filepath = self.config_path
        
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False, sort_keys=False)
            
            print(f"Configuration saved to {filepath}")
            return True
            
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def to_dict(self) -> Dict:
        """Get configuration as dictionary"""
        return self.config_data.copy()
    
    def to_json(self) -> str:
        """Get configuration as JSON string"""
        return json.dumps(self.config_data, indent=2)
    
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'grid': {
                'id': 'G01',
                'zone_type': 'stand',
                'area_sqm': 750,
                'capacity': 200,
                'location': {
                    'section': 'North Stand',
                    'level': 1,
                    'position': {'x': -75, 'y': 5, 'z': -60}
                }
            },
            'density_thresholds': {
                'normal': 60,
                'moderate': 100,
                'high': 150,
                'critical': 200
            },
            'camera': {
                'device_index': 0,
                'width': 1920,
                'height': 1080,
                'fps': 30,
                'rotation': 0
            },
            'models': {
                'people_counter': 'models/yolov8n.pt',
                'behavior_analyzer': 'models/behavior_lstm.h5',
                'emergency_detector': 'models/emergency_cnn.h5',
                'confidence_threshold': 0.5,
                'sequence_length': 16
            },
            'mqtt': {
                'host': 'localhost',
                'port': 1883,
                'username': None,
                'password': None,
                'ssl': False,
                'keepalive': 60,
                'qos': 1
            },
            'processing': {
                'frame_skip': 0,
                'enable_people_counting': True,
                'enable_behavior_analysis': True,
                'enable_emergency_detection': True
            },
            'storage': {
                'video_buffer_path': 'data/video_buffer',
                'logs_path': 'data/logs',
                'analytics_path': 'data/analytics',
                'retention_hours': 24
            },
            'monitoring': {
                'interval': 30,
                'thresholds': {
                    'cpu_temp': 80.0,
                    'cpu_usage': 90.0,
                    'memory_usage': 95.0,
                    'disk_usage': 90.0
                }
            },
            'logging': {
                'level': 'INFO',
                'console_output': True
            },
            'debug': {
                'enable_mock_models': False,
                'save_debug_images': False,
                'show_preview': False
            }
        }