# test_upload.py
import io

from fastapi.testclient import TestClient  # noqa: F401


def test_upload_model(client, auth_headers):
    """Test uploading a model zip file"""
    # Create a test zip file in memory
    test_file = io.BytesIO(b"fake zip file content")
    test_file.name = "test_model.zip"

    response = client.post(
        "/api/models/upload",
        headers=auth_headers,
        files={"file": ("test_model.zip", test_file, "application/zip")},
        data={
            "name": "Test Model",
            "description": "A test model for upload",
            "version": "1.0.0",
            "is_sensitive": "false"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Model uploaded successfully"
    assert "model_id" in data
    assert data["file_size"] == len(b"fake zip file content")


def test_upload_invalid_file_type(client, auth_headers):
    """Test uploading a non-zip file"""
    test_file = io.BytesIO(b"not a zip file")
    test_file.name = "test.txt"

    response = client.post(
        "/api/models/upload",
        headers=auth_headers,
        files={"file": ("test.txt", test_file, "text/plain")},
        data={"name": "Test Model"}
    )

    assert response.status_code == 400
    assert "Only .zip files are allowed" in response.json()["detail"]
