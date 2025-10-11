#!/bin/bash

# ============================================================================
# InfluxDB Backup Script for DHSILED
# Automated backup of InfluxDB time series data
# ============================================================================

set -e

# Configuration
BACKUP_DIR="/backups/influxdb"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="influxdb_backup_${TIMESTAMP}"
INFLUX_TOKEN="dhsiled-super-secret-token-2024"
INFLUX_ORG="dhsiled"
INFLUX_BUCKET="crowd_metrics"
RETENTION_DAYS=30

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "DHSILED InfluxDB Backup Script"
echo "============================================"
echo "Timestamp: $(date)"
echo "Backup Directory: ${BACKUP_DIR}"
echo ""

# Create backup directory
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# Start backup
echo -e "${YELLOW}Starting backup...${NC}"

if influx backup \
    --host http://localhost:8086 \
    --token "${INFLUX_TOKEN}" \
    --org "${INFLUX_ORG}" \
    --bucket "${INFLUX_BUCKET}" \
    "${BACKUP_DIR}/${BACKUP_NAME}"; then
    
    echo -e "${GREEN}✓ Backup completed successfully${NC}"
    
    # Create tarball
    echo -e "${YELLOW}Creating compressed archive...${NC}"
    tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" \
        -C "${BACKUP_DIR}" "${BACKUP_NAME}"
    
    # Remove uncompressed backup
    rm -rf "${BACKUP_DIR}/${BACKUP_NAME}"
    
    # Get backup size
    BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
    echo -e "${GREEN}✓ Archive created: ${BACKUP_NAME}.tar.gz (${BACKUP_SIZE})${NC}"
    
    # Clean old backups
    echo -e "${YELLOW}Cleaning old backups...${NC}"
    find "${BACKUP_DIR}" -name "influxdb_backup_*.tar.gz" \
         -type f -mtime +${RETENTION_DAYS} -delete
    
    echo -e "${GREEN}✓ Backup process complete${NC}"
    exit 0
else
    echo -e "${RED}✗ Backup failed!${NC}"
    exit 1
fi