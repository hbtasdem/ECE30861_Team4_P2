# How to Run Upload Tests

## Quick Start (2 Terminal Setup)

### Terminal 1 - Start API with Test Mode

**On Windows (CMD):**
```bash
start_api_test.bat
```

**On Windows (PowerShell):**
```powershell
.\start_api_test.ps1
```

**On Linux/Mac:**
```bash
TEST_USER_ID=1 python run_app_stable.py
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Terminal 2 - Run Tests

**Run simple tests:**
```bash
python test_simple.py
```

**Expected Output:**
```
======================================================================
  Upload Endpoint Tests
======================================================================

✅ API running: {'status': 'ok'}

----------------------------------------------------------------------
TEST 1: Basic Upload
----------------------------------------------------------------------
Status: 200
✅ SUCCESS
   Model ID: 1
   File Size: 245 bytes

----------------------------------------------------------------------
TEST 2: Upload with Metadata
----------------------------------------------------------------------
Status: 200
✅ SUCCESS - Model with metadata uploaded

----------------------------------------------------------------------
TEST 3: Sensitive Model Upload
----------------------------------------------------------------------
Status: 200
✅ SUCCESS - Sensitive model uploaded

----------------------------------------------------------------------
TEST 4: Invalid File Type (should fail)
----------------------------------------------------------------------
Status: 400
✅ CORRECT - Rejected non-ZIP file
   Detail: Only .zip files are allowed

----------------------------------------------------------------------
TEST 5: Multiple Sequential Uploads
----------------------------------------------------------------------
Status: 200
✅ SUCCESS - Uploaded 3 models
   IDs: [1, 2, 3]
```

## Files Provided

| File | Purpose |
|------|---------|
| `start_api_test.bat` | Start API with test mode (Windows CMD) |
| `start_api_test.ps1` | Start API with test mode (PowerShell) |
| `run_app_stable.py` | Run API without hot reload |
| `test_simple.py` | Run upload tests (5 scenarios) |

## Test Scenarios Covered

✅ **TEST 1: Basic Upload** - Upload a ZIP file with model metadata  
✅ **TEST 2: Upload with Metadata** - Add JSON metadata to upload  
✅ **TEST 3: Sensitive Model** - Mark model as sensitive  
✅ **TEST 4: Invalid File Type** - Verify non-ZIP files are rejected  
✅ **TEST 5: Multiple Uploads** - Upload 3 models sequentially  

## Troubleshooting

**"API running: 401 Not authenticated"**
- Make sure API was started with `start_api_test.bat` or `start_api_test.ps1`
- Check that `TEST_USER_ID=1` environment variable is set

**"Cannot connect to API"**
- Verify Terminal 1 shows "Uvicorn running on http://127.0.0.1:8000"
- Make sure Terminal 1 doesn't have any errors

**Tests still showing 401 errors**
- Kill any existing Python processes: `taskkill /F /IM python.exe`
- Restart API using the startup scripts above

## What Tests Verify

- ✅ File upload works correctly
- ✅ Model metadata is saved
- ✅ File size is reported correctly
- ✅ Non-ZIP files are rejected
- ✅ Sequential uploads work
- ✅ API authentication works
- ✅ Response format is correct

## Next Steps

1. Open Terminal 1, run: `start_api_test.bat`
2. Open Terminal 2, run: `python test_simple.py`
3. View test results

That's it! All 5 tests should pass with ✅ indicators.
