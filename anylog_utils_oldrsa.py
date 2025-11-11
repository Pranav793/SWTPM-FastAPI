# #!/usr/bin/env python3
# """
# AnyLog TPM2 Integration Utilities
#
# This module provides functions to integrate TPM2 encrypted file store
# with AnyLog nodes for storing and retrieving keys (pubkeys/privkeys).
# Uses HTTP requests to communicate with the TPM2 REST API.
# """
#
# import requests
# from typing import Dict, Any, Optional
#
# # Default API base URL
# DEFAULT_API_URL = "http://localhost:8000"
#
# # Default file names for TPM2 keys and file store
# DEFAULT_PRIMARY_CTX = "anylog_primary.ctx"
# DEFAULT_ENCRYPT_KEY_PUB = "anylog_encrypt_key.pub"
# DEFAULT_ENCRYPT_KEY_PRIV = "anylog_encrypt_key.priv"
# DEFAULT_ENCRYPT_KEY_CTX = "anylog_encrypt_key.ctx"
# DEFAULT_STORE_NAME = "anylog_key_store.json"
#
#
# def _make_request(method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None,
#                   base_url: str = DEFAULT_API_URL) -> Dict[str, Any]:
#     """
#     Make an HTTP request to the TPM2 REST API
#
#     Args:
#         method: HTTP method (e.g., "POST", "GET")
#         endpoint: API endpoint path (e.g., "/tpm2/create-primary")
#         json_data: Optional JSON data for the request
#         base_url: Base URL for the API
#
#     Returns:
#         Dictionary with response data or error information
#     """
#     try:
#         url = f"{base_url}{endpoint}"
#         response = requests.request(method, url, json=json_data, timeout=30)
#
#         if response.status_code == 200:
#             return response.json()
#         else:
#             # Try to parse the error response
#             try:
#                 error_json = response.json()
#                 # Extract error message
#                 error_msg = error_json.get("detail", error_json.get("error", "Unknown error"))
#                 # Clean up error messages that might have status code prefixes like "400: ..."
#                 if isinstance(error_msg, str) and ":" in error_msg and error_msg.split(":")[0].strip().isdigit():
#                     error_msg = ":".join(error_msg.split(":")[1:]).strip()
#
#                 # If the error response has useful fields, preserve them
#                 error_result = {
#                     "success": False,
#                     "error": error_msg
#                 }
#                 # Preserve additional fields like available_keys if present
#                 if "available_keys" in error_json:
#                     error_result["available_keys"] = error_json["available_keys"]
#                 return error_result
#             except (ValueError, KeyError):
#                 # If we can't parse JSON, use the text
#                 return {
#                     "success": False,
#                     "error": f"API request failed with status {response.status_code}: {response.text}"
#                 }
#     except requests.exceptions.RequestException as e:
#         return {
#             "success": False,
#             "error": f"Network error: {str(e)}"
#         }
#     except Exception as e:
#         return {
#             "success": False,
#             "error": f"Unexpected error: {str(e)}"
#         }
#
#
# def _flush_context(base_url: str = DEFAULT_API_URL) -> None:
#     """Flush TPM contexts to avoid memory issues"""
#     try:
#         result = _make_request("POST", "/tpm2/flush-context",
#                                json_data={"context_type": "transient"},
#                                base_url=base_url)
#         if not result.get("success"):
#             # Log warning but don't fail - flushing is best effort
#             print(f"Warning: Failed to flush TPM context: {result.get('error', 'Unknown error')}")
#     except Exception as e:
#         print(f"Warning: Failed to flush TPM context: {e}")
#
#
# def _ensure_tpm_setup(
#         primary_ctx: str = DEFAULT_PRIMARY_CTX,
#         encrypt_key_pub: str = DEFAULT_ENCRYPT_KEY_PUB,
#         encrypt_key_priv: str = DEFAULT_ENCRYPT_KEY_PRIV,
#         encrypt_key_ctx: str = DEFAULT_ENCRYPT_KEY_CTX,
#         store_name: str = DEFAULT_STORE_NAME,
#         base_url: str = DEFAULT_API_URL
# ) -> Dict[str, Any]:
#     """
#     Ensure all necessary TPM2 components are set up:
#     - Primary key (parent key)
#     - Encryption key
#     - Loaded encryption key context
#     - Encrypted file store
#
#     This function checks if components exist by trying to use them first.
#     Only creates components if they don't exist on the server.
#
#     Args:
#         primary_ctx: Path to primary key context file
#         encrypt_key_pub: Path to encryption key public file
#         encrypt_key_priv: Path to encryption key private file
#         encrypt_key_ctx: Path to loaded encryption key context file
#         store_name: Name of the encrypted file store
#         base_url: Base URL for the API
#
#     Returns:
#         Dictionary with success status and any errors
#     """
#     try:
#         # Quick check: Try to list keys from the file store
#         # If this succeeds, everything is already set up
#         _flush_context(base_url=base_url)
#         test_result = _make_request("POST", "/tpm2/file-store/list-keys",
#                                     json_data={
#                                         "context_file": encrypt_key_ctx,
#                                         "store_name": store_name
#                                     },
#                                     base_url=base_url)
#
#         if test_result.get("success"):
#             # Everything is already set up, we can use it
#             return {"success": True}
#
#         # If we get here, something is missing. Let's set up step by step.
#         # Step 1: Create primary key (try to create, ignore if already exists)
#         _flush_context(base_url=base_url)
#         result = _make_request("POST", "/tpm2/create-primary",
#                                json_data={
#                                    "hierarchy": "o",
#                                    "context_file": primary_ctx
#                                },
#                                base_url=base_url)
#         # Continue even if it fails - it might already exist
#
#         # Step 2: Create encryption key (try to create, ignore if already exists)
#         _flush_context(base_url=base_url)
#         result = _make_request("POST", "/tpm2/create-key",
#                                json_data={
#                                    "parent_context": primary_ctx,
#                                    "key_type": "rsa",
#                                    "public_file": encrypt_key_pub,
#                                    "private_file": encrypt_key_priv
#                                },
#                                base_url=base_url)
#         # Continue even if it fails - it might already exist
#
#         # Step 3: Load encryption key (try to load, ignore if already loaded)
#         _flush_context(base_url=base_url)
#         result = _make_request("POST", "/tpm2/load-key",
#                                json_data={
#                                    "parent_context": primary_ctx,
#                                    "public_file": encrypt_key_pub,
#                                    "private_file": encrypt_key_priv,
#                                    "context_file": encrypt_key_ctx
#                                },
#                                base_url=base_url)
#         # Continue even if it fails - it might already be loaded
#
#         # Step 4: Create encrypted file store (only if it doesn't exist)
#         # Try to list keys first to check if store exists
#         _flush_context(base_url=base_url)
#         check_store = _make_request("POST", "/tpm2/file-store/list-keys",
#                                     json_data={
#                                         "context_file": encrypt_key_ctx,
#                                         "store_name": store_name
#                                     },
#                                     base_url=base_url)
#
#         if not check_store.get("success"):
#             # Store doesn't exist, create it
#             _flush_context(base_url=base_url)
#             result = _make_request("POST", "/tpm2/file-store/create",
#                                    json_data={
#                                        "context_file": encrypt_key_ctx,
#                                        "store_name": store_name
#                                    },
#                                    base_url=base_url)
#             # If creation fails with "already exists" type error, that's okay
#             # But if it's a real error (like wrong key), we should report it
#             if not result.get("success"):
#                 error_msg = result.get("error", "").lower()
#                 # Only fail if it's not an "already exists" type error
#                 if "already exists" not in error_msg and "file exists" not in error_msg:
#                     # Try one more time to verify the store works
#                     verify_result = _make_request("POST", "/tpm2/file-store/list-keys",
#                                                   json_data={
#                                                       "context_file": encrypt_key_ctx,
#                                                       "store_name": store_name
#                                                   },
#                                                   base_url=base_url)
#                     if not verify_result.get("success"):
#                         return {
#                             "success": False,
#                             "error": f"Failed to create or verify encrypted file store: {result.get('error', 'Unknown error')}"
#                         }
#
#         return {"success": True}
#
#     except Exception as e:
#         return {
#             "success": False,
#             "error": f"Error during TPM setup: {str(e)}"
#         }
#
#
# def write_key_to_tpm(
#         key: str,
#         secret: str,
#         primary_ctx: str = DEFAULT_PRIMARY_CTX,
#         encrypt_key_pub: str = DEFAULT_ENCRYPT_KEY_PUB,
#         encrypt_key_priv: str = DEFAULT_ENCRYPT_KEY_PRIV,
#         encrypt_key_ctx: str = DEFAULT_ENCRYPT_KEY_CTX,
#         store_name: str = DEFAULT_STORE_NAME,
#         base_url: str = DEFAULT_API_URL
# ) -> Dict[str, Any]:
#     """
#     Write a key-secret pair to the TPM2 encrypted file store.
#
#     This function stores a key (identifier) and secret (pubkey or privkey) in the
#     encrypted file store. It automatically handles initialization of the TPM2
#     components if they don't exist. Uses HTTP requests to communicate with the REST API.
#
#     Args:
#         key: The key identifier (e.g., "node_pubkey", "wallet_privkey")
#         secret: The secret value to store (pubkey or privkey)
#         primary_ctx: Path to primary key context file (default: anylog_primary.ctx)
#         encrypt_key_pub: Path to encryption key public file (default: anylog_encrypt_key.pub)
#         encrypt_key_priv: Path to encryption key private file (default: anylog_encrypt_key.priv)
#         encrypt_key_ctx: Path to loaded encryption key context file (default: anylog_encrypt_key.ctx)
#         store_name: Name of the encrypted file store (default: anylog_key_store.json)
#         base_url: Base URL for the TPM2 REST API (default: http://localhost:8000)
#
#     Returns:
#         Dictionary with success status and any errors or messages
#
#     Example:
#         >>> result = write_key_to_tpm("node_pubkey", "0x1234abcd...")
#         >>> if result["success"]:
#         ...     print("Key stored successfully")
#     """
#     try:
#         # Ensure TPM setup is complete
#         setup_result = _ensure_tpm_setup(
#             primary_ctx=primary_ctx,
#             encrypt_key_pub=encrypt_key_pub,
#             encrypt_key_priv=encrypt_key_priv,
#             encrypt_key_ctx=encrypt_key_ctx,
#             store_name=store_name,
#             base_url=base_url
#         )
#
#         if not setup_result.get("success"):
#             return setup_result
#
#         # Flush context before storing
#         _flush_context(base_url=base_url)
#
#         # Store the key-value pair via REST API
#         result = _make_request("POST", "/tpm2/file-store/store",
#                                json_data={
#                                    "context_file": encrypt_key_ctx,
#                                    "store_name": store_name,
#                                    "key": key,
#                                    "value": secret
#                                },
#                                base_url=base_url)
#
#         # Flush context after storing
#         _flush_context(base_url=base_url)
#
#         if result.get("success"):
#             return {
#                 "success": True,
#                 "message": f"Key '{key}' stored successfully",
#                 "key": key
#             }
#         else:
#             return {
#                 "success": False,
#                 "error": f"Failed to store key: {result.get('error', 'Unknown error')}"
#             }
#
#     except Exception as e:
#         _flush_context(base_url=base_url)  # Try to flush on error
#         return {
#             "success": False,
#             "error": f"Error storing key to TPM: {str(e)}"
#         }
#
#
# def read_key_from_tpm(
#         key: str,
#         primary_ctx: str = DEFAULT_PRIMARY_CTX,
#         encrypt_key_pub: str = DEFAULT_ENCRYPT_KEY_PUB,
#         encrypt_key_priv: str = DEFAULT_ENCRYPT_KEY_PRIV,
#         encrypt_key_ctx: str = DEFAULT_ENCRYPT_KEY_CTX,
#         store_name: str = DEFAULT_STORE_NAME,
#         base_url: str = DEFAULT_API_URL
# ) -> Dict[str, Any]:
#     """
#     Read a key-secret pair from the TPM2 encrypted file store.
#
#     This function retrieves a secret (pubkey or privkey) associated with a key
#     identifier from the encrypted file store. It automatically handles initialization
#     of the TPM2 components if they don't exist. Uses HTTP requests to communicate with the REST API.
#
#     Args:
#         key: The key identifier to retrieve (e.g., "node_pubkey", "wallet_privkey")
#         primary_ctx: Path to primary key context file (default: anylog_primary.ctx)
#         encrypt_key_pub: Path to encryption key public file (default: anylog_encrypt_key.pub)
#         encrypt_key_priv: Path to encryption key private file (default: anylog_encrypt_key.priv)
#         encrypt_key_ctx: Path to loaded encryption key context file (default: anylog_encrypt_key.ctx)
#         store_name: Name of the encrypted file store (default: anylog_key_store.json)
#         base_url: Base URL for the TPM2 REST API (default: http://localhost:8000)
#
#     Returns:
#         Dictionary with success status, the retrieved value (if successful), and any errors
#
#     Example:
#         >>> result = read_key_from_tpm("node_pubkey")
#         >>> if result["success"]:
#         ...     pubkey = result["value"]
#         ...     print(f"Retrieved pubkey: {pubkey}")
#     """
#     try:
#         # Ensure TPM setup is complete
#         setup_result = _ensure_tpm_setup(
#             primary_ctx=primary_ctx,
#             encrypt_key_pub=encrypt_key_pub,
#             encrypt_key_priv=encrypt_key_priv,
#             encrypt_key_ctx=encrypt_key_ctx,
#             store_name=store_name,
#             base_url=base_url
#         )
#
#         if not setup_result.get("success"):
#             return setup_result
#
#         # Flush context before retrieving
#         _flush_context(base_url=base_url)
#
#         # Retrieve the key-value pair via REST API
#         result = _make_request("POST", "/tpm2/file-store/retrieve",
#                                json_data={
#                                    "context_file": encrypt_key_ctx,
#                                    "store_name": store_name,
#                                    "key": key
#                                },
#                                base_url=base_url)
#
#         # Flush context after retrieving
#         _flush_context(base_url=base_url)
#
#         if result.get("success"):
#             return {
#                 "success": True,
#                 "key": key,
#                 "value": result.get("value"),
#                 "message": f"Key '{key}' retrieved successfully"
#             }
#         else:
#             # Provide a more helpful error message
#             error_msg = result.get("error", "Unknown error")
#             available_keys = result.get("available_keys", [])
#
#             # Check if the error indicates the key doesn't exist
#             if "not found" in error_msg.lower() or "not found in file store" in error_msg.lower():
#                 if available_keys:
#                     return {
#                         "success": False,
#                         "error": f"Key '{key}' not found in file store. Available keys: {', '.join(available_keys)}",
#                         "available_keys": available_keys
#                     }
#                 else:
#                     return {
#                         "success": False,
#                         "error": f"Key '{key}' not found in file store. The file store is empty - you need to write the key first using write_key_to_tpm().",
#                         "available_keys": available_keys
#                     }
#
#             return {
#                 "success": False,
#                 "error": error_msg,
#                 "available_keys": available_keys
#             }
#
#     except Exception as e:
#         _flush_context(base_url=base_url)  # Try to flush on error
#         return {
#             "success": False,
#             "error": f"Error reading key from TPM: {str(e)}"
#         }
#
#
# # Example usage
# if __name__ == "__main__":
#     # Step 2: Write a pubkey
#     print("Writing pubkey to TPM...")
#     result = write_key_to_tpm("node_pubkey", "0x1234567890abcdef")
#     print(f"Write result: {result}")
#
#     # Step 3: Read the pubkey back
#     print("\nReading pubkey from TPM...")
#     result = read_key_from_tpm("node_pubkey")
#     print(f"Read result: {result}")
#
#     if result.get("success"):
#         print(f"Retrieved value: {result.get('value')}")
#



