# edge-computing/src/models/emergency_detector.py
"""
Emergency Detection Model for fire, accidents, and critical incidents
"""

import cv2
import numpy as np
import asyncio
import time
from typing import Dict, List, Optional, Tuple
import json

try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("Warning: TensorFlow not available, using mock implementation")

class EmergencyDetector:
    def __init__(self, model_path: str = "models/emergency_cnn.h5"):
        self.model_path = model_path
        self.model = None
        
        # Input parameters
        self.input_size = (224, 224)
        self.input_shape = (224, 224, 3)
        
        # Emergency classes
        self.emergency_classes = [
            'normal',
            'fire',
            'smoke',
            'accident',
            'medical_emergency',
            'structural_damage',
            'flood',
            'explosion'
        ]
        
        # Detection thresholds
        self.detection_thresholds = {
            'fire': 0.7,
            'smoke': 0.6,
            'accident': 0.65,
            'medical_emergency': 0.7,
            'structural_damage': 0.8,
            'flood': 0.75,
            'explosion': 0.9
        }
        
        # Multi-modal features (for future enhancement)
        self.use_color_analysis = True
        self.use_motion_analysis = True
        
        # Performance tracking
        self.processing_times = []
        self.detection_history = []
        
        # Alert cooldown to prevent spam
        self.last_alert_time = {}
        self.alert_cooldown_seconds = 30
        
    async def load_model(self):
        """Load the emergency detection model"""
        try:
            if TF_AVAILABLE:
                # Check if model file exists
                import os
                if os.path.exists(self.model_path):
                    self.model = keras.models.load_model(self.model_path)
                    print(f"Loaded emergency detection model from {self.model_path}")
                else:
                    # Create a simple CNN model
                    self.model = self._create_emergency_model()
                    print(f"Created mock emergency detection model (file not found: {self.model_path})")
                
                # Optimize for inference
                if hasattr(self.model, 'compile'):
                    self.model.compile(optimizer='adam', loss='categorical_crossentropy')
                
                # Warm up model
                await self._warmup_model()
                
            else:
                # Use mock model
                self.model = MockEmergencyModel(self.emergency_classes)
                print("Using mock emergency detection model (TensorFlow not available)")
                
        except Exception as e:
            print(f"Error loading emergency model: {e}")
            self.model = MockEmergencyModel(self.emergency_classes)
    
    def _create_emergency_model(self):
        """Create a CNN model for emergency detection"""
        if not TF_AVAILABLE:
            return MockEmergencyModel(self.emergency_classes)
        
        try:
            # CNN architecture optimized for emergency detection
            model = keras.Sequential([
                # First conv block
                keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=self.input_shape),
                keras.layers.BatchNormalization(),
                keras.layers.MaxPooling2D(2, 2),
                
                # Second conv block
                keras.layers.Conv2D(64, (3, 3), activation='relu'),
                keras.layers.BatchNormalization(),
                keras.layers.MaxPooling2D(2, 2),
                
                # Third conv block
                keras.layers.Conv2D(128, (3, 3), activation='relu'),
                keras.layers.BatchNormalization(),
                keras.layers.MaxPooling2D(2, 2),
                
                # Fourth conv block
                keras.layers.Conv2D(256, (3, 3), activation='relu'),
                keras.layers.BatchNormalization(),
                keras.layers.MaxPooling2D(2, 2),
                
                # Global average pooling
                keras.layers.GlobalAveragePooling2D(),
                
                # Dense layers
                keras.layers.Dense(512, activation='relu'),
                keras.layers.Dropout(0.5),
                keras.layers.Dense(256, activation='relu'),
                keras.layers.Dropout(0.3),
                keras.layers.Dense(len(self.emergency_classes), activation='softmax')
            ])
            
            model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=0.001),
                loss='categorical_crossentropy',
                metrics=['accuracy']
            )
            
            return model
            
        except Exception as e:
            print(f"Error creating emergency model: {e}")
            return MockEmergencyModel(self.emergency_classes)
    
    async def _warmup_model(self):
        """Warm up the model with dummy data"""
        try:
            if TF_AVAILABLE and hasattr(self.model, 'predict'):
                dummy_frame = np.random.randint(0, 255, (1, *self.input_shape), dtype=np.uint8)
                dummy_frame = dummy_frame.astype(np.float32) / 255.0
                
                # Run a few prediction passes
                for _ in range(3):
                    _ = self.model.predict(dummy_frame, verbose=0)
                    await asyncio.sleep(0.1)
                
                print("Emergency model warmup completed")
            
        except Exception as e:
            print(f"Emergency model warmup failed: {e}")
    
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame for emergency detection"""
        # Resize frame
        resized = cv2.resize(frame, self.input_size, interpolation=cv2.INTER_LINEAR)
        
        # Normalize pixel values
        normalized = resized.astype(np.float32) / 255.0
        
        # Add batch dimension
        preprocessed = np.expand_dims(normalized, axis=0)
        
        return preprocessed
    
    async def detect_emergencies(self, frame: np.ndarray) -> Dict[str, float]:
        """Detect emergency situations in the frame"""
        start_time = time.time()
        
        try:
            # Preprocess frame
            processed_frame = self.preprocess_frame(frame)
            
            if TF_AVAILABLE and hasattr(self.model, 'predict'):
                # Run model inference
                predictions = self.model.predict(processed_frame, verbose=0)
                
                # Convert predictions to emergency scores
                emergency_scores = {}
                for i, emergency in enumerate(self.emergency_classes):
                    emergency_scores[emergency] = float(predictions[0][i])
                
            else:
                # Use mock predictions
                emergency_scores = await self.model.detect_emergencies(processed_frame)
            
            # Apply additional analysis
            enhanced_scores = await self._enhance_detection(frame, emergency_scores)
            
            # Record detection in history
            self.detection_history.append({
                'timestamp': time.time(),
                'scores': enhanced_scores.copy()
            })
            
            # Keep only recent history
            if len(self.detection_history) > 100:
                self.detection_history.pop(0)
            
            # Record performance
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            if len(self.processing_times) > 100:
                self.processing_times.pop(0)
            
            return enhanced_scores
            
        except Exception as e:
            print(f"Emergency detection failed: {e}")
            # Return default normal status
            return {emergency: (1.0 if emergency == 'normal' else 0.0) 
                   for emergency in self.emergency_classes}
    
    async def _enhance_detection(self, frame: np.ndarray, base_scores: Dict[str, float]) -> Dict[str, float]:
        """Enhance detection with additional analysis"""
        enhanced_scores = base_scores.copy()
        
        try:
            # Color-based fire/smoke detection
            if self.use_color_analysis:
                fire_color_score = self._analyze_fire_colors(frame)
                smoke_color_score = self._analyze_smoke_colors(frame)
                
                # Boost fire/smoke scores based on color analysis
                enhanced_scores['fire'] = min(1.0, enhanced_scores['fire'] + fire_color_score * 0.3)
                enhanced_scores['smoke'] = min(1.0, enhanced_scores['smoke'] + smoke_color_score * 0.3)
            
            # Motion-based analysis (simplified)
            if self.use_motion_analysis and len(self.detection_history) > 0:
                motion_emergency_score = self._analyze_motion_patterns()
                enhanced_scores['accident'] = min(1.0, enhanced_scores['accident'] + motion_emergency_score * 0.2)
            
            # Normalize scores to ensure they sum to 1
            total_score = sum(enhanced_scores.values())
            if total_score > 0:
                enhanced_scores = {k: v / total_score for k, v in enhanced_scores.items()}
            
        except Exception as e:
            print(f"Detection enhancement failed: {e}")
        
        return enhanced_scores
    
    def _analyze_fire_colors(self, frame: np.ndarray) -> float:
        """Analyze frame for fire-like colors"""
        try:
            # Convert to HSV for better color analysis
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Define fire color ranges (red, orange, yellow)
            fire_lower1 = np.array([0, 50, 50])    # Red lower
            fire_upper1 = np.array([10, 255, 255]) # Red upper
            fire_lower2 = np.array([15, 50, 50])   # Orange-yellow lower  
            fire_upper2 = np.array([35, 255, 255]) # Orange-yellow upper
            
            # Create masks
            mask1 = cv2.inRange(hsv, fire_lower1, fire_upper1)
            mask2 = cv2.inRange(hsv, fire_lower2, fire_upper2)
            fire_mask = cv2.bitwise_or(mask1, mask2)
            
            # Calculate fire color percentage
            fire_pixels = np.sum(fire_mask > 0)
            total_pixels = frame.shape[0] * frame.shape[1]
            fire_ratio = fire_pixels / total_pixels
            
            return min(1.0, fire_ratio * 10)  # Scale up sensitivity
            
        except Exception as e:
            return 0.0
    
    def _analyze_smoke_colors(self, frame: np.ndarray) -> float:
        """Analyze frame for smoke-like colors"""
        try:
            # Convert to HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Define smoke color ranges (gray, white, light gray)
            smoke_lower = np.array([0, 0, 50])     # Light gray
            smoke_upper = np.array([180, 30, 200]) # White-ish
            
            # Create mask
            smoke_mask = cv2.inRange(hsv, smoke_lower, smoke_upper)
            
            # Calculate smoke color percentage
            smoke_pixels = np.sum(smoke_mask > 0)
            total_pixels = frame.shape[0] * frame.shape[1]
            smoke_ratio = smoke_pixels / total_pixels
            
            return min(1.0, smoke_ratio * 5)  # Scale sensitivity
            
        except Exception as e:
            return 0.0
    
    def _analyze_motion_patterns(self) -> float:
        """Analyze motion patterns for emergency indicators"""
        try:
            if len(self.detection_history) < 2:
                return 0.0
            
            # Compare recent detections for rapid changes
            recent_scores = [entry['scores'] for entry in self.detection_history[-5:]]
            
            # Calculate variance in emergency scores
            emergency_variance = 0.0
            for emergency in self.emergency_classes:
                if emergency != 'normal':
                    scores = [entry[emergency] for entry in recent_scores]
                    if len(scores) > 1:
                        emergency_variance += np.var(scores)
            
            # High variance might indicate sudden emergency
            return min(1.0, emergency_variance * 2)
            
        except Exception as e:
            return 0.0
    
    def is_emergency_detected(self, emergency_scores: Dict[str, float]) -> Tuple[bool, List[Dict]]:
        """Check if any emergency is detected above threshold"""
        detected_emergencies = []
        
        for emergency, score in emergency_scores.items():
            if emergency == 'normal':
                continue
                
            threshold = self.detection_thresholds.get(emergency, 0.7)
            
            if score > threshold:
                # Check cooldown
                if not self._is_in_cooldown(emergency):
                    severity = self._get_emergency_severity(emergency, score)
                    
                    detected_emergency = {
                        'type': emergency,
                        'confidence': score,
                        'severity': severity,
                        'threshold': threshold,
                        'timestamp': time.time(),
                        'description': self._get_emergency_description(emergency)
                    }
                    
                    detected_emergencies.append(detected_emergency)
                    self._set_alert_cooldown(emergency)
        
        return len(detected_emergencies) > 0, detected_emergencies
    
    def _is_in_cooldown(self, emergency_type: str) -> bool:
        """Check if emergency type is in cooldown period"""
        if emergency_type not in self.last_alert_time:
            return False
        
        elapsed = time.time() - self.last_alert_time[emergency_type]
        return elapsed < self.alert_cooldown_seconds
    
    def _set_alert_cooldown(self, emergency_type: str):
        """Set cooldown for emergency type"""
        self.last_alert_time[emergency_type] = time.time()
    
    def _get_emergency_severity(self, emergency: str, confidence: float) -> str:
        """Calculate emergency severity based on type and confidence"""
        critical_emergencies = ['fire', 'explosion', 'structural_damage']
        high_emergencies = ['smoke', 'flood', 'accident']
        medium_emergencies = ['medical_emergency']
        
        if emergency in critical_emergencies:
            if confidence > 0.9:
                return 'critical'
            elif confidence > 0.8:
                return 'high'
            else:
                return 'medium'
        elif emergency in high_emergencies:
            if confidence > 0.85:
                return 'high'
            elif confidence > 0.7:
                return 'medium'
            else:
                return 'low'
        else:  # medium_emergencies
            if confidence > 0.8:
                return 'medium'
            else:
                return 'low'
    
    def _get_emergency_description(self, emergency: str) -> str:
        """Get human-readable description of emergency"""
        descriptions = {
            'fire': 'Fire detected - immediate evacuation may be required',
            'smoke': 'Smoke detected - potential fire hazard',
            'accident': 'Accident or incident detected',
            'medical_emergency': 'Medical emergency detected',
            'structural_damage': 'Structural damage detected - safety risk',
            'flood': 'Flooding detected in area',
            'explosion': 'Explosion detected - critical emergency'
        }
        return descriptions.get(emergency, f'Emergency situation: {emergency}')
    
    def get_detection_statistics(self) -> Dict:
        """Get emergency detection statistics"""
        if not self.processing_times:
            return {
                'avg_processing_time': 0,
                'model_loaded': self.model is not None,
                'detection_classes': len(self.emergency_classes)
            }
        
        # Calculate recent detection rates
        recent_detections = self.detection_history[-50:] if self.detection_history else []
        emergency_rates = {}
        
        for emergency in self.emergency_classes:
            if emergency != 'normal':
                high_conf_detections = sum(1 for d in recent_detections 
                                         if d['scores'][emergency] > 0.5)
                emergency_rates[emergency] = high_conf_detections / max(1, len(recent_detections))
        
        return {
            'avg_processing_time': np.mean(self.processing_times),
            'max_processing_time': np.max(self.processing_times),
            'min_processing_time': np.min(self.processing_times),
            'model_loaded': self.model is not None,
            'detection_classes': len(self.emergency_classes),
            'samples_processed': len(self.processing_times),
            'emergency_detection_rates': emergency_rates,
            'detection_history_length': len(self.detection_history)
        }
    
    async def cleanup(self):
        """Clean up model resources"""
        try:
            if self.model and TF_AVAILABLE:
                # Clear model from memory
                del self.model
                
                # Clear TensorFlow session if available
                if hasattr(tf.keras, 'clear_session'):
                    tf.keras.backend.clear_session()
            
            print("Emergency detector cleanup completed")
            
        except Exception as e:
            print(f"Cleanup error: {e}")


class MockEmergencyModel:
    """Mock emergency detection model for testing and development"""
    
    def __init__(self, emergency_classes: List[str]):
        self.emergency_classes = emergency_classes
        self.base_probabilities = {
            'normal': 0.85,
            'fire': 0.02,
            'smoke': 0.03,
            'accident': 0.04,
            'medical_emergency': 0.03,
            'structural_damage': 0.01,
            'flood': 0.01,
            'explosion': 0.01
        }
    
    async def detect_emergencies(self, frame: np.ndarray) -> Dict[str, float]:
        """Generate mock emergency predictions"""
        await asyncio.sleep(0.06)  # Simulate processing time
        
        # Generate realistic predictions with some randomness
        predictions = {}
        
        for emergency in self.emergency_classes:
            base_prob = self.base_probabilities.get(emergency, 0.05)
            
            # Add some random variation
            noise = np.random.normal(0, 0.02)
            prob = max(0.0, min(1.0, base_prob + noise))
            predictions[emergency] = prob
        
        # Normalize probabilities to sum to 1
        total = sum(predictions.values())
        if total > 0:
            predictions = {k: v/total for k, v in predictions.items()}
        
        # Occasionally generate emergency for testing
        if np.random.random() < 0.02:  # 2% chance of emergency
            emergency_type = np.random.choice(['fire', 'smoke', 'accident'])
            predictions[emergency_type] = min(0.9, predictions[emergency_type] + 0.6)
            predictions['normal'] = max(0.1, predictions['normal'] - 0.4)
            
            # Re-normalize
            total = sum(predictions.values())
            predictions = {k: v/total for k, v in predictions.items()}
        
        return predictions