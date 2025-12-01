# Cleanup Function Verification

## Overview
The cleanup function `_cleanup_aes_blob_files()` is responsible for deleting `.pub` and `.priv` files via the TPM REST API after AES keys are created. These files contain the raw key blobs and should be removed from the working directory once the key is loaded into the TPM.

## Where Cleanup is Called

### Location: `_ensure_tpm_setup()` function
**File**: `anylog_utils.py`  
**Line**: ~1205-1210

```python
if created_new_aes_key and result and result.get("success"):
    _cleanup_aes_blob_files(
        encrypt_key_ctx,
        extra_paths=[result.get("public_file"), result.get("private_file")],
        base_url=base_url
    )
```

### When it's triggered:
1. **After AES key creation**: When `created_new_aes_key` is True and the key creation was successful
2. **Files to clean**: 
   - `anylog_encrypt_key_aes.pub` (derived from context file name)
   - `anylog_encrypt_key_aes.priv` (derived from context file name)
   - Additional files from API response (extra_paths)

## Cleanup Function Logic

### Step 1: List Files in Working Directory
- Calls `/tpm2/list-files` endpoint via REST API
- Shows what files currently exist
- Helps with debugging

### Step 2: Determine Files to Delete
- Extracts base name from context file (e.g., `"anylog_encrypt_key_aes"` from `"anylog_encrypt_key_aes.ctx"`)
- Creates filenames: `{base_name}.pub` and `{base_name}.priv`
- Adds any extra paths provided (from API response)
- Shows which files exist and which will be deleted

### Step 3: Delete Files via REST API
- For each file, calls `/tpm2/delete-file` endpoint
- Shows success/failure for each deletion
- Files that don't exist are considered successfully handled (already deleted)

## Verification Checklist

✅ **Cleanup is called after key creation**
   - Located in `_ensure_tpm_setup()` after successful AES key creation
   - Only called when `created_new_aes_key` is True

✅ **Correct files are identified**
   - Extracts base name from context file correctly
   - Creates `.pub` and `.priv` variants
   - Handles extra paths from API response

✅ **API endpoints work**
   - `/tpm2/list-files` - Lists files in working directory
   - `/tpm2/delete-file` - Deletes individual files
   - Both endpoints tested and working

✅ **Working directory is accessible**
   - Container working directory: `/opt/shared`
   - Mounted from host: `./shared_dir`
   - Files are visible and accessible

## Files That Should Be Deleted

When an AES key is created with context file `anylog_encrypt_key_aes.ctx`, the following files should be deleted:

1. `anylog_encrypt_key_aes.pub` - Public key blob
2. `anylog_encrypt_key_aes.priv` - Private key blob

These files are temporary - once the key is loaded into the TPM (stored in `.ctx` file), the blob files are no longer needed and should be removed.

## Testing

To test the cleanup function:

1. **Check files exist**: Use the list-files endpoint to see current files
2. **Trigger cleanup**: Call `_cleanup_aes_blob_files("anylog_encrypt_key_aes.ctx")`
3. **Verify deletion**: Check that .pub and .priv files are removed

### Test Script
Run `test_cleanup.py` to verify the cleanup logic and test with the actual API.

## Notes

- Cleanup is "best effort" - if deletion fails, it logs a warning but doesn't fail the overall operation
- Files that don't exist are considered successfully handled (already deleted)
- Cleanup happens automatically after key creation - no manual intervention needed

