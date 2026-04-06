#!/bin/bash
# Management script for AnyLog nodes with TPM
# Spins up AnyLog nodes (master/operator/publisher/query) each connected to an instance data dir (prefix+N)
#
# Port logic: +10 per same-type instance, +100 between types
# | Node      |  TCP  |  REST | Broker |
# | Master    | 32048 | 32049 | -      |
# | Operator  | 32148 | 32149 | 32150  |
# | Publisher | 32248 | 32249 | 32250  |
# | Query     | 32348 | 32349 | -      |

set -e

NODES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$NODES_DIR")"
# shellcheck source=../multiple-instances/shared-data-root.sh
source "$PROJECT_ROOT/multiple-instances/shared-data-root.sh"
load_shared_data_root
load_shared_dir_prefix
TPM_INSTANCES_DIR="$SHARED_DATA_ROOT"
CONFIG_FILE="$NODES_DIR/.anylog-nodes.config"
ANYLOG_IMAGE="anylogco/anylog-network:tpm-pp"

# Port bases - use functions for Bash 3.x compatibility (macOS default)
get_tcp_base() { case "$1" in master) echo 32048;; operator) echo 32148;; publisher) echo 32248;; query) echo 32348;; *) echo 32048;; esac; }
get_rest_base() { case "$1" in master) echo 32049;; operator) echo 32149;; publisher) echo 32249;; query) echo 32349;; *) echo 32049;; esac; }
get_broker_base() { case "$1" in operator) echo 32150;; publisher) echo 32250;; *) echo "";; esac; }

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }

show_usage() {
    cat << EOF
Usage: $0 <command> [options]

Commands:
  setup <N> <type> [N type ...]   Configure node layout. Creates TPM dirs if needed.
                                  Example: setup 2 master 3 operator 1 publisher
  start                          Start all AnyLog nodes (detached)
  stop                           Stop all AnyLog nodes
  list                           List AnyLog node containers and their status
  restart                        Stop and start all AnyLog nodes
  attach <type> <n>              Attach to a running node (e.g., attach master 1)

Examples:
  $0 setup 2 master 3 operator 1 publisher
  $0 start
  $0 stop
  $0 list
  $0 attach master 1

EOF
}

# Parse config into array: type1 count1 type2 count2 ...
get_config() {
    [ ! -f "$CONFIG_FILE" ] && return 1
    local line
    while read -r line; do
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        echo "$line"
    done < "$CONFIG_FILE"
}

# Expand config to flat list of types with TPM indices: master,operator,operator,publisher,...
expand_nodes() {
    local tpm_idx=1
    local line type count i
    while read -r line; do
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        read -r type count <<< "$line"
        for ((i=0; i<count; i++)); do
            echo "$type $tpm_idx"
            ((tpm_idx++)) || true
        done
    done < "$CONFIG_FILE"
}

# Get total number of nodes (TPM count needed)
get_total_nodes() {
    local total=0
    local line type count
    while read -r line; do
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        read -r type count <<< "$line"
        total=$((total + count))
    done < "$CONFIG_FILE" 2>/dev/null || true
    echo "$total"
}

setup_nodes() {
    shift  # skip "setup"
    if [ $# -lt 2 ]; then
        print_error "Usage: $0 setup <N> <type> [N type ...]"
        echo "Example: $0 setup 2 master 3 operator 1 publisher 1 query"
        exit 1
    fi
    local total=0
    mkdir -p "$NODES_DIR"
    > "$CONFIG_FILE"
    echo "# AnyLog node layout (type count)" >> "$CONFIG_FILE"
    while [ $# -ge 2 ]; do
        local count=$1
        local type=$2
        shift 2
        [[ "$type" =~ ^(master|operator|publisher|query)$ ]] || {
            print_error "Unknown type: $type (must be master|operator|publisher|query)"
            exit 1
        }
        echo "$type $count" >> "$CONFIG_FILE"
        total=$((total + count))
    done
    print_success "Config written: $CONFIG_FILE"
    print_info "Total nodes: $total"
    # Ensure TPM dirs exist (script lives in multiple-instances/)
    if [ "$total" -gt 0 ] && [ -f "$PROJECT_ROOT/multiple-instances/setup-multiple-instances.sh" ]; then
        print_info "Ensuring $total TPM instance(s) (data under $SHARED_DATA_ROOT)..."
        "$PROJECT_ROOT/multiple-instances/setup-multiple-instances.sh" "$total"
    fi
}

start_nodes() {
    [ ! -f "$CONFIG_FILE" ] && { print_error "No config. Run: $0 setup 2 master 3 operator ..."; exit 1; }
    cd "$PROJECT_ROOT"
    local node_idx
    local line type count
    local global_idx=0
    while read -r line; do
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        read -r type count <<< "$line"
        for ((node_idx=1; node_idx<=count; node_idx++)); do
            ((global_idx++)) || true
            local name="anylog-${type}-tpm${global_idx}"
            local tcp_base=$(get_tcp_base "$type")
            local rest_base=$(get_rest_base "$type")
            local tcp_port=$((tcp_base + (node_idx - 1) * 10))
            local rest_port=$((rest_base + (node_idx - 1) * 10))
            local shared_dir="$TPM_INSTANCES_DIR/${SHARED_DIR_PREFIX}${global_idx}"
            if [ ! -d "$shared_dir" ]; then
                print_warning "${SHARED_DIR_PREFIX}${global_idx} not found under $SHARED_DATA_ROOT, skipping $name"
                continue
            fi
            if docker ps -a --format '{{.Names}}' | grep -q "^${name}$"; then
                print_info "$name already exists, starting..."
                docker start "$name" 2>/dev/null || true
            else
                local run_cmd="docker run -it -d"
                run_cmd="$run_cmd -e INIT_TYPE=prod -e NODE_TYPE=$type"
                run_cmd="$run_cmd -e REST_PORT=$rest_port -e TCP_PORT=$tcp_port"
                run_cmd="$run_cmd -p $tcp_port:$tcp_port -p $rest_port:$rest_port"
                local broker_base=$(get_broker_base "$type")
                if [ -n "$broker_base" ]; then
                    local broker_port=$((broker_base + (node_idx - 1) * 10))
                    run_cmd="$run_cmd -e BROKER_PORT=$broker_port -p $broker_port:$broker_port"
                fi
                run_cmd="$run_cmd -v ${TPM_INSTANCES_DIR}/${SHARED_DIR_PREFIX}${global_idx}:/app/AnyLog-Network/tpm_dir"
                run_cmd="$run_cmd --name $name $ANYLOG_IMAGE"
                print_info "Starting $name (TCP=$tcp_port REST=$rest_port TPM=node$global_idx)..."
                eval $run_cmd
                print_success "Started $name"
            fi
        done
    done < "$CONFIG_FILE"
}

stop_nodes() {
    cd "$PROJECT_ROOT"
    local c
    for c in $(docker ps -a --format '{{.Names}}' 2>/dev/null | grep '^anylog-.*-tpm[0-9]*$' || true); do
        print_info "Stopping $c..."
        docker stop "$c" 2>/dev/null || true
        print_success "Stopped $c"
    done
}

list_nodes() {
    print_info "AnyLog Nodes:"
    echo ""
    printf "%-25s %-12s %-15s %-12s %-10s\n" "Name" "Type" "Status" "TCP/REST" "TPM"
    echo "--------------------------------------------------------------------------------"
    [ ! -f "$CONFIG_FILE" ] && { print_warning "No config. Run: $0 setup 2 master ..."; return; }
    local global_idx=0
    local line type count
    while read -r line; do
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        read -r type count <<< "$line"
        for ((node_idx=1; node_idx<=count; node_idx++)); do
            ((global_idx++)) || true
            local name="anylog-${type}-tpm${global_idx}"
            local tcp_base=$(get_tcp_base "$type")
            local rest_base=$(get_rest_base "$type")
            local tcp_port=$((tcp_base + (node_idx - 1) * 10))
            local rest_port=$((rest_base + (node_idx - 1) * 10))
            local status="Not found"
            if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${name}$"; then
                status="Running"
            elif docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${name}$"; then
                status="Stopped"
            fi
            local ports="$tcp_port/$rest_port"
            printf "%-25s %-12s %-15s %-12s %-10s\n" "$name" "$type" "$status" "$ports" "node$global_idx"
        done
    done < "$CONFIG_FILE"
    echo ""
}

attach_node() {
    local type=$1
    local n=$2
    [ -z "$type" ] || [ -z "$n" ] && { print_error "Usage: $0 attach <type> <n>"; exit 1; }
    local offset=0
    local line t c
    while read -r line; do
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        read -r t c <<< "$line"
        if [ "$t" = "$type" ]; then
            if [ "$n" -le "$c" ] && [ "$n" -ge 1 ]; then
                local global_idx=$((offset + n))
                local name="anylog-${type}-tpm${global_idx}"
                if [ -t 0 ]; then
                    docker attach --detach-keys=ctrl-d "$name"
                else
                    print_warning "No TTY (e.g. Cursor's terminal). Run this in a regular terminal:"
                    echo "  docker attach --detach-keys=ctrl-d $name"
                    echo ""
                    print_info "Or for a shell: docker exec -it $name bash"
                fi
                return
            fi
            print_error "Instance $n of $type not found (config has $c)"
            exit 1
        fi
        offset=$((offset + c))
    done < "$CONFIG_FILE"
    print_error "Type $type not found in config"
    exit 1
}

# Main
cd "$PROJECT_ROOT"
case "${1:-}" in
    setup)
        setup_nodes "$@"
        ;;
    start)
        start_nodes
        ;;
    stop)
        stop_nodes
        ;;
    list)
        list_nodes
        ;;
    restart)
        stop_nodes
        sleep 2
        start_nodes
        ;;
    attach)
        attach_node "$2" "$3"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
