# ============================================================================
# DHSILED Edge Processor Dockerfile
# Optimized for Raspberry Pi and edge devices
# ============================================================================

FROM python:3.10-slim

LABEL maintainer="DHSILED Team"
LABEL description="Edge processor for crowd monitoring"

WORKDIR /app

# ============================================================================
# Install System Dependencies
# ============================================================================
RUN apt-get update && apt-get install -y \
    # OpenCV dependencies
    libopencv-dev \
    python3-opencv \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # ML libraries dependencies
    libatlas-base-dev \
    libhdf5-dev \
    libhdf5-serial-dev \
    libharfbuzz0b \
    libwebp7 \
    libjasper1 \
    libilmbase25 \
    libopenexr25 \
    libgstreamer1.0-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libgtk-3-0 \
    # Utilities
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# Copy Requirements and Install Python Dependencies
# ============================================================================
COPY edge-computing/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Copy Application Code
# ============================================================================
COPY edge-computing/ .

# ============================================================================
# Create Necessary Directories
# ============================================================================
RUN mkdir -p \
    data/logs \
    data/video_buffer \
    data/analytics \
    models

# ============================================================================
# Environment Variables
# ============================================================================
ENV PYTHONUNBUFFERED=1
ENV OPENCV_VIDEOIO_PRIORITY_MSMF=0
ENV GRID_ID=G01
ENV MQTT_HOST=mosquitto
ENV MQTT_PORT=1883

# ============================================================================
# Health Check
# ============================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# ============================================================================
# Run Application
# ============================================================================
CMD ["python", "src/main.py"]