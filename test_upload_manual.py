#!/usr/bin/env python
"""
Manual testing script for the upload endpoint.
Makes it easy to test the upload API without using complex curl commands.

Usage:
    python test_upload_manual.py              # Run all demo tests
    python test_upload_manual.py basic        # Run basic upload test
    python test_upload_manual.py validation   # Run validation tests
    python test_upload_manual.py metadata     # Run metadata tests
"""

import json
import sys
import time
import zipfile
from io import BytesIO
from pathlib import Path

import requests


# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_ENDPOINT = f"{BASE_URL}/api/models/upload"


def create_test_zip(name: str = "test_model") -> BytesIO:
    """Create a simple ZIP file for testing."""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("model.txt", f"This is a test model: {name}\n")
        zf.writestr("config.json", json.dumps({"name": name, "version": "1.0.0"}))
    zip_buffer.seek(0)
    return zip_buffer


def print_header(title: str) -> None:
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_result(test_name: str, success: bool, message: str = "", response_data: dict | None = None) -> None:
    """Print test result with formatting."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\n{status} | {test_name}")
    if message:
        print(f"        {message}")
    if response_data:
        print(f"        Response: {json.dumps(response_data, indent=2)}")


def test_basic_upload() -> None:
    """Test basic successful upload."""
    print_header("TEST 1: Basic Upload")

    try:
        zip_file = create_test_zip("BasicTestModel")
        response = requests.post(
            API_ENDPOINT,
            data={
                "name": "BasicTestModel",
                "description": "A basic test model",
                "version": "1.0.0",
            },
            files={"file": ("model.zip", zip_file, "application/zip")},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print_result(
                "Basic Upload",
                True,
                f"Model ID: {data['model_id']}, File Size: {data['file_size']} bytes",
                data,
            )
            return True
        else:
            print_result("Basic Upload", False, f"Status: {response.status_code}", response.json())
            return False
    except Exception as e:
        print_result("Basic Upload", False, f"Error: {str(e)}")
        return False


def test_upload_with_metadata() -> None:
    """Test upload with JSON metadata."""
    print_header("TEST 2: Upload with Metadata")

    try:
        metadata = {
            "framework": "PyTorch",
            "task": "image_classification",
            "accuracy": 0.95,
            "training_date": "2024-11-02",
        }

        zip_file = create_test_zip("MetadataTestModel")
        response = requests.post(
            API_ENDPOINT,
            data={
                "name": "MetadataTestModel",
                "description": "Model with metadata",
                "metadata": json.dumps(metadata),
            },
            files={"file": ("model.zip", zip_file, "application/zip")},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print_result(
                "Upload with Metadata",
                True,
                f"Model ID: {data['model_id']}, Metadata added",
                data,
            )
            return True
        else:
            print_result("Upload with Metadata", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_result("Upload with Metadata", False, f"Error: {str(e)}")
        return False


def test_upload_sensitive_model() -> None:
    """Test uploading a sensitive model."""
    print_header("TEST 3: Upload Sensitive Model")

    try:
        zip_file = create_test_zip("SensitiveModel")
        response = requests.post(
            API_ENDPOINT,
            data={
                "name": "SensitiveModel",
                "description": "A sensitive model",
                "is_sensitive": True,
            },
            files={"file": ("model.zip", zip_file, "application/zip")},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print_result(
                "Sensitive Model Upload",
                True,
                f"Model ID: {data['model_id']}, Marked as sensitive",
                data,
            )
            return True
        else:
            print_result("Sensitive Model Upload", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_result("Sensitive Model Upload", False, f"Error: {str(e)}")
        return False


def test_validation_missing_name() -> None:
    """Test validation: missing model name."""
    print_header("TEST 4: Validation - Missing Name")

    try:
        zip_file = create_test_zip("NoNameModel")
        response = requests.post(
            API_ENDPOINT,
            data={},  # No name provided
            files={"file": ("model.zip", zip_file, "application/zip")},
            timeout=10,
        )

        if response.status_code == 422:
            print_result(
                "Missing Name Validation",
                True,
                "Correctly rejected request (Status 422)",
            )
            return True
        else:
            print_result(
                "Missing Name Validation",
                False,
                f"Expected 422, got {response.status_code}",
            )
            return False
    except Exception as e:
        print_result("Missing Name Validation", False, f"Error: {str(e)}")
        return False


def test_validation_non_zip() -> None:
    """Test validation: non-ZIP file."""
    print_header("TEST 5: Validation - Non-ZIP File")

    try:
        response = requests.post(
            API_ENDPOINT,
            data={"name": "BadFileModel"},
            files={"file": ("model.txt", BytesIO(b"This is not a ZIP file"), "text/plain")},
            timeout=10,
        )

        if response.status_code == 400:
            data = response.json()
            if "Only .zip files are allowed" in data.get("detail", ""):
                print_result(
                    "Non-ZIP Validation",
                    True,
                    "Correctly rejected non-ZIP file",
                    {"detail": data["detail"]},
                )
                return True
        print_result(
            "Non-ZIP Validation",
            False,
            f"Expected 400 with ZIP rejection, got {response.status_code}",
        )
        return False
    except Exception as e:
        print_result("Non-ZIP Validation", False, f"Error: {str(e)}")
        return False


def test_upload_multiple_sequential() -> None:
    """Test uploading multiple models sequentially."""
    print_header("TEST 6: Multiple Sequential Uploads")

    try:
        model_ids = []
        for i in range(3):
            zip_file = create_test_zip(f"SequentialModel{i}")
            response = requests.post(
                API_ENDPOINT,
                data={"name": f"SequentialModel{i}", "version": f"1.0.{i}"},
                files={"file": ("model.zip", zip_file, "application/zip")},
                timeout=10,
            )
            if response.status_code == 200:
                model_ids.append(response.json()["model_id"])
            else:
                print_result(f"Upload #{i+1}", False, f"Status: {response.status_code}")
                return False

        if len(set(model_ids)) == 3:
            print_result(
                "Sequential Uploads",
                True,
                f"Successfully uploaded 3 models with IDs: {model_ids}",
                {"model_ids": model_ids},
            )
            return True
        else:
            print_result("Sequential Uploads", False, "Model IDs not unique")
            return False
    except Exception as e:
        print_result("Sequential Uploads", False, f"Error: {str(e)}")
        return False


def test_special_characters() -> None:
    """Test upload with special characters in model name."""
    print_header("TEST 7: Special Characters in Name")

    try:
        special_name = "Model-v2.0_Test@2024!#123"
        zip_file = create_test_zip(special_name)
        response = requests.post(
            API_ENDPOINT,
            data={"name": special_name},
            files={"file": ("model.zip", zip_file, "application/zip")},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print_result(
                "Special Characters",
                True,
                f"Model ID: {data['model_id']}, Name accepted",
                data,
            )
            return True
        else:
            print_result("Special Characters", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_result("Special Characters", False, f"Error: {str(e)}")
        return False


def run_test_suite(test_type: str = "all") -> None:
    """Run tests based on type."""
    print("\n" + "=" * 70)
    print("  Upload Endpoint Test Suite")
    print("=" * 70)

    tests_map = {
        "basic": [test_basic_upload],
        "metadata": [test_upload_with_metadata, test_upload_sensitive_model],
        "validation": [test_validation_missing_name, test_validation_non_zip],
        "sequential": [test_upload_multiple_sequential],
        "special": [test_special_characters],
        "all": [
            test_basic_upload,
            test_upload_with_metadata,
            test_upload_sensitive_model,
            test_validation_missing_name,
            test_validation_non_zip,
            test_upload_multiple_sequential,
            test_special_characters,
        ],
    }

    tests = tests_map.get(test_type, tests_map["all"])

    print(f"\nRunning {len(tests)} test(s)...\n")
    start_time = time.time()

    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
            time.sleep(0.5)  # Small delay between tests
        except Exception as e:
            print(f"\n❌ Exception in {test.__name__}: {str(e)}")
            results.append((test.__name__, False))

    # Summary
    elapsed = time.time() - start_time
    passed = sum(1 for _, result in results if result)
    total = len(results)

    print("\n" + "=" * 70)
    print("  Test Summary")
    print("=" * 70)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {total - passed} ❌")
    print(f"Time: {elapsed:.2f}s")
    print("=" * 70 + "\n")

    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    print("\n📋 Checking if API is running at", BASE_URL)
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print("✅ API is running!\n")
        else:
            print(f"⚠️  API returned status {response.status_code}")
            print("   Make sure to run: python run_app.py\n")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API!")
        print("   Start the API with: python run_app.py\n")
        sys.exit(1)

    # Get test type from command line
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"

    if test_type not in ["all", "basic", "metadata", "validation", "sequential", "special"]:
        print(f"Unknown test type: {test_type}")
        print(
            "Available: all, basic, metadata, validation, sequential, special"
        )
        sys.exit(1)

    run_test_suite(test_type)
