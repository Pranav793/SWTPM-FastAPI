#!/usr/bin/env python3
"""
TPM2 REST API - FastAPI wrapper for TPM2 operations
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import os
import json

# Import our TPM2 API
from tpm2_api import TPM2API

# Initialize FastAPI app
app = FastAPI(
    title="TPM2 REST API",
    description="REST API for TPM2 operations using software TPM emulator",
    version="1.0.0"
)

# Initialize TPM2 API
try:
    tpm_api = TPM2API()
except Exception as e:
    print(f"Warning: TPM2 API initialization failed: {e}")
    tpm_api = None

# Pydantic models for request/response
class PrimaryKeyRequest(BaseModel):
    hierarchy: str = "o"
    context_file: str = "primary.ctx"

class CreateKeyRequest(BaseModel):
    parent_context: str
    key_type: str = "rsa"
    public_file: str = "key.pub"
    private_file: str = "key.priv"

class LoadKeyRequest(BaseModel):
    parent_context: str
    public_file: str
    private_file: str
    context_file: str = "loaded_key.ctx"

class PersistentRequest(BaseModel):
    context_file: str
    persistent_handle: int = 0x81010001

class FlushContextRequest(BaseModel):
    context_type: str = "transient"

class SignDataRequest(BaseModel):
    context_file: str
    data: str  # base64 encoded data
    signature_file: str = "signature.sig"

class VerifySignatureRequest(BaseModel):
    context_file: str
    data: str  # base64 encoded data
    signature: str  # base64 encoded signature

class EncryptDataRequest(BaseModel):
    context_file: str
    data: str  # base64 encoded data
    encrypted_file: str = "encrypted.bin"

class DecryptDataRequest(BaseModel):
    context_file: str
    encrypted_data: str  # base64 encoded encrypted data
    decrypted_file: str = "decrypted.bin"



# Health check endpoint
@app.get("/")
async def root():
    return {"message": "TPM2 REST API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        info = tpm_api.get_tpm_info()
        return {
            "status": "healthy",
            "tpm_info": info
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"TPM2 health check failed: {e}")

# TPM2 operation endpoints
@app.post("/tpm2/create-primary")
async def create_primary_key(request: PrimaryKeyRequest):
    """Create a primary key in the specified hierarchy"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        result = tpm_api.create_primary_key(
            hierarchy=request.hierarchy,
            context_file=request.context_file
        )
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tpm2/create-key")
async def create_key(request: CreateKeyRequest):
    """Create a key under the specified parent"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        result = tpm_api.create_key(
            parent_context=request.parent_context,
            key_type=request.key_type,
            public_file=request.public_file,
            private_file=request.private_file
        )
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tpm2/load-key")
async def load_key(request: LoadKeyRequest):
    """Load a key into the TPM"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        result = tpm_api.load_key(
            parent_context=request.parent_context,
            public_file=request.public_file,
            private_file=request.private_file,
            context_file=request.context_file
        )
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tpm2/make-persistent")
async def make_persistent(request: PersistentRequest):
    """Make a loaded key persistent"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        result = tpm_api.make_persistent(
            context_file=request.context_file,
            persistent_handle=request.persistent_handle
        )
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tpm2/flush-context")
async def flush_context(request: FlushContextRequest):
    """Flush TPM contexts"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        result = tpm_api.flush_context(context_type=request.context_type)
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tpm2/info")
async def get_tpm_info():
    """Get TPM information"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        result = tpm_api.get_tpm_info()
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tpm2/sign")
async def sign_data(request: SignDataRequest):
    """Sign data using a loaded key"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        result = tpm_api.sign_data(
            context_file=request.context_file,
            data=request.data,
            signature_file=request.signature_file
        )
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tpm2/verify")
async def verify_signature(request: VerifySignatureRequest):
    """Verify a signature"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        result = tpm_api.verify_signature(
            context_file=request.context_file,
            data=request.data,
            signature=request.signature
        )
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/tpm2/encrypt")
async def encrypt_data(request: EncryptDataRequest):
    """Encrypt data using a loaded RSA key"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        result = tpm_api.encrypt_data(
            context_file=request.context_file,
            data=request.data,
            encrypted_file=request.encrypted_file
        )
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tpm2/decrypt")
async def decrypt_data(request: DecryptDataRequest):
    """Decrypt data using a loaded RSA key"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        result = tpm_api.decrypt_data(
            context_file=request.context_file,
            encrypted_data=request.encrypted_data,
            decrypted_file=request.decrypted_file
        )
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tpm2/full-reset")
async def full_reset():
    """Perform a complete TPM reset - clears all contexts, persistent objects, and authorizations"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        result = tpm_api.full_reset()
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Convenience endpoint for the complete workflow
@app.post("/tpm2/workflow/complete")
async def complete_workflow():
    """Execute the complete TPM2 workflow: create primary -> create key -> load -> make persistent"""
    if tpm_api is None:
        raise HTTPException(status_code=503, detail="TPM2 API not available")
    
    try:
        results = {}
        
        # Step 1: Create primary key
        print("Creating primary key...")
        result = tpm_api.create_primary_key()
        results["create_primary"] = result
        if not result["success"]:
            raise HTTPException(status_code=400, detail=f"Primary key creation failed: {result['error']}")
        
        # Step 2: Create RSA key
        print("Creating RSA key...")
        result = tpm_api.create_key("primary.ctx", "rsa", "rsa.pub", "rsa.priv")
        results["create_key"] = result
        if not result["success"]:
            raise HTTPException(status_code=400, detail=f"Key creation failed: {result['error']}")
        
        # Step 3: Load key
        print("Loading key...")
        result = tpm_api.load_key("primary.ctx", "rsa.pub", "rsa.priv", "rsa.ctx")
        results["load_key"] = result
        if not result["success"]:
            raise HTTPException(status_code=400, detail=f"Key loading failed: {result['error']}")
        
        # Step 4: Make persistent
        print("Making key persistent...")
        result = tpm_api.make_persistent("rsa.ctx")
        results["make_persistent"] = result
        if not result["success"]:
            raise HTTPException(status_code=400, detail=f"Making persistent failed: {result['error']}")
        
        return JSONResponse(content={
            "success": True,
            "message": "Complete workflow executed successfully",
            "results": results
        }, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# File upload endpoint for key files
@app.post("/tpm2/upload-key")
async def upload_key(
    public_file: UploadFile = File(...),
    private_file: UploadFile = File(...)
):
    """Upload public and private key files"""
    try:
        # Save uploaded files
        public_path = f"uploaded_{public_file.filename}"
        private_path = f"uploaded_{private_file.filename}"
        
        with open(public_path, "wb") as f:
            f.write(await public_file.read())
        
        with open(private_path, "wb") as f:
            f.write(await private_file.read())
        
        return {
            "success": True,
            "public_file": public_path,
            "private_file": private_path,
            "message": "Files uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Run the FastAPI server
    uvicorn.run(
        "tpm2_rest_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 