"""Debug script to see actual endpoint errors."""

import io
import os
import sys
import tempfile
from pathlib import Path

# Set testing mode
os.environ["TESTING"] = "true"

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.crud.app import app
from src.crud.upload.auth import get_current_user
from src.database import get_db
from src.database_models import Base, User, Artifact

# Create temporary database
temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
temp_db_path = temp_db.name
temp_db.close()

engine = create_engine(
    f"sqlite:///{temp_db_path}",
    connect_args={"check_same_thread": False}
)

Base.metadata.create_all(engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
test_db = TestingSessionLocal()

# Create test user
test_user = User(
    id=1,
    username="testuser",
    email="test@example.com",
    hashed_password="$2b$12$w9wxhMSXjJh/NLXdVJr8se0qR/0XNPq8U3QXzPzW4nH5gKmJsQJri",
    is_admin=False
)
test_db.add(test_user)
test_db.commit()

# Create test artifact
artifact = Artifact(
    id="test-artifact-001",
    name="Test Model",
    type="model",
    url="https://example.com/model",
    download_url="https://example.com/model/download",
    uploader_id=1
)
test_db.add(artifact)
test_db.commit()

# Override dependencies
def override_get_db():
    yield test_db

def override_get_current_user():
    return test_user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

# Create client
client = TestClient(app)

# Test batch upload
file_content = b"test model content"
files = [
    ("files", ("model.pth", io.BytesIO(file_content), "application/octet-stream"))
]

try:
    response = client.post(
        "/api/models/upload-batch",
        params={"artifact_id": "test-artifact-001"},
        files=files
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
test_db.close()
os.remove(temp_db_path)
