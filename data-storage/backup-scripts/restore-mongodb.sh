#!/bin/bash

# ============================================================================
# MongoDB Restore Script for DHSILED
# Restore MongoDB database from backup
# ============================================================================

set -e

# Configuration
BACKUP_DIR="/backups/mongodb"
MONGODB_URI="mongodb://dhsiled_admin:dhsiled_secure_2024@localhost:27017"
DATABASE_NAME="dhsiled"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "DHSILED MongoDB Restore Script"
echo "============================================"
echo "Timestamp: $(date)"
echo ""

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Available backups:${NC}"
    ls -lh "${BACKUP_DIR}"/dhsiled_backup_*.tar.gz 2>/dev/null || echo "No backups found"
    echo ""
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 dhsiled_backup_20240101_120000.tar.gz"
    exit 1
fi

BACKUP_FILE="$1"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Check if backup file exists
if [ ! -f "${BACKUP_PATH}" ]; then
    echo -e "${RED}✗ Backup file not found: ${BACKUP_PATH}${NC}"
    exit 1
fi

echo -e "${YELLOW}⚠️  WARNING: This will overwrite the existing database!${NC}"
echo "Backup file: ${BACKUP_FILE}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

# Extract backup
echo -e "${YELLOW}Extracting backup...${NC}"
TEMP_DIR=$(mktemp -d)
tar -xzf "${BACKUP_PATH}" -C "${TEMP_DIR}"

BACKUP_NAME=$(basename "${BACKUP_FILE}" .tar.gz)
EXTRACT_DIR="${TEMP_DIR}/${BACKUP_NAME}"

if [ ! -d "${EXTRACT_DIR}" ]; then
    echo -e "${RED}✗ Extracted directory not found${NC}"
    rm -rf "${TEMP_DIR}"
    exit 1
fi

# Restore database
echo -e "${YELLOW}Restoring database...${NC}"

if mongorestore --uri="${MONGODB_URI}" \
                --db="${DATABASE_NAME}" \
                --gzip \
                --drop \
                "${EXTRACT_DIR}/${DATABASE_NAME}"; then
    echo -e "${GREEN}✓ Database restored successfully${NC}"
    
    # Cleanup
    rm -rf "${TEMP_DIR}"
    
    echo ""
    echo "============================================"
    echo -e "${GREEN}Restore completed successfully!${NC}"
    echo "============================================"
    exit 0
else
    echo -e "${RED}✗ Restore failed!${NC}"
    rm -rf "${TEMP_DIR}"
    exit 1
fi