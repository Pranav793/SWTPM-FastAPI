#!/usr/bin/env python3
"""
Script to clear all TPM data from shared_dir, tpm_state, and key_backups.
WARNING: This will delete all keys, backups, and TPM state!
"""

import os
import shutil
from pathlib import Path

SHARED_DIR = Path("shared_dir")
TPM_STATE_DIR = SHARED_DIR / "tpm_state"
KEY_BACKUPS_DIR = SHARED_DIR / "key_backups"

def clear_directory(directory: Path, description: str):
    """Clear all files in a directory, keeping the directory structure."""
    if not directory.exists():
        print(f"  ⚠️  {directory}/ does not exist, skipping...")
        return
    
    deleted_count = 0
    
    # Delete all files in the directory
    for item in directory.iterdir():
        try:
            if item.is_file():
                item.unlink()
                deleted_count += 1
            elif item.is_dir():
                shutil.rmtree(item)
                deleted_count += 1
        except Exception as e:
            print(f"  ⚠️  Warning: Could not delete {item}: {e}")
    
    if deleted_count > 0:
        print(f"  ✓ Cleared {description} ({deleted_count} items)")
    else:
        print(f"  ✓ {description} is already empty")

def main():
    print("=" * 50)
    print("TPM Data Cleanup Script")
    print("=" * 50)
    print()
    print("This will delete:")
    print(f"  - All files in {SHARED_DIR}/")
    print(f"  - All files in {TPM_STATE_DIR}/")
    print(f"  - All files in {KEY_BACKUPS_DIR}/")
    print()
    print("⚠️  WARNING: This will permanently delete all TPM keys, backups, and state!")
    print()
    
    # Ask for confirmation
    confirm = input("Are you sure you want to continue? (type 'yes' to confirm): ")
    
    if confirm != "yes":
        print("Cleanup cancelled.")
        return
    
    print()
    print("Starting cleanup...")
    print()
    
    # Clear shared_dir (keep directory structure, remove all files)
    print(f"Clearing {SHARED_DIR}/...")
    if SHARED_DIR.exists():
        # Delete all files in shared_dir root (not subdirectories)
        for item in SHARED_DIR.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                except Exception as e:
                    print(f"  ⚠️  Warning: Could not delete {item}: {e}")
        print(f"  ✓ Cleared files in {SHARED_DIR}/")
    else:
        print(f"  ⚠️  {SHARED_DIR}/ does not exist, skipping...")
    
    # Clear tpm_state directory
    print(f"Clearing {TPM_STATE_DIR}/...")
    if TPM_STATE_DIR.exists():
        for item in TPM_STATE_DIR.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                print(f"  ⚠️  Warning: Could not delete {item}: {e}")
        print(f"  ✓ Cleared {TPM_STATE_DIR}/")
    else:
        print(f"  ⚠️  {TPM_STATE_DIR}/ does not exist, skipping...")
    
    # Clear key_backups directory
    print(f"Clearing {KEY_BACKUPS_DIR}/...")
    if KEY_BACKUPS_DIR.exists():
        for item in KEY_BACKUPS_DIR.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                print(f"  ⚠️  Warning: Could not delete {item}: {e}")
        print(f"  ✓ Cleared {KEY_BACKUPS_DIR}/")
    else:
        print(f"  ⚠️  {KEY_BACKUPS_DIR}/ does not exist, skipping...")
    
    print()
    print("=" * 50)
    print("✓ Cleanup complete!")
    print("=" * 50)
    print()
    print("All TPM data has been cleared.")
    print("Directories are preserved but empty.")
    print()
    print("To recreate everything, restart the TPM2 API and create new keys.")

if __name__ == "__main__":
    main()



