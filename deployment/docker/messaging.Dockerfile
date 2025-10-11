# ============================================================================
# DHSILED Messaging Bridge Dockerfile
# Eclipse Ditto bridge for digital twin synchronization
# ============================================================================

FROM node:18-alpine

LABEL maintainer="DHSILED Team"
LABEL description="MQTT to Ditto bridge"

WORKDIR /app

# ============================================================================
# Install Dependencies
# ============================================================================
COPY messaging/ditto-bridge/package.json messaging/ditto-bridge/package-lock.json ./

RUN npm ci --only=production

# ============================================================================
# Copy Application Code
# ============================================================================
COPY messaging/ditto-bridge/ .

# ============================================================================
# Environment Variables
# ============================================================================
ENV NODE_ENV=production
ENV MQTT_HOST=mosquitto
ENV MQTT_PORT=1883
ENV DITTO_HOST=ditto-gateway
ENV DITTO_PORT=8080

# ============================================================================
# Health Check
# ============================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD node -e "process.exit(0)"

# ============================================================================
# Run Application
# ============================================================================
CMD ["node", "src/bridge.js"]