#!/bin/bash
# Generates docker-compose.instances.yaml with N TPM instance services
# Usage: ./generate-docker-compose.sh [NUM_INSTANCES]
# If NUM_INSTANCES not specified, uses value from .num_instances or defaults to 3

set -e

INSTANCES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$INSTANCES_DIR"

NUM_INSTANCES=${1:-$(cat .num_instances 2>/dev/null || echo "3")}

# Validate
if ! [[ "$NUM_INSTANCES" =~ ^[0-9]+$ ]] || [ "$NUM_INSTANCES" -lt 1 ]; then
    echo "Error: NUM_INSTANCES must be a positive integer (got: $NUM_INSTANCES)" >&2
    exit 1
fi

OUTPUT_FILE="docker-compose.instances.yaml"

echo "Generating $OUTPUT_FILE with $NUM_INSTANCES TPM instance(s)..."

# Write the header - build context is parent (project root) where Dockerfile lives
cat > "$OUTPUT_FILE" << 'EOF'
# Auto-generated TPM instance services - DO NOT EDIT
# Regenerate with: ./generate-docker-compose.sh <NUM_INSTANCES>
# Or run: ./setup-multiple-instances.sh <NUM_INSTANCES>

version: '3.8'

services:
EOF

# Generate each instance - volumes are relative to this compose file (multiple-instances/)
for i in $(seq 1 $NUM_INSTANCES); do
    API_PORT=$((8000 + i))
    SWTPM_SERVER=$((2321 + (i - 1) * 2))
    SWTPM_CTRL=$((2322 + (i - 1) * 2))
    
    cat >> "$OUTPUT_FILE" << EOF

  tpm2-api-node${i}:
    build:
      context: ..
      dockerfile: Dockerfile
    container_name: tpm2-api-node${i}
    ports:
      - "${API_PORT}:8000"
    volumes:
      - ./shared_dir_node${i}:/opt/shared
      - ./shared_dir_node${i}/tpm_state:/tmp/tpm2-emulated
    working_dir: /opt/shared
    command: sh -c "chmod 777 /opt/shared 2>/dev/null || true && mkdir -p /tmp/tpm2-emulated /opt/shared/key_backups && chmod 700 /tmp/tpm2-emulated 2>/dev/null || true && chmod 777 /opt/shared/key_backups 2>/dev/null || true && [ ! -f /opt/shared/signing_keys_metadata.json ] && echo '{}' > /opt/shared/signing_keys_metadata.json || true && cd /opt/shared && python3 /opt/tpm2_rest_api.py"
    user: root
    environment:
      - TSS2_TCTI=swtpm:host=127.0.0.1,port=${SWTPM_SERVER}
      - TPM2TOOLS_TCTI=swtpm:host=127.0.0.1,port=${SWTPM_SERVER}
      - SWTPM_SERVER_PORT=${SWTPM_SERVER}
      - SWTPM_CTRL_PORT=${SWTPM_CTRL}
      - TPM_STATE_DIR=/tmp/tpm2-emulated
      - SWTPM_LOG_FILE=/var/log/swtpm-node${i}.log
    restart: unless-stopped
EOF
done

# Persist the count for future runs
echo "$NUM_INSTANCES" > .num_instances

echo "✓ Generated $OUTPUT_FILE with $NUM_INSTANCES instance(s)"
echo "  API ports: 8001-$((8000 + NUM_INSTANCES))"
echo "  Start with: docker-compose -f multiple-instances/docker-compose.instances.yaml up -d"
