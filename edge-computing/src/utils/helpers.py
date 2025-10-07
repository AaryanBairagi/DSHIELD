#!/usr/bin/env python3
"""
Utility helper functions for DHSILED Edge Computing
"""

import os
import cv2
import numpy as np
import asyncio
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import json

def ensure_directories(paths: List[str]):
    """Ensure directories exist, create if they don't"""
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)
        print(f"Directory ensured: {path}")

async def save_frame(frame: np.ndarray, filepath: str, quality: int = 95):
    """Save frame to disk asynchronously"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save image
        def _save():
            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        
        await asyncio.to_thread(_save)
        return True
        
    except Exception as e:
        print(f"Error saving frame: {e}")
        return False

def calculate_density(people_count: int, area_sqm: float) -> float:
    """Calculate crowd density (people per square meter)"""
    if area_sqm <= 0:
        return 0.0
    return people_count / area_sqm

def generate_alert_id() -> str:
    """Generate unique alert ID"""
    timestamp = datetime.now(timezone.utc).isoformat()
    random_component = os.urandom(8).hex()
    alert_string = f"{timestamp}-{random_component}"
    
    # Create short hash
    hash_object = hashlib.sha256(alert_string.encode())
    short_hash = hash_object.hexdigest()[:12]
    
    return f"ALT-{short_hash.upper()}"

def calculate_iou(box1: Tuple[float, float, float, float], 
                  box2: Tuple[float, float, float, float]) -> float:
    """Calculate Intersection over Union for two bounding boxes"""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    # Calculate intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i < x1_i or y2_i < y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    
    # Calculate union
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    if union <= 0:
        return 0.0
    
    return intersection / union

def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

def calculate_fps(frame_times: List[float], window_size: int = 30) -> float:
    """Calculate FPS from frame timestamps"""
    if len(frame_times) < 2:
        return 0.0
    
    recent_times = frame_times[-window_size:]
    time_diff = recent_times[-1] - recent_times[0]
    
    if time_diff <= 0:
        return 0.0
    
    return (len(recent_times) - 1) / time_diff

def smooth_values(values: List[float], window_size: int = 5) -> List[float]:
    """Apply moving average smoothing to values"""
    if len(values) < window_size:
        return values
    
    smoothed = []
    for i in range(len(values)):
        start_idx = max(0, i - window_size + 1)
        window = values[start_idx:i + 1]
        smoothed.append(sum(window) / len(window))
    
    return smoothed

def create_heatmap(density_map: np.ndarray, colormap: int = cv2.COLORMAP_JET) -> np.ndarray:
    """Create heatmap visualization from density map"""
    # Normalize to 0-255
    normalized = cv2.normalize(density_map, None, 0, 255, cv2.NORM_MINMAX)
    normalized = normalized.astype(np.uint8)
    
    # Apply colormap
    heatmap = cv2.applyColorMap(normalized, colormap)
    
    return heatmap

def draw_bounding_boxes(frame: np.ndarray, 
                        detections: List[Tuple[float, float, float, float, float]],
                        color: Tuple[int, int, int] = (0, 255, 0),
                        thickness: int = 2) -> np.ndarray:
    """Draw bounding boxes on frame"""
    result = frame.copy()
    
    for detection in detections:
        x, y, w, h, conf = detection
        x1, y1 = int(x), int(y)
        x2, y2 = int(x + w), int(y + h)
        
        # Draw rectangle
        cv2.rectangle(result, (x1, y1), (x2, y2), color, thickness)
        
        # Draw confidence
        text = f"{conf:.2f}"
        cv2.putText(result, text, (x1, y1 - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    return result

def calculate_centroid(box: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """Calculate centroid of bounding box"""
    x, y, w, h = box
    cx = x + w / 2
    cy = y + h / 2
    return (cx, cy)

def euclidean_distance(point1: Tuple[float, float], 
                       point2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points"""
    return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def resize_with_aspect_ratio(image: np.ndarray, 
                             target_size: Tuple[int, int],
                             padding_color: Tuple[int, int, int] = (114, 114, 114)) -> np.ndarray:
    """Resize image maintaining aspect ratio with padding"""
    h, w = image.shape[:2]
    target_w, target_h = target_size
    
    # Calculate scaling factor
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    
    # Resize image
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    # Create padded image
    padded = np.full((target_h, target_w, 3), padding_color, dtype=np.uint8)
    
    # Calculate padding offsets
    pad_x = (target_w - new_w) // 2
    pad_y = (target_h - new_h) // 2
    
    # Place resized image in center
    padded[pad_y:pad_y+new_h, pad_x:pad_x+new_w] = resized
    
    return padded

def clip_boxes(boxes: List[Tuple[float, float, float, float]], 
               image_shape: Tuple[int, int]) -> List[Tuple[float, float, float, float]]:
    """Clip bounding boxes to image boundaries"""
    h, w = image_shape[:2]
    clipped_boxes = []
    
    for box in boxes:
        x, y, box_w, box_h = box
        x = max(0, min(x, w - 1))
        y = max(0, min(y, h - 1))
        box_w = max(1, min(box_w, w - x))
        box_h = max(1, min(box_h, h - y))
        clipped_boxes.append((x, y, box_w, box_h))
    
    return clipped_boxes

def calculate_overlap_ratio(box1: Tuple[float, float, float, float],
                           box2: Tuple[float, float, float, float]) -> float:
    """Calculate overlap ratio between two boxes"""
    x1_1, y1_1, w1, h1 = box1
    x1_2, y1_2, w2, h2 = box2
    
    x2_1, y2_1 = x1_1 + w1, y1_1 + h1
    x2_2, y2_2 = x1_2 + w2, y1_2 + h2
    
    # Calculate intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i < x1_i or y2_i < y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    area1 = w1 * h1
    
    if area1 <= 0:
        return 0.0
    
    return intersection / area1

def load_json(filepath: str, default: Any = None) -> Any:
    """Load JSON file safely"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON from {filepath}: {e}")
        return default

def save_json(data: Any, filepath: str, indent: int = 2) -> bool:
    """Save data to JSON file"""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=indent)
        return True
    except Exception as e:
        print(f"Error saving JSON to {filepath}: {e}")
        return False

def timestamp_to_string(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Convert Unix timestamp to formatted string"""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(format_str)

def string_to_timestamp(time_string: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> float:
    """Convert formatted string to Unix timestamp"""
    dt = datetime.strptime(time_string, format_str)
    return dt.replace(tzinfo=timezone.utc).timestamp()

def get_file_size(filepath: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(filepath)
    except:
        return 0

def cleanup_old_files(directory: str, max_age_hours: int = 24):
    """Delete files older than specified hours"""
    try:
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        deleted_count = 0
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                
                if file_age > max_age_seconds:
                    os.remove(filepath)
                    deleted_count += 1
        
        return deleted_count
        
    except Exception as e:
        print(f"Error cleaning up old files: {e}")
        return 0

def create_thumbnail(image: np.ndarray, max_size: Tuple[int, int] = (320, 240)) -> np.ndarray:
    """Create thumbnail of image"""
    h, w = image.shape[:2]
    max_w, max_h = max_size
    
    # Calculate scale
    scale = min(max_w / w, max_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    
    # Resize
    thumbnail = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    return thumbnail

class PerformanceTimer:
    """Context manager for timing code execution"""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.elapsed = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time
        print(f"{self.name} took {self.elapsed*1000:.2f}ms")
        return False

class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    
    def is_allowed(self) -> bool:
        """Check if call is allowed"""
        current_time = time.time()
        
        # Remove old calls
        self.calls = [t for t in self.calls if current_time - t < self.period]
        
        # Check limit
        if len(self.calls) < self.max_calls:
            self.calls.append(current_time)
            return True
        
        return False
    
    def time_until_allowed(self) -> float:
        """Get time until next call is allowed"""
        if len(self.calls) < self.max_calls:
            return 0.0
        
        oldest_call = min(self.calls)
        return max(0.0, self.period - (time.time() - oldest_call))