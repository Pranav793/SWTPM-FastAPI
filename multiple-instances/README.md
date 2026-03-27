# Running Multiple Independent TPM Instances

Run any number of TPM instances (1, 5, 10, 100+) for different nodes, each with its own isolated state and API endpoint.

## Quick Reference

### Setup
```bash
# From project root:
cd multiple-instances
./setup-multiple-instances.sh 5

# Or from project root in one step:
./multiple-instances/setup-multiple-instances.sh 5

# Start all instances (run from project root):
docker-compose -f multiple-instances/docker-compose.instances.yaml up -d
```

### Management
```bash
# All management commands (run from project root or multiple-instances/):
./multiple-instances/manage-instances.sh list
./multiple-instances/manage-instances.sh clear-tpm 1,2
./multiple-instances/manage-instances.sh clear-tpm all
./multiple-instances/manage-instances.sh clear-all 1
./multiple-instances/manage-instances.sh delete 3
./multiple-instances/manage-instances.sh reset      # Full wipe: containers + all dirs + generated files
./multiple-instances/manage-instances.sh stop all
./multiple-instances/manage-instances.sh start 1,2
./multiple-instances/manage-instances.sh restart all
```

## Directory Structure

All multiple-instance files live in `multiple-instances/`:

```
multiple-instances/
├── setup-multiple-instances.sh    # Create dirs and generate compose
├── generate-docker-compose.sh     # Generate docker-compose.instances.yaml
├── manage-instances.sh            # List, clear, start, stop instances
├── test-multiple-instances.py    # Test script
├── README.md                     # This file
├── docker-compose.instances.yaml # Generated (do not edit)
├── .num_instances                # Generated (instance count)
└── shared_dir_node1/             # Created by setup
    ├── tpm_state/
    ├── key_backups/
    └── signing_keys_metadata.json
    shared_dir_node2/
    ...
```

## Quick Start

### 1. Setup
```bash
./multiple-instances/setup-multiple-instances.sh 5
```

Creates `multiple-instances/shared_dir_node1` through `shared_dir_node5` and generates the compose file.

### 2. Start
```bash
docker-compose -f multiple-instances/docker-compose.instances.yaml up -d
```

### 3. Verify
```bash
./multiple-instances/manage-instances.sh list
python multiple-instances/test-multiple-instances.py
```

## Port Allocation

| Instance | API Port | SWTPM Server | SWTPM Control |
|----------|----------|--------------|----------------|
| Node 1   | 8001     | 2321         | 2322           |
| Node 2   | 8002     | 2323         | 2324           |
| Node N   | 8000+N   | 2321+2(N-1)  | 2322+2(N-1)    |

## Changing Instance Count

```bash
# Scale up
./multiple-instances/setup-multiple-instances.sh 10

# Scale down
./multiple-instances/manage-instances.sh delete 8,9,10
./multiple-instances/generate-docker-compose.sh 7
```

## Manual Docker Commands

```bash
COMPOSE_CMD="docker-compose -f multiple-instances/docker-compose.instances.yaml"
$COMPOSE_CMD up -d tpm2-api-node1
$COMPOSE_CMD stop tpm2-api-node1
$COMPOSE_CMD logs -f tpm2-api-node1
```

For AnyLog nodes, see **[multiple-nodes/README.md](../multiple-nodes/README.md)**.

## Notes

- After **clear-tpm** or **clear-all**, the containers are removed so that the next **start** or **restart** creates fresh containers. This ensures swtpm reinitializes and repopulates `tpm_state/` with new TPM state files.

## Troubleshooting

- **Port conflicts**: `netstat -tuln | grep -E '800[0-9]|232[0-9]'`
- **Permissions**: `chmod -R 777 multiple-instances/shared_dir_node*/`
- **Logs**: `$COMPOSE_CMD logs tpm2-api-node1`
