#!/bin/bash
set -e

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="db_backup_${TIMESTAMP}.sql.gz"
# Master Key for encryption (Should come from env, but fallback here for script)
ENCRYPTION_KEY=${MASTER_KEY:-"default_insecure_key_please_change"}

echo "--- Starting Backup at ${TIMESTAMP} ---"

# Ensure directory exists
mkdir -p ${BACKUP_DIR}

# 1. Dump Database (using pg_dump inside the container logic)
# This script is intended to run *inside* the postgres container or have access to it via pg_dump host
# We assume we run this via: docker exec -t bot_postgres /scripts/backup_db.sh

# If running inside container:
export PGPASSWORD=${POSTGRES_PASSWORD}
pg_dump -U ${POSTGRES_USER} -d ${POSTGRES_DB} | gzip > "${BACKUP_DIR}/${FILENAME}"

# 2. Encrypt (Optional - using openssl)
# openssl enc -aes-256-cbc -salt -in "${BACKUP_DIR}/${FILENAME}" -out "${BACKUP_DIR}/${FILENAME}.enc" -k "${ENCRYPTION_KEY}"
# rm "${BACKUP_DIR}/${FILENAME}" # Remove unencrypted
# echo "✅ Encrypted to ${FILENAME}.enc"

echo "✅ Backup created: ${BACKUP_DIR}/${FILENAME}"

# 3. Prune old backups (Keep last 7 days)
find ${BACKUP_DIR} -type f -name "*.sql.gz" -mtime +7 -exec rm {} \;
echo "🧹 Pruned backups older than 7 days."

echo "--- Backup Complete ---"
