# DHSILED System Installation Guide

Complete installation guide for the DHSILED Stadium Crowd Monitoring System.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Prerequisites](#prerequisites)
3. [Edge Computing Setup](#edge-computing-setup)
4. [Central Services Setup](#central-services-setup)
5. [Network Configuration](#network-configuration)
6. [Verification](#verification)
7. [Post-Installation Tasks](#post-installation-tasks)
8. [Troubleshooting](#troubleshooting)
9. [Next Steps](#next-steps)
10. [Support](#support)

---

## System Requirements

### Edge Devices (Raspberry Pi)

* **Hardware:**

  * Raspberry Pi 4 Model B (4GB RAM minimum, 8GB recommended)
  * Camera Module v2 or compatible USB camera
  * 32GB+ microSD card (Class 10, UHS-1)
  * Power supply (5V 3A)
  * Network connectivity (Ethernet or WiFi)

* **Software:**

  * Python 3.9 or higher
  * 10GB+ free disk space

### Central Server

* **Hardware:**

  * CPU: 8+ cores
  * RAM: 16GB minimum, 32GB recommended
  * Storage: 500GB+ SSD
  * Network: 1Gbps

* **Software:**

  * Ubuntu 22.04 LTS or similar
  * Docker 24.x
  * Docker Compose v2.x
  * Kubernetes 1.28+ (optional, for production)

---

## Prerequisites

### 1. Install Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker-compose --version
```

### 2. Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y git python3 python3-pip curl wget vim htop
```

### 3. Clone Repository

```bash
git clone https://github.com/your-org/dhsiled-system.git
cd dhsiled-system
```

## Edge Computing Setup

### Option A: Automated Setup (Recommended) using Ansible

```bash
# Install Ansible
sudo apt install -y ansible

# Configure inventory
cat > inventory.ini <<EOF
[raspberry_pi]
rpi-g01 ansible_host=192.168.1.101 grid_id=G01
rpi-g02 ansible_host=192.168.1.102 grid_id=G02

[raspberry_pi:vars]
ansible_user=pi
ansible_ssh_pass=raspberry
mqtt_broker=192.168.1.100
EOF

# Run setup playbook
cd deployment/ansible
ansible-playbook -i ../../inventory.ini raspberry-pi-setup.yml
ansible-playbook -i ../../inventory.ini edge-deployment.yml
```

### Option B: Manual Setup

#### Step 1: Prepare Raspberry Pi

```bash
ssh pi@192.168.1.101
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-opencv libatlas-base-dev libhdf5-dev git
```

#### Step 2: Install Python Dependencies

```bash
sudo mkdir -p /opt/dhsiled
sudo chown pi:pi /opt/dhsiled
cd /opt/dhsiled
rsync -av edge-computing/ pi@192.168.1.101:/opt/dhsiled/
pip3 install -r requirements.txt --no-cache-dir
```

#### Step 3: Configure Grid Settings

```bash
nano config/grid_config.yaml
```

#### Step 4: Create Systemd Service

```bash
sudo nano /etc/systemd/system/dhsiled-edge.service
```

```ini
[Unit]
Description=DHSILED Edge Processor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/dhsiled
ExecStart=/usr/bin/python3 /opt/dhsiled/src/main.py
Restart=always
RestartSec=10
Environment="GRID_ID=G01"
Environment="MQTT_HOST=192.168.1.100"

[Install]
WantedBy=multi-user.target
```

#### Step 5: Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable dhsiled-edge
sudo systemctl start dhsiled-edge
sudo systemctl status dhsiled-edge
sudo journalctl -u dhsiled-edge -f
```

## Central Services Setup

### Option A: Docker Compose (Recommended for Testing)

```bash
cp .env.example .env
nano .env
docker-compose up -d
docker-compose ps
docker-compose logs -f
```

Services will be available at:

* Command Center: [http://localhost](http://localhost)
* Backend API: [http://localhost:5000](http://localhost:5000)
* WebSocket: ws://localhost:8080
* MongoDB: localhost:27017
* MQTT Broker: localhost:1883
* Ditto UI: [http://localhost:8080](http://localhost:8080)

### Option B: Kubernetes (Production)

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube start --cpus=4 --memory=8192
cd deployment/k8s
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: dhsiled
EOF
kubectl apply -f central-services.yaml
kubectl apply -f monitoring.yaml
kubectl get pods -n dhsiled
kubectl get services -n dhsiled
kubectl port-forward -n dhsiled svc/command-center 8080:80
kubectl port-forward -n dhsiled svc/backend 5000:5000
```

## Network Configuration

### Firewall Rules

**Central Server:**

```bash
sudo ufw allow 1883/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5000/tcp
sudo ufw allow 8080/tcp
sudo ufw enable
```

**Edge Devices:**

```bash
sudo ufw allow 22/tcp
sudo ufw allow out 1883/tcp
sudo ufw enable
```

### DNS Configuration

Add entries to `/etc/hosts` or configure DNS server:

```
192.168.1.100  dhsiled-server
192.168.1.100  mosquitto
192.168.1.100  backend
192.168.1.101  edge-g01
192.168.1.102  edge-g02
```

## Verification

```bash
# Check Edge Processors
curl http://192.168.1.101:9090/health

# Verify MQTT Communication
mosquitto_sub -h localhost -t "dhsiled/grids/#" -v

# Test Backend API
curl http://localhost:5000/api/grids
curl http://localhost:5000/api/health
```

Open browser: [http://localhost](http://localhost) to verify 3D stadium visualization, real-time grid updates, alert panel, and system health metrics.

Check Monitoring:

* Prometheus: [http://localhost:9090](http://localhost:9090)
* Grafana: [http://localhost:3001](http://localhost:3001) (admin/admin123)
* Alertmanager: [http://localhost:9093](http://localhost:9093)

## Post-Installation Tasks

```bash
# Download ML Models
cd /opt/dhsiled/models
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
ls -lh models/

# Configure Cameras
raspistill -o test.jpg
ls -l /dev/video*
nano /opt/dhsiled/config/grid_config.yaml

# Set Up Backups
sudo crontab -e
# Add daily backup at 2 AM
0 2 * * * /opt/dhsiled/data-storage/backup-scripts/backup-mongodb.sh

# Configure Monitoring Alerts
nano monitoring/alertmanager/config.yml
docker-compose restart alertmanager
```

## Troubleshooting

```bash
# Edge Processor Won't Start
sudo journalctl -u dhsiled-edge -n 50
ls -l /dev/video0
ping mosquitto-server-ip
telnet mosquitto-server-ip 1883
pip3 install -r requirements.txt --no-cache-dir

# MQTT Connection Issues
mosquitto_sub -h localhost -t test
docker-compose logs mosquitto
docker-compose restart mosquitto

# High CPU/Memory Usage
htop
nano config/grid_config.yaml

# Cannot Access Command Center
docker-compose ps
docker-compose logs command-center
docker-compose restart command-center
```

## Next Steps

* Read Configuration Guide
* Review API Documentation
* Set up monitoring dashboards
* Configure alert notifications
* Train staff on system usage

## Support

* GitHub Issues: [https://github.com/your-org/dhsiled-system/issues](https://github.com/your-org/dhsiled-system/issues)
* Documentation: [https://docs.dhsiled.org](https://docs.dhsiled.org)
* Email: [support@dhsiled.org](mailto:support@dhsiled.org)

Installation complete! 🎉
