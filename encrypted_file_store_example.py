#!/usr/bin/env python3
"""
Encrypted File Store Example - Complete workflow demonstration

This script demonstrates how to use the TPM2 encrypted file store feature:
1. Create a primary key
2. Create an encryption key
3. Create an encrypted file store
4. Store and retrieve key-value pairs
5. List keys and delete entries

Usage:
    python3 encrypted_file_store_example.py
"""

import base64
import requests
import json
import time


def trim_at_slash(s):
    """
    If s contains "/", return substring before the first "/".
    Otherwise, return s unchanged.
    """
    idx = s.find("/")
    if idx != -1:
        return s[:idx]
    return s




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
    print("🚀 TPM2 Encrypted File Store Demo")
    print("This demo will create an encrypted file store and demonstrate all operations")
    
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
        
        # Step 2: Create encryption key
        print_step(2, "Creating Encryption Key")
        response = requests.post(f"{BASE_URL}/tpm2/create-key",
                               json={"parent_context": "primary.ctx", 
                                     "key_type": "rsa", 
                                     "public_file": "encrypt_key.pub", 
                                     "private_file": "encrypt_key.priv"})
        result = response.json()
        print_result(result, "Encryption Key Creation")
        
        if not result.get("success"):
            print("❌ Failed to create encryption key")
            return
        
        # Step 3: Load encryption key
        print_step(3, "Loading Encryption Key")
        response = requests.post(f"{BASE_URL}/tpm2/load-key",
                               json={"parent_context": "primary.ctx",
                                     "public_file": "encrypt_key.pub",
                                     "private_file": "encrypt_key.priv",
                                     "context_file": "encrypt_key.ctx"})
        result = response.json()
        print_result(result, "Key Loading")
        
        if not result.get("success"):
            print("❌ Failed to load encryption key")
            return
        
        # Step 4: Create encrypted file store
        print_step(4, "Creating Encrypted File Store")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/create",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json"})
        result = response.json()
        print_result(result, "File Store Creation")
        
        if not result.get("success"):
            print("❌ Failed to create file store")
            return
        
        # Step 5: Store various types of data
        print_step(5, "Storing Key-Value Pairs")
        
        # Store a simple string
        print("\n📝 Storing string value...")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/store",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json",
                                     "key": "username",
                                     "value": "john_doe"})
        result = response.json()
        print_result(result, "String Storage")
        
        # Store a number
        print("\n📝 Storing numeric value...")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/store",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json",
                                     "key": "age",
                                     "value": 30})
        result = response.json()
        print_result(result, "Number Storage")
        
        # Store a complex object
        print("\n📝 Storing complex object...")
        user_profile = {
            "name": "John Doe",
            "email": "john@example.com",
            "preferences": {
                "theme": "dark",
                "notifications": True,
                "language": "en"
            },
            "metadata": {
                "created": "2024-01-01",
                "last_login": "2024-01-15"
            }
        }
        response = requests.post(f"{BASE_URL}/tpm2/file-store/store",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json",
                                     "key": "user_profile",
                                     "value": user_profile})
        result = response.json()
        print_result(result, "Object Storage")
        
        # Store an array
        print("\n📝 Storing array...")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/store",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json",
                                     "key": "favorite_colors",
                                     "value": ["blue", "green", "red"]})
        result = response.json()
        print_result(result, "Array Storage")
        
        # Step 6: List all keys
        print_step(6, "Listing All Keys")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/list-keys",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json"})
        result = response.json()
        print_result(result, "Key Listing")
        
        if result.get("success"):
            print(f"📋 Total keys stored: {result.get('total_keys', 0)}")
            print(f"🔑 Available keys: {', '.join(result.get('keys', []))}")
        
        # Step 7: Retrieve values
        print_step(7, "Retrieving Values")
        
        # Retrieve string
        print("\n📖 Retrieving string value...")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/retrieve",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json",
                                     "key": "username"})
        result = response.json()
        print_result(result, "String Retrieval")
        
        # Retrieve number
        print("\n📖 Retrieving numeric value...")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/retrieve",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json",
                                     "key": "age"})
        result = response.json()
        print_result(result, "Number Retrieval")
        
        # Retrieve complex object
        print("\n📖 Retrieving complex object...")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/retrieve",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json",
                                     "key": "user_profile"})
        result = response.json()
        print_result(result, "Object Retrieval")
        
        # Step 8: Update existing value
        print_step(8, "Updating Existing Value")
        print("\n📝 Updating age value...")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/store",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json",
                                     "key": "age",
                                     "value": 31})  # Updated age
        result = response.json()
        print_result(result, "Value Update")
        
        # Verify the update
        print("\n📖 Verifying updated value...")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/retrieve",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json",
                                     "key": "age"})
        result = response.json()
        print_result(result, "Updated Value Verification")
        
        # Step 9: Delete a key
        print_step(9, "Deleting Key-Value Pair")
        print("\n🗑️ Deleting 'favorite_colors' key...")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/delete",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json",
                                     "key": "favorite_colors"})
        result = response.json()
        print_result(result, "Key Deletion")
        
        # Verify deletion by listing keys again
        print("\n📋 Listing keys after deletion...")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/list-keys",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json"})
        result = response.json()
        print_result(result, "Updated Key Listing")
        
        # Step 10: Try to retrieve deleted key (should fail)
        print_step(10, "Attempting to Retrieve Deleted Key")
        response = requests.post(f"{BASE_URL}/tpm2/file-store/retrieve",
                               json={"context_file": "encrypt_key.ctx",
                                     "store_name": "my_secure_store.json",
                                     "key": "favorite_colors"})
        result = response.json()
        print_result(result, "Deleted Key Retrieval (Expected to Fail)")
        
        # Final summary
        print_step(11, "Demo Summary")
        print("✅ Encrypted file store demo completed successfully!")
        print("\n📊 What was demonstrated:")
        print("  • Created TPM2 primary and encryption keys")
        print("  • Created an encrypted file store")
        print("  • Stored various data types (string, number, object, array)")
        print("  • Retrieved stored values")
        print("  • Updated existing values")
        print("  • Listed all keys")
        print("  • Deleted keys")
        print("  • Proper error handling for missing keys")
        print("\n🔐 All data was encrypted using TPM2 RSA encryption!")
        print("📁 The encrypted file 'my_secure_store.json' contains all your data securely")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main() 