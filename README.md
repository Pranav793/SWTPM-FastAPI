# TPM2 Python API - System Call Based Implementation
<!-- 
## Overview

This project provides a Python API for TPM2 operations using system calls to the `tpm2-tools` command-line utilities instead of the problematic `tpm2-pytss` Python library. This approach is much more reliable and works perfectly in Docker containers with software TPM emulators.

## Key Features

- **System Call Based**: Uses `tpm2-tools` command-line utilities instead of Python libraries
- **Docker Ready**: Works seamlessly in containers with swtpm (software TPM emulator)
- **REST API**: FastAPI-based REST interface for TPM2 operations
- **CLI Interface**: Command-line interface for direct TPM2 operations
- **No Complex Dependencies**: Eliminates the need for complex TPM2 Python library installations

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Python API    │    │   tpm2-tools    │
│   REST Server   │───▶│   (System Calls)│───▶│   (CLI Tools)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   swtpm         │
                       │   (TPM Emulator)│
                       └─────────────────┘
```

## Docker Setup

The project includes a complete Docker setup with:
- Ubuntu base image
- TPM2-TSS library (built from source)
- swtpm (software TPM emulator)
- tpm2-tools (command-line utilities)
- FastAPI and Python dependencies -->


## Key Features
- **REST API**: Access TPM2 functionality via a FastAPI-based REST API for easy integration with other services and automation.
- **CLI Interface**: Use the Python command-line interface (CLI) for direct TPM2 operations from the terminal or scripts.



### Building and Running

```bash
# Build the Docker image
docker build -t tpm2-api .

# Run the container for REST API
docker run -d --name tpm2-test -p 8000:8000 tpm2-api python3 /opt/tpm2_rest_api.py

# Run the container for interactive CLI
# Start container and get a bash shell
docker run --rm -it tpm2-api bash
# With volume mount for file sharing
docker run --rm -it -v $(pwd):/workspace -w /workspace tpm2-api bash

# Delete the container and image
docker rm -f tpm2-test tpm2-cli 2>/dev/null; docker rmi -f tpm2-api 2>/dev/null
```


## API Endpoints

### Health Check
- `GET /health` - Check TPM2 connection and status

### TPM2 Operations
- `POST /tpm2/create-primary` - Create a primary key
- `POST /tpm2/create-key` - Create a key under a parent
- `POST /tpm2/load-key` - Load a key into TPM context
- `POST /tpm2/make-persistent` - Make a key persistent
- `POST /tpm2/flush-context` - Flush TPM contexts
- `GET /tpm2/info` - Get TPM information
- `POST /tpm2/sign` - Sign data using a loaded key
- `POST /tpm2/verify` - Verify a signature
- `POST /tpm2/encrypt` - Encrypt data using a loaded RSA key
- `POST /tpm2/decrypt` - Decrypt data using a loaded RSA key
- `POST /tpm2/full-reset` - Complete TPM reset (clears all contexts, persistent objects, and authorizations)

### Convenience Endpoints
- `POST /tpm2/workflow/complete` - Execute complete workflow
- `POST /tpm2/upload-key` - Upload key files

## Usage Examples

### Create Primary Key
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"hierarchy": "o", "context_file": "primary.ctx"}' \
  http://localhost:8000/tpm2/create-primary
```

### Create RSA Key
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"parent_context": "primary.ctx", "key_type": "rsa", "public_file": "rsa.pub", "private_file": "rsa.priv"}' \
  http://localhost:8000/tpm2/create-key
```

### Load Key
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"parent_context": "primary.ctx", "public_file": "rsa.pub", "private_file": "rsa.priv", "context_file": "loaded_key.ctx"}' \
  http://localhost:8000/tpm2/load-key
```

### Make Key Persistent (EvictControl)
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"context_file": "loaded_key.ctx", "persistent_handle": "0x81010001"}' \
  http://localhost:8000/tpm2/make-persistent
```

### Flush Contexts (when running out of memory)
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"context_type": "all"}' \
  http://localhost:8000/tpm2/flush-context
```

### Full TPM Reset (CLI)
```bash
# ⚠️ WARNING: This performs a complete TPM reset!
python3 tpm2_cli.py full-reset
```

### Sign Data
```bash
# First, ensure you have a loaded key context
# Then sign data (data must be base64 encoded)
curl -X POST -H "Content-Type: application/json" \
  -d '{"context_file": "loaded_key.ctx", "data": "SGVsbG8gV29ybGQ=", "signature_file": "signature.sig"}' \
  http://localhost:8000/tpm2/sign
```

### Verify Signature
```bash
# Verify a signature against the original data
curl -X POST -H "Content-Type: application/json" \
  -d '{"context_file": "loaded_key.ctx", "data": "SGVsbG8gV29ybGQ=", "signature": "base64_encoded_signature_here"}' \
  http://localhost:8000/tpm2/verify
```



### Encrypt Data
```bash
# Encrypt data using a loaded RSA key
curl -X POST -H "Content-Type: application/json" \
  -d '{"context_file": "loaded_key.ctx", "data": "SGVsbG8gV29ybGQ=", "encrypted_file": "encrypted.bin"}' \
  http://localhost:8000/tpm2/encrypt
```

### Decrypt Data
```bash
# Decrypt data using a loaded RSA key
curl -X POST -H "Content-Type: application/json" \
  -d '{"context_file": "loaded_key.ctx", "encrypted_data": "base64_encoded_encrypted_data", "decrypted_file": "decrypted.bin"}' \
  http://localhost:8000/tpm2/decrypt
```

### Full TPM Reset
```bash
# ⚠️ WARNING: This performs a complete TPM reset!
# Clears all contexts, persistent objects, and authorizations
curl -X POST http://localhost:8000/tpm2/full-reset
```

### Complete Sign/Verify Workflow Example
```python
import base64
import requests
import json

# API base URL
base_url = "http://localhost:8000"

# 1. Create primary key
print("Creating primary key...")
response = requests.post(f"{base_url}/tpm2/create-primary", 
                        json={"hierarchy": "o", "context_file": "primary.ctx"})
print(json.dumps(response.json(), indent=2))

# 2. Create RSA key
print("\nCreating RSA key...")
response = requests.post(f"{base_url}/tpm2/create-key",
                        json={"parent_context": "primary.ctx", 
                              "key_type": "rsa", 
                              "public_file": "rsa.pub", 
                              "private_file": "rsa.priv"})
print(json.dumps(response.json(), indent=2))

# 3. Load the key
print("\nLoading key...")
response = requests.post(f"{base_url}/tpm2/load-key",
                        json={"parent_context": "primary.ctx",
                              "public_file": "rsa.pub",
                              "private_file": "rsa.priv",
                              "context_file": "loaded_key.ctx"})
print(json.dumps(response.json(), indent=2))

# 4. Prepare data to sign (base64 encode)
data_to_sign = "Hello, TPM2 World!"
encoded_data = base64.b64encode(data_to_sign.encode()).decode()
print(f"\nData to sign: {data_to_sign}")
print(f"Base64 encoded: {encoded_data}")

# 5. Sign the data
print("\nSigning data...")
response = requests.post(f"{base_url}/tpm2/sign",
                        json={"context_file": "loaded_key.ctx",
                              "data": encoded_data,
                              "signature_file": "signature.sig"})
sign_result = response.json()
print(json.dumps(sign_result, indent=2))

if sign_result.get("success"):
    signature = sign_result["signature"]
    print(f"Signature (base64): {signature}")
    
    # 6. Verify the signature
    print("\nVerifying signature...")
    response = requests.post(f"{base_url}/tpm2/verify",
                            json={"context_file": "loaded_key.ctx",
                                  "data": encoded_data,
                                  "signature": signature})
    verify_result = response.json()
    print(json.dumps(verify_result, indent=2))
    
    if verify_result.get("verified"):
        print("✅ Signature verification successful!")
    else:
        print("❌ Signature verification failed!")
else:
    print("❌ Signing failed!")
```

### Direct Python API Usage (without REST)
```python
from tpm2_api import TPM2API
import base64

# Initialize TPM2 API
tpm = TPM2API()

# Create primary key
result = tpm.create_primary_key()
print("Primary key created:", result["success"])

# Create and load RSA key
result = tpm.create_key("primary.ctx", "rsa", "rsa.pub", "rsa.priv")
print("RSA key created:", result["success"])

result = tpm.load_key("primary.ctx", "rsa.pub", "rsa.priv", "loaded_key.ctx")
print("Key loaded:", result["success"])

# Sign data
data = "Hello, TPM2!"
encoded_data = base64.b64encode(data.encode()).decode()

result = tpm.sign_data("loaded_key.ctx", encoded_data, "signature.sig")
if result["success"]:
    signature = result["signature"]
    print(f"Signature: {signature}")
    
    # Verify signature
    verify_result = tpm.verify_signature("loaded_key.ctx", encoded_data, signature)
    print(f"Verification: {verify_result['verified']}")
```

### Complete Encryption/Decryption Workflow Example
```python
import base64
import requests
import json

# API base URL
base_url = "http://localhost:8000"

# 1. Create primary key
print("Creating primary key...")
response = requests.post(f"{base_url}/tpm2/create-primary", 
                        json={"hierarchy": "o", "context_file": "primary.ctx"})
print(json.dumps(response.json(), indent=2))

# 2. Create encryption key
print("\nCreating encryption key...")
response = requests.post(f"{base_url}/tpm2/create-key",
                        json={"parent_context": "primary.ctx", 
                              "key_type": "rsa", 
                              "public_file": "encrypt_key.pub", 
                              "private_file": "encrypt_key.priv"})
print(json.dumps(response.json(), indent=2))

# 3. Load encryption key
print("\nLoading encryption key...")
response = requests.post(f"{base_url}/tpm2/load-key",
                        json={"parent_context": "primary.ctx",
                              "public_file": "encrypt_key.pub",
                              "private_file": "encrypt_key.priv",
                              "context_file": "encrypt_key.ctx"})
print(json.dumps(response.json(), indent=2))

# 4. Prepare data to encrypt (base64 encode)
data_to_encrypt = "Secret message for encryption!"
encoded_data = base64.b64encode(data_to_encrypt.encode()).decode()
print(f"\nData to encrypt: {data_to_encrypt}")
print(f"Base64 encoded: {encoded_data}")

# 5. Encrypt the data
print("\nEncrypting data...")
response = requests.post(f"{base_url}/tpm2/encrypt",
                        json={"context_file": "encrypt_key.ctx",
                              "data": encoded_data,
                              "encrypted_file": "encrypted.bin"})
encrypt_result = response.json()
print(json.dumps(encrypt_result, indent=2))

if encrypt_result.get("success"):
    encrypted_data = encrypt_result["encrypted_data"]
    print(f"Encrypted data (base64): {encrypted_data}")
    
    # 6. Decrypt the data
    print("\nDecrypting data...")
    response = requests.post(f"{base_url}/tpm2/decrypt",
                            json={"context_file": "encrypt_key.ctx",
                                  "encrypted_data": encrypted_data,
                                  "decrypted_file": "decrypted.bin"})
    decrypt_result = response.json()
    print(json.dumps(decrypt_result, indent=2))
    
    if decrypt_result.get("success"):
        decrypted_data = decrypt_result["decrypted_data"]
        original_data = base64.b64decode(decrypted_data).decode()
        print(f"✅ Decryption successful!")
        print(f"Original data: {data_to_encrypt}")
        print(f"Decrypted data: {original_data}")
        print(f"Match: {data_to_encrypt == original_data}")
    else:
        print("❌ Decryption failed!")
else:
    print("❌ Encryption failed!")
```
<!-- 
## Key Advantages

1. **Reliability**: No complex Python library dependencies
2. **Compatibility**: Works with any TPM2 implementation
3. **Simplicity**: Uses proven command-line tools
4. **Docker Friendly**: Perfect for containerized deployments
5. **Error Handling**: Better error messages and debugging
6. **Extensibility**: Easy to add new TPM2 operations -->

## Limitations

- **Memory Constraints**: Software TPM emulators have limited memory for object contexts
- **Performance**: System calls are slightly slower than direct library calls
- **File Management**: Requires careful management of context files

## Troubleshooting

### Out of Memory Errors
When you encounter "out of memory for object contexts" errors:
1. Flush all contexts: `POST /tpm2/flush-context` with `{"context_type": "transient"}` or `{"context_type": "all"}`
2. Retry your operation

### TCTI Configuration
The API automatically configures the TCTI for swtpm:
- `TSS2_TCTI=swtpm:host=127.0.0.1,port=2321`
- `TPM2TOOLS_TCTI=swtpm:host=127.0.0.1,port=2321`

## Development

### Local Development
```bash
# Install dependencies
pip install fastapi uvicorn pydantic python-multipart

# Run the API
python3 tpm2_rest_api.py
```

### Testing
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test complete workflow
curl -X POST http://localhost:8000/tpm2/workflow/complete
```
<!-- 
## Files Structure

- `tpm2_api.py` - Core TPM2 API using system calls
- `tpm2_rest_api.py` - FastAPI REST server
- `tpm2_cli.py` - Command-line interface
- `Dockerfile` - Docker container definition
- `entrypoint.sh` - Container startup script
- `requirements.txt` - Python dependencies

## Success Metrics

✅ **Primary Key Creation**: Working  
✅ **Key Creation**: Working  
✅ **Context Flushing**: Working  
✅ **TPM Information**: Working  
✅ **REST API**: Working  
✅ **Docker Container**: Working  
✅ **System Call Approach**: Working   -->
<!-- 
The system-call-based approach successfully eliminates the dependency issues with `tpm2-pytss` and provides a reliable, containerized TPM2 API solution.  -->