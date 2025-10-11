# ============================================================================
# DHSILED Command Center Dockerfile
# Multi-stage build for React application
# ============================================================================

# ============================================================================
# Stage 1: Build React Application
# ============================================================================
FROM node:18-alpine AS builder

LABEL maintainer="DHSILED Team"

WORKDIR /app

# Copy package files
COPY command-center/package.json command-center/package-lock.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application source
COPY command-center/ .

# Build the application
RUN npm run build

# ============================================================================
# Stage 2: Production Server with Nginx
# ============================================================================
FROM nginx:1.25-alpine

# Copy built files from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY deployment/docker/nginx-command-center.conf /etc/nginx/conf.d/default.conf

# Create nginx cache directory
RUN mkdir -p /var/cache/nginx/client_temp && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]