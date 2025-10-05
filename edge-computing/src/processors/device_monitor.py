#!/usr/bin/env python3
"""
Device Health Monitoring for Raspberry Pi Edge Nodes
"""

import asyncio
import psutil
import time
import json
import subprocess
from typing import Dict, Optional, List
from datetime import datetime, timezone
import os
import logging

class DeviceMonitor:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        
        # Monitoring intervals
        self.monitor_interval = config.get('monitoring.interval', 30)
        
        # Health thresholds
        self.thresholds = config.get('monitoring.thresholds', {
            'cpu_temp': 80.0,
            'cpu_usage': 90.0,
            'memory_usage': 95.0,
            'disk_usage': 90.0,
            'network_errors': 100
        })
        
        # History tracking
        self.health_history = []
        self.max_history_length = 288
        
        # Alert tracking
        self.last_alerts = {}
        self.alert_cooldown = 300
        
        # System info cache
        self.system_info = None
        self.last_system_info_update = 0
        
    async def get_health_status(self) -> Dict:
        """Get comprehensive device health status"""
        try:
            health_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'cpu_temperature': await self._get_cpu_temperature(),
                'cpu_usage': self._get_cpu_usage(),
                'memory_usage': self._get_memory_usage(),
                'disk_usage': self._get_disk_usage(),
                'network_stats': await self._get_network_stats(),
                'uptime': self._get_uptime(),
                'load_average': self._get_load_average(),
                'gpio_status': await self._get_gpio_status(),
                'camera_status': await self._check_camera_status(),
                'system_info': await self._get_system_info()
            }
            
            # Add health assessment
            health_data['health_score'] = self._calculate_health_score(health_data)
            health_data['alerts'] = self._check_health_alerts(health_data)
            
            # Update history
            self._update_health_history(health_data)
            
            return health_data
            
        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            return self._get_error_health_status(str(e))
    
    async def _get_cpu_temperature(self) -> float:
        """Get CPU temperature in Celsius"""
        try:
            temp_sources = [
                '/sys/class/thermal/thermal_zone0/temp',
                '/sys/devices/virtual/thermal/thermal_zone0/temp'
            ]
            
            for temp_file in temp_sources:
                if os.path.exists(temp_file):
                    with open(temp_file, 'r') as f:
                        temp_str = f.read().strip()
                        temp = float(temp_str) / 1000.0
                        return round(temp, 1)
            
            try:
                result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    temp_str = result.stdout.strip().split('=')[1].replace("'C", "")
                    return round(float(temp_str), 1)
            except:
                pass
            
            return 45.0
            
        except Exception as e:
            self.logger.warning(f"Could not read CPU temperature: {e}")
            return 45.0
        
########################################################################
    def _get_cpu_usage(self) -> Dict:
        """Get CPU usage statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            
            return {
                'overall': round(psutil.cpu_percent(interval=None), 1),
                'per_core': [round(core, 1) for core in cpu_percent],
                'core_count': psutil.cpu_count(),
                'frequency': self._get_cpu_frequency()
            }
            
        except Exception as e:
            self.logger.warning(f"Could not read CPU usage: {e}")
            return {'overall': 0.0, 'per_core': [], 'core_count': 4}
    
    def _get_cpu_frequency(self) -> Dict:
        """Get CPU frequency information"""
        try:
            freq = psutil.cpu_freq()
            if freq:
                return {
                    'current': round(freq.current, 1),
                    'min': round(freq.min, 1) if freq.min else 0,
                    'max': round(freq.max, 1) if freq.max else 0
                }
            return {'current': 0, 'min': 0, 'max': 0}
            
        except:
            return {'current': 0, 'min': 0, 'max': 0}
    
    def _get_memory_usage(self) -> Dict:
        """Get memory usage statistics"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percentage': round(memory.percent, 1),
                'swap_total': swap.total,
                'swap_used': swap.used,
                'swap_percentage': round(swap.percent, 1)
            }
            
        except Exception as e:
            self.logger.warning(f"Could not read memory usage: {e}")
            return {'total': 0, 'available': 0, 'used': 0, 'percentage': 0}
    
    def _get_disk_usage(self) -> Dict:
        """Get disk usage statistics"""
        try:
            disk_usage = {}
            
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.mountpoint] = {
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percentage': round((usage.used / usage.total) * 100, 1),
                        'filesystem': partition.fstype
                    }
                except PermissionError:
                    continue
            
            disk_io = psutil.disk_io_counters()
            if disk_io:
                disk_usage['io_stats'] = {
                    'read_count': disk_io.read_count,
                    'write_count': disk_io.write_count,
                    'read_bytes': disk_io.read_bytes,
                    'write_bytes': disk_io.write_bytes
                }
            
            return disk_usage
            
        except Exception as e:
            self.logger.warning(f"Could not read disk usage: {e}")
            return {}
    
    async def _get_network_stats(self) -> Dict:
        """Get network statistics"""
        try:
            net_io = psutil.net_io_counters()
            
            interfaces = {}
            net_if_stats = psutil.net_if_stats()
            
            for interface, stats in net_if_stats.items():
                if interface != 'lo':
                    interfaces[interface] = {
                        'is_up': stats.isup,
                        'duplex': stats.duplex.name if stats.duplex else 'unknown',
                        'speed': stats.speed,
                        'mtu': stats.mtu
                    }
            
            connectivity = await self._test_connectivity()
            
            return {
                'bytes_sent': net_io.bytes_sent if net_io else 0,
                'bytes_recv': net_io.bytes_recv if net_io else 0,
                'packets_sent': net_io.packets_sent if net_io else 0,
                'packets_recv': net_io.packets_recv if net_io else 0,
                'errin': net_io.errin if net_io else 0,
                'errout': net_io.errout if net_io else 0,
                'dropin': net_io.dropin if net_io else 0,
                'dropout': net_io.dropout if net_io else 0,
                'interfaces': interfaces,
                'connectivity': connectivity
            }
            
        except Exception as e:
            self.logger.warning(f"Could not read network stats: {e}")
            return {'connectivity': False}
    
    async def _test_connectivity(self) -> bool:
        """Test internet connectivity"""
        try:
            result = await asyncio.create_subprocess_exec(
                'ping', '-c', '1', '-W', '3', '8.8.8.8',
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await result.wait()
            return result.returncode == 0
            
        except:
            return False
    
    def _get_uptime(self) -> Dict:
        """Get system uptime"""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            return {
                'boot_time': datetime.fromtimestamp(boot_time, tz=timezone.utc).isoformat(),
                'uptime_seconds': round(uptime_seconds),
                'uptime_string': self._format_uptime(uptime_seconds)
            }
            
        except Exception as e:
            self.logger.warning(f"Could not read uptime: {e}")
            return {'uptime_seconds': 0, 'uptime_string': 'unknown'}
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def _get_load_average(self) -> List[float]:
        """Get system load average"""
        try:
            if hasattr(os, 'getloadavg'):
                load = os.getloadavg()
                return [round(load[0], 2), round(load[1], 2), round(load[2], 2)]
            return [0.0, 0.0, 0.0]
            
        except:
            return [0.0, 0.0, 0.0]
    
    async def _get_gpio_status(self) -> Dict:
        """Get GPIO status for Raspberry Pi"""
        try:
            return {
                'available': False,
                'pins_used': [],
                'status': 'GPIO library not available'
            }
            
        except Exception as e:
            return {'available': False, 'error': str(e)}
    
    async def _check_camera_status(self) -> Dict:
        """Check camera module status"""
        try:
            result = await asyncio.create_subprocess_exec(
                'vcgencmd', 'get_camera',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                output = stdout.decode().strip()
                status = {}
                for item in output.split():
                    key, value = item.split('=')
                    status[key] = value == '1'
                
                return {
                    'available': status.get('detected', False),
                    'supported': status.get('supported', False),
                    'status': 'detected' if status.get('detected', False) else 'not_detected'
                }
            else:
                return {'available': False, 'status': 'check_failed'}
                
        except Exception as e:
            return {'available': False, 'status': 'unknown', 'error': str(e)}
    
    async def _get_system_info(self) -> Dict:
        """Get system information"""
        current_time = time.time()
        
        if (self.system_info is None or 
            current_time - self.last_system_info_update > 600):
            
            try:
                self.system_info = {
                    'platform': psutil.LINUX if hasattr(psutil, 'LINUX') else 'unknown',
                    'hostname': os.uname().nodename if hasattr(os, 'uname') else 'unknown',
                    'cpu_count_physical': psutil.cpu_count(logical=False),
                    'cpu_count_logical': psutil.cpu_count(logical=True),
                    'memory_total': psutil.virtual_memory().total,
                    'boot_time': psutil.boot_time()
                }
                
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        cpuinfo = f.read()
                        if 'Raspberry Pi' in cpuinfo:
                            for line in cpuinfo.split('\n'):
                                if 'Model' in line:
                                    self.system_info['model'] = line.split(':')[1].strip()
                                elif 'Serial' in line:
                                    self.system_info['serial'] = line.split(':')[1].strip()
                except:
                    pass
                
                self.last_system_info_update = current_time
                
            except Exception as e:
                self.logger.warning(f"Could not get system info: {e}")
                return {}
        
        return self.system_info
    
    def _calculate_health_score(self, health_data: Dict) -> float:
        """Calculate overall health score (0-100)"""
        try:
            score = 100.0
            
            cpu_temp = health_data.get('cpu_temperature', 0)
            if cpu_temp > 70:
                score -= min(30, (cpu_temp - 70) * 2)
            
            cpu_usage = health_data.get('cpu_usage', {}).get('overall', 0)
            if cpu_usage > 80:
                score -= min(20, (cpu_usage - 80) * 1)
            
            memory_usage = health_data.get('memory_usage', {}).get('percentage', 0)
            if memory_usage > 85:
                score -= min(20, (memory_usage - 85) * 1.5)
            
            disk_usage = health_data.get('disk_usage', {})
            for mount, info in disk_usage.items():
                if isinstance(info, dict) and info.get('percentage', 0) > 90:
                    score -= 10
            
            if not health_data.get('network_stats', {}).get('connectivity', False):
                score -= 15
            
            if not health_data.get('camera_status', {}).get('available', False):
                score -= 5
            
            return max(0.0, min(100.0, round(score, 1)))
            
        except:
            return 50.0
    
    def _check_health_alerts(self, health_data: Dict) -> List[Dict]:
        """Check for health alerts based on thresholds"""
        alerts = []
        current_time = time.time()
        
        cpu_temp = health_data.get('cpu_temperature', 0)
        if cpu_temp > self.thresholds['cpu_temp']:
            if self._should_send_alert('cpu_temp', current_time):
                alerts.append({
                    'type': 'cpu_temperature',
                    'severity': 'high' if cpu_temp > 85 else 'medium',
                    'value': cpu_temp,
                    'threshold': self.thresholds['cpu_temp'],
                    'message': f'CPU temperature high: {cpu_temp}°C'
                })
        
        memory_usage = health_data.get('memory_usage', {}).get('percentage', 0)
        if memory_usage > self.thresholds['memory_usage']:
            if self._should_send_alert('memory_usage', current_time):
                alerts.append({
                    'type': 'memory_usage',
                    'severity': 'high',
                    'value': memory_usage,
                    'threshold': self.thresholds['memory_usage'],
                    'message': f'Memory usage critical: {memory_usage}%'
                })
        
        disk_usage = health_data.get('disk_usage', {})
        for mount, info in disk_usage.items():
            if isinstance(info, dict):
                usage = info.get('percentage', 0)
                if usage > self.thresholds['disk_usage']:
                    alert_key = f'disk_usage_{mount}'
                    if self._should_send_alert(alert_key, current_time):
                        alerts.append({
                            'type': 'disk_usage',
                            'severity': 'high' if usage > 95 else 'medium',
                            'value': usage,
                            'threshold': self.thresholds['disk_usage'],
                            'mount_point': mount,
                            'message': f'Disk usage high on {mount}: {usage}%'
                        })
        
        return alerts
    
    def _should_send_alert(self, alert_type: str, current_time: float) -> bool:
        """Check if alert should be sent based on cooldown"""
        if alert_type not in self.last_alerts:
            self.last_alerts[alert_type] = current_time
            return True
        
        elapsed = current_time - self.last_alerts[alert_type]
        if elapsed >= self.alert_cooldown:
            self.last_alerts[alert_type] = current_time
            return True
        
        return False
    
    def _update_health_history(self, health_data: Dict):
        """Update health history for trend analysis"""
        history_entry = {
            'timestamp': health_data['timestamp'],
            'cpu_temperature': health_data['cpu_temperature'],
            'cpu_usage': health_data['cpu_usage']['overall'],
            'memory_usage': health_data['memory_usage']['percentage'],
            'health_score': health_data['health_score']
        }
        
        self.health_history.append(history_entry)
        
        if len(self.health_history) > self.max_history_length:
            self.health_history.pop(0)
    
    def get_health_trends(self, hours: int = 24) -> Dict:
        """Get health trends for specified hours"""
        try:
            cutoff_time = time.time() - (hours * 3600)
            
            recent_history = [
                entry for entry in self.health_history
                if datetime.fromisoformat(entry['timestamp']).timestamp() > cutoff_time
            ]
            
            if not recent_history:
                return {
                    'available': False,
                    'message': 'No historical data available'
                }
            
            cpu_temps = [entry['cpu_temperature'] for entry in recent_history]
            cpu_usages = [entry['cpu_usage'] for entry in recent_history]
            memory_usages = [entry['memory_usage'] for entry in recent_history]
            health_scores = [entry['health_score'] for entry in recent_history]
            
            trends = {
                'available': True,
                'period_hours': hours,
                'sample_count': len(recent_history),
                'cpu_temperature': {
                    'current': cpu_temps[-1] if cpu_temps else 0,
                    'average': round(sum(cpu_temps) / len(cpu_temps), 2) if cpu_temps else 0,
                    'min': round(min(cpu_temps), 2) if cpu_temps else 0,
                    'max': round(max(cpu_temps), 2) if cpu_temps else 0,
                    'trend': self._calculate_trend(cpu_temps)
                },
                'cpu_usage': {
                    'current': cpu_usages[-1] if cpu_usages else 0,
                    'average': round(sum(cpu_usages) / len(cpu_usages), 2) if cpu_usages else 0,
                    'min': round(min(cpu_usages), 2) if cpu_usages else 0,
                    'max': round(max(cpu_usages), 2) if cpu_usages else 0,
                    'trend': self._calculate_trend(cpu_usages)
                },
                'memory_usage': {
                    'current': memory_usages[-1] if memory_usages else 0,
                    'average': round(sum(memory_usages) / len(memory_usages), 2) if memory_usages else 0,
                    'min': round(min(memory_usages), 2) if memory_usages else 0,
                    'max': round(max(memory_usages), 2) if memory_usages else 0,
                    'trend': self._calculate_trend(memory_usages)
                },
                'health_score': {
                    'current': health_scores[-1] if health_scores else 0,
                    'average': round(sum(health_scores) / len(health_scores), 2) if health_scores else 0,
                    'trend': self._calculate_trend(health_scores)
                }
            }
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error calculating health trends: {e}")
            return {'available': False, 'error': str(e)}
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values"""
        if len(values) < 2:
            return 'stable'
        
        split_point = len(values) // 2
        older_avg = sum(values[:split_point]) / split_point
        recent_avg = sum(values[split_point:]) / (len(values) - split_point)
        
        diff_percent = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        
        if diff_percent > 10:
            return 'increasing'
        elif diff_percent < -10:
            return 'decreasing'
        else:
            return 'stable'
    
    def _get_error_health_status(self, error_message: str) -> Dict:
        """Create error health status"""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'error',
            'error_message': error_message,
            'cpu_temperature': 0,
            'cpu_usage': {'overall': 0},
            'memory_usage': {'percentage': 0},
            'disk_usage': {},
            'network_stats': {},
            'uptime': {'uptime_seconds': 0},
            'health_score': 0,
            'alerts': []
        }