#!/bin/bash

# ============================================================================
# MongoDB Backup Script for DHSILED
# Automated backup of MongoDB database
# ============================================================================

set -e

# Configuration
BACKUP_DIR="/backups/mongodb"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="dhsiled_backup_${TIMESTAMP}"
MONGODB_URI="mongodb://dhsiled_admin:dhsiled_secure_2024@localhost:27017"
DATABASE_NAME="dhsiled"
RETENTION_DAYS=30

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "DHSILED MongoDB Backup Script"
echo "============================================"
echo "Timestamp: $(date)"
echo "Backup Directory: ${BACKUP_DIR}"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Start backup
echo -e "${YELLOW}Starting backup...${NC}"

if mongodump --uri="${MONGODB_URI}" \
             --db="${DATABASE_NAME}" \
             --out="${BACKUP_DIR}/${BACKUP_NAME}" \
             --gzip; then
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
    echo -e "${YELLOW}Cleaning old backups (older than ${RETENTION_DAYS} days)...${NC}"
    find "${BACKUP_DIR}" -name "dhsiled_backup_*.tar.gz" \
         -type f -mtime +${RETENTION_DAYS} -delete
    
    REMAINING_BACKUPS=$(ls -1 "${BACKUP_DIR}"/dhsiled_backup_*.tar.gz 2>/dev/null | wc -l)
    echo -e "${GREEN}✓ Cleanup complete. ${REMAINING_BACKUPS} backups remaining${NC}"
    
    echo ""
    echo "============================================"
    echo -e "${GREEN}Backup completed successfully!${NC}"
    echo "============================================"
    exit 0
else
    echo -e "${RED}✗ Backup failed!${NC}"
    exit 1
fi