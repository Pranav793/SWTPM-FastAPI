#!/usr/bin/env python3
"""
AnyLog TPM2 Integration Utilities

This module provides functions to integrate TPM2 encrypted file store
with AnyLog nodes for storing and retrieving keys (pubkeys/privkeys).
Uses HTTP requests to communicate with the TPM2 REST API.
"""

import requests
import subprocess
import time
from typing import Dict, Any, Optional

# Default API base URL
DEFAULT_API_URL = "http://127.0.0.1:8000"

# Default file names for TPM2 keys and file store
DEFAULT_PRIMARY_CTX = "anylog_primary.ctx"
# For AES keys, the API creates .pub and .priv files internally, then loads them into the .ctx file
# Users only need to reference the context file (.ctx) - the API handles the rest automatically
DEFAULT_ENCRYPT_KEY_CTX = "anylog_encrypt_key_aes.ctx"
DEFAULT_STORE_NAME = "anylog_key_store.json"


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


def _make_request(method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None,
                  base_url: str = DEFAULT_API_URL) -> Dict[str, Any]:
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
    """
    try:
        # First, check if the API is reachable before attempting any operations
        connectivity_check = _check_api_connectivity(base_url=base_url)
        if not connectivity_check.get("success"):
            return {
                "success": False,
                "error": connectivity_check.get("error", "API connectivity check failed")
            }

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
            return {"success": True}

        # If we get here, something is missing. Let's set up step by step.

        # Step 1: Create primary key (RSA key used as parent for AES key)
        _flush_context(base_url=base_url)
        _make_request("POST", "/tpm2/create-primary",
                      json_data={
                          "hierarchy": "o",
                          "context_file": primary_ctx
                      },
                      base_url=base_url)
        # Continue even if it fails - it might already exist

        # Step 2: Create AES-256 encryption key under the primary key
        # The API will automatically create the key with tpm2_create and load it
        _flush_context(base_url=base_url)
        result = _make_request("POST", "/tpm2/create-key",
                               json_data={
                                   "parent_context": primary_ctx,  # Use primary key as parent
                                   "key_type": "aes256",
                                   "public_file": encrypt_key_ctx,  # Will create .pub and .priv, then load into .ctx
                               },
                               base_url=base_url)

        # Check if the key was created and loaded successfully
        if not result.get("success"):
            error_msg = result.get("error", "").lower()
            # If key creation failed for reasons other than "already exists", report it
            if "already exists" not in error_msg and "file exists" not in error_msg:
                # Check if the context_file was created (key is loaded and ready)
                if result.get("context_file") is None:
                    return {
                        "success": False,
                        "error": f"Failed to create AES key: {result.get('error', 'Unknown error')}"
                    }
        else:
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
                            "error": f"AES key created but failed to load: {load_result.get('error', 'Unknown error')}"
                        }

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

        return {"success": True}

    except Exception as e:
        return {
            "success": False,
            "error": f"Error during TPM setup: {str(e)}"
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
        Dictionary with success status and any errors or messages

    Example:
        >>> result = write_key_to_tpm("node_pubkey", "0x1234abcd...")
        >>> if result["success"]:
        ...     print("Key stored successfully")
    """
    try:
        # Ensure TPM setup is complete
        setup_result = _ensure_tpm_setup(
            primary_ctx=primary_ctx,
            encrypt_key_ctx=encrypt_key_ctx,
            store_name=store_name,
            base_url=base_url
        )

        if not setup_result.get("success"):
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
            return {
                "success": True,
                "message": f"Key '{key}' stored successfully",
                "key": key
            }
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
        Dictionary with success status, the retrieved value (if successful), and any errors

    Example:
        >>> result = read_key_from_tpm("node_pubkey")
        >>> if result["success"]:
        ...     pubkey = result["value"]
        ...     print(f"Retrieved pubkey: {pubkey}")
    """
    try:
        # Ensure TPM setup is complete
        setup_result = _ensure_tpm_setup(
            primary_ctx=primary_ctx,
            encrypt_key_ctx=encrypt_key_ctx,
            store_name=store_name,
            base_url=base_url
        )

        if not setup_result.get("success"):
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
            return {
                "success": True,
                "key": key,
                "value": result.get("value"),
                "message": f"Key '{key}' retrieved successfully"
            }
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

#
# # Example usage
# if __name__ == "__main__":
#     # Step 1: Set up Docker container (run this before using TPM functions)
#     print("Setting up Docker container...")
#     docker_result = setup_docker_container()
#     if not docker_result.get("success"):
#         print(f"Failed to set up Docker container: {docker_result.get('error')}")
#         exit(1)
#     print(f"Docker setup: {docker_result.get('message')}\n")
#
#     # Step 2: Write a pubkey
#     print("Writing pubkey to TPM...")
#     result = write_key_to_tpm("pubkey", """-----BEGIN PUBLIC KEY-----
# MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDZqVfeViSx34IzP5XL3bxA08vD
# hgrQu3JStfQl2rjETY3O5hmUs/A2ZKKRZgBQvTO70cIYaS5rQoz0Be96iOdEwOmb
# Rt+ky3Zh4iQBTPRWWK1x7F/r1K8PBSTX+kKdcawSTTTtWUyC3O8U1GxzzukonZQx
# 2EriSsxeoR+3ynW3TwIDAQAB
# -----END PUBLIC KEY-----""")
#     print(f"Write result: {result}")
#
#     # Step 3: Read the pubkey back
#     print("\nReading pubkey from TPM...")
#     result = read_key_from_tpm("pubkey")
#     print(f"Read result: {result}")
#
#     # if result.get("success"):
#     #     print(f"Retrieved value: {result.get('value')}")
#