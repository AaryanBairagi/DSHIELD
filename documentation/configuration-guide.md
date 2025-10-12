# DHSILED Configuration Guide

Comprehensive configuration guide for customizing the DHSILED system.

---

## Table of Contents

1. [Grid Configuration](#grid-configuration)
2. [Camera Settings](#camera-settings)
3. [ML Model Configuration](#ml-model-configuration)
4. [MQTT Configuration](#mqtt-configuration)
5. [Database Configuration](#database-configuration)
6. [Monitoring Configuration](#monitoring-configuration)
7. [Alert Configuration](#alert-configuration)
8. [Performance Tuning](#performance-tuning)

---

## Grid Configuration

### Basic Grid Settings

**File:** `edge-computing/config/grid_config.yaml`

```yaml
grid:
  id: "G01"
  zone_type: "stand"
  area_sqm: 750
  capacity: 200
  location:
    section: "North Stand"
    level: 1
    position:
      x: -75
      y: 5
      z: -60
```

### Grid ID Naming Convention

```
Format: G + two-digit number
Examples: G01, G02, ..., G48
Use sequential numbering for easy management
```

### Zone Types

```
stand      - Spectator seating areas
concourse  - Walkways and corridors
exit       - Emergency exits and doorways
emergency  - Critical monitoring zones
```

### Density Thresholds

```yaml
density_thresholds:
  normal: 60
  moderate: 100
  high: 150
  critical: 200
```

### Calculate Thresholds

```
normal   = area_sqm * 0.08
moderate = area_sqm * 0.13
high     = area_sqm * 0.20
critical = area_sqm * 0.27
```

---

## Camera Settings

### Basic Camera Configuration

```yaml
camera:
  device_index: 0
  width: 1920
  height: 1080
  fps: 30
  rotation: 0
  flip_horizontal: false
  flip_vertical: false
  brightness: 50
  contrast: 50
```

### Best Practices

```
Height: 3-5 meters, avoid <2m or >8m
Angle: 30-45° from horizontal
Lighting: Minimum 50 lux; IR recommended for night events
```

### Advanced Camera Settings

```yaml
camera:
  picamera_settings:
    exposure_mode: "auto"
    awb_mode: "auto"
    iso: 0
    sharpness: 0
  v4l2_settings:
    exposure_auto: 3
    white_balance_auto: 1
    focus_auto: 1
```

---

## ML Model Configuration

### Model Paths and Parameters

```yaml
models:
  people_counter: "models/yolov8n-crowd.pt"
  behavior_analyzer: "models/behavior_lstm.h5"
  emergency_detector: "models/emergency_cnn.h5"
  confidence_threshold: 0.5
  sequence_length: 16
```

### Performance vs Accuracy Tuning

```yaml
models:
  confidence_threshold: 0.6
  use_quantization: true
  batch_size: 1

models:
  confidence_threshold: 0.4
  use_quantization: false
  batch_size: 4
```

---

## MQTT Configuration

### Basic MQTT Settings

```yaml
mqtt:
  broker:
    host: "192.168.1.100"
    port: 1883
    protocol: "tcp"
  auth:
    enabled: false
    username: "dhsiled_user"
    password: "secure_password"
  connection:
    keepalive: 60
    clean_session: true
    reconnect_delay: 5
  qos:
    default: 1
    status_messages: 1
    alerts: 2
    health_data: 0
```

### Topic Structure

```text
dhsiled/
├── grids/
│   ├── {grid_id}/
│   │   ├── status
│   │   ├── alerts
│   │   ├── health
│   │   └── commands
│   └── +/status
└── system/
    ├── broadcast
    └── firmware
```

---

## Database Configuration

### MongoDB Settings

```yaml
environment:
  MONGO_INITDB_ROOT_USERNAME: dhsiled_admin
  MONGO_INITDB_ROOT_PASSWORD: change_this_password
  MONGO_INITDB_DATABASE: dhsiled
```

### Data Retention Policies

```javascript
db.grids.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 2592000 });
db.health.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 2592000 });
db.alerts.createIndex({ "resolved_at": 1 }, { expireAfterSeconds: 7776000, partialFilterExpression: { "resolved": true } });
```

### InfluxDB Settings

```yaml
environment:
  DOCKER_INFLUXDB_INIT_BUCKET: crowd_metrics
  DOCKER_INFLUXDB_INIT_RETENTION: 30d
  DOCKER_INFLUXDB_INIT_ORG: dhsiled
```

---

## Monitoring Configuration

### Prometheus

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'dhsiled-production'
    environment: 'production'
```

### Grafana Data Source

```yaml
datasources:
  - name: InfluxDB-DHSILED
    type: influxdb
    url: http://influxdb:8086
    jsonData:
      version: Flux
      organization: dhsiled
      defaultBucket: crowd_metrics
```

### Custom Metrics

```python
from prometheus_client import Gauge, Counter

people_count_gauge = Gauge('crowd_people_count', 'Current people count in grid', ['grid_id'])
alert_counter = Counter('alerts_total', 'Total alerts generated', ['grid_id', 'severity'])
```

---

## Alert Configuration

### Alertmanager

```yaml
receivers:
  - name: 'email-alerts'
    email_configs:
      - to: 'ops@example.com'
        from: 'dhsiled@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'dhsiled@example.com'
        auth_password: 'app_password'
  - name: 'slack-alerts'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#dhsiled-alerts'
        title: 'DHSILED Alert'
```

### Custom Alert Rules

```yaml
groups:
  - name: custom_alerts
    rules:
      - alert: CustomCrowdThreshold
        expr: crowd_people_count > 175
        for: 2m
        labels:
          severity: high
          team: operations
        annotations:
          summary: "Custom threshold exceeded in {{ $labels.grid_id }}"
          description: "Count: {{ $value }}"
```

---

## Performance Tuning

### Edge Device Optimization

```yaml
performance:
  num_threads: 4
  use_gpu: false
  frame_skip: 0
  batch_size: 1
  optimize_inference: true
  use_quantization: false
```

### Memory Management

```yaml
processing:
  max_frame_buffer: 100
  behavior_analysis_interval: 16
  video_buffer_retention_hours: 24
  max_buffer_size_mb: 5000
```

### Network Optimization

```yaml
network:
  max_connections: 10
  connection_timeout: 30
  retry_attempts: 3
  retry_delay: 5
  max_queue_size: 1000
  queue_overflow_strategy: "drop_oldest"
```

### Environment Variables

```bash
export GRID_ID=G01
export ZONE_TYPE=stand
export MQTT_HOST=192.168.1.100
export MQTT_PORT=1883
export LOG_LEVEL=INFO
export LOG_FILE=/opt/dhsiled/data/logs/edge.log
export MODEL_PATH=/opt/dhsiled/models
export USE_MOCK_MODELS=false
export MONGODB_URI=mongodb://localhost:27017/dhsiled
export INFLUXDB_URL=http://localhost:8086
export API_PORT=5000
export API_HOST=0.0.0.0
```

### Configuration Validation

```bash
yamllint config/grid_config.yaml
mosquitto_pub -h localhost -t test -m "test"
v4l2-ctl --list-devices
python3 -c "from ultralytics import YOLO; model = YOLO('models/yolov8n.pt'); print('Model loaded successfully')"
```

### Best Practices

```
Always backup configurations before changes
Use version control for configuration files
Test changes in development environment first
Document custom configurations
Review logs after changes
Set up monitoring alerts for configuration issues
```

---

### Next Steps

```
Troubleshooting Guide
API Documentation
Performance optimization tips
```

✅ **configuration-guide.md COMPLETE!**
