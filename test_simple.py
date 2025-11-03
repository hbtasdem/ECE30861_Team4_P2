#!/usr/bin/env python
"""Simple test runner to demonstrate upload functionality"""

import io
import json
import os
import zipfile

import requests

# Set test user via environment variable BEFORE making requests
os.environ["TEST_USER_ID"] = "1"

BASE_URL = "http://127.0.0.1:8000"


def create_zip(name: str) -> io.BytesIO:
    """Create a test ZIP file"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("model.txt", f"Model: {name}")
    buf.seek(0)
    return buf


def main() -> None:
    """Run manual tests"""
    print("\n" + "="*70)
    print("  Upload Endpoint Tests")
    print("="*70)

    # Check API is running
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=2)
        print(f"\n✅ API running: {resp.json()}")
    except Exception as e:
        print(f"\n❌ API not running: {e}")
        return

    # Test 1: Basic upload
    print("\n" + "-"*70)
    print("TEST 1: Basic Upload")
    print("-"*70)
    try:
        data = {
            "name": "TestModel1",
            "description": "A test model",
            "version": "1.0.0",
        }
        files = {"file": ("model.zip", create_zip("TestModel1"), "application/zip")}
        resp = requests.post(f"{BASE_URL}/api/models/upload", data=data, files=files)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print("✅ SUCCESS")
            print(f"   Model ID: {result['model_id']}")
            print(f"   File Size: {result['file_size']} bytes")
        else:
            print(f"❌ FAILED: {resp.json()}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    # Test 2: Upload with metadata
    print("\n" + "-"*70)
    print("TEST 2: Upload with Metadata")
    print("-"*70)
    try:
        metadata = {"framework": "PyTorch", "accuracy": 0.95}
        data = {
            "name": "TestModel2",
            "metadata": json.dumps(metadata),
        }
        files = {"file": ("model.zip", create_zip("TestModel2"), "application/zip")}
        resp = requests.post(f"{BASE_URL}/api/models/upload", data=data, files=files)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("✅ SUCCESS - Model with metadata uploaded")
        else:
            print(f"❌ FAILED: {resp.json()}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

    # Test 3: Sensitive model
    print("\n" + "-"*70)
    print("TEST 3: Sensitive Model Upload")
    print("-"*70)
    try:
        data = {
            "name": "SensitiveModel",
            "is_sensitive": "true",
        }
        files = {"file": ("model.zip", create_zip("SensitiveModel"), "application/zip")}
        resp = requests.post(f"{BASE_URL}/api/models/upload", data=data, files=files)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("✅ SUCCESS - Sensitive model uploaded")
        else:
            print(f"❌ FAILED: {resp.json()}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

    # Test 4: Invalid file type
    print("\n" + "-"*70)
    print("TEST 4: Invalid File Type (should fail)")
    print("-"*70)
    try:
        data = {"name": "BadFile"}
        files = {"file": ("model.txt", io.BytesIO(b"not a zip"), "text/plain")}
        resp = requests.post(f"{BASE_URL}/api/models/upload", data=data, files=files)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 400:
            print("✅ CORRECT - Rejected non-ZIP file")
            print(f"   Detail: {resp.json()['detail']}")
        else:
            print("❌ FAILED - Should return 400")
    except Exception as e:
        print(f"❌ ERROR: {e}")

    # Test 5: Multiple uploads
    print("\n" + "-"*70)
    print("TEST 5: Multiple Sequential Uploads")
    print("-"*70)
    try:
        ids = []
        for i in range(3):
            data = {"name": f"SequentialModel{i}"}
            files = {"file": ("model.zip", create_zip(f"SequentialModel{i}"), "application/zip")}
            resp = requests.post(f"{BASE_URL}/api/models/upload", data=data, files=files)
            if resp.status_code == 200:
                ids.append(resp.json()["model_id"])

        print(f"Status: {resp.status_code}")
        if len(ids) == 3 and len(set(ids)) == 3:
            print("✅ SUCCESS - Uploaded 3 models")
            print(f"   IDs: {ids}")
        else:
            print(f"❌ FAILED - Expected 3 unique IDs, got {ids}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

    print("\n" + "="*70)
    print("  Test Summary")
    print("="*70)
    print("All manual tests completed!\n")


if __name__ == "__main__":
    main()
