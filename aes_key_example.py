#!/usr/bin/env python3
"""
AES Key Example - Complete workflow demonstration

This script demonstrates how to use AES keys with the TPM2 API:
1. Create a primary key
2. Create AES keys (128-bit and 256-bit)
3. Encrypt and decrypt data using AES
4. Create AES encrypted file stores
5. Store and retrieve key-value pairs using AES encryption

Usage:
    python3 aes_key_example.py
"""

import base64
import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:8000"

def print_step(step_num, description):
    """Print a formatted step header"""
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {description}")
    print(f"{'='*60}")

def print_result(result, title="Result"):
    """Print a formatted result"""
    print(f"\n{title}:")
    print(json.dumps(result, indent=2))

def wait_for_api():
    """Wait for the API to be ready"""
    print("Waiting for API to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if i < max_retries - 1:
            print(f"⏳ Retrying... ({i+1}/{max_retries})")
            time.sleep(2)
    
    print("❌ API is not responding")
    return False

def main():
    """Main workflow demonstration"""
    print("🚀 TPM2 AES Key Demo")
    print("This demo will create AES keys and demonstrate encryption/decryption")
    
    # Wait for API to be ready
    if not wait_for_api():
        return
    
    try:
        # Step 1: Create primary key
        print_step(1, "Creating Primary Key")
        response = requests.post(f"{BASE_URL}/tpm2/create-primary", 
                               json={"hierarchy": "o", "context_file": "primary.ctx"})
        result = response.json()
        print_result(result, "Primary Key Creation")
        
        if not result.get("success"):
            print("❌ Failed to create primary key")
            return
        
        # Step 2: Create AES-128 key
        print_step(2, "Creating AES-128 Key")
        response = requests.post(f"{BASE_URL}/tpm2/create-key",
                               json={"parent_context": "primary.ctx", 
                                     "key_type": "aes128", 
                                     "public_file": "aes128_key.ctx"})
        result = response.json()
        print_result(result, "AES-128 Key Creation")
        
        if not result.get("success"):
            print("❌ Failed to create AES-128 key")
            return
        
        # Step 3: Create AES-256 key
        print_step(3, "Creating AES-256 Key")
        response = requests.post(f"{BASE_URL}/tpm2/create-key",
                               json={"parent_context": "primary.ctx", 
                                     "key_type": "aes256", 
                                     "public_file": "aes256_key.ctx"})
        result = response.json()
        print_result(result, "AES-256 Key Creation")
        
        if not result.get("success"):
            print("❌ Failed to create AES-256 key")
            return
        
        # Step 4: Test AES-128 encryption/decryption
        print_step(4, "Testing AES-128 Encryption/Decryption")
        
        # Prepare data to encrypt
        data_to_encrypt = "Hello, AES-128 World!"
        encoded_data = base64.b64encode(data_to_encrypt.encode()).decode()
        print(f"Data to encrypt: {data_to_encrypt}")
        print(f"Base64 encoded: {encoded_data}")
        
        # Encrypt with AES-128
        print("\n🔐 Encrypting with AES-128...")
        response = requests.post(f"{BASE_URL}/tpm2/encrypt-aes",
                               json={"context_file": "aes128_key.ctx",
                                     "data": encoded_data,
                                     "encrypted_file": "encrypted_aes128.bin"})
        encrypt_result = response.json()
        print_result(encrypt_result, "AES-128 Encryption")
        
        if encrypt_result.get("success"):
            encrypted_data = encrypt_result["encrypted_data"]
            print(f"Encrypted data (base64): {encrypted_data}")
            
            # Decrypt with AES-128
            print("\n🔓 Decrypting with AES-128...")
            response = requests.post(f"{BASE_URL}/tpm2/decrypt-aes",
                                   json={"context_file": "aes128_key.ctx",
                                         "encrypted_data": encrypted_data,
                                         "decrypted_file": "decrypted_aes128.bin"})
            decrypt_result = response.json()
            print_result(decrypt_result, "AES-128 Decryption")
            
            if decrypt_result.get("success"):
                decrypted_data = decrypt_result["decrypted_data"]
                original_data = base64.b64decode(decrypted_data).decode()
                print(f"✅ AES-128 Decryption successful!")
                print(f"Original data: {data_to_encrypt}")
                print(f"Decrypted data: {original_data}")
                print(f"Match: {data_to_encrypt == original_data}")
            else:
                print("❌ AES-128 Decryption failed!")
        else:
            print("❌ AES-128 Encryption failed!")
        
        # Step 5: Test AES-256 encryption/decryption
        print_step(5, "Testing AES-256 Encryption/Decryption")
        
        # Prepare different data for AES-256
        data_to_encrypt_256 = "Hello, AES-256 World! This is a longer message for testing."
        encoded_data_256 = base64.b64encode(data_to_encrypt_256.encode()).decode()
        print(f"Data to encrypt: {data_to_encrypt_256}")
        print(f"Base64 encoded: {encoded_data_256}")
        
        # Encrypt with AES-256
        print("\n🔐 Encrypting with AES-256...")
        response = requests.post(f"{BASE_URL}/tpm2/encrypt-aes",
                               json={"context_file": "aes256_key.ctx",
                                     "data": encoded_data_256,
                                     "encrypted_file": "encrypted_aes256.bin"})
        encrypt_result = response.json()
        print_result(encrypt_result, "AES-256 Encryption")
        
        if encrypt_result.get("success"):
            encrypted_data_256 = encrypt_result["encrypted_data"]
            print(f"Encrypted data (base64): {encrypted_data_256}")
            
            # Decrypt with AES-256
            print("\n🔓 Decrypting with AES-256...")
            response = requests.post(f"{BASE_URL}/tpm2/decrypt-aes",
                                   json={"context_file": "aes256_key.ctx",
                                         "encrypted_data": encrypted_data_256,
                                         "decrypted_file": "decrypted_aes256.bin"})
            decrypt_result = response.json()
            print_result(decrypt_result, "AES-256 Decryption")
            
            if decrypt_result.get("success"):
                decrypted_data_256 = decrypt_result["decrypted_data"]
                original_data_256 = base64.b64decode(decrypted_data_256).decode()
                print(f"✅ AES-256 Decryption successful!")
                print(f"Original data: {data_to_encrypt_256}")
                print(f"Decrypted data: {original_data_256}")
                print(f"Match: {data_to_encrypt_256 == original_data_256}")
            else:
                print("❌ AES-256 Decryption failed!")
        else:
            print("❌ AES-256 Encryption failed!")
        
        # Step 6: Create AES encrypted file store
        print_step(6, "Creating AES Encrypted File Store")
        response = requests.post(f"{BASE_URL}/tpm2/file-store-aes/create",
                               json={"context_file": "aes256_key.ctx",
                                     "store_name": "my_aes_secure_store.json"})
        result = response.json()
        print_result(result, "AES File Store Creation")
        
        if not result.get("success"):
            print("❌ Failed to create AES file store")
            return
        
        # Step 7: Store data in AES encrypted file store
        print_step(7, "Storing Data in AES Encrypted File Store")
        
        # Store various types of data
        test_data = {
            "string": "Hello AES World!",
            "number": 42,
            "boolean": True,
            "array": [1, 2, 3, 4, 5],
            "object": {
                "name": "AES Test",
                "version": "1.0",
                "features": ["encryption", "decryption", "file_store"]
            }
        }
        
        for key, value in test_data.items():
            print(f"\n📝 Storing {key}...")
            response = requests.post(f"{BASE_URL}/tpm2/file-store-aes/store",
                                   json={"context_file": "aes256_key.ctx",
                                         "store_name": "my_aes_secure_store.json",
                                         "key": key,
                                         "value": value})
            result = response.json()
            print(f"Stored {key}: {result.get('success', False)}")
        
        # Step 8: List keys in AES file store
        print_step(8, "Listing Keys in AES File Store")
        response = requests.post(f"{BASE_URL}/tpm2/file-store-aes/list-keys",
                               json={"context_file": "aes256_key.ctx",
                                     "store_name": "my_aes_secure_store.json"})
        result = response.json()
        print_result(result, "AES Key Listing")
        
        if result.get("success"):
            print(f"📋 Total keys stored: {result.get('total_keys', 0)}")
            print(f"🔑 Available keys: {', '.join(result.get('keys', []))}")
        
        # Step 9: Retrieve data from AES file store
        print_step(9, "Retrieving Data from AES File Store")
        
        for key in test_data.keys():
            print(f"\n📖 Retrieving {key}...")
            response = requests.post(f"{BASE_URL}/tpm2/file-store-aes/retrieve",
                                   json={"context_file": "aes256_key.ctx",
                                         "store_name": "my_aes_secure_store.json",
                                         "key": key})
            result = response.json()
            if result.get("success"):
                print(f"Retrieved {key}: {result['value']}")
            else:
                print(f"Failed to retrieve {key}: {result.get('error', 'Unknown error')}")
        
        # Step 10: Delete a key from AES file store
        print_step(10, "Deleting Key from AES File Store")
        print("\n🗑️ Deleting 'number' key...")
        response = requests.post(f"{BASE_URL}/tpm2/file-store-aes/delete",
                               json={"context_file": "aes256_key.ctx",
                                     "store_name": "my_aes_secure_store.json",
                                     "key": "number"})
        result = response.json()
        print_result(result, "Key Deletion")
        
        # Verify deletion
        print("\n📋 Listing keys after deletion...")
        response = requests.post(f"{BASE_URL}/tpm2/file-store-aes/list-keys",
                               json={"context_file": "aes256_key.ctx",
                                     "store_name": "my_aes_secure_store.json"})
        result = response.json()
        if result.get("success"):
            print(f"Remaining keys: {', '.join(result.get('keys', []))}")
        
        # Final summary
        print_step(11, "Demo Summary")
        print("✅ AES key demo completed successfully!")
        print("\n📊 What was demonstrated:")
        print("  • Created TPM2 primary key")
        print("  • Created AES-128 and AES-256 keys")
        print("  • Encrypted and decrypted data using AES-128")
        print("  • Encrypted and decrypted data using AES-256")
        print("  • Created AES encrypted file store")
        print("  • Stored various data types in AES encrypted store")
        print("  • Retrieved data from AES encrypted store")
        print("  • Listed keys in AES encrypted store")
        print("  • Deleted keys from AES encrypted store")
        print("\n🔐 All data was encrypted using TPM2 AES encryption!")
        print("📁 The encrypted file 'my_aes_secure_store.json' contains all your data securely")
        print("\n💡 AES advantages over RSA:")
        print("  • Faster encryption/decryption for bulk data")
        print("  • Smaller key sizes for same security level")
        print("  • Better performance for file operations")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main() 