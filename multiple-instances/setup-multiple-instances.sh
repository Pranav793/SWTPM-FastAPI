#!/bin/bash
# Helper script to set up directories for multiple TPM instances
# Usage: ./setup-multiple-instances.sh [NUM_INSTANCES]
# Supports any number of instances (default: 3)
# Creates or deletes folders to match the requested count exactly.

set -e

INSTANCES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$INSTANCES_DIR")"
cd "$INSTANCES_DIR"

NUM_INSTANCES=${1:-$(cat .num_instances 2>/dev/null || echo "3")}

# Validate
if ! [[ "$NUM_INSTANCES" =~ ^[0-9]+$ ]] || [ "$NUM_INSTANCES" -lt 1 ]; then
    echo "Error: NUM_INSTANCES must be a positive integer (got: $NUM_INSTANCES)" >&2
    exit 1
fi

echo "Setting up exactly $NUM_INSTANCES TPM instance(s) in $INSTANCES_DIR..."

# Find existing node directories and remove extras when scaling down
EXISTING_NODES=$(ls -d shared_dir_node* 2>/dev/null | sed 's/shared_dir_node//' | sort -n || true)
if [ -n "$EXISTING_NODES" ]; then
    MAX_EXISTING=$(echo "$EXISTING_NODES" | tail -1)
    if [ "$NUM_INSTANCES" -lt "$MAX_EXISTING" ]; then
        echo "Scaling down: removing nodes $((NUM_INSTANCES + 1)) through $MAX_EXISTING..."
        for i in $(seq $((NUM_INSTANCES + 1)) $MAX_EXISTING); do
            DIR="shared_dir_node${i}"
            CONTAINER="tpm2-api-node${i}"
            if [ -d "$DIR" ]; then
                # Stop and remove container if running
                if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER}$"; then
                    echo "  Stopping and removing container ${CONTAINER}..."
                    docker stop "$CONTAINER" 2>/dev/null || true
                    docker rm "$CONTAINER" 2>/dev/null || true
                fi
                echo "  Removing $DIR..."
                rm -rf "$DIR"
            fi
        done
    fi
fi

# Create/ensure directories for nodes 1 through NUM_INSTANCES
for i in $(seq 1 $NUM_INSTANCES); do
    DIR="shared_dir_node${i}"
    TPM_STATE_DIR="${DIR}/tpm_state"
    KEY_BACKUPS_DIR="${DIR}/key_backups"
    METADATA_FILE="${DIR}/signing_keys_metadata.json"
    
    echo "Creating directories for node${i}..."
    mkdir -p "$TPM_STATE_DIR"
    mkdir -p "$KEY_BACKUPS_DIR"
    
    # Initialize signing_keys_metadata.json if it doesn't exist
    if [ ! -f "$METADATA_FILE" ]; then
        echo "{}" > "$METADATA_FILE"
        echo "  ✓ Initialized $METADATA_FILE"
    fi
    
    # Set permissions
    chmod 777 "$DIR" 2>/dev/null || true
    chmod 777 "$TPM_STATE_DIR" 2>/dev/null || true
    chmod 777 "$KEY_BACKUPS_DIR" 2>/dev/null || true
    chmod 666 "$METADATA_FILE" 2>/dev/null || true
    
    echo "✓ Created $DIR, $TPM_STATE_DIR, and $KEY_BACKUPS_DIR"
done

echo ""
echo "Setup complete! Directories created:"
for i in $(seq 1 $NUM_INSTANCES); do
    echo "  - multiple-instances/shared_dir_node${i}/"
    echo "    ├── tpm_state/"
    echo "    ├── key_backups/"
    echo "    └── signing_keys_metadata.json"
done

# Generate docker-compose.instances.yaml
if [ -f "$INSTANCES_DIR/generate-docker-compose.sh" ]; then
    "$INSTANCES_DIR/generate-docker-compose.sh" "$NUM_INSTANCES"
else
    echo ""
    echo "Warning: generate-docker-compose.sh not found. Run it manually:"
    echo "  ./generate-docker-compose.sh $NUM_INSTANCES"
fi

echo ""
echo "You can now start the instances with (from project root):"
echo "  docker-compose -f multiple-instances/docker-compose.instances.yaml up -d"
