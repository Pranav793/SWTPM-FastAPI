# Hardware TPM Setup Guide

This guide explains how to use the TPM2 API with a hardware TPM device on Ubuntu.

## Prerequisites

### 1. Install TPM2 Tools
```bash
sudo apt-get update
sudo apt-get install -y tpm2-tools tpm2-abrmd
```

### 2. Verify TPM Device
Check if your hardware TPM is accessible:
```bash
ls -l /dev/tpm*
```

You should see at least one of:
- `/dev/tpm0` - Direct TPM device
- `/dev/tpmrm0` - TPM Resource Manager device (preferred)

### 3. User Permissions
Add your user to the `tss` group to access TPM without root:
```bash
sudo usermod -aG tss $USER
# Log out and log back in for changes to take effect
```

Verify group membership:
```bash
groups
```

## Usage

### Automatic Detection (Recommended)
The API will automatically detect and use hardware TPM if available:

```python
from tpm2_api import TPM2API

# Auto-detects hardware TPM
tpm = TPM2API()
```

### Manual Configuration

#### Option 1: Environment Variable
```bash
# Using TPM Resource Manager (recommended)
export TPM2_TCTI="device:/dev/tpmrm0"

# Or using direct device access
export TPM2_TCTI="device:/dev/tpm0"

# Or using tabrmd daemon
export TPM2_TCTI="tabrmd:"
```

Then run your Python script:
```bash
python3 tpm2_rest_api.py
```

#### Option 2: Python Code
```python
from tpm2_api import TPM2API

# Specify TCTI explicitly
tpm = TPM2API("device:/dev/tpmrm0")
# or
tpm = TPM2API("tabrmd:")
```

## TCTI Options

### 1. TPM Resource Manager (`device:/dev/tpmrm0`)
- **Pros**: No root required, better resource management
- **Cons**: Requires kernel TPM Resource Manager support
- **Best for**: Most use cases

### 2. Direct Device (`device:/dev/tpm0`)
- **Pros**: Direct access, no daemon needed
- **Cons**: Requires root or tss group membership
- **Best for**: System-level operations

### 3. TPM2 Access Broker (`tabrmd:`)
- **Pros**: Production-ready, handles multiple clients
- **Cons**: Requires daemon to be running
- **Best for**: Production deployments

Start the daemon:
```bash
sudo systemctl start tpm2-abrmd
sudo systemctl enable tpm2-abrmd  # Enable on boot
```

## Testing Hardware TPM

### Quick Test
```bash
# Test TPM connection
tpm2_getcap properties-fixed

# Test with specific TCTI
TSS2_TCTI=device:/dev/tpmrm0 tpm2_getcap properties-fixed
```

### Python Test
```python
from tpm2_api import TPM2API

try:
    tpm = TPM2API()
    info = tpm.get_tpm_info()
    print(f"TPM Info: {info}")
    print(f"Using TCTI: {tpm.tcti_name}")
except Exception as e:
    print(f"Error: {e}")
```

## Remote Access via SSH

When SSH'ing to a remote Ubuntu machine with hardware TPM:

1. **SSH into the machine:**
   ```bash
   ssh user@remote-machine
   ```

2. **Verify TPM is accessible:**
   ```bash
   ls -l /dev/tpm*
   tpm2_getcap properties-fixed
   ```

3. **Run the API normally:**
   ```bash
   cd /path/to/SWTPM-FastAPI
   python3 tpm2_rest_api.py
   ```

   The API will automatically detect and use the hardware TPM.

4. **Or set TCTI explicitly:**
   ```bash
   export TPM2_TCTI="device:/dev/tpmrm0"
   python3 tpm2_rest_api.py
   ```

## Troubleshooting

### Permission Denied
**Error**: `Permission denied: /dev/tpm0`

**Solution**:
```bash
sudo usermod -aG tss $USER
# Log out and log back in
```

### Device Not Found
**Error**: `No such file or directory: /dev/tpm0`

**Solutions**:
1. Check if TPM is enabled in BIOS/UEFI
2. Verify kernel module is loaded: `lsmod | grep tpm`
3. Check dmesg for TPM errors: `dmesg | grep -i tpm`

### TPM Locked
**Error**: TPM is in dictionary attack lockout mode

**Solution** (requires root):
```bash
sudo tpm2_dictionarylockout --setup-parameters --max-tries=4294967295 --clear-lockout
```

### tabrmd Not Running
**Error**: `Failed to connect to tabrmd`

**Solution**:
```bash
sudo systemctl start tpm2-abrmd
sudo systemctl status tpm2-abrmd
```

## Differences from SWTPM

1. **Persistent Storage**: Hardware TPM keys persist across reboots (if made persistent)
2. **Performance**: Hardware TPM is typically faster
3. **Security**: Hardware TPM provides true hardware security
4. **No Emulator**: No need to start swtpm or manage TPM state files

## Example: Complete Workflow

```python
from tpm2_api import TPM2API

# Initialize (auto-detects hardware TPM)
tpm = TPM2API()

# Create primary key
result = tpm.create_primary_key()
print(f"Primary key: {result}")

# Create RSA key
result = tpm.create_key("primary.ctx", "rsa", "rsa.pub", "rsa.priv")
print(f"RSA key: {result}")

# Load key
result = tpm.load_key("primary.ctx", "rsa.pub", "rsa.priv", "rsa.ctx")
print(f"Loaded: {result}")

# Make persistent (survives reboot on hardware TPM)
result = tpm.make_persistent("rsa.ctx")
print(f"Persistent: {result}")
```

## REST API with Hardware TPM

The REST API works the same way with hardware TPM:

```bash
# Start API (auto-detects hardware TPM)
python3 tpm2_rest_api.py

# Or with explicit TCTI
TPM2_TCTI=device:/dev/tpmrm0 python3 tpm2_rest_api.py

# Test health endpoint
curl http://localhost:8000/health
```

The API will show which TCTI it's using in the startup logs.

