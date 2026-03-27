#!/bin/bash
# Script to clear all TPM data from shared_dir, tpm_state, and key_backups
# WARNING: This will delete all keys, backups, and TPM state!

set -e

SHARED_DIR="shared_dir"
TPM_STATE_DIR="${SHARED_DIR}/tpm_state"
KEY_BACKUPS_DIR="${SHARED_DIR}/key_backups"

echo "=========================================="
echo "TPM Data Cleanup Script"
echo "=========================================="
echo ""
echo "This will delete:"
echo "  - All files in ${SHARED_DIR}/"
echo "  - All files in ${TPM_STATE_DIR}/"
echo "  - All files in ${KEY_BACKUPS_DIR}/"
echo ""
echo "⚠️  WARNING: This will permanently delete all TPM keys, backups, and state!"
echo ""

# Ask for confirmation
read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."

# Clear shared_dir (keep directory structure, remove all files)
if [ -d "$SHARED_DIR" ]; then
    echo "Clearing ${SHARED_DIR}/..."
    find "$SHARED_DIR" -maxdepth 1 -type f -delete 2>/dev/null || true
    echo "  ✓ Cleared files in ${SHARED_DIR}/"
else
    echo "  ⚠️  ${SHARED_DIR}/ does not exist, skipping..."
fi

# Clear tpm_state directory
if [ -d "$TPM_STATE_DIR" ]; then
    echo "Clearing ${TPM_STATE_DIR}/..."
    find "$TPM_STATE_DIR" -type f -delete 2>/dev/null || true
    find "$TPM_STATE_DIR" -type d ! -path "$TPM_STATE_DIR" -exec rm -rf {} + 2>/dev/null || true
    echo "  ✓ Cleared ${TPM_STATE_DIR}/"
else
    echo "  ⚠️  ${TPM_STATE_DIR}/ does not exist, skipping..."
fi

# Clear key_backups directory
if [ -d "$KEY_BACKUPS_DIR" ]; then
    echo "Clearing ${KEY_BACKUPS_DIR}/..."
    find "$KEY_BACKUPS_DIR" -type f -delete 2>/dev/null || true
    echo "  ✓ Cleared ${KEY_BACKUPS_DIR}/"
else
    echo "  ⚠️  ${KEY_BACKUPS_DIR}/ does not exist, skipping..."
fi

echo ""
echo "=========================================="
echo "✓ Cleanup complete!"
echo "=========================================="
echo ""
echo "All TPM data has been cleared."
echo "Directories are preserved but empty."
echo ""
echo "To recreate everything, restart the TPM2 API and create new keys."



