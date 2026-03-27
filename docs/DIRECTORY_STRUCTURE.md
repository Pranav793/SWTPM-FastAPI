# TPM2 Directory and File Structure Guide

This document describes all the directories and files required for the TPM2 system to function properly.

## Required Directory Structure

```
SWTPM-FastAPI/
├── shared_dir/                          # Main shared directory (required)
│   ├── tpm_state/                       # TPM emulator state (required for SWTPM)
│   │   └── tpm2-00.permall             # TPM persistent state file (auto-created)
│   ├── key_backups/                     # Key backup directory (auto-created)
│   │   └── {key_name}_backup.json      # Individual key backups (auto-created)
│   ├── signing_keys_metadata.json       # Signing keys metadata (auto-created)
│   ├── anylog_signing_primary.ctx      # Primary signing key context (auto-created)
│   ├── anylog_primary.ctx               # Primary key for encrypted file store (auto-created)
│   ├── anylog_encrypt_key_aes.ctx       # AES encryption key context (auto-created)
│   ├── anylog_key_store.json            # Encrypted file store (auto-created)
│   ├── {key_name}_{timestamp}.ctx      # Signing key context files (auto-created)
│   ├── {key_name}_{timestamp}.pub      # Public key blobs (temporary, auto-deleted)
│   ├── {key_name}_{timestamp}.priv     # Private key blobs (temporary, auto-deleted)
│   └── signature_{key_name}_{timestamp}.sig  # Signature files (auto-created)
├── docs/                                # Documentation directory
├── tests/                               # Test files directory
└── [other project files...]
```

## Directory Details

### 1. `shared_dir/` (Main Shared Directory)

**Purpose**: Main directory for all TPM-related files and state.

**Location**: 
- **Development**: `./shared_dir` (relative to project root)
- **Production**: Configured via `!tpm_dir` AnyLog parameter (in `anylog_inrn.py`)
- **Docker**: Mounted to `/opt/shared` inside container

**Permissions**: 
- Must be writable by the TPM2 API process
- Docker: `chmod 777` (or appropriate permissions for your user)

**Contents**:
- All TPM context files (`.ctx`)
- Key metadata files (`.json`)
- Encrypted file stores (`.json`)
- Signature files (`.sig`)
- Temporary key blobs (`.pub`, `.priv`) - auto-deleted after use

**Auto-created**: Yes, by the code if it doesn't exist

---

### 2. `shared_dir/tpm_state/` (TPM Emulator State)

**Purpose**: Stores the software TPM emulator's persistent state.

**Location**: `shared_dir/tpm_state/`

**Docker Mount**: `./shared_dir/tpm_state:/tmp/tpm2-emulated`

**Permissions**: 
- `chmod 700` (restricted access)
- Docker: Created automatically with proper permissions

**Contents**:
- `tpm2-00.permall` - TPM persistent state file (contains all TPM keys and state)

**Important Notes**:
- **SWTPM Only**: This directory is only needed when using software TPM emulator (Docker)
- **Hardware TPM**: Not needed when using hardware TPM (keys stored in hardware chip)
- **Persistence**: This file persists TPM state across container restarts
- **Backup**: Backup this directory to preserve TPM state

**Auto-created**: Yes, by docker-compose or entrypoint.sh

---

### 3. `shared_dir/key_backups/` (Key Backups)

**Purpose**: Stores backup copies of key blobs before deletion.

**Location**: `shared_dir/key_backups/`

**Auto-created**: Yes, by the code when backing up keys

**Contents**:
- `{key_name}_backup.json` - Backup files containing:
  - Base64-encoded public key blob
  - Base64-encoded private key blob
  - Key metadata
  - Backup timestamp

**Format Example**:
```json
{
  "key_name": "my_signing_key",
  "backed_up_at": 1234567890,
  "public_blob": "base64_encoded_public_key_blob...",
  "private_blob": "base64_encoded_private_key_blob...",
  "public_file": "my_signing_key_1234567890.pub",
  "private_file": "my_signing_key_1234567890.priv",
  "key_info": {
    "key_name": "my_signing_key",
    "key_type": "rsa",
    "context_file": "my_signing_key_1234567890.ctx",
    ...
  }
}
```

**Usage**: Used for key recovery after TPM restarts or state loss

---

## File Types and Naming Conventions

### Context Files (`.ctx`)

**Purpose**: TPM context files that reference loaded keys in the TPM.

**Naming**:
- Primary keys: `anylog_signing_primary.ctx`, `anylog_primary.ctx`
- Signing keys: `{key_name}_{timestamp}.ctx`
- AES keys: `anylog_encrypt_key_aes.ctx`

**Location**: `shared_dir/`

**Persistence**: 
- Context files persist on disk
- But they reference TPM state, which may be lost after TPM restart
- Use backups to recover if TPM state is lost

---

### Key Blob Files (`.pub`, `.priv`)

**Purpose**: Public and private key blobs (encrypted TPM format).

**Naming**: `{key_name}_{timestamp}.pub` and `{key_name}_{timestamp}.priv`

**Location**: `shared_dir/` (temporary)

**Lifecycle**:
1. Created when key is generated
2. Loaded into TPM (creates `.ctx` file)
3. **Automatically deleted** after successful load (for security)
4. Backed up to `key_backups/` before deletion

**Important**: These files are deleted for security - keys are stored in TPM, not on disk

---

### Signature Files (`.sig`)

**Purpose**: Store signatures created by TPM signing operations.

**Naming**: `signature_{key_name}_{timestamp}.sig`

**Location**: `shared_dir/`

**Format**: Base64-encoded signature data

**Persistence**: Files persist until manually deleted

---

### Metadata Files (`.json`)

#### `signing_keys_metadata.json`

**Purpose**: Stores metadata about all signing keys.

**Location**: `shared_dir/signing_keys_metadata.json`

**Format**:
```json
{
  "key_name_1": {
    "key_name": "key_name_1",
    "key_type": "rsa",
    "context_file": "key_name_1_1234567890.ctx",
    "public_file": "key_name_1_1234567890.pub",
    "private_file": "key_name_1_1234567890.priv",
    "persistent_handle": null,
    "created_at": 1234567890,
    "parent_context": "anylog_signing_primary.ctx"
  },
  "key_name_2": { ... }
}
```

**Auto-created**: Yes, when first key is created

---

#### `anylog_key_store.json` (Encrypted File Store)

**Purpose**: Encrypted key-value store for AnyLog keys (pubkeys/privkeys).

**Location**: `shared_dir/anylog_key_store.json`

**Format**: Encrypted JSON file (AES-encrypted)

**Default Name**: `anylog_key_store.json` (configurable)

**Auto-created**: Yes, when first key-value pair is stored

---

## Default File Names

### Signing Keys (anylog_utils_sign.py)

| File Type | Default Name | Location |
|-----------|-------------|----------|
| Primary Context | `anylog_signing_primary.ctx` | `shared_dir/` |
| Metadata | `signing_keys_metadata.json` | `shared_dir/` |
| Backup Directory | `key_backups/` | `shared_dir/key_backups/` |

### Encrypted File Store (anylog_inrn.py)

| File Type | Default Name | Location |
|-----------|-------------|----------|
| Primary Context | `anylog_primary.ctx` | `shared_dir/` |
| AES Key Context | `anylog_encrypt_key_aes.ctx` | `shared_dir/` |
| Encrypted Store | `anylog_key_store.json` | `shared_dir/` |

---

## Docker Setup

### Volume Mounts

```yaml
volumes:
  - ./shared_dir:/opt/shared              # Main shared directory
  - ./shared_dir/tpm_state:/tmp/tpm2-emulated  # TPM state
```

### Working Directory

The API runs from `/opt/shared` (mapped to `./shared_dir`) so all files are created in the shared directory.

### Initial Setup

```bash
# Create directories
mkdir -p shared_dir
mkdir -p shared_dir/tpm_state

# Set permissions (if needed)
chmod 777 shared_dir
chmod 700 shared_dir/tpm_state

# Start docker-compose
docker-compose up -d
```

---

## Production Setup (AnyLog Integration)

### Dynamic Path Configuration

In production, the shared directory path is configured via AnyLog parameters:

```python
# anylog_inrn.py uses:
Path(anylog_params.get_value_if_available("!tpm_dir"))
```

**Set the parameter in AnyLog**:
```sql
!tpm_dir = /path/to/your/tpm/directory
```

### Required Structure

```
/path/to/your/tpm/directory/
├── tpm_state/                    # Only if using SWTPM
│   └── tpm2-00.permall
├── key_backups/                  # Auto-created
│   └── {key_name}_backup.json
├── signing_keys_metadata.json    # Auto-created
├── anylog_signing_primary.ctx    # Auto-created
├── anylog_primary.ctx            # Auto-created
├── anylog_encrypt_key_aes.ctx    # Auto-created
└── anylog_key_store.json         # Auto-created
```

---

## File Lifecycle

### Signing Key Creation Flow

1. **Create Key**: 
   - Creates `{key_name}_{timestamp}.pub` and `{key_name}_{timestamp}.priv`
   
2. **Load into TPM**: 
   - Creates `{key_name}_{timestamp}.ctx` (context file)
   
3. **Backup Blobs**: 
   - Creates `key_backups/{key_name}_backup.json` with base64-encoded blobs
   
4. **Delete Blobs**: 
   - Deletes `.pub` and `.priv` files (for security)
   - Keys now only exist in TPM (referenced by `.ctx` file)

5. **Update Metadata**: 
   - Updates `signing_keys_metadata.json` with key information

### Encrypted File Store Flow

1. **Create Primary Key**: 
   - Creates `anylog_primary.ctx`
   
2. **Create AES Key**: 
   - Creates `anylog_encrypt_key_aes.pub` and `anylog_encrypt_key_aes.priv` (temporary)
   - Creates `anylog_encrypt_key_aes.ctx` (context file)
   - Deletes `.pub` and `.priv` files
   
3. **Create Store**: 
   - Creates `anylog_key_store.json` (encrypted)
   
4. **Store Keys**: 
   - Encrypted key-value pairs stored in `anylog_key_store.json`

---

## Backup and Recovery

### What to Backup

**Critical Files** (must backup):
- `shared_dir/tpm_state/tpm2-00.permall` - TPM state (SWTPM only)
- `shared_dir/key_backups/` - All key backup files
- `shared_dir/signing_keys_metadata.json` - Key metadata
- `shared_dir/anylog_key_store.json` - Encrypted file store

**Optional Files** (can be regenerated):
- `.ctx` files - Can be regenerated from backups
- `.sig` files - Signatures (usually not needed for recovery)

### Recovery Process

1. **After TPM Restart** (SWTPM):
   - Restore `tpm_state/tpm2-00.permall` from backup
   - Context files should work again

2. **After TPM State Loss**:
   - Use `recover_key_from_backup()` function
   - Restores keys from `key_backups/` directory
   - Recreates context files

3. **After Complete Loss**:
   - Restore `key_backups/` directory
   - Restore `signing_keys_metadata.json`
   - Restore `anylog_key_store.json`
   - Run recovery functions to reload keys

---

## Permissions

### Recommended Permissions

```bash
# Main shared directory
chmod 755 shared_dir          # Readable by all, writable by owner

# TPM state (sensitive)
chmod 700 shared_dir/tpm_state  # Only owner can access

# Key backups (sensitive)
chmod 700 shared_dir/key_backups  # Only owner can access

# Metadata and stores
chmod 644 shared_dir/*.json   # Readable by all, writable by owner
chmod 644 shared_dir/*.ctx     # Readable by all, writable by owner
```

### Docker Permissions

Docker runs as root by default, so permissions are less critical. However, for production:

```bash
# Set ownership
chown -R tpm-user:tpm-user shared_dir

# Set permissions
chmod 755 shared_dir
chmod 700 shared_dir/tpm_state
chmod 700 shared_dir/key_backups
```

---

## Cleanup

### Temporary Files

The system automatically cleans up:
- `.pub` and `.priv` files after keys are loaded
- Temporary decrypted files (if any)

### Manual Cleanup

You can safely delete:
- Old `.sig` files (signatures)
- Old context files (if keys are no longer needed)
- Old backup files (if keys are no longer needed)

**Do NOT delete**:
- `tpm_state/tpm2-00.permall` - Contains TPM state
- `key_backups/` - Needed for recovery
- `signing_keys_metadata.json` - Needed to find keys
- `anylog_key_store.json` - Contains encrypted data

---

## Summary

### Required Directories

1. ✅ `shared_dir/` - Main shared directory
2. ✅ `shared_dir/tpm_state/` - TPM state (SWTPM only)
3. ✅ `shared_dir/key_backups/` - Key backups (auto-created)

### Required Files (Auto-Created)

1. ✅ `shared_dir/signing_keys_metadata.json` - Key metadata
2. ✅ `shared_dir/anylog_signing_primary.ctx` - Primary signing key
3. ✅ `shared_dir/anylog_primary.ctx` - Primary key for file store
4. ✅ `shared_dir/anylog_encrypt_key_aes.ctx` - AES encryption key
5. ✅ `shared_dir/anylog_key_store.json` - Encrypted file store
6. ✅ `shared_dir/tpm_state/tpm2-00.permall` - TPM state (SWTPM)

### Temporary Files (Auto-Deleted)

1. ⚠️ `{key_name}_{timestamp}.pub` - Deleted after load
2. ⚠️ `{key_name}_{timestamp}.priv` - Deleted after load

All directories and most files are auto-created by the system. You only need to ensure the base `shared_dir/` directory exists and is writable.

