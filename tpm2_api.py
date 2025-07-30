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
            key_type: Type of key ('rsa', 'ecc')
            public_file: File to save the public key
            private_file: File to save the private key
            
        Returns:
            Dictionary with key information
        """
        try:
            if key_type.lower() == "rsa":
                key_alg = "rsa2048"
            elif key_type.lower() == "ecc":
                key_alg = "ecc256"
            else:
                return {"success": False, "error": f"Unsupported key type: {key_type}"}
            
            cmd = [
                'tpm2_create',
                '-C', parent_context,
                '-G', key_alg,
                '-u', public_file,
                '-r', private_file
            ]
            
            result = self._run_command(cmd)
            
            if result['success']:
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