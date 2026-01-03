# Hardware TPM Setup and Usage Guide

This comprehensive guide covers everything you need to know about using the TPM2 API with a hardware TPM device on Ubuntu.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Setup Guide](#setup-guide)
4. [Running the API](#running-the-api)
5. [Testing](#testing)
6. [Resetting the TPM](#resetting-the-tpm)
7. [Troubleshooting](#troubleshooting)

---

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

---

## Quick Start

### Step 1: Verify TPM is Available
```bash
# Check if TPM devices exist
ls -l /dev/tpm*

# You should see at least one of:
# /dev/tpm0  or  /dev/tpmrm0
```

### Step 2: Quick Test with TPM2 Tools
```bash
# Test basic TPM connectivity
tpm2_getcap properties-fixed

# If that works, you're good to go!
```

### Step 3: Test with Python API
```bash
python3 test_hardware_tpm.py
```

### Step 4: Start the REST API
```bash
# Easiest method - use the provided script
./start_api_background.sh

# Or run directly
python3 tpm2_rest_api.py
```

### Step 5: Test the API
```bash
curl http://localhost:8000/health
```

---

## Setup Guide

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
export TSS2_TCTI="device:/dev/tpmrm0"
export TPM2TOOLS_TCTI="device:/dev/tpmrm0"
python3 tpm2_rest_api.py
```

#### Option 2: In Python Code
```python
import os
os.environ['TSS2_TCTI'] = 'device:/dev/tpmrm0'
os.environ['TPM2TOOLS_TCTI'] = 'device:/dev/tpmrm0'

from tpm2_api import TPM2API
tpm = TPM2API()
```

---

## Running the API

### Option A: Run in Foreground (for testing)
```bash
cd SWTPM-FastAPI
source venv/bin/activate  # if using venv
python3 tpm2_rest_api.py
```

### Option B: Run in Background

#### Method 1: Using nohup (Simple)
```bash
cd SWTPM-FastAPI
source venv/bin/activate  # if using venv

# Run in background with nohup (logs to nohup.out)
nohup python3 tpm2_rest_api.py > tpm2_api.log 2>&1 &

# Check if it's running
ps aux | grep tpm2_rest_api

# View logs
tail -f tpm2_api.log

# Stop the process
kill $(lsof -t -i:8000)
```

#### Method 2: Using screen
```bash
# Install screen if not available
sudo apt-get install screen

# Start a screen session
screen -S tpm2-api

# Inside screen, start the API
cd SWTPM-FastAPI
source venv/bin/activate  # if using venv
python3 tpm2_rest_api.py

# Detach from screen: Press Ctrl+A, then D
# Reattach later: screen -r tpm2-api
```

#### Method 3: Using tmux
```bash
# Install tmux if not available
sudo apt-get install tmux

# Start a tmux session
tmux new -s tpm2-api

# Inside tmux, start the API
cd SWTPM-FastAPI
source venv/bin/activate  # if using venv
python3 tpm2_rest_api.py

# Detach from tmux: Press Ctrl+B, then D
# Reattach later: tmux attach -t tpm2-api
```

#### Method 4: Systemd Service (Permanent, auto-starts on boot)
```bash
# Create systemd service file
sudo nano /etc/systemd/system/tpm2-api.service
```

Add this content (adjust paths as needed):
```ini
[Unit]
Description=TPM2 REST API Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/SWTPM-FastAPI
Environment="PATH=/home/your-username/SWTPM-FastAPI/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/your-username/SWTPM-FastAPI/venv/bin/python3 /home/your-username/SWTPM-FastAPI/tpm2_rest_api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Start the service
sudo systemctl start tpm2-api

# Enable it to start on boot
sudo systemctl enable tpm2-api

# Check status
sudo systemctl status tpm2-api

# View logs
sudo journalctl -u tpm2-api -f

# Stop the service
sudo systemctl stop tpm2-api
```

### Using Provided Scripts
```bash
# Start API in background (easiest method)
./start_api_background.sh

# Start on different port
./start_api_background.sh 8001

# Stop API
./stop_api.sh

# Stop API on specific port
./stop_api.sh 8001
```

---

## Testing

### Test with TPM2 Tools
```bash
# Test basic TPM connectivity
tpm2_getcap properties-fixed

# Test with specific TCTI
TSS2_TCTI=device:/dev/tpmrm0 tpm2_getcap properties-fixed
```

### Test with Python API
```bash
# Run the test script
python3 test_hardware_tpm.py
```

### Test the REST API
```bash
# Health check
curl http://localhost:8000/health

# Get TPM info
curl http://localhost:8000/tpm2/info

# Create primary key
curl -X POST http://localhost:8000/tpm2/create-primary \
  -H "Content-Type: application/json" \
  -d '{"hierarchy": "o", "context_file": "primary.ctx"}'
```

---

## Resetting the TPM

**⚠️ WARNING: Resetting a TPM will permanently delete all keys and data stored in it.**

### Method 1: Using the REST API (Recommended)
```bash
# Reset via REST API
curl -X POST http://localhost:8000/tpm2/full-reset
```

This will:
- Clear all persistent objects (keys made persistent)
- Flush all contexts (transient keys)
- Clear owner authorization
- Clear endorsement authorization  
- Clear platform authorization

### Method 2: Using Python API Directly
```python
from tpm2_api import TPM2API

# Initialize (will auto-detect hardware TPM)
tpm = TPM2API()

# Perform full reset
result = tpm.full_reset()
print(result)
```

### Method 3: Using TPM2 Tools Directly
```bash
# Clear owner hierarchy (most common)
sudo tpm2_clear -c o

# Clear endorsement hierarchy
sudo tpm2_clear -c e

# Clear platform hierarchy
sudo tpm2_clear -c p

# Flush all contexts
tpm2_flushcontext -t  # Transient contexts
tpm2_flushcontext -l  # Loaded contexts
tpm2_flushcontext -s  # Saved contexts
tpm2_flushcontext -t -l -s  # All contexts

# Remove persistent objects (if you know the handles)
tpm2_evictcontrol -C o -c 0x81010001  # Remove handle 0x81010001
```

**Note:** For hardware TPM, you may need root access or be in the `tss` group.

### What Gets Reset?

#### ✅ What is Cleared:
- **Persistent Keys**: All keys made persistent (stored in TPM NVRAM)
- **Transient Keys**: All keys loaded in TPM memory
- **Contexts**: All key contexts and sessions
- **Authorizations**: Owner, endorsement, and platform passwords/authorizations
- **Dictionary Attack Lockout**: Lockout state is reset

#### ❌ What is NOT Affected:
- **TPM Firmware**: The TPM firmware itself is not changed
- **Endorsement Key (EK)**: The TPM's unique endorsement key (if present) is not deleted
- **Platform Configuration Registers (PCRs)**: PCR values are reset on reboot, not by clear
- **Files on Disk**: Context files (`.ctx`, `.pub`, `.priv`) on your filesystem are NOT deleted
- **Encrypted File Stores**: Encrypted files (like `anylog_key_store.json`) remain on disk but cannot be decrypted without the keys

### ⚠️ Recovery After Reset

**After resetting a hardware TPM:**
1. **All keys are lost** - You cannot recover keys that were only in the TPM
2. **Recovery blobs become useless** - If you saved recovery blobs (`.pub`/`.priv` files), they won't work because the primary key that encrypted them is gone
3. **Encrypted data is lost** - Any data encrypted with TPM keys cannot be decrypted
4. **You must recreate everything** - Primary keys, AES keys, and encrypted stores must be recreated

### 💡 Best Practices

1. **Backup Recovery Material**: Before resetting, ensure you have:
   - Recovery blobs (`.pub`/`.priv` files) for all important keys
   - The encrypted file stores (they're encrypted but you need the keys to decrypt)
   - Any other important TPM-related data

2. **Test in Non-Production First**: Always test reset procedures on a test system first

3. **Document Your Keys**: Keep a record of what keys you had and their purposes

4. **Use Recovery Blobs**: When creating keys, always save the recovery blobs securely

---

## Troubleshooting

### "Permission denied" error
```bash
# Make sure you're in the tss group
groups | grep tss

# If not, add yourself and start a NEW SSH session
sudo usermod -aG tss $USER
# Then exit and SSH back in
exit
```

### "No such file or directory: /dev/tpm0"
- Check if TPM is enabled in BIOS/UEFI
- Check kernel modules: `lsmod | grep tpm`
- Check dmesg: `dmesg | grep -i tpm`

### "TPM2 connection failed"
- Try specifying TCTI explicitly:
  ```bash
  export TPM2_TCTI="device:/dev/tpmrm0"
  python3 tpm2_rest_api.py
  ```

### API won't start - "Address already in use"
**Error**: `OSError: [Errno 48] Address already in use`

**Solutions**:

1. **Find and kill the process using port 8000:**
   ```bash
   # Find what's using port 8000
   lsof -i :8000
   # or
   sudo netstat -tulpn | grep :8000
   
   # Kill the process (replace PID with the actual process ID)
   kill -9 <PID>
   ```

2. **Use a different port:**
   ```bash
   # Option 1: Use command line argument
   python3 tpm2_rest_api.py 8001
   
   # Option 2: Use environment variable
   export TPM2_API_PORT=8001
   python3 tpm2_rest_api.py
   
   # Option 3: Use uvicorn directly
   uvicorn tpm2_rest_api:app --host 0.0.0.0 --port 8001
   ```

### "TPM is locked"
If the TPM is in dictionary attack lockout:
```bash
# Clear lockout first
sudo tpm2_dictionarylockout --clear-lockout

# Then proceed with reset
sudo tpm2_clear -c o
```

### "Cannot connect to API"
If the API isn't running:
```bash
# Start the API first
python3 tpm2_rest_api.py

# Or use TPM2 tools directly
sudo tpm2_clear -c o
```

---

## Quick Reference Commands

```bash
# Check TPM device
ls -l /dev/tpm*

# Test TPM connectivity
tpm2_getcap properties-fixed

# Test with specific TCTI
TSS2_TCTI=device:/dev/tpmrm0 tpm2_getcap properties-fixed

# Run Python test
python3 test_hardware_tpm.py

# Start REST API (foreground)
python3 tpm2_rest_api.py

# Start REST API (background) - EASIEST METHOD
./start_api_background.sh

# Start on different port
./start_api_background.sh 8001

# Stop REST API
./stop_api.sh

# Stop API on specific port
./stop_api.sh 8001

# View API logs
tail -f tpm2_api.log

# Test API health
curl http://localhost:8000/health

# Reset TPM via REST API
curl -X POST http://localhost:8000/tpm2/full-reset

# Reset TPM via Python
python3 -c "from tpm2_api import TPM2API; TPM2API().full_reset()"

# Reset TPM via TPM2 tools
sudo tpm2_clear -c o
tpm2_flushcontext -t -l -s
```

---

## Next Steps

Once everything is working:
1. The API will automatically use hardware TPM
2. Keys created and made persistent will survive reboots
3. You can use the REST API endpoints as documented in README.md
4. All operations work the same as with SWTPM, but using real hardware

---

## Additional Resources

- [TPM2 Documentation Guide](TPM2_Documentation_Guide.md) - Links to official TPM2 documentation
- [AnyLog Compatibility Guide](ANYLOG_COMPATIBILITY.md) - How to make TPM keys compatible with AnyLog

