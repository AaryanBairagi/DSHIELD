#!/usr/bin/env python3
"""
Behavior Analysis Model using CNN-LSTM for temporal crowd behavior detection
"""

import cv2
import numpy as np
import asyncio
import time
from typing import List, Dict, Optional, Tuple
from collections import deque
import json

try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("Warning: TensorFlow not available, using mock implementation")

class BehaviorAnalyzer:
    def __init__(self, model_path: str = "models/behavior_lstm.h5", sequence_length: int = 16):
        self.model_path = model_path
        self.sequence_length = sequence_length
        self.model = None
        
        # Input parameters
        self.input_shape = (sequence_length, 224, 224, 3)  # Time, Height, Width, Channels
        self.target_size = (224, 224)
        
        # Behavior classes
        self.behavior_classes = [
            'normal',
            'panic',
            'running',
            'fighting',
            'falling',
            'unusual_gathering',
            'crowd_surge',
            'evacuation'
        ]
        
        # Frame preprocessing
        self.frame_buffer = deque(maxlen=sequence_length)
        
        # Temporal smoothing
        self.prediction_history = deque(maxlen=5)
        self.confidence_threshold = 0.6
        
        # Performance tracking
        self.processing_times = []
        
    async def load_model(self):
        """Load the behavior analysis model"""
        try:
            if TF_AVAILABLE:
                # Check if model file exists
                import os
                if os.path.exists(self.model_path):
                    self.model = keras.models.load_model(self.model_path)
                    print(f"Loaded behavior analysis model from {self.model_path}")
                else:
                    # Create a simple mock model
                    self.model = self._create_mock_model()
                    print(f"Created mock behavior analysis model (file not found: {self.model_path})")
                
                # Optimize for inference
                if hasattr(self.model, 'compile'):
                    self.model.compile(optimizer='adam', loss='categorical_crossentropy')
                
                # Warm up model
                await self._warmup_model()
                
            else:
                # Use mock model
                self.model = MockBehaviorModel(self.behavior_classes)
                print("Using mock behavior analysis model (TensorFlow not available)")
                
        except Exception as e:
            print(f"Error loading behavior model: {e}")
            self.model = MockBehaviorModel(self.behavior_classes)
    
    def _create_mock_model(self):
        """Create a simple mock CNN-LSTM model"""
        if not TF_AVAILABLE:
            return MockBehaviorModel(self.behavior_classes)
        
        try:
            # Simple CNN-LSTM architecture
            model = keras.Sequential([
                # Convolutional layers for spatial features
                keras.layers.TimeDistributed(
                    keras.layers.Conv2D(32, (3, 3), activation='relu'),
                    input_shape=self.input_shape
                ),
                keras.layers.TimeDistributed(keras.layers.MaxPooling2D(2, 2)),
                keras.layers.TimeDistributed(keras.layers.Conv2D(64, (3, 3), activation='relu')),
                keras.layers.TimeDistributed(keras.layers.MaxPooling2D(2, 2)),
                keras.layers.TimeDistributed(keras.layers.Conv2D(128, (3, 3), activation='relu')),
                keras.layers.TimeDistributed(keras.layers.MaxPooling2D(2, 2)),
                
                # Flatten for LSTM
                keras.layers.TimeDistributed(keras.layers.Flatten()),
                
                # LSTM layers for temporal features
                keras.layers.LSTM(128, return_sequences=True),
                keras.layers.Dropout(0.5),
                keras.layers.LSTM(64),
                keras.layers.Dropout(0.5),
                
                # Dense layers for classification
                keras.layers.Dense(64, activation='relu'),
                keras.layers.Dropout(0.3),
                keras.layers.Dense(len(self.behavior_classes), activation='softmax')
            ])
            
            model.compile(
                optimizer='adam',
                loss='categorical_crossentropy',
                metrics=['accuracy']
            )
            
            return model
            
        except Exception as e:
            print(f"Error creating mock model: {e}")
            return MockBehaviorModel(self.behavior_classes)
    
    async def _warmup_model(self):
        """Warm up the model with dummy data"""
        try:
            if TF_AVAILABLE and hasattr(self.model, 'predict'):
                dummy_sequence = np.random.randint(0, 255, self.input_shape, dtype=np.uint8)
                dummy_sequence = np.expand_dims(dummy_sequence, axis=0)  # Add batch dimension
                dummy_sequence = dummy_sequence.astype(np.float32) / 255.0
                
                # Run a few prediction passes
                for _ in range(3):
                    _ = self.model.predict(dummy_sequence, verbose=0)
                    await asyncio.sleep(0.1)
                
                print("Behavior model warmup completed")
            
        except Exception as e:
            print(f"Behavior model warmup failed: {e}")
    
    def preprocess_sequence(self, frame_sequence: List[np.ndarray]) -> np.ndarray:
        """Preprocess frame sequence for model input"""
        processed_frames = []
        
        for frame in frame_sequence:
            # Resize frame
            resized = cv2.resize(frame, self.target_size, interpolation=cv2.INTER_LINEAR)
            
            # Normalize pixel values
            normalized = resized.astype(np.float32) / 255.0
            
            processed_frames.append(normalized)
        
        # Convert to numpy array
        sequence = np.array(processed_frames)
        
        # Add batch dimension
        sequence = np.expand_dims(sequence, axis=0)
        
        return sequence
    
    async def analyze_sequence(self, frame_sequence: np.ndarray) -> Dict[str, float]:
        """Analyze behavior from frame sequence"""
        start_time = time.time()
        
        try:
            if TF_AVAILABLE and hasattr(self.model, 'predict'):
                # Run model inference
                predictions = self.model.predict(frame_sequence, verbose=0)
                
                # Convert predictions to behavior scores
                behavior_scores = {}
                for i, behavior in enumerate(self.behavior_classes):
                    behavior_scores[behavior] = float(predictions[0][i])
                
            else:
                # Use mock predictions
                behavior_scores = await self.model.analyze_sequence(frame_sequence)
            
            # Apply temporal smoothing
            smoothed_scores = self._apply_temporal_smoothing(behavior_scores)
            
            # Record performance
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            if len(self.processing_times) > 100:
                self.processing_times.pop(0)
            
            return smoothed_scores
            
        except Exception as e:
            print(f"Behavior analysis failed: {e}")
            # Return default normal behavior
            return {behavior: (1.0 if behavior == 'normal' else 0.0) 
                   for behavior in self.behavior_classes}
    
    def _apply_temporal_smoothing(self, current_predictions: Dict[str, float]) -> Dict[str, float]:
        """Apply temporal smoothing to reduce noise in predictions"""
        # Add current predictions to history
        self.prediction_history.append(current_predictions.copy())
        
        # Calculate weighted average (more weight to recent predictions)
        weights = np.array([0.1, 0.2, 0.3, 0.4])[:len(self.prediction_history)]
        weights = weights / weights.sum()
        
        smoothed_predictions = {}
        for behavior in self.behavior_classes:
            scores = [pred[behavior] for pred in self.prediction_history]
            smoothed_score = np.average(scores, weights=weights[:len(scores)])
            smoothed_predictions[behavior] = float(smoothed_score)
        
        return smoothed_predictions
    
    def detect_anomalous_behavior(self, behavior_scores: Dict[str, float]) -> List[Dict]:
        """Detect anomalous behaviors based on confidence thresholds"""
        anomalies = []
        
        for behavior, confidence in behavior_scores.items():
            if behavior != 'normal' and confidence > self.confidence_threshold:
                severity = self._calculate_severity(behavior, confidence)
                
                anomaly = {
                    'behavior': behavior,
                    'confidence': confidence,
                    'severity': severity,
                    'timestamp': time.time(),
                    'description': self._get_behavior_description(behavior)
                }
                anomalies.append(anomaly)
        
        return anomalies
    
    def _calculate_severity(self, behavior: str, confidence: float) -> str:
        """Calculate severity level based on behavior type and confidence"""
        # Behavior severity mapping
        high_severity_behaviors = ['panic', 'fighting', 'crowd_surge']
        medium_severity_behaviors = ['running', 'unusual_gathering', 'evacuation']
        low_severity_behaviors = ['falling']
        
        if behavior in high_severity_behaviors:
            if confidence > 0.8:
                return 'critical'
            elif confidence > 0.6:
                return 'high'
            else:
                return 'medium'
        elif behavior in medium_severity_behaviors:
            if confidence > 0.8:
                return 'high'
            elif confidence > 0.6:
                return 'medium'
            else:
                return 'low'
        else:  # low_severity_behaviors
            if confidence > 0.8:
                return 'medium'
            else:
                return 'low'
    
    def _get_behavior_description(self, behavior: str) -> str:
        """Get human-readable description of behavior"""
        descriptions = {
            'panic': 'Panic behavior detected in crowd',
            'running': 'People running detected',
            'fighting': 'Aggressive behavior or fighting detected',
            'falling': 'Person falling detected',
            'unusual_gathering': 'Unusual crowd gathering pattern',
            'crowd_surge': 'Dangerous crowd surge detected',
            'evacuation': 'Evacuation behavior detected'
        }
        return descriptions.get(behavior, f'Unusual behavior: {behavior}')
    
    def get_behavior_statistics(self) -> Dict:
        """Get behavior analysis statistics"""
        if not self.processing_times:
            return {
                'avg_processing_time': 0,
                'model_loaded': self.model is not None,
                'sequence_length': self.sequence_length
            }
        
        return {
            'avg_processing_time': np.mean(self.processing_times),
            'max_processing_time': np.max(self.processing_times),
            'min_processing_time': np.min(self.processing_times),
            'model_loaded': self.model is not None,
            'sequence_length': self.sequence_length,
            'samples_processed': len(self.processing_times)
        }
    
    def add_frame_to_buffer(self, frame: np.ndarray):
        """Add frame to the analysis buffer"""
        self.frame_buffer.append(frame.copy())
    
    def has_enough_frames(self) -> bool:
        """Check if buffer has enough frames for analysis"""
        return len(self.frame_buffer) >= self.sequence_length
    
    def get_frame_sequence(self) -> List[np.ndarray]:
        """Get current frame sequence from buffer"""
        return list(self.frame_buffer)
    
    async def cleanup(self):
        """Clean up model resources"""
        try:
            if self.model and TF_AVAILABLE:
                # Clear model from memory
                del self.model
                
                # Clear TensorFlow session if available
                if hasattr(tf.keras, 'clear_session'):
                    tf.keras.backend.clear_session()
            
            print("Behavior analyzer cleanup completed")
            
        except Exception as e:
            print(f"Cleanup error: {e}")


class MockBehaviorModel:
    """Mock behavior analysis model for testing and development"""
    
    def __init__(self, behavior_classes: List[str]):
        self.behavior_classes = behavior_classes
        self.base_probabilities = {
            'normal': 0.8,
            'panic': 0.05,
            'running': 0.08,
            'fighting': 0.02,
            'falling': 0.03,
            'unusual_gathering': 0.015,
            'crowd_surge': 0.005,
            'evacuation': 0.01
        }
    
    async def analyze_sequence(self, frame_sequence: np.ndarray) -> Dict[str, float]:
        """Generate mock behavior predictions"""
        await asyncio.sleep(0.08)  # Simulate processing time
        
        # Generate realistic predictions with some randomness
        predictions = {}
        
        for behavior in self.behavior_classes:
            base_prob = self.base_probabilities.get(behavior, 0.1)
            
            # Add some random variation
            noise = np.random.normal(0, 0.1)
            prob = max(0.0, min(1.0, base_prob + noise))
            predictions[behavior] = prob
        
        # Normalize probabilities to sum to 1
        total = sum(predictions.values())
        if total > 0:
            predictions = {k: v/total for k, v in predictions.items()}
        
        # Occasionally generate anomalous behavior for testing
        if np.random.random() < 0.05:  # 5% chance of anomaly
            anomaly_behavior = np.random.choice(['panic', 'running', 'fighting'])
            predictions[anomaly_behavior] = min(0.9, predictions[anomaly_behavior] + 0.5)
            predictions['normal'] = max(0.1, predictions['normal'] - 0.3)
            
            # Re-normalize
            total = sum(predictions.values())
            predictions = {k: v/total for k, v in predictions.items()}
        
        return predictions