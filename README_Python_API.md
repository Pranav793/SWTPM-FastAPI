# TPM2 Python API - System Call Based Implementation

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
- FastAPI and Python dependencies

### Building and Running

```bash
# Build the Docker image
docker build -t tpm2-api .

# Run the container
docker run -d --name tpm2-test -p 8000:8000 tpm2-api python3 /opt/tpm2_rest_api.py
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
  -d '{"context_file": "loaded_key.ctx", "persistent_handle": 0x81010001}' \
  http://localhost:8000/tpm2/make-persistent
```

### Flush Contexts (when running out of memory)
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"context_type": "all"}' \
  http://localhost:8000/tpm2/flush-context
```

## Key Advantages

1. **Reliability**: No complex Python library dependencies
2. **Compatibility**: Works with any TPM2 implementation
3. **Simplicity**: Uses proven command-line tools
4. **Docker Friendly**: Perfect for containerized deployments
5. **Error Handling**: Better error messages and debugging
6. **Extensibility**: Easy to add new TPM2 operations

## Limitations

- **Memory Constraints**: Software TPM emulators have limited memory for object contexts
- **Performance**: System calls are slightly slower than direct library calls
- **File Management**: Requires careful management of context files

## Troubleshooting

### Out of Memory Errors
When you encounter "out of memory for object contexts" errors:
1. Flush all contexts: `POST /tpm2/flush-context` with `{"context_type": "all"}`
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
✅ **System Call Approach**: Working  

The system-call-based approach successfully eliminates the dependency issues with `tpm2-pytss` and provides a reliable, containerized TPM2 API solution. 