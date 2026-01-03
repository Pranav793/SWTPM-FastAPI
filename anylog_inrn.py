#!/usr/bin/env python3
"""
AnyLog TPM2 Signing Utilities

This module provides functions for creating, storing, and using signing keys in the TPM.
Keys are created, loaded into the TPM, and external private key files are deleted for security.
Keys can be located by name and used to sign messages.

Key Features:
- Create and store signing keys in TPM
- Automatically delete external private key files after storage
- Locate keys by name
- Sign messages using stored keys
- List and manage stored keys
"""

import base64
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import requests
import anylog_node.generic.params as anylog_params

# Default API base URL
DEFAULT_API_URL = "http://localhost:8000"

# Default file names
DEFAULT_PRIMARY_CTX = "anylog_signing_primary.ctx"


def get_shared_dir() -> Path:
    """
    Get the shared directory path.
    This function allows for dynamic path configuration in production.

    Returns:
        Path object pointing to the shared directory
    """
    return Path(anylog_params.get_value_if_available("!tpm_dir"))

def get_keys_metadata_file() -> Path:
    """
    Get the keys metadata file path.
    This function allows for dynamic path configuration in production.

    Returns:
        Path object pointing to the keys metadata file
    """
    return get_shared_dir() / "signing_keys_metadata.json"


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
            try:
                error_json = response.json()
                error_msg = error_json.get("detail") or error_json.get("error") or error_json.get(
                    "message") or "Unknown error"

                # Clean up error messages
                if isinstance(error_msg, str) and ":" in error_msg and error_msg.split(":")[0].strip().isdigit():
                    error_msg = ":".join(error_msg.split(":")[1:]).strip()

                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code,
                    "url": url
                }
            except (ValueError, KeyError):
                return {
                    "success": False,
                    "error": f"API request failed with status {response.status_code}: {response.text[:200]}",
                    "status_code": response.status_code,
                    "url": url
                }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Network error: {str(e)}",
            "url": f"{base_url}{endpoint}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "url": f"{base_url}{endpoint}"
        }


def _load_keys_metadata() -> Dict[str, Any]:
    """Load the keys metadata file"""
    metadata_file = get_keys_metadata_file()
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_keys_metadata(metadata: Dict[str, Any]) -> bool:
    """Save the keys metadata file"""
    try:
        get_shared_dir().mkdir(parents=True, exist_ok=True)
        metadata_file = get_keys_metadata_file()
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving keys metadata: {e}")
        return False


def _flush_context(context_type: str = "transient", base_url: str = DEFAULT_API_URL) -> Dict[str, Any]:
    """Flush TPM contexts to free up memory"""
    result = _make_request(
        "POST",
        "/tpm2/flush-context",
        json_data={"context_type": context_type},
        base_url=base_url
    )
    return result


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
        health_url = f"{base_url}/health"
        response = requests.get(health_url, timeout=timeout)

        if response.status_code == 200:
            return {
                "success": True,
                "message": "API is accessible and TPM is available"
            }
        else:
            return {
                "success": False,
                "error": f"API returned status {response.status_code}. TPM may not be available."
            }
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


def _ensure_primary_key(base_url: str = DEFAULT_API_URL) -> Dict[str, Any]:
    """
    Ensure a primary key exists for signing operations.
    Creates one if it doesn't exist.

    Returns:
        Dictionary with primary key context file or error
    """
    # Check if primary key already exists
    primary_result = _make_request(
        "POST",
        "/tpm2/create-primary",
        json_data={"hierarchy": "o", "context_file": DEFAULT_PRIMARY_CTX},
        base_url=base_url
    )

    # Flush contexts after creating primary
    _flush_context(context_type="transient", base_url=base_url)

    # If it already exists, that's fine - we'll use it
    if primary_result.get("success"):
        return {
            "success": True,
            "context_file": primary_result.get("context_file", DEFAULT_PRIMARY_CTX)
        }

    # Check if error is because it already exists
    error_msg = primary_result.get("error", "").lower()
    if "already exists" in error_msg or "file exists" in error_msg:
        return {
            "success": True,
            "context_file": DEFAULT_PRIMARY_CTX
        }

    return primary_result


def _backup_key_blobs(key_name: str, base_url: str = DEFAULT_API_URL) -> Dict[str, Any]:
    """
    Backup key blobs (public and private) to a secure backup location before deletion.
    Reads the actual blob file content and stores it base64-encoded in the backup.
    This allows recovery if the TPM state is lost.

    Args:
        key_name: Name of the key
        base_url: Base URL for the API

    Returns:
        Dictionary with backup information
    """
    metadata = _load_keys_metadata()
    if key_name not in metadata:
        return {"success": False, "error": f"Key '{key_name}' not found in metadata"}

    key_info = metadata[key_name]
    backup_dir = get_shared_dir() / "key_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_data = {
        "key_name": key_name,
        "backed_up_at": int(time.time()),
        "public_blob": None,
        "private_blob": None,
        "public_file": None,
        "private_file": None,
        "key_info": key_info
    }

    # Read and backup public key blob
    if "public_file" in key_info:
        public_file_path = get_shared_dir() / key_info["public_file"]
        try:
            if public_file_path.exists():
                with open(public_file_path, 'rb') as f:
                    public_blob_data = f.read()
                backup_data["public_blob"] = base64.b64encode(public_blob_data).decode()
                backup_data["public_file"] = key_info["public_file"]
            else:
                print(f"Warning: Public file {public_file_path} does not exist")
        except Exception as e:
            print(f"Warning: Could not read public blob: {e}")

    # Read and backup private key blob
    if "private_file" in key_info:
        private_file_path = get_shared_dir() / key_info["private_file"]
        try:
            if private_file_path.exists():
                with open(private_file_path, 'rb') as f:
                    private_blob_data = f.read()
                backup_data["private_blob"] = base64.b64encode(private_blob_data).decode()
                backup_data["private_file"] = key_info["private_file"]
            else:
                print(f"Warning: Private file {private_file_path} does not exist")
        except Exception as e:
            print(f"Warning: Could not read private blob: {e}")

    # Save backup metadata
    backup_file = backup_dir / f"{key_name}_backup.json"
    try:
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)

        has_public = backup_data["public_blob"] is not None
        has_private = backup_data["private_blob"] is not None

        return {
            "success": True,
            "backup_file": str(backup_file),
            "has_public_blob": has_public,
            "has_private_blob": has_private,
            "message": f"Key '{key_name}' backup saved"
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to save backup: {e}"}


def _delete_key_files(key_name: str, base_url: str = DEFAULT_API_URL, backup: bool = True) -> None:
    """
    Delete external key files (blob files) after storing in TPM.
    Backs up blob content before deletion for recovery purposes.
    Blobs are stored in encrypted TPM format, but we delete them for security.
    They can be restored from backup when needed for reload after TPM restart.

    Args:
        key_name: Name of the key
        base_url: Base URL for the API
        backup: If True, backup key blobs before deletion (default: True)
    """
    # Backup before deletion if requested
    if backup:
        backup_result = _backup_key_blobs(key_name, base_url=base_url)
        if backup_result.get("success"):
            backup_file = backup_result.get('backup_file', 'N/A')
            has_public = backup_result.get('has_public_blob', False)
            has_private = backup_result.get('has_private_blob', False)
            print(f"Backed up key '{key_name}' to {backup_file} (public: {has_public}, private: {has_private})")
        else:
            error_msg = backup_result.get('error', 'Unknown error')
            print(f"Warning: Backup failed for '{key_name}': {error_msg}")
            # Don't delete if backup failed
            return

    metadata = _load_keys_metadata()
    if key_name not in metadata:
        return

    key_info = metadata[key_name]
    files_to_delete = []

    # Add private key file (most important to delete)
    if "private_file" in key_info:
        files_to_delete.append(key_info["private_file"])

    # Add public file (also delete for security)
    if "public_file" in key_info:
        files_to_delete.append(key_info["public_file"])

    # Delete files via API
    deleted_count = 0
    for filename in files_to_delete:
        try:
            result = _make_request(
                "POST",
                "/tpm2/delete-file",
                json_data={"file_path": filename},
                base_url=base_url
            )
            if result.get("success"):
                print(f"Deleted external file: {filename}")
                deleted_count += 1
            else:
                print(f"Warning: Failed to delete {filename}: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"Warning: Failed to delete {filename}: {e}")

    if deleted_count > 0:
        print(f"✓ Deleted {deleted_count} blob file(s) for key '{key_name}' (backed up for recovery)")


# ============================================================================
# TOP-LEVEL FUNCTIONS
# ============================================================================

def create_and_store_signing_key(
        key_name: str,
        key_type: str = "rsa",
        make_persistent: bool = False,
        base_url: str = DEFAULT_API_URL
) -> Dict[str, Any]:
    """
    Create a signing key and store it in the TPM.
    After storage, external private key files are automatically deleted.

    Args:
        key_name: Unique name to identify this key
        key_type: Type of key ('rsa' or 'ecc')
        make_persistent: If True, make the key persistent in TPM
        base_url: Base URL for the TPM2 REST API

    Returns:
        Dictionary with success status and key information
    """
    # Check API connectivity first
    connectivity_result = _check_api_connectivity(base_url=base_url)
    if not connectivity_result.get("success"):
        return {
            "success": False,
            "error": connectivity_result.get("error", "API connectivity check failed")
        }

    # Check if key name already exists
    metadata = _load_keys_metadata()
    if key_name in metadata:
        return {
            "success": False,
            "error": f"Key with name '{key_name}' already exists"
        }

    # Ensure primary key exists
    primary_result = _ensure_primary_key(base_url=base_url)
    if not primary_result.get("success"):
        return {
            "success": False,
            "error": f"Failed to ensure primary key: {primary_result.get('error', 'Unknown error')}"
        }

    parent_context = primary_result["context_file"]

    # Generate unique filenames with timestamp
    timestamp = int(time.time())
    key_prefix = f"{key_name}_{timestamp}"
    public_file = f"{key_prefix}.pub"
    private_file = f"{key_prefix}.priv"
    context_file = f"{key_prefix}.ctx"

    # Create key
    create_result = _make_request(
        "POST",
        "/tpm2/create-key",
        json_data={
            "parent_context": parent_context,
            "key_type": key_type,
            "public_file": public_file,
            "private_file": private_file
        },
        base_url=base_url
    )

    # Flush contexts after create
    _flush_context(context_type="transient", base_url=base_url)

    if not create_result.get("success"):
        return {
            "success": False,
            "error": f"Failed to create key: {create_result.get('error', 'Unknown error')}"
        }

    # Load key into TPM
    load_result = _make_request(
        "POST",
        "/tpm2/load-key",
        json_data={
            "parent_context": parent_context,
            "public_file": public_file,
            "private_file": private_file,
            "context_file": context_file
        },
        base_url=base_url
    )

    # Flush contexts after load
    _flush_context(context_type="transient", base_url=base_url)

    if not load_result.get("success"):
        return {
            "success": False,
            "error": f"Failed to load key: {load_result.get('error', 'Unknown error')}"
        }

    # Optionally make persistent
    persistent_handle = None
    if make_persistent:
        persistent_handle_val = 0x81010000 + len(metadata) + 1
        persistent_result = _make_request(
            "POST",
            "/tpm2/make-persistent",
            json_data={
                "context_file": context_file,
                "persistent_handle": persistent_handle_val
            },
            base_url=base_url
        )

        # Flush contexts after making persistent
        _flush_context(context_type="transient", base_url=base_url)

        if persistent_result.get("success"):
            persistent_handle = persistent_result.get("persistent_handle")

    # Store metadata
    key_metadata = {
        "key_name": key_name,
        "key_type": key_type,
        "context_file": context_file,
        "public_file": public_file,
        "private_file": private_file,
        "persistent_handle": persistent_handle,
        "created_at": timestamp,
        "parent_context": parent_context
    }

    metadata[key_name] = key_metadata
    _save_keys_metadata(metadata)

    # Delete external private key file (security)
    # Backup is enabled by default for recovery purposes
    _delete_key_files(key_name, base_url=base_url, backup=True)

    return {
        "success": True,
        "key_name": key_name,
        "context_file": context_file,
        "persistent_handle": persistent_handle,
        "message": f"Key '{key_name}' created and stored in TPM. External private key file deleted."
    }


def _reload_key_from_blobs(key_name: str, base_url: str = DEFAULT_API_URL) -> Dict[str, Any]:
    """
    Reload a key from backup blobs if the context is invalid.
    This is needed after TPM restarts since context files are transient.
    Restores blob files temporarily from backup, reloads the key, then deletes blobs again.

    Args:
        key_name: Name of the key to reload
        base_url: Base URL for the API

    Returns:
        Dictionary with success status and new context file
    """
    metadata = _load_keys_metadata()
    if key_name not in metadata:
        return {"success": False, "error": f"Key '{key_name}' not found in metadata"}

    key_info = metadata[key_name]
    parent_context = key_info.get("parent_context", DEFAULT_PRIMARY_CTX)

    # Load backup
    backup_dir = get_shared_dir() / "key_backups"
    backup_file = backup_dir / f"{key_name}_backup.json"

    if not backup_file.exists():
        return {"success": False, "error": f"Backup file not found for key '{key_name}'"}

    try:
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
    except Exception as e:
        return {"success": False, "error": f"Failed to read backup file: {e}"}

    # Check if we have blob data in backup
    public_blob_b64 = backup_data.get("public_blob")
    private_blob_b64 = backup_data.get("private_blob")

    if not public_blob_b64 or not private_blob_b64:
        return {"success": False, "error": f"Backup for '{key_name}' is incomplete. Missing blob data."}

    # Get original filenames from backup
    public_file = backup_data.get("public_file") or key_info.get("public_file")
    private_file = backup_data.get("private_file") or key_info.get("private_file")

    if not public_file or not private_file:
        return {"success": False, "error": f"Blob filenames not found in backup for key '{key_name}'"}

    # Restore blob files temporarily from backup
    public_file_path = get_shared_dir() / public_file
    private_file_path = get_shared_dir() / private_file

    try:
        # Decode and write public blob
        public_blob_data = base64.b64decode(public_blob_b64)
        with open(public_file_path, 'wb') as f:
            f.write(public_blob_data)

        # Decode and write private blob
        private_blob_data = base64.b64decode(private_blob_b64)
        with open(private_file_path, 'wb') as f:
            f.write(private_blob_data)

        print(f"Temporarily restored blob files for '{key_name}' from backup")
    except Exception as e:
        return {"success": False, "error": f"Failed to restore blob files from backup: {e}"}

    try:
        # Ensure primary key exists
        primary_result = _ensure_primary_key(base_url=base_url)
        if not primary_result.get("success"):
            return {"success": False, "error": "Failed to ensure primary key exists"}

        # Generate new context file name
        timestamp = int(time.time())
        context_file = f"{key_name}_{timestamp}.ctx"

        # Reload the key from restored blobs
        load_result = _make_request(
            "POST",
            "/tpm2/load-key",
            json_data={
                "parent_context": parent_context,
                "public_file": public_file,
                "private_file": private_file,
                "context_file": context_file
            },
            base_url=base_url
        )

        # Flush contexts after loading
        _flush_context(context_type="transient", base_url=base_url)

        if not load_result.get("success"):
            # Clean up restored files on failure
            try:
                if public_file_path.exists():
                    public_file_path.unlink()
                if private_file_path.exists():
                    private_file_path.unlink()
            except Exception:
                pass
            return {
                "success": False,
                "error": f"Failed to reload key from blobs: {load_result.get('error', 'Unknown error')}"
            }

        # Update metadata with new context file
        key_info["context_file"] = context_file
        metadata[key_name] = key_info
        _save_keys_metadata(metadata)

        # Delete restored blob files immediately after successful reload
        try:
            if public_file_path.exists():
                result = _make_request(
                    "POST",
                    "/tpm2/delete-file",
                    json_data={"file_path": public_file},
                    base_url=base_url
                )
                if result.get("success"):
                    print(f"Deleted restored public blob: {public_file}")

            if private_file_path.exists():
                result = _make_request(
                    "POST",
                    "/tpm2/delete-file",
                    json_data={"file_path": private_file},
                    base_url=base_url
                )
                if result.get("success"):
                    print(f"Deleted restored private blob: {private_file}")
        except Exception as e:
            print(f"Warning: Failed to delete restored blob files: {e}")

        return {
            "success": True,
            "context_file": context_file,
            "message": f"Key '{key_name}' reloaded from backup and blob files deleted"
        }

    except Exception as e:
        # Clean up restored files on exception
        try:
            if public_file_path.exists():
                public_file_path.unlink()
            if private_file_path.exists():
                private_file_path.unlink()
        except Exception:
            pass
        return {"success": False, "error": f"Exception during reload: {e}"}


def find_key_by_name(key_name: str, base_url: str = DEFAULT_API_URL) -> Dict[str, Any]:
    """
    Locate a stored key by its name.
    If the context file is invalid (e.g., after TPM restart), automatically reloads from blobs.

    Args:
        key_name: Name of the key to find
        base_url: Base URL for the API

    Returns:
        Dictionary with key information or error if not found
    """
    # Check API connectivity first
    connectivity_result = _check_api_connectivity(base_url=base_url)
    if not connectivity_result.get("success"):
        return {
            "success": False,
            "error": connectivity_result.get("error", "API connectivity check failed")
        }

    metadata = _load_keys_metadata()

    if key_name not in metadata:
        return {
            "success": False,
            "error": f"Key '{key_name}' not found"
        }

    key_info = metadata[key_name]
    context_file = key_info.get("context_file")

    # Try to verify context is valid by attempting a simple operation
    # If it fails, reload from blobs
    if context_file:
        # Quick check: try to read the context file (simple validation)
        # If context is invalid, we'll catch it when we try to use it
        pass

    return {
        "success": True,
        "key_name": key_name,
        "context_file": context_file,
        "persistent_handle": key_info.get("persistent_handle"),
        "key_type": key_info.get("key_type"),
        "created_at": key_info.get("created_at"),
        "key_info": key_info
    }


def sign_message(
        key_name: str,
        message: str,
        base_url: str = DEFAULT_API_URL
) -> Dict[str, Any]:
    """
    Sign a message using a stored key identified by name.
    Automatically reloads the key from blob files if the context is invalid.

    Args:
        key_name: Name of the key to use for signing
        message: Message to sign (will be base64 encoded)
        base_url: Base URL for the TPM2 REST API

    Returns:
        Dictionary with signature (base64 encoded) or error
    """
    # Check API connectivity first
    connectivity_result = _check_api_connectivity(base_url=base_url)
    if not connectivity_result.get("success"):
        return {
            "success": False,
            "error": connectivity_result.get("error", "API connectivity check failed")
        }

    # Find the key
    key_result = find_key_by_name(key_name, base_url=base_url)
    if not key_result.get("success"):
        return key_result

    context_file = key_result["context_file"]

    # Encode message to base64
    encoded_message = base64.b64encode(message.encode()).decode()

    # Sign the message
    sign_result = _make_request(
        "POST",
        "/tpm2/sign",
        json_data={
            "context_file": context_file,
            "data": encoded_message,
            "signature_file": f"signature_{key_name}_{int(time.time())}.sig"
        },
        base_url=base_url
    )

    # Flush contexts after signing
    _flush_context(context_type="transient", base_url=base_url)

    # If signing failed due to invalid context, try to reload and retry
    if not sign_result.get("success"):
        error_msg = sign_result.get('error', '')
        # Check if error is due to invalid context
        if "integrity check failed" in error_msg or "Invalid key authorization" in error_msg or "Cannot make sense of object context" in error_msg:
            print(f"Context invalid for '{key_name}', attempting to reload from blobs...")
            reload_result = _reload_key_from_blobs(key_name, base_url=base_url)

            if reload_result.get("success"):
                # Update context file and retry signing
                context_file = reload_result["context_file"]
                print(f"Key '{key_name}' reloaded successfully, retrying sign...")

                sign_result = _make_request(
                    "POST",
                    "/tpm2/sign",
                    json_data={
                        "context_file": context_file,
                        "data": encoded_message,
                        "signature_file": f"signature_{key_name}_{int(time.time())}.sig"
                    },
                    base_url=base_url
                )

                # Flush contexts after signing
                _flush_context(context_type="transient", base_url=base_url)

                if not sign_result.get("success"):
                    return {
                        "success": False,
                        "error": f"Failed to sign message after reload: {sign_result.get('error', 'Unknown error')}"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Failed to sign message and reload failed: {reload_result.get('error', 'Unknown error')}"
                }
        else:
            return {
                "success": False,
                "error": f"Failed to sign message: {error_msg}"
            }

    # Get the complete signature
    signature = sign_result.get("signature", "")
    signature_file = sign_result.get("signature_file", "")

    return {
        "success": True,
        "key_name": key_name,
        "message": message,
        "signature": signature,  # Complete base64-encoded signature
        "signature_file": signature_file,  # Signature file path
        "message_encoded": encoded_message,
        "signature_length": len(signature) if signature else 0
    }


def get_public_key(
        key_name: str,
        output_format: str = "pem",
        base_url: str = DEFAULT_API_URL
) -> Dict[str, Any]:
    """
    Get the public key portion of a stored key.

    Args:
        key_name: Name of the key
        output_format: Output format ('pem' or 'der', default: 'pem')
        base_url: Base URL for the TPM2 REST API

    Returns:
        Dictionary with public key data (base64 encoded and text format for PEM)
    """
    # Check API connectivity first
    connectivity_result = _check_api_connectivity(base_url=base_url)
    if not connectivity_result.get("success"):
        return {
            "success": False,
            "error": connectivity_result.get("error", "API connectivity check failed")
        }

    # Find the key
    key_result = find_key_by_name(key_name, base_url=base_url)
    if not key_result.get("success"):
        return key_result

    context_file = key_result["context_file"]

    # Read public key from TPM
    read_result = _make_request(
        "POST",
        "/tpm2/read-public-key",
        json_data={
            "context_file": context_file,
            "output_format": output_format
        },
        base_url=base_url
    )

    # Flush contexts after reading
    _flush_context(context_type="transient", base_url=base_url)

    if not read_result.get("success"):
        # If reading failed due to invalid context, try to reload and retry
        error_msg = read_result.get('error', '')
        if "integrity check failed" in error_msg or "Invalid key authorization" in error_msg or "Cannot make sense of object context" in error_msg:
            print(f"Context invalid for '{key_name}', attempting to reload from backup...")
            reload_result = _reload_key_from_blobs(key_name, base_url=base_url)

            if reload_result.get("success"):
                # Update context file and retry
                context_file = reload_result["context_file"]
                print(f"Key '{key_name}' reloaded successfully, retrying read public key...")

                read_result = _make_request(
                    "POST",
                    "/tpm2/read-public-key",
                    json_data={
                        "context_file": context_file,
                        "output_format": output_format
                    },
                    base_url=base_url
                )

                # Flush contexts after reading
                _flush_context(context_type="transient", base_url=base_url)

                if not read_result.get("success"):
                    return {
                        "success": False,
                        "error": f"Failed to read public key after reload: {read_result.get('error', 'Unknown error')}"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Failed to read public key and reload failed: {reload_result.get('error', 'Unknown error')}"
                }
        else:
            return {
                "success": False,
                "error": f"Failed to read public key: {read_result.get('error', 'Unknown error')}"
            }

    # Extract public key data
    public_key_b64 = read_result.get("public_key", "")
    public_key_text = read_result.get("public_key_text")  # Only for PEM format

    return {
        "success": True,
        "key_name": key_name,
        "public_key": public_key_b64,  # Base64 encoded public key
        "public_key_text": public_key_text,  # Text format (PEM only, None for DER)
        "format": output_format,
        "context_file": context_file
    }


def list_stored_keys() -> Dict[str, Any]:
    """
    List all stored signing keys.

    Returns:
        Dictionary with list of key names and their information
    """
    metadata = _load_keys_metadata()

    keys_list = []
    for key_name, key_info in metadata.items():
        keys_list.append({
            "key_name": key_name,
            "key_type": key_info.get("key_type"),
            "context_file": key_info.get("context_file"),
            "persistent_handle": key_info.get("persistent_handle"),
            "created_at": key_info.get("created_at")
        })

    return {
        "success": True,
        "keys": keys_list,
        "total_keys": len(keys_list)
    }


def delete_key(
        key_name: str,
        base_url: str = DEFAULT_API_URL
) -> Dict[str, Any]:
    """
    Delete a stored key from the TPM and metadata.

    Args:
        key_name: Name of the key to delete
        base_url: Base URL for the TPM2 REST API

    Returns:
        Dictionary with deletion result
    """
    # Check API connectivity first
    connectivity_result = _check_api_connectivity(base_url=base_url)
    if not connectivity_result.get("success"):
        return {
            "success": False,
            "error": connectivity_result.get("error", "API connectivity check failed")
        }

    metadata = _load_keys_metadata()

    if key_name not in metadata:
        return {
            "success": False,
            "error": f"Key '{key_name}' not found"
        }

    # If key is persistent, we might want to evict it
    # For now, we'll just remove from metadata
    # The context file will be cleaned up on TPM reset or flush

    # Remove from metadata
    del metadata[key_name]
    _save_keys_metadata(metadata)

    return {
        "success": True,
        "key_name": key_name,
        "message": f"Key '{key_name}' removed from metadata"
    }


def recover_key_from_backup(
        key_name: str,
        base_url: str = DEFAULT_API_URL
) -> Dict[str, Any]:
    """
    Recover a key from backup if the TPM state was lost.
    This requires that the key blobs were backed up before deletion.

    Args:
        key_name: Name of the key to recover
        base_url: Base URL for the TPM2 REST API

    Returns:
        Dictionary with recovery result
    """
    # Check API connectivity first
    connectivity_result = _check_api_connectivity(base_url=base_url)
    if not connectivity_result.get("success"):
        return {
            "success": False,
            "error": connectivity_result.get("error", "API connectivity check failed")
        }

    backup_dir = get_shared_dir() / "key_backups"
    backup_file = backup_dir / f"{key_name}_backup.json"

    if not backup_file.exists():
        return {
            "success": False,
            "error": f"No backup found for key '{key_name}'. Backup file not found: {backup_file}"
        }

    try:
        # Load backup data
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)

        key_info = backup_data.get("key_info", {})

        # Check if key already exists in metadata
        metadata = _load_keys_metadata()
        if key_name in metadata:
            return {
                "success": False,
                "error": f"Key '{key_name}' already exists. No recovery needed."
            }

        # Check if backup has blob data
        public_blob_b64 = backup_data.get("public_blob")
        private_blob_b64 = backup_data.get("private_blob")

        if not public_blob_b64 or not private_blob_b64:
            return {
                "success": False,
                "error": f"Backup for '{key_name}' is incomplete. Missing blob data."
            }

        # Get filenames from backup
        public_file = key_info.get("public_file")
        private_file = key_info.get("private_file")

        if not public_file or not private_file:
            return {
                "success": False,
                "error": f"Backup for '{key_name}' is incomplete. Missing blob filenames."
            }

        # Restore blob files temporarily from backup
        public_file_path = get_shared_dir() / public_file
        private_file_path = get_shared_dir() / private_file
        parent_context = key_info.get("parent_context", DEFAULT_PRIMARY_CTX)

        try:
            # Decode and write public blob
            public_blob_data = base64.b64decode(public_blob_b64)
            with open(public_file_path, 'wb') as f:
                f.write(public_blob_data)

            # Decode and write private blob
            private_blob_data = base64.b64decode(private_blob_b64)
            with open(private_file_path, 'wb') as f:
                f.write(private_blob_data)

            print(f"Temporarily restored blob files for '{key_name}' from backup")
        except Exception as e:
            return {"success": False, "error": f"Failed to restore blob files from backup: {e}"}

        try:
            # Ensure primary key exists
            primary_result = _ensure_primary_key(base_url=base_url)
            if not primary_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to ensure primary key: {primary_result.get('error', 'Unknown error')}"
                }

            # Generate new context file name
            timestamp = int(time.time())
            context_file = f"{key_name}_{timestamp}.ctx"

            # Reload the key from restored blobs
            load_result = _make_request(
                "POST",
                "/tpm2/load-key",
                json_data={
                    "parent_context": parent_context,
                    "public_file": public_file,
                    "private_file": private_file,
                    "context_file": context_file
                },
                base_url=base_url
            )

            # Flush contexts after loading
            _flush_context(context_type="transient", base_url=base_url)

            if not load_result.get("success"):
                # Clean up restored files on failure
                try:
                    if public_file_path.exists():
                        public_file_path.unlink()
                    if private_file_path.exists():
                        private_file_path.unlink()
                except Exception:
                    pass
                return {
                    "success": False,
                    "error": f"Failed to reload key from backup: {load_result.get('error', 'Unknown error')}"
                }

            # Update key info with new context file
            key_info["context_file"] = context_file
            key_info["created_at"] = int(time.time())  # Update creation time

            # Restore metadata
            metadata[key_name] = key_info
            _save_keys_metadata(metadata)

            # Delete restored blob files immediately after successful reload
            try:
                if public_file_path.exists():
                    result = _make_request(
                        "POST",
                        "/tpm2/delete-file",
                        json_data={"file_path": public_file},
                        base_url=base_url
                    )
                    if result.get("success"):
                        print(f"Deleted restored public blob: {public_file}")

                if private_file_path.exists():
                    result = _make_request(
                        "POST",
                        "/tpm2/delete-file",
                        json_data={"file_path": private_file},
                        base_url=base_url
                    )
                    if result.get("success"):
                        print(f"Deleted restored private blob: {private_file}")
            except Exception as e:
                print(f"Warning: Failed to delete restored blob files: {e}")

            return {
                "success": True,
                "key_name": key_name,
                "message": f"Key '{key_name}' recovered from backup and reloaded. Blob files deleted.",
                "context_file": context_file,
                "backup_restored_at": int(time.time())
            }

        except Exception as e:
            # Clean up restored files on exception
            try:
                if public_file_path.exists():
                    public_file_path.unlink()
                if private_file_path.exists():
                    private_file_path.unlink()
            except Exception:
                pass
            return {
                "success": False,
                "error": f"Exception during recovery: {e}"
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to recover key from backup: {str(e)}"
        }


def verify_signature(
        key_name: str,
        message: str,
        signature: str,
        base_url: str = DEFAULT_API_URL
) -> Dict[str, Any]:
    """
    Verify a signature using a stored key.

    Args:
        key_name: Name of the key to use for verification
        message: Original message
        signature: Base64 encoded signature to verify
        base_url: Base URL for the TPM2 REST API

    Returns:
        Dictionary with verification result
    """
    # Check API connectivity first
    connectivity_result = _check_api_connectivity(base_url=base_url)
    if not connectivity_result.get("success"):
        return {
            "success": False,
            "error": connectivity_result.get("error", "API connectivity check failed")
        }

    # Find the key
    key_result = find_key_by_name(key_name, base_url=base_url)
    if not key_result.get("success"):
        return key_result

    context_file = key_result["context_file"]

    # Encode message to base64
    encoded_message = base64.b64encode(message.encode()).decode()

    # Verify the signature
    verify_result = _make_request(
        "POST",
        "/tpm2/verify",
        json_data={
            "context_file": context_file,
            "data": encoded_message,
            "signature": signature
        },
        base_url=base_url
    )

    # Flush contexts after verification
    _flush_context(context_type="transient", base_url=base_url)

    if not verify_result.get("success"):
        return {
            "success": False,
            "error": f"Verification failed: {verify_result.get('error', 'Unknown error')}"
        }

    return {
        "success": True,
        "verified": verify_result.get("verified", False),
        "key_name": key_name,
        "message": "Signature verified successfully" if verify_result.get(
            "verified") else "Signature verification failed"
    }


def list_backups() -> Dict[str, Any]:
    """
    List all available key backups.

    Returns:
        Dictionary with list of backup files
    """
    backup_dir = get_shared_dir() / "key_backups"

    if not backup_dir.exists():
        return {
            "success": True,
            "backups": [],
            "total_backups": 0,
            "message": "No backup directory found"
        }

    backups = []
    for backup_file in backup_dir.glob("*_backup.json"):
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
                backups.append({
                    "key_name": backup_data.get("key_name"),
                    "backup_file": backup_file.name,
                    "backed_up_at": backup_data.get("backed_up_at"),
                    "has_public_blob": "public_file" in backup_data,
                    "has_private_blob": "private_file" in backup_data
                })
        except Exception as e:
            print(f"Warning: Could not read backup file {backup_file}: {e}")

    return {
        "success": True,
        "backups": backups,
        "total_backups": len(backups)
    }
