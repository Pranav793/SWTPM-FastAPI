# Multiple AnyLog Nodes with TPM

Run multiple AnyLog nodes (master/operator/publisher/query), each connected to a TPM instance in `multiple-instances/`.

## Quick Reference

```bash
# Configure: 2 masters, 3 operators, 1 publisher (creates TPM dirs in multiple-instances/ if needed)
./multiple-nodes/manage-anylog-nodes.sh setup 1 master 2 operator 3 publisher

# Start all
./multiple-nodes/manage-anylog-nodes.sh start

# List, stop, restart, attach
./multiple-nodes/manage-anylog-nodes.sh list
./multiple-nodes/manage-anylog-nodes.sh stop
./multiple-nodes/manage-anylog-nodes.sh restart
./multiple-nodes/manage-anylog-nodes.sh attach master 1 # doesn't always work just use docker attach --detach-keys=ctrl-d <name>
```

## Prerequisites

- TPM instances must exist in `multiple-instances/`. Run `./multiple-instances/setup-multiple-instances.sh N` first, or `setup` will create them automatically.

## Port Allocation

| Node      |  TCP  |  REST | Broker | +10 per instance |
|-----------|-------|-------|--------|------------------|
| Master    | 32048 | 32049 | -      | 32058/32059      |
| Operator  | 32148 | 32149 | 32150  | 32158/32159/32160|
| Publisher | 32248 | 32249 | 32250  | 32258/32259/32260|
| Query     | 32348 | 32349 | -      | 32358/32359      |

## Container Naming

`anylog-{type}-tpm{N}` — e.g., `anylog-master-tpm1`, `anylog-operator-tpm3`

Each node mounts `<prefix>{N}` from the configured shared data root (see `multiple-instances/README.md`: data root, `.instances-prefix` / `SWTPM_SHARED_DIR_PREFIX`) to `/app/AnyLog-Network/tpm_dir`.
