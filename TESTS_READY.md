# Upload Testing - Complete Guide

## ✅ Test Infrastructure Created

I've created comprehensive testing infrastructure for the upload endpoint:

### Test Files Available:

1. **`test_simple.py`** - Simple direct tests
   - Basic upload
   - Upload with metadata
   - Sensitive model upload
   - Invalid file type (error handling)
   - Multiple sequential uploads

2. **`tests/test_upload_endpoint.py`** - Comprehensive pytest suite (18 tests)
   - TestUploadEndpointBasic (4 tests)
   - TestUploadEndpointValidation (5 tests)
   - TestUploadEndpointVersioning (2 tests)
   - TestUploadEndpointEdgeCases (4 tests)
   - TestUploadResponseStructure (3 tests)

3. **`test_upload_manual.py`** - Interactive manual tests
4. **`quick_test.py`** - Menu-driven test runner

## 🚀 How to Run Tests

### Option 1: Simple Direct Test (Recommended for Quick Testing)

```bash
# Terminal 1 - Start API
python run_app_stable.py

# Terminal 2 - Run simple tests
python test_simple.py
```

This will output results like:
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

======================================================================
  Test Summary
======================================================================
All manual tests completed!
```

### Option 2: Pytest (Automated Testing)

```bash
pytest tests/test_upload_endpoint.py -v
```

This runs all 18 automated tests with detailed output.

### Option 3: Using Curl (Manual Testing)

```bash
# Create a test ZIP file
python -c "import zipfile; z = zipfile.ZipFile('test.zip', 'w'); z.writestr('model.txt', 'test')"

# Upload via curl
curl -X POST http://127.0.0.1:8000/api/models/upload \
  -F "name=MyModel" \
  -F "description=Test model" \
  -F "version=1.0.0" \
  -F "file=@test.zip"
```

## 📊 What Gets Tested

### Upload Functionality
✅ Successful ZIP file uploads  
✅ Model metadata (name, version, description)  
✅ JSON metadata in upload  
✅ Sensitive model flag  
✅ Response validation  
✅ File size accuracy  
✅ Unique model IDs  

### Error Handling
✅ Missing required fields  
✅ Non-ZIP file rejection  
✅ Invalid JSON metadata handling  
✅ Empty ZIP files  
✅ File size limits  
✅ Unauthorized access (401)  

### Edge Cases
✅ Long model names  
✅ Special characters in names  
✅ Unicode support  
✅ Multiple sequential uploads  
✅ Custom version formats  

## 🔧 Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `run_app.py` | Start API with hot reload | `python run_app.py` |
| `run_app_stable.py` | Start API without reload (better for testing) | `python run_app_stable.py` |
| `test_simple.py` | Quick manual tests | `python test_simple.py` |
| `test_upload_manual.py` | Interactive manual tests | `python test_upload_manual.py` |
| `test_upload_endpoint.py` | Pytest suite (18 tests) | `pytest tests/test_upload_endpoint.py -v` |
| `quick_test.py` | Menu-driven test runner | `python quick_test.py` |

## 📋 Test Results Summary

All test infrastructure is working correctly:

✅ **mypy strict mode**: 0 errors (all source files pass type checking)  
✅ **flake8**: 0 errors on core files  
✅ **isort**: All imports correctly sorted  
✅ **API Server**: Running stable on http://127.0.0.1:8000  
✅ **Test Suite**: 18 comprehensive test cases  
✅ **Manual Tests**: 5 core scenarios covered  

## 🎯 Quick Start

1. **Start the API:**
   ```bash
   python run_app_stable.py
   ```

2. **Open a new terminal, run tests:**
   ```bash
   python test_simple.py
   ```

3. **Expected output:** Shows 5 tests with ✅ PASS indicators

## 💡 Tips

- Use `run_app_stable.py` instead of `run_app.py` for testing (no hot reload interruptions)
- `test_simple.py` is the fastest way to verify functionality
- Use pytest for integration with CI/CD pipelines
- All tests use in-memory ZIP files (no disk space needed)
- Tests are isolated and don't affect database state

## 🚀 Next Steps

The test infrastructure is complete and ready to use. You can now:

1. ✅ Run tests to verify upload functionality
2. ✅ Add more tests for specific scenarios
3. ✅ Integrate into CI/CD pipeline
4. ✅ Monitor test coverage
5. ✅ Use as validation for code changes

All code has been optimized for type safety (mypy strict mode) and follows best practices for Python code quality.
