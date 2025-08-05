#!/usr/bin/env python3
"""
TPM2 Python API - A simple interface for TPM2 operations using system calls
"""

import os
import json
import base64
import subprocess
import tempfile
from typing import Dict, List, Optional, Any
from pathlib import Path

class TPM2API:
    """
    Python API for TPM2 operations using tpm2 command-line tools
    """
    
    def __init__(self, tcti_name: str = "swtpm:host=127.0.0.1,port=2321"):
        """
        Initialize TPM2 API
        
        Args:
            tcti_name: TCTI configuration (default: swtpm for Docker container)
        """
        self.tcti_name = tcti_name
        self._set_environment()
        self._test_connection()
    
    def _set_environment(self):
        """Set environment variables for TPM2 tools"""
        os.environ['TSS2_TCTI'] = self.tcti_name
        os.environ['TPM2TOOLS_TCTI'] = self.tcti_name
        print(f"Set TPM2 environment: TSS2_TCTI={self.tcti_name}")
    
    def _test_connection(self):
        """Test TPM2 connection"""
        try:
            result = self._run_command(['tpm2_getcap', 'properties-fixed'])
            if result['success']:
                print("TPM2 connection successful")
            else:
                raise Exception(f"TPM2 connection failed: {result['error']}")
        except Exception as e:
            raise Exception(f"Failed to connect to TPM: {e}")
    
    def _run_command(self, cmd: List[str], input_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a TPM2 command and return the result
        
        Args:
            cmd: Command list to execute
            input_data: Optional input data for the command
            
        Returns:
            Dictionary with success status and output/error
        """
        try:
            # Add TCTI to command if not already present
            if '--tcti' not in ' '.join(cmd):
                cmd.extend(['--tcti', self.tcti_name])
            
            print(f"Running command: {' '.join(cmd)}")
            
            # Set environment variables for the subprocess
            env = os.environ.copy()
            env['TSS2_TCTI'] = self.tcti_name
            env['TPM2TOOLS_TCTI'] = self.tcti_name
            
            # Run the command
            if input_data:
                result = subprocess.run(
                    cmd,
                    input=input_data.encode(),
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env
                )
            else:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env
                )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout.strip(),
                    "stderr": result.stderr.strip()
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip() or result.stdout.strip(),
                    "returncode": result.returncode
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_primary_key(self, hierarchy: str = "o", context_file: str = "primary.ctx") -> Dict[str, Any]:
        """
        Create a primary key in the specified hierarchy
        
        Args:
            hierarchy: TPM hierarchy ('o' for owner, 'e' for endorsement, 'p' for platform)
            context_file: File to save the primary key context
            
        Returns:
            Dictionary with key information
        """
        try:
            cmd = [
                'tpm2_createprimary',
                '-C', hierarchy,
                '-c', context_file,
                '-G', 'rsa2048',
                '-g', 'sha256'
            ]
            
            result = self._run_command(cmd)
            
            if result['success']:
                # Parse the output to get key information
                output_lines = result['output'].split('\n')
                key_info = {}
                
                for line in output_lines:
                    if 'name:' in line:
                        key_info['name'] = line.split('name:')[1].strip()
                    elif 'qualified name:' in line:
                        key_info['qualified_name'] = line.split('qualified name:')[1].strip()
                
                return {
                    "success": True,
                    "context_file": context_file,
                    "hierarchy": hierarchy,
                    "key_info": key_info,
                    "action": "primary_key_created"
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_key(self, parent_context: str, key_type: str = "rsa", 
                   public_file: str = "key.pub", private_file: str = "key.priv") -> Dict[str, Any]:
        """
        Create a key under the specified parent
        
        Args:
            parent_context: Parent key context file
            key_type: Type of key ('rsa', 'ecc', 'aes128', 'aes256')
            public_file: File to save the public key (for RSA/ECC) or key context (for AES)
            private_file: File to save the private key (for RSA/ECC) or not used (for AES)
            
        Returns:
            Dictionary with key information
        """
        try:
            if key_type.lower() == "rsa":
                key_alg = "rsa2048"
                cmd = [
                    'tpm2_create',
                    '-C', parent_context,
                    '-G', key_alg,
                    '-u', public_file,
                    '-r', private_file
                ]
            elif key_type.lower() == "ecc":
                key_alg = "ecc256"
                cmd = [
                    'tpm2_create',
                    '-C', parent_context,
                    '-G', key_alg,
                    '-u', public_file,
                    '-r', private_file
                ]
            elif key_type.lower() in ["aes128", "aes256"]:
                # For AES keys, we use tpm2_createprimary to create a symmetric key
                # AES keys are stored directly as context files
                key_size = "128" if key_type.lower() == "aes128" else "256"
                cmd = [
                    'tpm2_createprimary',
                    '-C', parent_context,
                    '-G', f'aes{key_size}',
                    '-c', public_file  # For AES, we save the context directly
                ]
            else:
                return {"success": False, "error": f"Unsupported key type: {key_type}"}
            
            result = self._run_command(cmd)
            
            if result['success']:
                if key_type.lower().startswith("aes"):
                    return {
                        "success": True,
                        "context_file": public_file,  # For AES, this is the context file
                        "key_type": key_type,
                        "parent_context": parent_context,
                        "action": "aes_key_created"
                    }
                else:
                    return {
                        "success": True,
                        "public_file": public_file,
                        "private_file": private_file,
                        "key_type": key_type,
                        "parent_context": parent_context,
                        "action": "key_created"
                    }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def load_key(self, parent_context: str, public_file: str, private_file: str,
                 context_file: str = "loaded_key.ctx") -> Dict[str, Any]:
        """
        Load a key into TPM context
        
        Args:
            parent_context: Parent key context file
            public_file: Public key file
            private_file: Private key file
            context_file: File to save the loaded key context
            
        Returns:
            Dictionary with result
        """
        try:
            cmd = [
                'tpm2_load',
                '-C', parent_context,
                '-u', public_file,
                '-r', private_file,
                '-c', context_file
            ]
            
            result = self._run_command(cmd)
            
            if result['success']:
                return {
                    "success": True,
                    "context_file": context_file,
                    "parent_context": parent_context,
                    "action": "key_loaded"
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def make_persistent(self, context_file: str, persistent_handle: int = 0x81010001) -> Dict[str, Any]:
        """
        Make a key persistent in TPM
        
        Args:
            context_file: Key context file
            persistent_handle: Persistent handle to use
            
        Returns:
            Dictionary with result
        """
        try:
            cmd = [
                'tpm2_evictcontrol',
                '-C', 'o',
                '-c', context_file,
                str(persistent_handle)
            ]
            
            result = self._run_command(cmd)
            
            if result['success']:
                return {
                    "success": True,
                    "persistent_handle": hex(persistent_handle),
                    "context_file": context_file,
                    "action": "key_persisted"
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def flush_context(self, context_type: str = "transient") -> Dict[str, Any]:
        """
        Flush TPM contexts
        
        Args:
            context_type: Type of contexts to flush ('transient', 'loaded', 'saved', 'all')
            
        Returns:
            Dictionary with result
        """
        try:
            if context_type == "transient":
                cmd = ['tpm2_flushcontext', '-t']
            elif context_type == "loaded":
                cmd = ['tpm2_flushcontext', '-l']
            elif context_type == "saved":
                cmd = ['tpm2_flushcontext', '-s']
            elif context_type == "all":
                cmd = ['tpm2_flushcontext', '-t', '-l', '-s']
            else:
                return {"success": False, "error": f"Invalid context type: {context_type}"}
            result = self._run_command(cmd)
            
            if result['success']:
                return {
                    "success": True,
                    "flushed_type": context_type,
                    "action": "contexts_flushed"
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_tpm_info(self) -> Dict[str, Any]:
        """
        Get TPM information
        
        Returns:
            Dictionary with TPM information
        """
        try:
            # Get TPM properties
            result = self._run_command(['tpm2_getcap', 'properties-fixed'])
            
            if result['success']:
                # Parse properties
                properties = {}
                for line in result['output'].split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        properties[key.strip()] = value.strip()
                
                return {
                    "success": True,
                    "tcti": self.tcti_name,
                    "properties": properties,
                    "action": "tpm_info_retrieved"
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sign_data(self, context_file: str, data: str, signature_file: str = "signature.sig") -> Dict[str, Any]:
        """
        Sign data using a loaded key
        
        Args:
            context_file: Key context file
            data: Data to sign (base64 encoded)
            signature_file: File to save the signature
            
        Returns:
            Dictionary with result
        """
        try:
            # Decode base64 data
            decoded_data = base64.b64decode(data)
            
            # Create temporary file for data
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_file:
                temp_file.write(decoded_data)
                temp_data_file = temp_file.name
            
            try:
                cmd = [
                    'tpm2_sign',
                    '-c', context_file,
                    '-g', 'sha256',
                    '-m', temp_data_file,
                    '-s', signature_file
                ]
                
                result = self._run_command(cmd)
                
                if result['success']:
                    # Read signature file
                    with open(signature_file, 'rb') as f:
                        signature_data = f.read()
                    
                    return {
                        "success": True,
                        "signature": base64.b64encode(signature_data).decode(),
                        "signature_file": signature_file,
                        "action": "data_signed"
                    }
                else:
                    return result
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_data_file)
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_signature(self, context_file: str, data: str, signature: str) -> Dict[str, Any]:
        """
        Verify a signature
        
        Args:
            context_file: Key context file
            data: Original data (base64 encoded)
            signature: Signature to verify (base64 encoded)
            
        Returns:
            Dictionary with verification result
        """
        try:
            # Decode base64 data
            decoded_data = base64.b64decode(data)
            decoded_signature = base64.b64decode(signature)
            
            # Create temporary files
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_data_file:
                temp_data_file.write(decoded_data)
                temp_data_path = temp_data_file.name
            
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_sig_file:
                temp_sig_file.write(decoded_signature)
                temp_sig_path = temp_sig_file.name
            
            try:
                cmd = [
                    'tpm2_verifysignature',
                    '-c', context_file,
                    '-g', 'sha256',
                    '-m', temp_data_path,
                    '-s', temp_sig_path
                ]
                
                result = self._run_command(cmd)
                
                if result['success']:
                    return {
                        "success": True,
                        "verified": True,
                        "action": "signature_verified"
                    }
                else:
                    return {
                        "success": False,
                        "verified": False,
                        "error": result['error']
                    }
                    
            finally:
                # Clean up temporary files
                os.unlink(temp_data_path)
                os.unlink(temp_sig_path)
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def encrypt_data(self, context_file: str, data: str, encrypted_file: str = "encrypted.bin") -> Dict[str, Any]:
        """
        Encrypt data using a loaded RSA key
        
        Args:
            context_file: Key context file (RSA key)
            data: Data to encrypt (base64 encoded)
            encrypted_file: File to save the encrypted data
            
        Returns:
            Dictionary with encryption result
        """
        try:
            # Decode base64 data
            decoded_data = base64.b64decode(data)
            
            # Create temporary file for data
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_file:
                temp_file.write(decoded_data)
                temp_data_file = temp_file.name
            
            try:
                cmd = [
                    'tpm2_rsaencrypt',
                    '-c', context_file,
                    '-o', encrypted_file,
                    temp_data_file
                ]
                
                result = self._run_command(cmd)
                
                if result['success']:
                    # Read encrypted file
                    with open(encrypted_file, 'rb') as f:
                        encrypted_data = f.read()
                    
                    return {
                        "success": True,
                        "encrypted_data": base64.b64encode(encrypted_data).decode(),
                        "encrypted_file": encrypted_file,
                        "action": "data_encrypted"
                    }
                else:
                    return result
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_data_file)
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def decrypt_data(self, context_file: str, encrypted_data: str, decrypted_file: str = "decrypted.bin") -> Dict[str, Any]:
        """
        Decrypt data using a loaded RSA key
        
        Args:
            context_file: Key context file (RSA key)
            encrypted_data: Encrypted data to decrypt (base64 encoded)
            decrypted_file: File to save the decrypted data
            
        Returns:
            Dictionary with decryption result
        """
        try:
            # Decode base64 encrypted data
            decoded_encrypted = base64.b64decode(encrypted_data)
            
            # Create temporary file for encrypted data
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_file:
                temp_file.write(decoded_encrypted)
                temp_encrypted_file = temp_file.name
            
            try:
                cmd = [
                    'tpm2_rsadecrypt',
                    '-c', context_file,
                    '-o', decrypted_file,
                    temp_encrypted_file
                ]
                
                result = self._run_command(cmd)
                
                if result['success']:
                    # Read decrypted file
                    with open(decrypted_file, 'rb') as f:
                        decrypted_data = f.read()
                    
                    return {
                        "success": True,
                        "decrypted_data": base64.b64encode(decrypted_data).decode(),
                        "decrypted_file": decrypted_file,
                        "action": "data_decrypted"
                    }
                else:
                    return result
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_encrypted_file)
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def encrypt_data_aes(self, context_file: str, data: str, encrypted_file: str = "encrypted_aes.bin") -> Dict[str, Any]:
        """
        Encrypt data using a loaded AES key
        
        Args:
            context_file: Key context file (AES key)
            data: Data to encrypt (base64 encoded)
            encrypted_file: File to save the encrypted data
            
        Returns:
            Dictionary with encryption result
        """
        try:
            # Decode base64 data
            decoded_data = base64.b64decode(data)
            
            # Create temporary file for data
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_file:
                temp_file.write(decoded_data)
                temp_data_file = temp_file.name
            
            try:
                cmd = [
                    'tpm2_encryptdecrypt',
                    '-c', context_file,
                    '-d', temp_data_file,
                    '-o', encrypted_file
                ]
                
                result = self._run_command(cmd)
                
                if result['success']:
                    # Read encrypted file
                    with open(encrypted_file, 'rb') as f:
                        encrypted_data = f.read()
                    
                    return {
                        "success": True,
                        "encrypted_data": base64.b64encode(encrypted_data).decode(),
                        "encrypted_file": encrypted_file,
                        "action": "data_encrypted_aes"
                    }
                else:
                    return result
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_data_file)
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def decrypt_data_aes(self, context_file: str, encrypted_data: str, decrypted_file: str = "decrypted_aes.bin") -> Dict[str, Any]:
        """
        Decrypt data using a loaded AES key
        
        Args:
            context_file: Key context file (AES key)
            encrypted_data: Encrypted data to decrypt (base64 encoded)
            decrypted_file: File to save the decrypted data
            
        Returns:
            Dictionary with decryption result
        """
        try:
            # Decode base64 encrypted data
            decoded_encrypted = base64.b64decode(encrypted_data)
            
            # Create temporary file for encrypted data
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_file:
                temp_file.write(decoded_encrypted)
                temp_encrypted_file = temp_file.name
            
            try:
                cmd = [
                    'tpm2_encryptdecrypt',
                    '-c', context_file,
                    '-d', temp_encrypted_file,
                    '-o', decrypted_file,
                    '--decrypt'
                ]
                
                result = self._run_command(cmd)
                
                if result['success']:
                    # Read decrypted file
                    with open(decrypted_file, 'rb') as f:
                        decrypted_data = f.read()
                    
                    return {
                        "success": True,
                        "decrypted_data": base64.b64encode(decrypted_data).decode(),
                        "decrypted_file": decrypted_file,
                        "action": "data_decrypted_aes"
                    }
                else:
                    return result
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_encrypted_file)
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_encrypted_file_store(self, context_file: str, store_name: str = "file_store.json") -> Dict[str, Any]:
        """
        Create a new encrypted file store with an empty JSON structure
        
        Args:
            context_file: Key context file (RSA key) for encryption
            store_name: Name of the encrypted file store
            
        Returns:
            Dictionary with creation result
        """
        try:
            # Create empty JSON structure
            empty_store = {}
            json_data = json.dumps(empty_store, indent=2)
            
            # Encrypt the empty JSON
            result = self.encrypt_data(context_file, base64.b64encode(json_data.encode()).decode(), store_name)
            
            if result['success']:
                return {
                    "success": True,
                    "store_name": store_name,
                    "message": "Encrypted file store created successfully",
                    "action": "file_store_created"
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def store_key_value(self, context_file: str, store_name: str, key: str, value: Any) -> Dict[str, Any]:
        """
        Store a key-value pair in the encrypted file store
        
        Args:
            context_file: Key context file (RSA key) for encryption/decryption
            store_name: Name of the encrypted file store
            key: Key to store
            value: Value to store (will be JSON serialized)
            
        Returns:
            Dictionary with storage result
        """
        try:
            # Step 1: Decrypt the existing file store
            if os.path.exists(store_name):
                # Read encrypted file
                with open(store_name, 'rb') as f:
                    encrypted_data = f.read()
                
                # Decrypt the data
                decrypt_result = self.decrypt_data(
                    context_file, 
                    base64.b64encode(encrypted_data).decode(), 
                    "temp_decrypted.json"
                )
                
                if not decrypt_result['success']:
                    return decrypt_result
                
                # Parse the decrypted JSON
                with open("temp_decrypted.json", 'r') as f:
                    store_data = json.load(f)
            else:
                # Create new empty store
                store_data = {}
            
            # Step 2: Add/modify the key-value pair
            store_data[key] = value
            
            # Step 3: Re-encrypt the updated data
            json_data = json.dumps(store_data, indent=2)
            encrypt_result = self.encrypt_data(
                context_file, 
                base64.b64encode(json_data.encode()).decode(), 
                store_name
            )
            
            # Clean up temporary file
            if os.path.exists("temp_decrypted.json"):
                os.unlink("temp_decrypted.json")
            
            if encrypt_result['success']:
                return {
                    "success": True,
                    "key": key,
                    "value": value,
                    "store_name": store_name,
                    "message": f"Key '{key}' stored successfully",
                    "action": "key_value_stored"
                }
            else:
                return encrypt_result
                
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists("temp_decrypted.json"):
                os.unlink("temp_decrypted.json")
            return {"success": False, "error": str(e)}

    def retrieve_key_value(self, context_file: str, store_name: str, key: str) -> Dict[str, Any]:
        """
        Retrieve a key-value pair from the encrypted file store
        
        Args:
            context_file: Key context file (RSA key) for decryption
            store_name: Name of the encrypted file store
            key: Key to retrieve
            
        Returns:
            Dictionary with retrieval result
        """
        try:
            if not os.path.exists(store_name):
                return {"success": False, "error": f"File store '{store_name}' does not exist"}
            
            # Step 1: Read and decrypt the file store
            with open(store_name, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt the data
            decrypt_result = self.decrypt_data(
                context_file, 
                base64.b64encode(encrypted_data).decode(), 
                "temp_decrypted.json"
            )
            
            if not decrypt_result['success']:
                return decrypt_result
            
            # Step 2: Parse the decrypted JSON and retrieve the key
            with open("temp_decrypted.json", 'r') as f:
                store_data = json.load(f)
            
            # Clean up temporary file
            os.unlink("temp_decrypted.json")
            
            if key in store_data:
                return {
                    "success": True,
                    "key": key,
                    "value": store_data[key],
                    "store_name": store_name,
                    "action": "key_value_retrieved"
                }
            else:
                return {
                    "success": False,
                    "error": f"Key '{key}' not found in file store",
                    "available_keys": list(store_data.keys())
                }
                
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists("temp_decrypted.json"):
                os.unlink("temp_decrypted.json")
            return {"success": False, "error": str(e)}

    def list_file_store_keys(self, context_file: str, store_name: str) -> Dict[str, Any]:
        """
        List all keys in the encrypted file store
        
        Args:
            context_file: Key context file (RSA key) for decryption
            store_name: Name of the encrypted file store
            
        Returns:
            Dictionary with list of keys
        """
        try:
            if not os.path.exists(store_name):
                return {"success": False, "error": f"File store '{store_name}' does not exist"}
            
            # Step 1: Read and decrypt the file store
            with open(store_name, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt the data
            decrypt_result = self.decrypt_data(
                context_file, 
                base64.b64encode(encrypted_data).decode(), 
                "temp_decrypted.json"
            )
            
            if not decrypt_result['success']:
                return decrypt_result
            
            # Step 2: Parse the decrypted JSON and get all keys
            with open("temp_decrypted.json", 'r') as f:
                store_data = json.load(f)
            
            # Clean up temporary file
            os.unlink("temp_decrypted.json")
            
            return {
                "success": True,
                "keys": list(store_data.keys()),
                "total_keys": len(store_data),
                "store_name": store_name,
                "action": "keys_listed"
            }
                
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists("temp_decrypted.json"):
                os.unlink("temp_decrypted.json")
            return {"success": False, "error": str(e)}

    def delete_key_value(self, context_file: str, store_name: str, key: str) -> Dict[str, Any]:
        """
        Delete a key-value pair from the encrypted file store
        
        Args:
            context_file: Key context file (RSA key) for encryption/decryption
            store_name: Name of the encrypted file store
            key: Key to delete
            
        Returns:
            Dictionary with deletion result
        """
        try:
            if not os.path.exists(store_name):
                return {"success": False, "error": f"File store '{store_name}' does not exist"}
            
            # Step 1: Read and decrypt the file store
            with open(store_name, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt the data
            decrypt_result = self.decrypt_data(
                context_file, 
                base64.b64encode(encrypted_data).decode(), 
                "temp_decrypted.json"
            )
            
            if not decrypt_result['success']:
                return decrypt_result
            
            # Step 2: Parse the decrypted JSON and delete the key
            with open("temp_decrypted.json", 'r') as f:
                store_data = json.load(f)
            
            if key not in store_data:
                # Clean up temporary file
                os.unlink("temp_decrypted.json")
                return {
                    "success": False,
                    "error": f"Key '{key}' not found in file store",
                    "available_keys": list(store_data.keys())
                }
            
            # Store the value before deletion for response
            deleted_value = store_data[key]
            del store_data[key]
            
            # Step 3: Re-encrypt the updated data
            json_data = json.dumps(store_data, indent=2)
            encrypt_result = self.encrypt_data(
                context_file, 
                base64.b64encode(json_data.encode()).decode(), 
                store_name
            )
            
            # Clean up temporary file
            os.unlink("temp_decrypted.json")
            
            if encrypt_result['success']:
                return {
                    "success": True,
                    "key": key,
                    "deleted_value": deleted_value,
                    "store_name": store_name,
                    "message": f"Key '{key}' deleted successfully",
                    "action": "key_value_deleted"
                }
            else:
                return encrypt_result
                
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists("temp_decrypted.json"):
                os.unlink("temp_decrypted.json")
            return {"success": False, "error": str(e)}

    def create_encrypted_file_store_aes(self, context_file: str, store_name: str = "file_store_aes.json") -> Dict[str, Any]:
        """
        Create a new encrypted file store using AES encryption
        
        Args:
            context_file: Key context file (AES key) for encryption
            store_name: Name of the encrypted file store
            
        Returns:
            Dictionary with creation result
        """
        try:
            # Create empty JSON structure
            empty_store = {}
            json_data = json.dumps(empty_store, indent=2)
            
            # Encrypt the empty JSON using AES
            result = self.encrypt_data_aes(context_file, base64.b64encode(json_data.encode()).decode(), store_name)
            
            if result['success']:
                return {
                    "success": True,
                    "store_name": store_name,
                    "message": "AES encrypted file store created successfully",
                    "action": "aes_file_store_created"
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def store_key_value_aes(self, context_file: str, store_name: str, key: str, value: Any) -> Dict[str, Any]:
        """
        Store a key-value pair in the AES encrypted file store
        
        Args:
            context_file: Key context file (AES key) for encryption/decryption
            store_name: Name of the encrypted file store
            key: Key to store
            value: Value to store (will be JSON serialized)
            
        Returns:
            Dictionary with storage result
        """
        try:
            # Step 1: Decrypt the existing file store
            if os.path.exists(store_name):
                # Read encrypted file
                with open(store_name, 'rb') as f:
                    encrypted_data = f.read()
                
                # Decrypt the data using AES
                decrypt_result = self.decrypt_data_aes(
                    context_file, 
                    base64.b64encode(encrypted_data).decode(), 
                    "temp_decrypted_aes.json"
                )
                
                if not decrypt_result['success']:
                    return decrypt_result
                
                # Parse the decrypted JSON
                with open("temp_decrypted_aes.json", 'r') as f:
                    store_data = json.load(f)
            else:
                # Create new empty store
                store_data = {}
            
            # Step 2: Add/modify the key-value pair
            store_data[key] = value
            
            # Step 3: Re-encrypt the updated data using AES
            json_data = json.dumps(store_data, indent=2)
            encrypt_result = self.encrypt_data_aes(
                context_file, 
                base64.b64encode(json_data.encode()).decode(), 
                store_name
            )
            
            # Clean up temporary file
            if os.path.exists("temp_decrypted_aes.json"):
                os.unlink("temp_decrypted_aes.json")
            
            if encrypt_result['success']:
                return {
                    "success": True,
                    "key": key,
                    "value": value,
                    "store_name": store_name,
                    "message": f"Key '{key}' stored successfully using AES",
                    "action": "key_value_stored_aes"
                }
            else:
                return encrypt_result
                
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists("temp_decrypted_aes.json"):
                os.unlink("temp_decrypted_aes.json")
            return {"success": False, "error": str(e)}

    def retrieve_key_value_aes(self, context_file: str, store_name: str, key: str) -> Dict[str, Any]:
        """
        Retrieve a key-value pair from the AES encrypted file store
        
        Args:
            context_file: Key context file (AES key) for decryption
            store_name: Name of the encrypted file store
            key: Key to retrieve
            
        Returns:
            Dictionary with retrieval result
        """
        try:
            if not os.path.exists(store_name):
                return {"success": False, "error": f"AES file store '{store_name}' does not exist"}
            
            # Step 1: Read and decrypt the file store
            with open(store_name, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt the data using AES
            decrypt_result = self.decrypt_data_aes(
                context_file, 
                base64.b64encode(encrypted_data).decode(), 
                "temp_decrypted_aes.json"
            )
            
            if not decrypt_result['success']:
                return decrypt_result
            
            # Step 2: Parse the decrypted JSON and retrieve the key
            with open("temp_decrypted_aes.json", 'r') as f:
                store_data = json.load(f)
            
            # Clean up temporary file
            os.unlink("temp_decrypted_aes.json")
            
            if key in store_data:
                return {
                    "success": True,
                    "key": key,
                    "value": store_data[key],
                    "store_name": store_name,
                    "action": "key_value_retrieved_aes"
                }
            else:
                return {
                    "success": False,
                    "error": f"Key '{key}' not found in AES file store",
                    "available_keys": list(store_data.keys())
                }
                
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists("temp_decrypted_aes.json"):
                os.unlink("temp_decrypted_aes.json")
            return {"success": False, "error": str(e)}

    def list_file_store_keys_aes(self, context_file: str, store_name: str) -> Dict[str, Any]:
        """
        List all keys in the AES encrypted file store
        
        Args:
            context_file: Key context file (AES key) for decryption
            store_name: Name of the encrypted file store
            
        Returns:
            Dictionary with list of keys
        """
        try:
            if not os.path.exists(store_name):
                return {"success": False, "error": f"AES file store '{store_name}' does not exist"}
            
            # Step 1: Read and decrypt the file store
            with open(store_name, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt the data using AES
            decrypt_result = self.decrypt_data_aes(
                context_file, 
                base64.b64encode(encrypted_data).decode(), 
                "temp_decrypted_aes.json"
            )
            
            if not decrypt_result['success']:
                return decrypt_result
            
            # Step 2: Parse the decrypted JSON and get all keys
            with open("temp_decrypted_aes.json", 'r') as f:
                store_data = json.load(f)
            
            # Clean up temporary file
            os.unlink("temp_decrypted_aes.json")
            
            return {
                "success": True,
                "keys": list(store_data.keys()),
                "total_keys": len(store_data),
                "store_name": store_name,
                "action": "keys_listed_aes"
            }
                
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists("temp_decrypted_aes.json"):
                os.unlink("temp_decrypted_aes.json")
            return {"success": False, "error": str(e)}

    def delete_key_value_aes(self, context_file: str, store_name: str, key: str) -> Dict[str, Any]:
        """
        Delete a key-value pair from the AES encrypted file store
        
        Args:
            context_file: Key context file (AES key) for encryption/decryption
            store_name: Name of the encrypted file store
            key: Key to delete
            
        Returns:
            Dictionary with deletion result
        """
        try:
            if not os.path.exists(store_name):
                return {"success": False, "error": f"AES file store '{store_name}' does not exist"}
            
            # Step 1: Read and decrypt the file store
            with open(store_name, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt the data using AES
            decrypt_result = self.decrypt_data_aes(
                context_file, 
                base64.b64encode(encrypted_data).decode(), 
                "temp_decrypted_aes.json"
            )
            
            if not decrypt_result['success']:
                return decrypt_result
            
            # Step 2: Parse the decrypted JSON and delete the key
            with open("temp_decrypted_aes.json", 'r') as f:
                store_data = json.load(f)
            
            if key not in store_data:
                # Clean up temporary file
                os.unlink("temp_decrypted_aes.json")
                return {
                    "success": False,
                    "error": f"Key '{key}' not found in AES file store",
                    "available_keys": list(store_data.keys())
                }
            
            # Store the value before deletion for response
            deleted_value = store_data[key]
            del store_data[key]
            
            # Step 3: Re-encrypt the updated data using AES
            json_data = json.dumps(store_data, indent=2)
            encrypt_result = self.encrypt_data_aes(
                context_file, 
                base64.b64encode(json_data.encode()).decode(), 
                store_name
            )
            
            # Clean up temporary file
            os.unlink("temp_decrypted_aes.json")
            
            if encrypt_result['success']:
                return {
                    "success": True,
                    "key": key,
                    "deleted_value": deleted_value,
                    "store_name": store_name,
                    "message": f"Key '{key}' deleted successfully from AES store",
                    "action": "key_value_deleted_aes"
                }
            else:
                return encrypt_result
                
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists("temp_decrypted_aes.json"):
                os.unlink("temp_decrypted_aes.json")
            return {"success": False, "error": str(e)}

    def full_reset(self) -> Dict[str, Any]:
        """
        Perform a complete TPM reset - clears all contexts, persistent objects, and authorizations
        
        Returns:
            Dictionary with reset result
        """
        try:
            results = {}
            
            # Step 1: Clear all persistent objects (common handles)
            print("Clearing persistent objects...")
            persistent_handles = [
                0x81010001, 0x81010002, 0x81010003, 0x81010004, 0x81010005,
                0x81010006, 0x81010007, 0x81010008, 0x81010009, 0x8101000A,
                0x8101000B, 0x8101000C, 0x8101000D, 0x8101000E, 0x8101000F,
                0x81010010, 0x81010011, 0x81010012, 0x81010013, 0x81010014
            ]
            
            cleared_persistent = []
            for handle in persistent_handles:
                try:
                    cmd = ['tpm2_evictcontrol', '-C', 'o', '-c', str(handle)]
                    result = self._run_command(cmd)
                    if result['success']:
                        cleared_persistent.append(hex(handle))
                    # Don't fail if handle doesn't exist - that's expected
                except Exception:
                    # Ignore errors for non-existent handles
                    pass
            
            results["cleared_persistent"] = cleared_persistent
            
            # Step 2: Clear all contexts
            print("Clearing all contexts...")
            flush_result = self.flush_context("all")
            results["flush_contexts"] = flush_result
            
            # Step 3: Clear owner authorization
            print("Clearing owner authorization...")
            try:
                cmd = ['tpm2_clear', '-c', 'o']
                result = self._run_command(cmd)
                results["clear_owner"] = result
            except Exception as e:
                results["clear_owner"] = {"success": False, "error": str(e)}
            
            # Step 4: Clear endorsement authorization
            print("Clearing endorsement authorization...")
            try:
                cmd = ['tpm2_clear', '-c', 'e']
                result = self._run_command(cmd)
                results["clear_endorsement"] = result
            except Exception as e:
                results["clear_endorsement"] = {"success": False, "error": str(e)}
            
            # Step 5: Clear platform authorization
            print("Clearing platform authorization...")
            try:
                cmd = ['tpm2_clear', '-c', 'p']
                result = self._run_command(cmd)
                results["clear_platform"] = result
            except Exception as e:
                results["clear_platform"] = {"success": False, "error": str(e)}
            
            return {
                "success": True,
                "message": "TPM full reset completed",
                "results": results,
                "action": "tpm_full_reset"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# Example usage
if __name__ == "__main__":
    # Initialize TPM2 API
    tpm = TPM2API()
    
    # Create primary key
    print("Creating primary key...")
    result = tpm.create_primary_key()
    print(json.dumps(result, indent=2))
    
    # Create RSA key
    print("\nCreating RSA key...")
    result = tpm.create_key("primary.ctx", "rsa", "rsa.pub", "rsa.priv")
    print(json.dumps(result, indent=2))
    
    # Load key
    print("\nLoading key...")
    result = tpm.load_key("primary.ctx", "rsa.pub", "rsa.priv", "rsa.ctx")
    print(json.dumps(result, indent=2))
    
    # Make persistent
    print("\nMaking key persistent...")
    result = tpm.make_persistent("rsa.ctx")
    print(json.dumps(result, indent=2)) 