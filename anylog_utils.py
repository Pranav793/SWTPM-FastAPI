#!/usr/bin/env python3
"""
AnyLog TPM2 Integration Utilities

This module provides functions to integrate TPM2 encrypted file store
with AnyLog nodes for storing and retrieving keys (pubkeys/privkeys).
Uses HTTP requests to communicate with the TPM2 REST API.
"""

import base64
import os
from pathlib import Path
import requests
import subprocess
import time
from typing import Dict, Any, Optional, List, Iterable, Set

# Default API base URL
DEFAULT_API_URL = "http://localhost:8000"

# Default file names for TPM2 keys and file store
DEFAULT_PRIMARY_CTX = "anylog_primary.ctx"
# For AES keys, the API creates .pub and .priv files internally, then loads them into the .ctx file
# Users only need to reference the context file (.ctx) - the API handles the rest automatically
DEFAULT_ENCRYPT_KEY_CTX = "anylog_encrypt_key_aes.ctx"
DEFAULT_STORE_NAME = "anylog_key_store.json"
SHARED_DIR = Path("shared_dir")



def _resolve_shared_file_paths(raw_path: Optional[str]) -> Set[Path]:
    candidates: Set[Path] = set()
    if not raw_path:
        return candidates
    stripped = raw_path.strip()
    if not stripped:
        return candidates
    candidate = Path(stripped)
    candidates.add(candidate)
    if candidate.is_absolute():
        try:
            rel = candidate.relative_to("/opt/shared")
            candidates.add(SHARED_DIR / rel)
        except Exception:
            pass
    else:
        if candidate.parts and candidate.parts[0] == "shared_dir":
            candidates.add(candidate)
        else:
            candidates.add(SHARED_DIR / candidate)
    return candidates


def _remove_path_candidates(paths: Iterable[Path]) -> None:
    for path in paths:
        if not path:
            continue
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass


def _cleanup_aes_blob_files(encrypt_key_ctx: str, extra_paths: Optional[Iterable[str]] = None) -> None:
    ctx_path = Path(encrypt_key_ctx)
    base = ctx_path.with_suffix("") if ctx_path.suffix == ".ctx" else ctx_path
    candidates: Set[Path] = set()
    candidates.update(_resolve_shared_file_paths(str(base.with_suffix(".pub"))))
    candidates.update(_resolve_shared_file_paths(str(base.with_suffix(".priv"))))
    if extra_paths:
        for extra in extra_paths:
            candidates.update(_resolve_shared_file_paths(extra))
    _remove_path_candidates(candidates)


def setup_docker_container(
    build_path: str = ".",
    image_name: str = "tpm2-api",
    container_name: str = "tpm2-test",
    port: int = 8000,
    wait_for_ready: bool = True,
    wait_timeout: int = 60
) -> Dict[str, Any]:
    """
    Set up the TPM2 Docker container by removing old containers/images,
    building a new image, and running the container.
    
    Args:
        build_path: Path to the directory containing Dockerfile (default: current directory)
        image_name: Docker image name (default: tpm2-api)
        container_name: Docker container name (default: tpm2-test)
        port: Port to expose (default: 8000)
        wait_for_ready: Whether to wait for the API to be ready (default: True)
        wait_timeout: Maximum seconds to wait for API readiness (default: 60)
        
    Returns:
        Dictionary with success status and any errors
    """
    try:
        # Step 1: Remove existing containers and images
        print("Removing existing containers and images...")
        cleanup_cmd = f"docker rm -f tpm2-test tpm2-cli 2>/dev/null; docker rmi -f {image_name} 2>/dev/null"
        result = subprocess.run(
            cleanup_cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        # Ignore errors - containers/images might not exist
        
        # Step 2: Build Docker image
        print(f"Building Docker image '{image_name}'...")
        build_cmd = ["docker", "build", "-t", image_name, build_path]
        result = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for build
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Failed to build Docker image: {result.stderr}"
            }
        
        print(f"Docker image '{image_name}' built successfully")
        
        # Step 3: Run Docker container
        print(f"Starting Docker container '{container_name}'...")
        run_cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"{port}:8000",
            image_name,
            "python3", "/opt/tpm2_rest_api.py"
        ]
        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Failed to run Docker container: {result.stderr}"
            }
        
        container_id = result.stdout.strip()
        print(f"Docker container '{container_name}' started (ID: {container_id})")
        
        # Step 4: Wait for API to be ready (optional)
        if wait_for_ready:
            print("Waiting for API to be ready...")
            api_url = f"http://localhost:{port}"
            start_time = time.time()
            
            while time.time() - start_time < wait_timeout:
                try:
                    response = requests.get(f"{api_url}/health", timeout=2)
                    if response.status_code == 200:
                        print("API is ready!")
                        return {
                            "success": True,
                            "container_id": container_id,
                            "message": f"Container '{container_name}' is running and API is ready"
                        }
                except requests.exceptions.RequestException:
                    pass
                
                time.sleep(2)
            
            return {
                "success": False,
                "error": f"Container started but API did not become ready within {wait_timeout} seconds"
            }
        else:
            return {
                "success": True,
                "container_id": container_id,
                "message": f"Container '{container_name}' started (not waiting for API readiness)"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Docker operation timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error setting up Docker container: {str(e)}"
        }


def _make_request(method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None, base_url: str = DEFAULT_API_URL) -> Dict[str, Any]:
    """
    Make an HTTP request to the TPM2 REST API
    
    Args:
        method: HTTP method (e.g., "POST", "GET")
        endpoint: API endpoint path (e.g., "/tpm2/create-primary")
        json_data: Optional JSON data for the request
        base_url: Base URL for the API
        
    Returns:
        Dictionary with response data or error information
    """
    try:
        url = f"{base_url}{endpoint}"
        response = requests.request(method, url, json=json_data, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            # Try to parse the error response
            try:
                error_json = response.json()
                # Extract error message
                error_msg = error_json.get("detail", error_json.get("error", "Unknown error"))
                # Clean up error messages that might have status code prefixes like "400: ..."
                if isinstance(error_msg, str) and ":" in error_msg and error_msg.split(":")[0].strip().isdigit():
                    error_msg = ":".join(error_msg.split(":")[1:]).strip()
                
                # If the error response has useful fields, preserve them
                error_result = {
                    "success": False,
                    "error": error_msg
                }
                # Preserve additional fields like available_keys if present
                if "available_keys" in error_json:
                    error_result["available_keys"] = error_json["available_keys"]
                return error_result
            except (ValueError, KeyError):
                # If we can't parse JSON, use the text
                return {
                    "success": False,
                    "error": f"API request failed with status {response.status_code}: {response.text}"
                }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Network error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def _check_api_connectivity(base_url: str = DEFAULT_API_URL, timeout: int = 5) -> Dict[str, Any]:
    """
    Check if the TPM2 REST API at base_url is reachable and responding.
    
    Args:
        base_url: Base URL for the API
        timeout: Timeout in seconds for the connectivity check (default: 5)
    
    Returns:
        Dictionary with success status and any errors
    """
    try:
        # Try to reach the health endpoint first (if available)
        health_url = f"{base_url}/health"
        try:
            response = requests.get(health_url, timeout=timeout)
            if response.status_code == 200:
                return {"success": True}
        except requests.exceptions.RequestException:
            # Health endpoint might not exist, try the root endpoint
            pass
        
        # If health endpoint doesn't work, try the root endpoint
        try:
            response = requests.get(base_url, timeout=timeout)
            # Any response (even 404) means the server is reachable
            return {"success": True}
        except requests.exceptions.ConnectionError as e:
            return {
                "success": False,
                "error": f"Cannot connect to TPM2 API at {base_url}. Please ensure the API server is running and accessible. Connection error: {str(e)}"
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"Connection to TPM2 API at {base_url} timed out after {timeout} seconds. Please check if the server is running and accessible."
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Failed to connect to TPM2 API at {base_url}: {str(e)}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error checking API connectivity: {str(e)}"
        }


def _flush_context(base_url: str = DEFAULT_API_URL) -> None:
    """Flush TPM contexts to avoid memory issues"""
    try:
        result = _make_request("POST", "/tpm2/flush-context", 
                              json_data={"context_type": "transient"},
                              base_url=base_url)
        if not result.get("success"):
            # Log warning but don't fail - flushing is best effort
            print(f"Warning: Failed to flush TPM context: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"Warning: Failed to flush TPM context: {e}")


def _emit_aes_recovery_material(
    recovery_material: Optional[Dict[str, Any]],
    encrypt_key_ctx: str,
    store_name: str
) -> None:
    """
    Print recovery material for a newly created AES key so operators can back it up.
    Only emits output when private blob data is present.
    """
    if not recovery_material:
        return
    
    validation_errors = _validate_recovery_material(recovery_material)
    if validation_errors:
        print("Warning: Recovery material validation failed:")
        for error in validation_errors:
            print(f" - {error}")
        # Continue printing any captured blobs even if validation failed,
        # since operators might still salvage the data.
    
    if "private_blob_error" in recovery_material:
        print(f"Warning: Unable to capture AES private blob: {recovery_material['private_blob_error']}")
    if "public_blob_error" in recovery_material:
        print(f"Warning: Unable to capture AES public blob: {recovery_material['public_blob_error']}")
    
    if "private_blob_b64" not in recovery_material:
        return
    
    private_blob = recovery_material.get("private_blob_b64")
    public_blob = recovery_material.get("public_blob_b64")
    
    print("\n=== AnyLog TPM AES Recovery Material ===")
    print("A new AES key was created for the encrypted file store.")
    print(f"Context file: {encrypt_key_ctx}")
    print(f"File store: {store_name}")
    print("\nPrivate blob (base64):")
    print(private_blob)
    
    if public_blob:
        print("\nPublic blob (base64):")
        print(public_blob)
    
    print("\nStore these blobs securely off-container. They are required to restore the AES key if the TPM state is lost.")
    print("=== End AES Recovery Material ===\n")
    


def _validate_recovery_material(recovery_material: Dict[str, Any]) -> List[str]:
    """
    Validate that recovery material blobs are well-formed base64 strings.
    Returns a list of validation error messages.
    """
    errors: List[str] = []
    for label in ("private", "public"):
        blob = recovery_material.get(f"{label}_blob_b64")
        if blob:
            try:
                decoded = base64.b64decode(blob, validate=True)
                if not decoded:
                    errors.append(f"{label} blob decoded to empty bytes")
            except Exception as exc:
                errors.append(f"{label} blob is not valid base64: {exc}")
    return errors


def _decode_base64_blob(blob_b64: str, label: str) -> bytes:
    """
    Decode a base64-encoded blob, providing a helpful error message.
    """
    try:
        data = base64.b64decode(blob_b64, validate=True)
        if not data:
            raise ValueError("decoded data is empty")
        return data
    except Exception as exc:
        raise ValueError(f"{label} blob is not valid base64: {exc}") from exc


def _write_blob_to_file(blob_b64: str, destination: str, label: str) -> str:
    """
    Decode a base64 blob and write it to the supplied destination path.
    Returns the absolute path to the written file.
    """
    data = _decode_base64_blob(blob_b64, label)
    path = Path(destination).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return str(path)


def save_recovery_material_to_directory(
    recovery_material: Dict[str, Any],
    output_dir: str,
    prefix: Optional[str] = None
) -> Dict[str, Any]:
    """
    Persist AES recovery blobs to disk so they can be re-imported later.
    
    Args:
        recovery_material: Dict containing 'private_blob_b64' (required) and 'public_blob_b64' (optional)
        output_dir: Directory where the files should be written
        prefix: Optional prefix for the generated filenames (defaults to 'anylog_encrypt_key_aes')
        
    Returns:
        Dict with success flag and file paths
    """
    if not recovery_material:
        return {
            "success": False,
            "error": "No recovery material provided"
        }
    
    if "private_blob_b64" not in recovery_material:
        return {
            "success": False,
            "error": "Recovery material missing required 'private_blob_b64' field"
        }
    
    prefix = prefix or "anylog_encrypt_key_aes"
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    
    private_path = output_path / f"{prefix}.priv"
    public_path = None
    
    try:
        written_private = _write_blob_to_file(recovery_material["private_blob_b64"], str(private_path), "private")
        if "public_blob_b64" in recovery_material and recovery_material["public_blob_b64"]:
            public_path = output_path / f"{prefix}.pub"
            written_public = _write_blob_to_file(recovery_material["public_blob_b64"], str(public_path), "public")
        else:
            written_public = None
        
        return {
            "success": True,
            "private_file": written_private,
            "public_file": written_public,
            "output_dir": str(output_path)
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to write recovery files: {exc}"
        }


def restore_aes_key_from_recovery(
    parent_ctx: str = DEFAULT_PRIMARY_CTX,
    encrypt_key_ctx: str = DEFAULT_ENCRYPT_KEY_CTX,
    private_blob_b64: Optional[str] = None,
    public_blob_b64: Optional[str] = None,
    private_blob_path: Optional[str] = None,
    public_blob_path: Optional[str] = None,
    base_url: str = DEFAULT_API_URL,
    ensure_primary: bool = True,
    cleanup_temporary: bool = True
) -> Dict[str, Any]:
    """
    Restore the AES encryption key inside the TPM using previously exported blobs.
    
    The caller can supply either base64-encoded blobs, file paths, or a mix of both.
    
    Args:
        parent_ctx: Primary context file that owns the AES key
        encrypt_key_ctx: Target context file to recreate for the AES key
        private_blob_b64/public_blob_b64: Base64 encoded TPM blobs
        private_blob_path/public_blob_path: Paths to TPM blob files on disk
        base_url: REST API base URL
        ensure_primary: Whether to attempt re-creating the parent primary key if missing
        cleanup_temporary: Remove temporary files created for base64 blobs after loading
        
    Returns:
        Dict with success flag and any relevant messages/errors
    """
    tmp_files: List[str] = []
    
    def resolve_blob(label: str, blob_b64: Optional[str], blob_path: Optional[str], suffix: str) -> Optional[str]:
        # Ensure shared_dir exists
        shared_dir = Path("shared_dir")
        shared_dir.mkdir(exist_ok=True)
        
        if blob_path:
            path = Path(blob_path).expanduser().resolve()
            if not path.exists():
                raise FileNotFoundError(f"{label.capitalize()} blob file not found: {path}")
            
            # Check if path is already in shared_dir
            try:
                # Try to get relative path from shared_dir
                rel_path = path.relative_to(shared_dir.resolve())
                # Already in shared_dir, return relative path (container can access it)
                return str(rel_path)
            except ValueError:
                # Not in shared_dir, copy it there so container can access it
                tmp_filename = f"temp_recovery_{label}_{os.urandom(8).hex()}{suffix}"
                tmp_path_host = shared_dir / tmp_filename
                import shutil
                shutil.copy2(str(path), str(tmp_path_host))
                tmp_files.append(str(tmp_path_host))
                # Return relative path (just filename) that container can access
                return tmp_filename
        
        if blob_b64:
            # Write temp files to shared_dir so the Docker container can access them
            # shared_dir is mounted at /opt/shared in the container (which is the working directory)
            # So we write to shared_dir on host, and use relative path in container
            tmp_filename = f"temp_recovery_{label}_{os.urandom(8).hex()}{suffix}"
            tmp_path_host = shared_dir / tmp_filename
            _write_blob_to_file(blob_b64, str(tmp_path_host), label)
            tmp_files.append(str(tmp_path_host))
            # Return relative path (just filename) that container can access
            # The container's working directory is /opt/shared, so just the filename works
            return tmp_filename
        
        return None
    
    try:
        private_file = resolve_blob("private", private_blob_b64, private_blob_path, ".priv")
        public_file = resolve_blob("public", public_blob_b64, public_blob_path, ".pub")
        
        if not private_file:
            return {
                "success": False,
                "error": "A private blob is required to restore the AES key"
            }
        if not public_file:
            return {
                "success": False,
                "error": "A public blob is required to restore the AES key"
            }
        
        # Optionally recreate the primary parent (best effort)
        # IMPORTANT: Do NOT create a new primary key if TPM state is persisted and contains the original primary key.
        # Creating a new primary key would overwrite the old one, making recovery blobs unusable.
        # If ensure_primary is True, we assume the primary key already exists in persisted TPM state.
        # We'll try to use it directly - if it doesn't exist, the AES key load will fail with a clear error.
        if ensure_primary:
            primary_result = _make_request(
                    "POST",
                    "/tpm2/create-primary",
                    json_data={"hierarchy": "o", "context_file": parent_ctx},
                    base_url=base_url
                )
            if not primary_result.get("success"):
                error_msg = primary_result.get("error", "").lower()
                # if the backend ever returns an "already exists" style error, ignore it
                if "already exists" not in error_msg and "file exists" not in error_msg:
                    return {
                        "success": False,
                        "error": (
                            f"Failed to ensure primary key '{parent_ctx}': "
                            f"{primary_result.get('error', 'Unknown error')}"
                        ),
                    }
            # # Check if primary key context file exists - if it does, assume primary key exists in TPM state
            # # and skip creation (creating would make a NEW primary key, breaking recovery)
            # primary_ctx_exists = False
            # try:
            #     primary_path = Path(parent_ctx)
            #     if primary_path.is_absolute():
            #         primary_ctx_exists = primary_path.exists()
            #     else:
            #         primary_ctx_exists = primary_path.exists() or Path(f"shared_dir/{parent_ctx}").exists()
            # except Exception:
            #     primary_ctx_exists = False
            
            # # Only try to create primary key if context file doesn't exist
            # # If it exists, assume primary key is in TPM state and use it directly
            # if not primary_ctx_exists:
            #     primary_result = _make_request(
            #         "POST",
            #         "/tpm2/create-primary",
            #         json_data={"hierarchy": "o", "context_file": parent_ctx},
            #         base_url=base_url
            #     )
            #     if not primary_result.get("success"):
            #         # If the error indicates the primary already exists, ignore it; otherwise return failure.
            #         error_msg = primary_result.get("error", "").lower()
            #         if "already exists" not in error_msg and "file exists" not in error_msg:
            #             return {
            #                 "success": False,
            #                 "error": f"Failed to ensure primary key '{parent_ctx}': {primary_result.get('error', 'Unknown error')}"
            #             }
        
        _flush_context(base_url=base_url)
        
        load_result = _make_request(
            "POST",
            "/tpm2/load-key",
            json_data={
                "parent_context": parent_ctx,
                "public_file": public_file,
                "private_file": private_file,
                "context_file": encrypt_key_ctx
            },
            base_url=base_url
        )
        
        _flush_context(base_url=base_url)
        
        if load_result.get("success"):
            return {
                "success": True,
                "message": f"AES key restored into context '{encrypt_key_ctx}'",
                "context_file": encrypt_key_ctx,
                "public_file": public_file,
                "private_file": private_file
            }
        else:
            return {
                "success": False,
                "error": load_result.get("error", "Unknown error restoring AES key"),
                "details": load_result
            }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to restore AES key: {exc}"
        }
    finally:
        if cleanup_temporary:
            for path in tmp_files:
                try:
                    os.unlink(path)
                except Exception:
                    pass


def set_custom_aes_key_from_files(
    private_blob_path: str,
    public_blob_path: str,
    parent_ctx: str = DEFAULT_PRIMARY_CTX,
    encrypt_key_ctx: str = DEFAULT_ENCRYPT_KEY_CTX,
    store_name: str = DEFAULT_STORE_NAME,
    base_url: str = DEFAULT_API_URL,
    recreate_store: bool = False
) -> Dict[str, Any]:
    """
    Load a custom AES key into the TPM using existing TPM blob files on disk.
    
    Args:
        private_blob_path/public_blob_path: Paths to TPM private/public blob files
        parent_ctx: Primary parent context file
        encrypt_key_ctx: Target context file for the AES key
        store_name: AES file store name (used if recreate_store=True)
        base_url: REST API base URL
        recreate_store: If True, reinitialize the encrypted file store after loading the key
        
    Returns:
        Dict with success flag and any messages/errors
    """
    restore_result = restore_aes_key_from_recovery(
        parent_ctx=parent_ctx,
        encrypt_key_ctx=encrypt_key_ctx,
        private_blob_path=private_blob_path,
        public_blob_path=public_blob_path,
        base_url=base_url
    )
    
    if not restore_result.get("success"):
        return restore_result
    
    if recreate_store:
        _flush_context(base_url=base_url)
        create_result = _make_request(
            "POST",
            "/tpm2/file-store-aes/create",
            json_data={
                "context_file": encrypt_key_ctx,
                "store_name": store_name
            },
            base_url=base_url
        )
        _flush_context(base_url=base_url)
        
        if not create_result.get("success"):
            return {
                "success": False,
                "error": f"AES key loaded but failed to create encrypted store '{store_name}': {create_result.get('error', 'Unknown error')}"
            }
    
    return {
        "success": True,
        "message": "Custom AES key loaded successfully",
        "context_file": encrypt_key_ctx,
        "store_name": store_name,
        "recreated_store": recreate_store
    }


def set_custom_aes_key_from_base64(
    private_blob_b64: str,
    public_blob_b64: str,
    parent_ctx: str = DEFAULT_PRIMARY_CTX,
    encrypt_key_ctx: str = DEFAULT_ENCRYPT_KEY_CTX,
    store_name: str = DEFAULT_STORE_NAME,
    base_url: str = DEFAULT_API_URL,
    recreate_store: bool = False
) -> Dict[str, Any]:
    """
    Load a custom AES key into the TPM using base64-encoded TPM blobs.
    
    Args mirror set_custom_aes_key_from_files, but accept base64 strings instead of file paths.
    """
    restore_result = restore_aes_key_from_recovery(
        parent_ctx=parent_ctx,
        encrypt_key_ctx=encrypt_key_ctx,
        private_blob_b64=private_blob_b64,
        public_blob_b64=public_blob_b64,
        base_url=base_url
    )
    
    if not restore_result.get("success"):
        return restore_result
    
    if recreate_store:
        _flush_context(base_url=base_url)
        create_result = _make_request(
            "POST",
            "/tpm2/file-store-aes/create",
            json_data={
                "context_file": encrypt_key_ctx,
                "store_name": store_name
            },
            base_url=base_url
        )
        _flush_context(base_url=base_url)
        
        if not create_result.get("success"):
            return {
                "success": False,
                "error": f"AES key loaded but failed to create encrypted store '{store_name}': {create_result.get('error', 'Unknown error')}"
            }
    
    return {
        "success": True,
        "message": "Custom AES key loaded successfully",
        "context_file": encrypt_key_ctx,
        "store_name": store_name,
        "recreated_store": recreate_store
    }


def _ensure_tpm_setup(
    primary_ctx: str = DEFAULT_PRIMARY_CTX,
    encrypt_key_ctx: str = DEFAULT_ENCRYPT_KEY_CTX,
    store_name: str = DEFAULT_STORE_NAME,
    base_url: str = DEFAULT_API_URL
) -> Dict[str, Any]:
    """
    Ensure all necessary TPM2 components are set up using AES encryption:
    - Primary key (RSA key used as parent for AES key)
    - AES-256 encryption key (created under primary key with proper attributes for EncryptDecrypt)
    - Encrypted file store (using AES)
    
    This function checks if components exist by trying to use them first.
    Only creates components if they don't exist on the server.
    Uses AES encryption which doesn't have size limitations like RSA.
    
    Note: AES keys are created using tpm2_create (not primary) under a primary key.
    This ensures the AES key has proper attributes for EncryptDecrypt operations.
    The key is automatically loaded after creation, so the context file is ready to use.
    
    Args:
        primary_ctx: Path to primary key context file (default: anylog_primary.ctx)
        encrypt_key_ctx: Path to AES encryption key context file (default: anylog_encrypt_key_aes.ctx)
        store_name: Name of the encrypted file store
        base_url: Base URL for the API
    Returns:
        Dictionary with success status and any errors
        Notes: When the encrypted store exists but the AES key is not loaded, this
        function returns `needs_recovery=True` along with an error explaining that
        recovery blobs are required to restore the AES key. In that case, the caller
        needs to invoke `recover_aes_key_from_recovery_material()` to reload the key.
    """
    try:
        # First, check if the API is reachable before attempting any operations
        connectivity_check = _check_api_connectivity(base_url=base_url)
        if not connectivity_check.get("success"):
            return {
                "success": False,
                "error": connectivity_check.get("error", "API connectivity check failed"),
                "tpm_available": False
            }
        tpm_available = True
        
        # Quick check: Try to list keys from the AES file store
        # If this succeeds, everything is already set up
        _flush_context(base_url=base_url)
        test_result = _make_request("POST", "/tpm2/file-store-aes/list-keys",
                                   json_data={
                                       "context_file": encrypt_key_ctx,
                                       "store_name": store_name
                                   },
                                   base_url=base_url)
        
        if test_result.get("success"):
            # Everything is already set up, we can use it
            return {"success": True, "tpm_available": tpm_available}
        
        # If we get here, the file store either doesn't exist or keys aren't loaded
        # Check if the encrypted file store file exists (even if we can't decrypt it)
        # This helps us determine if we need recovery blobs or can create new keys
        # Note: store_name is relative to the container's working directory (/opt/shared)
        # which maps to ./shared_dir on the host. We check if it exists there.
        store_exists = False
        try:
            # Try to check if the file exists in the shared directory
            # The store_name is typically just a filename like "anylog_key_store.json"
            # and it's saved in the working directory which is /opt/shared in container
            # which maps to ./shared_dir on host
            store_path = Path(store_name)
            if store_path.is_absolute():
                store_exists = store_path.exists()
            else:
                # Check in current directory and common shared_dir location
                store_exists = store_path.exists() or Path(f"shared_dir/{store_name}").exists()
        except Exception:
            # If we can't check, assume it doesn't exist and proceed
            store_exists = False
        
        # Step 1: Create or reload primary key (RSA key used as parent for AES key)
        # IMPORTANT: TPM primary keys are non-deterministic - each creation produces a different key.
        # The AES key blobs are tied to the parent primary key, so we need the SAME primary key
        # to restore the AES key.
        #
        # If TPM state is persisted (via docker-compose volume mount), the primary key persists
        # in the TPM. However, tpm2_createprimary will create a NEW primary key if called,
        # which would overwrite the old one. So we need to be careful:
        # - If recovery blobs are provided, we MUST use the same primary key that created them
        # - If TPM state is persisted, the primary key should still exist in the TPM
        # - We should NOT create a new primary key if one already exists (it would be different)
        #
        # Solution: If recovery blobs are provided, we assume TPM state is persisted and
        # the primary key exists. We'll try to use it without creating a new one.
        # If recovery blobs are NOT provided and file store doesn't exist, create new keys.
        
        _flush_context(base_url=base_url)
        
        if not store_exists:
            primary_result = _make_request("POST", "/tpm2/create-primary",
                                          json_data={
                                              "hierarchy": "o",
                                              "context_file": primary_ctx
                                          },
                                          base_url=base_url)
            
            # Check primary key creation result
            if not primary_result.get("success"):
                error_msg = primary_result.get("error", "").lower()
                # If the error is not about the key already existing, report it
                if "already exists" not in error_msg and "file exists" not in error_msg:
                    # Primary key creation failed for an unexpected reason
                    return {
                        "success": False,
                        "error": f"Failed to create primary key: {primary_result.get('error', 'Unknown error')}"
                    }

        # Step 2: Create or reload AES-256 encryption key under the primary key
        # Priority: Recovery blobs > Create new key
        # We do NOT try to load from .pub/.priv files - those should not be in shared_dir
        
        _flush_context(base_url=base_url)
        result = None
        created_new_aes_key = False
        recovery_material = None
        public_blob = None
        private_blob = None

        if store_exists:
            return {
                "success": False,
                "error": f"Encrypted file store '{store_name}' exists but AES keys are not loaded. Recovery blobs are required to restore access.",
                "needs_recovery": True,
                "store_name": store_name,
                "tpm_available": tpm_available
            }

        # File store doesn't exist - create new AES key
        _flush_context(base_url=base_url)
        result = _make_request("POST", "/tpm2/create-key",
                              json_data={
                                  "parent_context": primary_ctx,  # Use primary key as parent
                                  "key_type": "aes256",
                                  "public_file": encrypt_key_ctx,  # Will create .pub and .priv, then load into .ctx
                              },
                              base_url=base_url)
        created_new_aes_key = True

        # Check if the key was created and loaded successfully
        if not result.get("success"):
            error_msg = result.get("error", "").lower()
            # If key creation failed for reasons other than "already exists", report it
            if "already exists" not in error_msg and "file exists" not in error_msg:
                # Check if the context_file was created (key is loaded and ready)
                if result.get("context_file") is None:
                    return {
                        "success": False,
                        "error": f"Failed to create or restore AES key: {result.get('error', 'Unknown error')}"
                    }
        else:
            # Emit recovery material if a new AES key was created
            if result.get("action") == "aes_key_created":
                _emit_aes_recovery_material(
                    recovery_material=result.get("recovery_material"),
                    encrypt_key_ctx=encrypt_key_ctx,
                    store_name=store_name
                )
            # Verify the context file exists in the response
            if result.get("context_file") is None:
                # Try to manually load the key if auto-load failed
                if result.get("public_file") and result.get("private_file"):
                    _flush_context(base_url=base_url)
                    load_result = _make_request("POST", "/tpm2/load-key",
                                              json_data={
                                                  "parent_context": primary_ctx,
                                                  "public_file": result.get("public_file"),
                                                  "private_file": result.get("private_file"),
                                                  "context_file": encrypt_key_ctx
                                              },
                                              base_url=base_url)
                    if not load_result.get("success"):
                        return {
                            "success": False,
                            "error": f"AES key created but failed to load: {load_result.get('error', 'Unknown error')}",
                            "tpm_available": tpm_available
                        }
        
        if created_new_aes_key and result and result.get("success"):
            _cleanup_aes_blob_files(
                encrypt_key_ctx,
                extra_paths=[result.get("public_file"), result.get("private_file")]
            )
            recovery_material = result.get("recovery_material")
            if recovery_material:
                public_blob = recovery_material.get("public_blob_b64")
                private_blob = recovery_material.get("private_blob_b64")

        # Step 3: Create AES encrypted file store (only if it doesn't exist)
        # Try to list keys first to check if store exists
        _flush_context(base_url=base_url)
        check_store = _make_request("POST", "/tpm2/file-store-aes/list-keys",
                                   json_data={
                                       "context_file": encrypt_key_ctx,
                                       "store_name": store_name
                                   },
                                   base_url=base_url)
        
        if not check_store.get("success"):
            # Store doesn't exist, create it
            _flush_context(base_url=base_url)
            result = _make_request("POST", "/tpm2/file-store-aes/create",
                                  json_data={
                                      "context_file": encrypt_key_ctx,
                                      "store_name": store_name
                                  },
                                  base_url=base_url)
            # If creation fails with "already exists" type error, that's okay
            # But if it's a real error (like wrong key), we should report it
            if not result.get("success"):
                error_msg = result.get("error", "").lower()
                # Only fail if it's not an "already exists" type error
                if "already exists" not in error_msg and "file exists" not in error_msg:
                    # Try one more time to verify the store works
                    verify_result = _make_request("POST", "/tpm2/file-store-aes/list-keys",
                                                 json_data={
                                                     "context_file": encrypt_key_ctx,
                                                     "store_name": store_name
                                                 },
                                                 base_url=base_url)
                    if not verify_result.get("success"):
                        return {
                            "success": False,
                            "error": f"Failed to create or verify AES encrypted file store: {result.get('error', 'Unknown error')}"
                        }
        
        payload = {"success": True, "tpm_available": tpm_available}
        if recovery_material:
            payload["recovery_material"] = recovery_material
        if public_blob:
            payload["public_blob_b64"] = public_blob
        if private_blob:
            payload["private_blob_b64"] = private_blob
        return payload
    except Exception as e:
        return {
            "success": False,
            "error": f"Error during TPM setup: {str(e)}",
            "tpm_available": False
        }
        

def recover_aes_key_from_recovery_material(
    *,
    private_blob_b64: Optional[str] = None,
    public_blob_b64: Optional[str] = None,
    private_blob_path: Optional[str] = None,
    public_blob_path: Optional[str] = None,
    primary_ctx: str = DEFAULT_PRIMARY_CTX,
    encrypt_key_ctx: str = DEFAULT_ENCRYPT_KEY_CTX,
    store_name: str = DEFAULT_STORE_NAME,
    base_url: str = DEFAULT_API_URL
) -> Dict[str, Any]:
    """
    Use AES recovery blobs/files to rebuild the AES key and unlock the encrypted store.
    """
    if not (private_blob_b64 or private_blob_path):
        return {
            "success": False,
            "error": "A private AES recovery blob (base64 or filepath) is required to restore the key."
        }

    restore_result = restore_aes_key_from_recovery(
        parent_ctx=primary_ctx,
        encrypt_key_ctx=encrypt_key_ctx,
        private_blob_b64=private_blob_b64,
        public_blob_b64=public_blob_b64,
        private_blob_path=private_blob_path,
        public_blob_path=public_blob_path,
        base_url=base_url,
        ensure_primary=True
    )

    if not restore_result.get("success"):
        return {
            "success": False,
            "error": f"Failed to restore AES key from recovery material: {restore_result.get('error', 'Unknown error')}"
        }

    ensure_result = _ensure_tpm_setup(
        primary_ctx=primary_ctx,
        encrypt_key_ctx=encrypt_key_ctx,
        store_name=store_name,
        base_url=base_url
    )

    if not ensure_result.get("success"):
        ensure_result["recovery_result"] = restore_result
        return ensure_result

    return {
        "success": True,
        "message": "AES key restored from recovery material and encrypted store is accessible.",
        "tpm_available": ensure_result.get("tpm_available", False)
    }


def write_key_to_tpm(
    key: str,
    secret: str,
    primary_ctx: str = DEFAULT_PRIMARY_CTX,
    encrypt_key_ctx: str = DEFAULT_ENCRYPT_KEY_CTX,
    store_name: str = DEFAULT_STORE_NAME,
    base_url: str = DEFAULT_API_URL
) -> Dict[str, Any]:
    """
    Write a key-secret pair to the TPM2 encrypted file store using AES encryption.
    
    This function stores a key (identifier) and secret (pubkey or privkey) in the
    AES-encrypted file store. It automatically handles initialization of the TPM2
    components if they don't exist. Uses HTTP requests to communicate with the REST API.
    AES encryption doesn't have size limitations like RSA, so large secrets can be stored.
    
    Args:
        key: The key identifier (e.g., "node_pubkey", "wallet_privkey")
        secret: The secret value to store (pubkey or privkey) - can be any size
        primary_ctx: Path to primary key context file (default: anylog_primary.ctx)
        encrypt_key_ctx: Path to AES encryption key context file (default: anylog_encrypt_key_aes.ctx)
        store_name: Name of the encrypted file store (default: anylog_key_store.json)
        base_url: Base URL for the TPM2 REST API (default: http://localhost:8000)

    Returns:
        Dictionary with success status and any errors or messages.

    Notes:
        If `_ensure_tpm_setup` indicates the AES store exists but the AES key is not loaded,
        this function returns that same message along with `needs_recovery=True`.
    """
    try:
        # Ensure TPM setup is complete
        setup_result = _ensure_tpm_setup(
            primary_ctx=primary_ctx,
            encrypt_key_ctx=encrypt_key_ctx,
            store_name=store_name,
            base_url=base_url,
        )
        
        if not setup_result.get("success"):
            if setup_result.get("needs_recovery"):
                return {
                    "success": False,
                    "error": setup_result.get("error"),
                    "needs_recovery": True,
                    "store_name": setup_result.get("store_name"),
                    "tpm_available": setup_result.get("tpm_available", False)
                }
            return setup_result
        
        # Flush context before storing
        _flush_context(base_url=base_url)
        
        # Store the key-value pair via REST API using AES encryption
        result = _make_request("POST", "/tpm2/file-store-aes/store",
                              json_data={
                                  "context_file": encrypt_key_ctx,
                                  "store_name": store_name,
                                  "key": key,
                                  "value": secret
                              },
                              base_url=base_url)
        
        # Flush context after storing
        _flush_context(base_url=base_url)
        
        if result.get("success"):
            payload = {
                "success": True,
                "message": f"Key '{key}' stored successfully",
                "key": key
            }
            payload.update({k: v for k, v in setup_result.items() if k not in {"success", "error"}})
            return payload
        else:
            return {
                "success": False,
                "error": f"Failed to store key: {result.get('error', 'Unknown error')}"
            }
            
    except Exception as e:
        _flush_context(base_url=base_url)  # Try to flush on error
        return {
            "success": False,
            "error": f"Error storing key to TPM: {str(e)}"
        }


def read_key_from_tpm(
    key: str,
    primary_ctx: str = DEFAULT_PRIMARY_CTX,
    encrypt_key_ctx: str = DEFAULT_ENCRYPT_KEY_CTX,
    store_name: str = DEFAULT_STORE_NAME,
    base_url: str = DEFAULT_API_URL
) -> Dict[str, Any]:
    """
    Read a key-secret pair from the TPM2 encrypted file store using AES decryption.
    
    This function retrieves a secret (pubkey or privkey) associated with a key
    identifier from the AES-encrypted file store. It automatically handles initialization
    of the TPM2 components if they don't exist. Uses HTTP requests to communicate with the REST API.
    
    Args:
        key: The key identifier to retrieve (e.g., "node_pubkey", "wallet_privkey")
        primary_ctx: Path to primary key context file (default: anylog_primary.ctx)
        encrypt_key_ctx: Path to AES encryption key context file (default: anylog_encrypt_key_aes.ctx)
        store_name: Name of the encrypted file store (default: anylog_key_store.json)
        base_url: Base URL for the TPM2 REST API (default: http://localhost:8000)

    Returns:
        Dictionary with success status, the retrieved value (if successful), and any errors.
        When the encrypted store exists but the AES key is not loaded, this function
        now returns `needs_recovery=True` and no longer attempts to handle the recovery blobs itself.
    """
    try:
        # Ensure TPM setup is complete
        setup_result = _ensure_tpm_setup(
            primary_ctx=primary_ctx,
            encrypt_key_ctx=encrypt_key_ctx,
            store_name=store_name,
            base_url=base_url,
        )
        
        if not setup_result.get("success"):
            if setup_result.get("needs_recovery"):
                return {
                    "success": False,
                    "error": setup_result.get("error"),
                    "needs_recovery": True,
                    "store_name": setup_result.get("store_name"),
                    "tpm_available": setup_result.get("tpm_available", False)
                }
            return setup_result
        
        # Flush context before retrieving
        _flush_context(base_url=base_url)
        
        # Retrieve the key-value pair via REST API using AES decryption
        result = _make_request("POST", "/tpm2/file-store-aes/retrieve",
                              json_data={
                                  "context_file": encrypt_key_ctx,
                                  "store_name": store_name,
                                  "key": key
                              },
                              base_url=base_url)
        
        # Flush context after retrieving
        _flush_context(base_url=base_url)
        
        if result.get("success"):
            payload = {
                "success": True,
                "key": key,
                "value": result.get("value"),
                "message": f"Key '{key}' retrieved successfully"
            }
            payload.update({k: v for k, v in setup_result.items() if k not in {"success", "error"}})
            return payload
        else:
            # Provide a more helpful error message
            error_msg = result.get("error", "Unknown error")
            available_keys = result.get("available_keys", [])
            
            # Check if the error indicates the key doesn't exist
            if "not found" in error_msg.lower() or "not found in file store" in error_msg.lower():
                if available_keys:
                    return {
                        "success": False,
                        "error": f"Key '{key}' not found in file store. Available keys: {', '.join(available_keys)}",
                        "available_keys": available_keys
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Key '{key}' not found in file store. The file store is empty - you need to write the key first using write_key_to_tpm().",
                        "available_keys": available_keys
                    }
            
            return {
                "success": False,
                "error": error_msg,
                "available_keys": available_keys
            }
            
    except Exception as e:
        _flush_context(base_url=base_url)  # Try to flush on error
        return {
            "success": False,
            "error": f"Error reading key from TPM: {str(e)}"
        }


# Example usage
if __name__ == "__main__":
    # Recovery flow overview:
    # 1. When _ensure_tpm_setup() creates an AES key for the first time, we capture TPM blobs
    #    (base64) in the API response and print them with _emit_aes_recovery_material().
    # 2. Operators should call save_recovery_material_to_directory() to persist those blobs
    #    to disk (or other secret storage) as .priv/.pub files.
    # 3. On a fresh container or after TPM state loss, use restore_aes_key_from_recovery()
    #    with either the saved base64 strings or blob files to rebuild the AES context.
    # 4. Higher-level helpers set_custom_aes_key_from_files()/set_custom_aes_key_from_base64()
    #    wrap that restore call and optionally recreate the encrypted filestore in one shot.
    # 5. Once the AES key is restored, read_key_from_tpm()/write_key_to_tpm() resume working
    #    against the original encrypted data.
    #
    # IMPORTANT: The TPM state (tpm_state directory) MUST be persisted for recovery to work.
    # The recovery blobs are encrypted under a specific primary key. If the TPM state is lost,
    # the primary key changes and recovery blobs cannot be loaded.
    #
    # Minimal setup in shared_dir:
    # - anylog_key_store.json (encrypted file store) - REQUIRED
    # - tpm_state/ (TPM state including primary key) - REQUIRED for recovery to work
    # Recovery blobs should be stored securely off-container and provided when needed.


    # Delete everything in shared_dir/tpm_state
    tpm_state_dir = SHARED_DIR / "tpm_state"
    if tpm_state_dir.exists() and tpm_state_dir.is_dir():
        for item in tpm_state_dir.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                elif item.is_dir():
                    # Remove subdirectories and all contents
                    import shutil
                    shutil.rmtree(item)
            except Exception as e:
                print(f"Failed to remove {item}: {e}")
        print(f"All contents of {tpm_state_dir} have been deleted.")
    else:
        print(f"{tpm_state_dir} does not exist or is not a directory.")



    # Delete everything in shared_dir that is not a directory
    for item in SHARED_DIR.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                item.unlink()
        except Exception as e:
            print(f"Failed to remove {item}: {e}")
    print(f"All non-directory files in {SHARED_DIR} have been deleted.")



    import subprocess
    import time


    # step 0: restart docker compose
    print("\nRestarting Docker Compose stack...")

    try:
        subprocess.run(["docker-compose", "down"], check=True)
        print("Docker Compose stack stopped. Waiting 5 seconds before starting up...")
        time.sleep(5)
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        time.sleep(5)
        print("Docker Compose stack restarted successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error restarting Docker Compose stack: {e}")


    print("\nReading pubkey from TPM...")
    result = read_key_from_tpm("pubkey")
    print(f"Read result: {result}")


    # 1. write to tpm
    print("Writing pubkey to TPM...")
    result = write_key_to_tpm("pubkey", """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDZqVfeViSx34IzP5XL3bxA08vD
hgrQu3JStfQl2rjETY3O5hmUs/A2ZKKRZgBQvTO70cIYaS5rQoz0Be96iOdEwOmb
Rt+ky3Zh4iQBTPRWWK1x7F/r1K8PBSTX+kKdcawSTTTtWUyC3O8U1GxzzukonZQx
2EriSsxeoR+3ynW3TwIDAQAB
-----END PUBLIC KEY-----""")
    print(f"Write result: {result}")

    recovery_material = result.get("recovery_material")
    if recovery_material:
        public_blob = recovery_material.get("public_blob_b64")
        private_blob = recovery_material.get("private_blob_b64")
        print(f"Public blob: {public_blob}")
        print(f"Private blob: {private_blob}")
    else:
        print("No recovery material found")

    # Step 2: Read the pubkey back

    print("\nReading pubkey from TPM...")
    result = read_key_from_tpm("pubkey")
    print(f"Read result: {result}")



    # step 3. restart docker compose

    print("\nRestarting Docker Compose stack...")

    try:
        subprocess.run(["docker-compose", "down"], check=True)
        print("Docker Compose stack stopped. Waiting 5 seconds before starting up...")
        time.sleep(5)
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        time.sleep(5)
        print("Docker Compose stack restarted successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error restarting Docker Compose stack: {e}")



    # step 4. recovery helper
    print("\nRestoring AES key via recovery material...")
    recovery_result = recover_aes_key_from_recovery_material(
        private_blob_b64="AJ4AIHjc5VShq1Cnn1SrwYmzwd2IgNbvcdsiwDQLIhm+T/+oABAbRsSnSHx2I6+WuHV665Uk3s3im72ND6xTNUfyIU7maCuW+NfWsr4Q7Zk4b/5O5i69dhpQnSQof8i/LyDlAcfwQEj/HD9j+295VyuAU2OgY/SCP8bzwQyDU9K5iOW/KnlCWbS/krCmiQjLJIYiU9V6WHqEa9n8bGMEAA==",
        public_blob_b64="ADIAJQALAAYAcgAAAAYBAAAQACCL+sH3DAWYbzwM2frtWLo7qeo1pYZiG7MDiheykg1u0Q=="
    )
    print(f"Recovery result: {recovery_result}")


    # step 5. test read key from tpm

    print("\nReading pubkey again after recovery attempt...")
    result = read_key_from_tpm("pubkey")
    print(f"Read result: {result}")

    