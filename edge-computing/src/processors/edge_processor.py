#!/usr/bin/env python3
"""
Core edge processing logic for crowd monitoring and analysis
"""

import cv2
import numpy as np
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import asyncio

from models.people_counter import PeopleCounter
from models.behavior_analyzer import BehaviorAnalyzer
from models.emergency_detector import EmergencyDetector
from utils.helpers import save_frame, calculate_density, generate_alert_id

class EdgeProcessor:
    def __init__(self, grid_id: str, config, logger, mqtt_client):
        self.grid_id = grid_id
        self.config = config
        self.logger = logger
        self.mqtt_client = mqtt_client
        
        # Grid configuration
        self.grid_area = config.get('grid.area_sqm', 750)
        self.density_thresholds = config.get('grid.density_thresholds', {
            'normal': 60,
            'moderate': 100,
            'high': 150,
            'critical': 200
        })
        
        # Models
        self.people_counter = None
        self.behavior_analyzer = None
        self.emergency_detector = None
        
        # Processing state
        self.last_people_count = 0
        self.alert_cooldown = {}
        self.frame_history = []
        
        # Performance tracking
        self.processing_times = {
            'people_counting': [],
            'behavior_analysis': [],
            'emergency_detection': []
        }
        
    async def initialize(self):
        """Initialize all ML models"""
        try:
            self.logger.info("Loading ML models...")
            
            self.people_counter = PeopleCounter(
                model_path=self.config.get('models.people_counter', 'models/yolov8n.pt'),
                confidence_threshold=self.config.get('models.confidence_threshold', 0.5)
            )
            await self.people_counter.load_model()
            
            self.behavior_analyzer = BehaviorAnalyzer(
                model_path=self.config.get('models.behavior_analyzer', 'models/behavior_lstm.h5'),
                sequence_length=self.config.get('models.sequence_length', 16)
            )
            await self.behavior_analyzer.load_model()
            
            self.emergency_detector = EmergencyDetector(
                model_path=self.config.get('models.emergency_detector', 'models/emergency_cnn.h5')
            )
            await self.emergency_detector.load_model()
            
            self.logger.info("All ML models loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Model initialization failed: {e}")
            raise
    
    async def process_frame(self, frame: np.ndarray, frame_sequence: Optional[List[np.ndarray]] = None) -> Dict:
        """Process a single frame and return grid status"""
        start_time = time.time()
        
        try:
            # 1. People counting
            people_count, people_locations = await self.count_people(frame)
            
            # 2. Behavior analysis (if we have enough frames)
            behavior_alerts = []
            if frame_sequence and len(frame_sequence) >= 16:
                behavior_alerts = await self.analyze_behavior(frame_sequence)
            
            # 3. Emergency detection
            emergency_status = await self.detect_emergencies(frame)
            
            # 4. Calculate crowd density
            density_level, density_percentage = self.calculate_crowd_density(people_count)
            
            # 5. Generate alerts if necessary
            alerts = await self.generate_alerts(people_count, behavior_alerts, emergency_status)
            
            # 6. Save frame if critical event detected
            if alerts or emergency_status['status'] != 'clear':
                await self.save_critical_frame(frame)
            
            # 7. Compile grid status
            grid_status = {
                'grid_id': self.grid_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'people_count': people_count,
                'people_locations': people_locations,
                'crowd_density': {
                    'level': density_level,
                    'percentage': density_percentage,
                    'threshold_status': self.get_threshold_status(people_count)
                },
                'behavior_analysis': {
                    'alerts': behavior_alerts,
                    'normal_behavior_confidence': self.calculate_normal_confidence(behavior_alerts)
                },
                'emergency_detection': emergency_status,
                'alerts': alerts,
                'processing_time': time.time() - start_time,
                'model_performance': self.get_model_performance()
            }
            
            self.last_people_count = people_count
            
            return grid_status
            
        except Exception as e:
            self.logger.error(f"Frame processing failed: {e}")
            return self.create_error_status(str(e))
    
    async def count_people(self, frame: np.ndarray) -> Tuple[int, List[Dict]]:
        """Count people in the frame using YOLO model"""
        start_time = time.time()
        
        try:
            processed_frame = self.people_counter.preprocess_frame(frame)
            detections = await self.people_counter.detect_people(processed_frame)
            
            people_count = len(detections)
            people_locations = []
            
            for detection in detections:
                x, y, w, h, confidence = detection
                people_locations.append({
                    'bbox': [int(x), int(y), int(w), int(h)],
                    'confidence': float(confidence),
                    'center': [int(x + w/2), int(y + h/2)]
                })
            
            processing_time = time.time() - start_time
            self.processing_times['people_counting'].append(processing_time)
            
            if len(self.processing_times['people_counting']) > 100:
                self.processing_times['people_counting'].pop(0)
            
            return people_count, people_locations
            
        except Exception as e:
            self.logger.error(f"People counting failed: {e}")
            return 0, []
    
    async def analyze_behavior(self, frame_sequence: List[np.ndarray]) -> List[Dict]:
        """Analyze behavior patterns from frame sequence"""
        start_time = time.time()
        
        try:
            processed_sequence = self.behavior_analyzer.preprocess_sequence(frame_sequence)
            behavior_predictions = await self.behavior_analyzer.analyze_sequence(processed_sequence)
            
            behavior_alerts = []
            
            for behavior, confidence in behavior_predictions.items():
                if behavior != 'normal' and confidence > 0.7:
                    alert = {
                        'type': 'behavior_alert',
                        'behavior': behavior,
                        'confidence': float(confidence),
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'severity': self.get_behavior_severity(behavior, confidence)
                    }
                    behavior_alerts.append(alert)
            
            processing_time = time.time() - start_time
            self.processing_times['behavior_analysis'].append(processing_time)
            
            if len(self.processing_times['behavior_analysis']) > 100:
                self.processing_times['behavior_analysis'].pop(0)
            
            return behavior_alerts
            
        except Exception as e:
            self.logger.error(f"Behavior analysis failed: {e}")
            return []
    
    async def detect_emergencies(self, frame: np.ndarray) -> Dict:
        """Detect emergency situations in the frame"""
        start_time = time.time()
        
        try:
            processed_frame = self.emergency_detector.preprocess_frame(frame)
            emergency_predictions = await self.emergency_detector.detect_emergencies(processed_frame)
            
            emergency_status = {
                'status': 'clear',
                'type': None,
                'confidence': 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'details': emergency_predictions
            }
            
            max_confidence = 0.0
            emergency_type = None
            
            for emergency, confidence in emergency_predictions.items():
                if emergency != 'normal' and confidence > max_confidence:
                    max_confidence = confidence
                    emergency_type = emergency
            
            if max_confidence > 0.8:
                emergency_status.update({
                    'status': 'emergency',
                    'type': emergency_type,
                    'confidence': float(max_confidence)
                })
            elif max_confidence > 0.6:
                emergency_status.update({
                    'status': 'warning',
                    'type': emergency_type,
                    'confidence': float(max_confidence)
                })
            
            processing_time = time.time() - start_time
            self.processing_times['emergency_detection'].append(processing_time)
            
            if len(self.processing_times['emergency_detection']) > 100:
                self.processing_times['emergency_detection'].pop(0)
            
            return emergency_status
            
        except Exception as e:
            self.logger.error(f"Emergency detection failed: {e}")
            return {
                'status': 'error',
                'type': None,
                'confidence': 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
    
    def calculate_crowd_density(self, people_count: int) -> Tuple[str, float]:
        """Calculate crowd density level and percentage"""
        density_per_sqm = people_count / self.grid_area
        density_percentage = min((density_per_sqm / 4.0) * 100, 100)
        
        if people_count <= self.density_thresholds['normal']:
            density_level = 'low'
        elif people_count <= self.density_thresholds['moderate']:
            density_level = 'moderate'
        elif people_count <= self.density_thresholds['high']:
            density_level = 'high'
        else:
            density_level = 'critical'
        
        return density_level, round(density_percentage, 2)
    
    def get_threshold_status(self, people_count: int) -> str:
        """Get threshold status based on people count"""
        if people_count <= self.density_thresholds['normal']:
            return 'normal'
        elif people_count <= self.density_thresholds['moderate']:
            return 'moderate'
        elif people_count <= self.density_thresholds['high']:
            return 'high'
        else:
            return 'critical'
    
    def get_behavior_severity(self, behavior: str, confidence: float) -> str:
        """Determine severity of behavior alert"""
        severity_mapping = {
            'panic': 'critical',
            'running': 'high',
            'fighting': 'critical',
            'falling': 'high',
            'unusual_gathering': 'moderate'
        }
        
        base_severity = severity_mapping.get(behavior, 'moderate')
        
        if confidence > 0.9:
            if base_severity == 'moderate':
                return 'high'
            elif base_severity == 'high':
                return 'critical'
        
        return base_severity
    
    def calculate_normal_confidence(self, behavior_alerts: List[Dict]) -> float:
        """Calculate confidence that behavior is normal"""
        if not behavior_alerts:
            return 1.0
        
        total_abnormal_confidence = sum(alert['confidence'] for alert in behavior_alerts)
        normal_confidence = max(0.0, 1.0 - (total_abnormal_confidence / len(behavior_alerts)))
        
        return round(normal_confidence, 3)
    
    async def generate_alerts(self, people_count: int, behavior_alerts: List[Dict], emergency_status: Dict) -> List[Dict]:
        """Generate alerts based on analysis results"""
        alerts = []
        current_time = datetime.now(timezone.utc)
        
        threshold_status = self.get_threshold_status(people_count)
        if threshold_status in ['high', 'critical']:
            alert_key = f"density_{threshold_status}"
            
            if not self.is_alert_in_cooldown(alert_key):
                alert = {
                    'id': generate_alert_id(),
                    'type': 'crowd_density',
                    'severity': threshold_status,
                    'message': f"Crowd density {threshold_status}: {people_count} people detected",
                    'grid_id': self.grid_id,
                    'timestamp': current_time.isoformat(),
                    'people_count': people_count,
                    'threshold_exceeded': self.density_thresholds.get(threshold_status, 0)
                }
                alerts.append(alert)
                self.set_alert_cooldown(alert_key, 60)
        
        for behavior_alert in behavior_alerts:
            if behavior_alert['severity'] in ['high', 'critical']:
                alert_key = f"behavior_{behavior_alert['behavior']}"
                
                if not self.is_alert_in_cooldown(alert_key):
                    alert = {
                        'id': generate_alert_id(),
                        'type': 'behavior_anomaly',
                        'severity': behavior_alert['severity'],
                        'message': f"Abnormal behavior detected: {behavior_alert['behavior']}",
                        'grid_id': self.grid_id,
                        'timestamp': current_time.isoformat(),
                        'behavior': behavior_alert['behavior'],
                        'confidence': behavior_alert['confidence']
                    }
                    alerts.append(alert)
                    self.set_alert_cooldown(alert_key, 30)
        
        if emergency_status['status'] in ['warning', 'emergency']:
            alert_key = f"emergency_{emergency_status['type']}"
            
            if not self.is_alert_in_cooldown(alert_key):
                alert = {
                    'id': generate_alert_id(),
                    'type': 'emergency',
                    'severity': 'critical' if emergency_status['status'] == 'emergency' else 'high',
                    'message': f"Emergency detected: {emergency_status['type']}",
                    'grid_id': self.grid_id,
                    'timestamp': current_time.isoformat(),
                    'emergency_type': emergency_status['type'],
                    'confidence': emergency_status['confidence']
                }
                alerts.append(alert)
                self.set_alert_cooldown(alert_key, 10)
        
        for alert in alerts:
            await self.mqtt_client.publish(
                f"dhsiled/grids/{self.grid_id}/alerts",
                json.dumps(alert)
            )
            self.logger.warning(f"Alert generated: {alert['message']}")
        
        return alerts
    
    def is_alert_in_cooldown(self, alert_key: str) -> bool:
        """Check if alert is in cooldown period"""
        if alert_key not in self.alert_cooldown:
            return False
        
        cooldown_until = self.alert_cooldown[alert_key]
        return time.time() < cooldown_until
    
    def set_alert_cooldown(self, alert_key: str, cooldown_seconds: int):
        """Set cooldown period for alert"""
        self.alert_cooldown[alert_key] = time.time() + cooldown_seconds
    
    async def save_critical_frame(self, frame: np.ndarray):
        """Save frame when critical event is detected"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/video_buffer/critical_{self.grid_id}_{timestamp}.jpg"
            await save_frame(frame, filename)
            
        except Exception as e:
            self.logger.error(f"Failed to save critical frame: {e}")
    
    def get_model_performance(self) -> Dict:
        """Get current model performance metrics"""
        performance = {}
        
        for model, times in self.processing_times.items():
            if times:
                performance[model] = {
                    'avg_time_ms': round(np.mean(times) * 1000, 2),
                    'max_time_ms': round(np.max(times) * 1000, 2),
                    'min_time_ms': round(np.min(times) * 1000, 2),
                    'samples': len(times)
                }
            else:
                performance[model] = {
                    'avg_time_ms': 0,
                    'max_time_ms': 0,
                    'min_time_ms': 0,
                    'samples': 0
                }
        
        return performance
    
    def create_error_status(self, error_message: str) -> Dict:
        """Create error status when processing fails"""
        return {
            'grid_id': self.grid_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'error',
            'error_message': error_message,
            'people_count': self.last_people_count,
            'crowd_density': {'level': 'unknown', 'percentage': 0},
            'behavior_analysis': {'alerts': []},
            'emergency_detection': {'status': 'unknown'},
            'alerts': []
        }
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.people_counter:
                await self.people_counter.cleanup()
            
            if self.behavior_analyzer:
                await self.behavior_analyzer.cleanup()
            
            if self.emergency_detector:
                await self.emergency_detector.cleanup()
            
            self.logger.info("Edge processor cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")