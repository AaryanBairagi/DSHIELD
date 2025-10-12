# DHSILED Troubleshooting Guide

Common issues and solutions for the DHSILED system.

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Edge Processor Issues](#edge-processor-issues)
3. [Network & MQTT Issues](#network--mqtt-issues)
4. [Database Issues](#database-issues)
5. [Frontend Issues](#frontend-issues)
6. [Performance Issues](#performance-issues)
7. [Camera Issues](#camera-issues)
8. [ML Model Issues](#ml-model-issues)
9. [Alert System Issues](#alert-system-issues)
10. [Deployment Issues](#deployment-issues)

---

## Quick Diagnostics

### System Health Check Script

```bash
#!/bin/bash
# Quick system health check

echo "=========================================="
echo "DHSILED System Health Check"
echo "=========================================="

# Check edge processor
echo -e "\n[1] Edge Processor Status:"
sudo systemctl status dhsiled-edge | grep Active

# Check MQTT connectivity
echo -e "\n[2] MQTT Broker:"
mosquitto_sub -h localhost -t test -C 1 -W 2 && echo "✓ Connected" || echo "✗ Failed"

# Check disk space
echo -e "\n[3] Disk Usage:"
df -h | grep -E "/$|/opt"

# Check CPU temperature
echo -e "\n[4] CPU Temperature:"
vcgencmd measure_temp 2>/dev/null || echo "Command not available"

# Check memory
echo -e "\n[5] Memory Usage:"
free -h | grep Mem

# Check network
echo -e "\n[6] Network Connectivity:"
ping -c 1 8.8.8.8 >/dev/null 2>&1 && echo "✓ Internet connected" || echo "✗ No internet"

# Check camera
echo -e "\n[7] Camera Status:"
ls -l /dev/video* 2>/dev/null || echo "No camera detected"

# Check logs for errors
echo -e "\n[8] Recent Errors:"
sudo journalctl -u dhsiled-edge --since "10 minutes ago" | grep -i error | tail -5

echo -e "\n=========================================="
```

Save as `check_health.sh` and run:

```bash
chmod +x check_health.sh
./check_health.sh
```

## Edge Processor Issues

### Issue: Service Won't Start

**Symptoms:**

```bash
$ sudo systemctl status dhsiled-edge
● dhsiled-edge.service - DHSILED Edge Processor
   Loaded: loaded
   Active: failed (Result: exit-code)
```

**Solutions:**

1. **Check Logs:**

```bash
sudo journalctl -u dhsiled-edge -n 50 --no-pager
```

2. **Common Causes:**

* **Missing Dependencies:**

```bash
pip3 install opencv-python
pip3 install -r /opt/dhsiled/requirements.txt
```

* **Permission Issues:**

```bash
sudo chown -R pi:pi /opt/dhsiled
chmod +x /opt/dhsiled/src/main.py
```

* **Configuration Errors:**

```bash
python3 -c "import yaml; with open('/opt/dhsiled/config/grid_config.yaml') as f: yaml.safe_load(f); print('Config valid')"
```

3. **Test Manual Start:**

```bash
cd /opt/dhsiled
python3 src/main.py
```

### Issue: High CPU Usage

**Symptoms:** CPU usage >90%, unresponsive system, frame drops
**Solutions:**

1. Reduce Processing Load in `grid_config.yaml`:

```yaml
processing:
  frame_skip: 1
  enable_behavior_analysis: false
```

2. Lower Model Complexity:

```yaml
models:
  people_counter: "models/yolov8n.pt"
  confidence_threshold: 0.6
```

3. Limit Frame Rate:

```yaml
camera:
  fps: 15
  width: 1280
  height: 720
```

4. Monitor Memory Leaks:

```bash
watch -n 5 "ps aux | grep python | head -1"
```

### Issue: Service Crashes Randomly

**Solutions:**

1. Check memory with `free -h`
2. Increase Swap (2GB example)
3. Add watchdog and configure systemd `Restart=always`

## Network & MQTT Issues

### Issue: Cannot Connect to MQTT Broker

**Solutions:**

1. Verify broker running:

```bash
sudo netstat -tlnp | grep 1883
```

2. Test connection:

```bash
mosquitto_pub -h 192.168.1.100 -t test -m "hello"
```

3. Check firewall:

```bash
sudo ufw allow 1883/tcp
sudo ufw reload
```

4. Verify MQTT config:

```bash
cat /opt/dhsiled/config/mqtt_config.yaml | grep -A5 broker
```

### Issue: Messages Not Received

1. Check subscriptions:

```bash
mosquitto_sub -h localhost -t "dhsiled/#" -v
```

2. Verify QoS:

```yaml
mqtt:
  qos:
    default: 1
```

3. Check message queue

### Issue: Network Latency

1. Ping test to server
2. Reduce message size in `processing.send_detection_boxes`
3. Use wired connection

## Database Issues

### MongoDB Connection Failed

1. Check status and logs
2. Restart MongoDB
3. Verify connection string

### Database Full

1. Check disk usage
2. Clean old data
3. Increase storage

## Frontend Issues

### Command Center Not Loading

1. Check browser console
2. Verify backend/API connection
3. Clear cache and hard refresh
4. Check docker logs

### 3D Visualization Not Rendering

1. Check WebGL support
2. Enable hardware acceleration
3. Update graphics drivers
4. Try different browser

### Real-time Updates Not Working

1. Verify WebSocket connection
2. Check WebSocket server
3. Inspect network tab

## Performance Issues

### Slow Frame Processing

1. Profile code
2. Optimize model input and quantization
3. Reduce frame size

### Dashboard Lag

1. Reduce update frequency
2. Limit grid count
3. Optimize 3D rendering

## Camera Issues

### Camera Not Detected

1. Check connections and devices
2. Enable camera interface
3. Check permissions
4. Try different device index

### Poor Image Quality

1. Adjust brightness, contrast, exposure
2. Improve lighting
3. Clean lens
4. Focus camera

## ML Model Issues

### Low Detection Accuracy

1. Adjust confidence threshold
2. Improve camera position
3. Retrain model

### Model Loading Failed

1. Download models
2. Check file permissions
3. Verify path in config

## Alert System Issues

### Alerts Not Sent

1. Check Alertmanager logs and config
2. Test email configuration
3. Verify webhook

## Deployment Issues

### Docker Compose Fails

1. Check port conflicts
2. Clean Docker
3. Check logs

### Kubernetes Pods Crashing

1. Check pod logs
2. Check resource usage
3. Verify secrets

## Getting Help

### Collect Diagnostic Information

```bash
#!/bin/bash
BUNDLE_DIR="dhsiled_diagnostics_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BUNDLE_DIR"
uname -a > "$BUNDLE_DIR/system_info.txt"
free -h >> "$BUNDLE_DIR/system_info.txt"
df -h >> "$BUNDLE_DIR/system_info.txt"
sudo journalctl -u dhsiled-edge --since "1 hour ago" > "$BUNDLE_DIR/service_logs.txt"
cp /opt/dhsiled/config/*.yaml "$BUNDLE_DIR/"
docker-compose ps > "$BUNDLE_DIR/docker_status.txt"
docker-compose logs --tail=200 > "$BUNDLE_DIR/docker_logs.txt"
tar -czf "$BUNDLE_DIR.tar.gz" "$BUNDLE_DIR"
echo "Diagnostic bundle created: $BUNDLE_DIR.tar.gz"
```

Support Channels:

* GitHub Issues: [https://github.com/your-org/dhsiled-system/issues](https://github.com/your-org/dhsiled-system/issues)
* Documentation: [https://docs.dhsiled.org](https://docs.dhsiled.org)
* Email: [support@dhsiled.org](mailto:support@dhsiled.org)
* Community Forum: [https://forum.dhsiled.org](https://forum.dhsiled.org)

## Preventive Maintenance

**Daily Checks**

* Verify edge processors online
* Check for critical alerts
* Review health dashboard

**Weekly Checks**

* Review logs for errors
* Check disk usage
* Verify backups
* Test alert notifications

**Monthly Checks**

* Update system packages
* Clean old data
* Check camera alignment
* Test failover procedures
* Review performance metrics

✅ **troubleshooting.md COMPLETE!**
