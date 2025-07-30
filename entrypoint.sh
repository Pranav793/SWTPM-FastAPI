#!/bin/bash
set -e

# Start TPM Emulator
echo "Starting DBus..."
mkdir -p /var/run/dbus
dbus-daemon --system --fork

echo "Starting TPM Emulator (swtpm)..."
mkdir -p /tmp/tpm2-emulated 
chmod 700 /tmp/tpm2-emulated

swtpm socket --tpmstate dir=/tmp/tpm2-emulated \
             --ctrl type=tcp,port=2322 \
             --server type=tcp,port=2321 \
             --flags not-need-init \
             --log level=20 \
	     --log file=/var/log/swtpm.log \
	     --flags not-need-init \
             --tpm2 &

# Wait for the TPM emulator to start
sleep 2

# Start the TPM Resource Manager
echo "Starting TPM2-ABRMD..."
export TSS2_TCTI="swtpm:host=127.0.0.1,port=2321"
export TPM2TOOLS_TCTI="swtpm:host=127.0.0.1,port=2321"
tpm2-abrmd --tcti=swtpm: --allow-root &

# Keep container running
if [[ -z "$1" ]]; then
    echo "No command provided, running a default shell..."
    exec /bin/bash
else
    exec "$@"
fi
