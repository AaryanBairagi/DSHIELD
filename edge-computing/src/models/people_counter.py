# edge-computing/src/models/people_counter.py
"""
YOLOv8-based people counting model optimized for crowd detection
"""

import cv2
import numpy as np
import asyncio
import time
from typing import List, Tuple, Dict
from pathlib import Path
import torch

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("Warning: ultralytics not available, using mock implementation")

class PeopleCounter:
    def __init__(self, model_path: str = "models/yolov8n.pt", confidence_threshold: float = 0.5):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.input_size = (640, 640)
        
        # Performance optimization
        self.warmup_completed = False
        
        # Crowd-specific parameters
        self.crowd_classes = [0]  # Person class in COCO dataset
        self.nms_threshold = 0.4
        
        # Tracking for crowd density estimation
        self.detection_history = []
        self.max_history_length = 10
        
    async def load_model(self):
        """Load and initialize the YOLO model"""
        try:
            if YOLO_AVAILABLE:
                # Check if model file exists
                if not Path(self.model_path).exists():
                    print(f"Model file not found at {self.model_path}, downloading YOLOv8n...")
                    self.model_path = "yolov8n.pt"  # This will auto-download
                
                # Load YOLO model
                self.model = YOLO(self.model_path)
                
                # Move to appropriate device
                if self.device == 'cuda':
                    self.model.to('cuda')
                
                print(f"YOLOv8 model loaded on {self.device}")
                
                # Warm up the model
                await self.warmup_model()
                
            else:
                # Mock model for development/testing
                self.model = MockYOLOModel()
                print("Using mock YOLO model (ultralytics not available)")
                
        except Exception as e:
            print(f"Error loading model: {e}")
            # Fall back to mock model
            self.model = MockYOLOModel()
    
    async def warmup_model(self):
        """Warm up the model with dummy data"""
        try:
            dummy_frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
            
            # Run a few inference passes
            for _ in range(3):
                if YOLO_AVAILABLE and hasattr(self.model, 'predict'):
                    _ = self.model.predict(dummy_frame, verbose=False)
                await asyncio.sleep(0.1)
            
            self.warmup_completed = True
            print("Model warmup completed")
            
        except Exception as e:
            print(f"Model warmup failed: {e}")
            self.warmup_completed = True  # Continue anyway
    
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame for YOLO inference"""
        # Resize frame to model input size while maintaining aspect ratio
        h, w = frame.shape[:2]
        target_h, target_w = self.input_size
        
        # Calculate scaling factor
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        
        # Resize frame
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Create padded image
        padded = np.full((target_h, target_w, 3), 114, dtype=np.uint8)
        
        # Calculate padding offsets
        pad_x = (target_w - new_w) // 2
        pad_y = (target_h - new_h) // 2
        
        # Place resized image in center
        padded[pad_y:pad_y+new_h, pad_x:pad_x+new_w] = resized
        
        return padded
    
    async def detect_people(self, frame: np.ndarray) -> List[Tuple[float, float, float, float, float]]:
        """Detect people in the frame and return bounding boxes"""
        try:
            if YOLO_AVAILABLE and hasattr(self.model, 'predict'):
                # Run YOLO inference
                results = self.model.predict(
                    frame, 
                    conf=self.confidence_threshold,
                    iou=self.nms_threshold,
                    classes=self.crowd_classes,
                    verbose=False
                )
                
                detections = []
                
                if results and len(results) > 0:
                    result = results[0]
                    
                    if hasattr(result, 'boxes') and result.boxes is not None:
                        boxes = result.boxes
                        
                        # Convert to numpy if tensor
                        if hasattr(boxes.xyxy, 'cpu'):
                            xyxy = boxes.xyxy.cpu().numpy()
                            conf = boxes.conf.cpu().numpy()
                        else:
                            xyxy = boxes.xyxy
                            conf = boxes.conf
                        
                        # Process each detection
                        for i, box in enumerate(xyxy):
                            x1, y1, x2, y2 = box
                            confidence = conf[i]
                            
                            # Convert to x, y, w, h format
                            x, y = x1, y1
                            w, h = x2 - x1, y2 - y1
                            
                            # Filter small detections (likely false positives)
                            if w > 20 and h > 40:  # Minimum person size
                                detections.append((x, y, w, h, confidence))
                
                # Apply crowd-specific post-processing
                filtered_detections = self.filter_crowd_detections(detections)
                
                # Update detection history for tracking
                self.update_detection_history(filtered_detections)
                
                return filtered_detections
                
            else:
                # Use mock detection
                return await self.model.detect_people(frame)
                
        except Exception as e:
            print(f"Detection error: {e}")
            return []
    
    def filter_crowd_detections(self, detections: List[Tuple]) -> List[Tuple]:
        """Apply crowd-specific filtering to detections"""
        if not detections:
            return detections
        
        filtered = []
        
        for detection in detections:
            x, y, w, h, conf = detection
            
            # Size-based filtering for crowd scenarios
            area = w * h
            aspect_ratio = h / w if w > 0 else 0
            
            # Typical person aspect ratio and minimum size
            if (0.3 <= aspect_ratio <= 4.0 and  # Person-like aspect ratio
                area >= 800 and                  # Minimum area
                conf >= self.confidence_threshold):
                filtered.append(detection)
        
        # Apply Non-Maximum Suppression for overlapping detections
        filtered = self.apply_crowd_nms(filtered)
        
        return filtered
    
    def apply_crowd_nms(self, detections: List[Tuple], overlap_threshold: float = 0.3) -> List[Tuple]:
        """Apply Non-Maximum Suppression optimized for crowd scenarios"""
        if len(detections) <= 1:
            return detections
        
        # Convert to format suitable for NMS
        boxes = []
        scores = []
        
        for x, y, w, h, conf in detections:
            boxes.append([x, y, x + w, y + h])
            scores.append(conf)
        
        boxes = np.array(boxes, dtype=np.float32)
        scores = np.array(scores, dtype=np.float32)
        
        # Apply OpenCV's NMS
        indices = cv2.dnn.NMSBoxes(
            boxes.tolist(),
            scores.tolist(),
            self.confidence_threshold,
            overlap_threshold
        )
        
        # Filter detections based on NMS results
        filtered_detections = []
        if len(indices) > 0:
            indices = indices.flatten()
            for i in indices:
                filtered_detections.append(detections[i])
        
        return filtered_detections
    
    def update_detection_history(self, detections: List[Tuple]):
        """Update detection history for temporal consistency"""
        self.detection_history.append({
            'timestamp': time.time(),
            'count': len(detections),
            'detections': detections
        })
        
        # Keep only recent history
        if len(self.detection_history) > self.max_history_length:
            self.detection_history.pop(0)
    
    def get_crowd_statistics(self) -> Dict:
        """Get crowd statistics from detection history"""
        if not self.detection_history:
            return {'current_count': 0, 'average_count': 0, 'trend': 'stable'}
        
        counts = [entry['count'] for entry in self.detection_history]
        current_count = counts[-1]
        average_count = np.mean(counts)
        
        # Determine trend
        if len(counts) >= 3:
            recent_avg = np.mean(counts[-3:])
            older_avg = np.mean(counts[:-3]) if len(counts) > 3 else recent_avg
            
            if recent_avg > older_avg * 1.2:
                trend = 'increasing'
            elif recent_avg < older_avg * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        return {
            'current_count': current_count,
            'average_count': round(average_count, 1),
            'trend': trend,
            'history_length': len(counts)
        }
    
    def estimate_crowd_density(self, detections: List[Tuple], frame_shape: Tuple[int, int]) -> Dict:
        """Estimate crowd density from detections"""
        if not detections:
            return {'density': 0, 'level': 'empty'}
        
        frame_area = frame_shape[0] * frame_shape[1]
        person_count = len(detections)
        
        # Calculate average person area
        total_person_area = sum(w * h for x, y, w, h, conf in detections)
        avg_person_area = total_person_area / person_count if person_count > 0 else 0
        
        # Estimate crowd density
        if avg_person_area > 0:
            estimated_total_people = frame_area / (avg_person_area * 4)  # Account for occlusion
            density = min(person_count / estimated_total_people, 1.0) if estimated_total_people > 0 else 0
        else:
            density = person_count / (frame_area / 10000)  # Fallback calculation
        
        # Categorize density level
        if density < 0.1:
            level = 'low'
        elif density < 0.3:
            level = 'moderate'
        elif density < 0.6:
            level = 'high'
        else:
            level = 'critical'
        
        return {
            'density': round(density, 3),
            'level': level,
            'person_count': person_count,
            'avg_person_area': round(avg_person_area, 2)
        }
    
    async def cleanup(self):
        """Clean up model resources"""
        try:
            if self.model and hasattr(self.model, 'cpu'):
                self.model.cpu()
            
            # Clear CUDA cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            print("People counter cleanup completed")
            
        except Exception as e:
            print(f"Cleanup error: {e}")


class MockYOLOModel:
    """Mock YOLO model for testing and development"""
    
    def __init__(self):
        self.confidence_threshold = 0.5
        
    async def detect_people(self, frame: np.ndarray) -> List[Tuple[float, float, float, float, float]]:
        """Mock people detection with simulated results"""
        await asyncio.sleep(0.05)  # Simulate processing time
        
        h, w = frame.shape[:2]
        
        # Generate random detections for testing
        num_people = np.random.randint(5, 50)  # Random crowd size
        detections = []
        
        for _ in range(num_people):
            # Random position
            x = np.random.randint(0, max(1, w - 100))
            y = np.random.randint(0, max(1, h - 150))
            
            # Random but realistic person size
            person_w = np.random.randint(30, 80)
            person_h = np.random.randint(60, 180)
            
            # Random confidence
            conf = np.random.uniform(0.6, 0.95)
            
            detections.append((float(x), float(y), float(person_w), float(person_h), conf))
        
        return detections