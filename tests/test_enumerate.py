# """Test suite for the enumerate endpoint.
#
# Per OpenAPI v3.4.4 Section 3.2 - Model Enumeration Testing
#
# PURPOSE:
# Tests the GET /api/models/enumerate endpoint for listing registered models.
# Verifies pagination, filtering, and response structure.
#
# ENDPOINTS TESTED:
#     GET /api/models/enumerate
#     - Query Parameters: skip (default 0), limit (default 100, max 1000)
#     - Response: Array of ModelResponse objects
#     - HTTP Status: 200 OK
#     - Authentication: No authentication required (public endpoint)
#
# TEST CATEGORIES:
#
# 1. Empty/Single/Multiple Lists
#    - test_enumerate_empty_list: No models registered yet
#    - test_enumerate_single_model: One model after registration
#    - test_enumerate_multiple_models: Multiple models present
#
# 2. Pagination Support
#    - test_enumerate_with_pagination_skip: Offset parameter
#    - test_enumerate_with_limit: Limit parameter
#    - test_enumerate_max_limit_enforced: Limit capped at 1000
#
# 3. Response Structure
#    - test_enumerate_response_structure: All required fields present
#    - test_enumerate_returns_model_details: Metadata completeness
#
# 4. Edge Cases
#    - test_enumerate_negative_skip: Treats negative as 0
#    - test_enumerate_zero_limit: Returns empty array
#    - test_enumerate_no_auth_required: Public access works
#
# SCHEMA: ModelResponse
#     id: Integer (model ID)
#     name: String (model name)
#     description: Optional[String]
#     version: String
#     model_url: String (source URL)
#     artifact_type: String (model/dataset/code)
#     uploader_id: Integer
#     is_sensitive: Boolean
#     created_at: DateTime (ISO-8601)
#     updated_at: DateTime (ISO-8601)
#
# PAGINATION BEHAVIOR:
#     - Default: skip=0, limit=100
#     - Maximum limit: 1000 (enforced server-side)
#     - Invalid parameters: Treated as closest valid value
#
# ERROR RESPONSES:
#     - 422: Invalid query parameter types (non-integer skip/limit)
#     - 500: Server error accessing database
#
# SPEC SECTIONS REFERENCED:
#     Section 3.2: Model enumeration endpoint
#     Section 3.3: Pagination requirements
#
# RUN TESTS:
#     pytest tests/test_enumerate.py -v
# """

# from fastapi.testclient import TestClient


# class TestEnumerate:
#     """Test enumerate endpoint functionality."""

#     def test_enumerate_empty_list(self, client: TestClient) -> None:
#         """Test enumerate returns empty list when no models exist."""
#         response = client.get("/api/models/enumerate")
#         assert response.status_code == 200
#         data = response.json()
#         assert isinstance(data, list)
#         assert len(data) == 0

#     def test_enumerate_single_model(self, client: TestClient) -> None:
#         """Test enumerate returns single model after registration."""
#         # Register a model
#         register_response = client.post(
#             "/api/models/upload",
#             data={
#                 "name": "TestModel1",
#                 "model_url": "https://example.com/model1.zip",
#                 "description": "Test model",
#                 "version": "1.0.0",
#             },
#         )
#         assert register_response.status_code == 200
#         model_id = register_response.json()["model_id"]

#         # Enumerate models
#         response = client.get("/api/models/enumerate")
#         assert response.status_code == 200
#         data = response.json()
#         assert isinstance(data, list)
#         assert len(data) >= 1

#         # Find our registered model
#         model = next((m for m in data if m["id"] == model_id), None)
#         assert model is not None
#         assert model["name"] == "TestModel1"
#         assert model["model_url"] == "https://example.com/model1.zip"
#         assert model["description"] == "Test model"
#         assert model["version"] == "1.0.0"
#         assert model["artifact_type"] == "model"
#         assert model["is_sensitive"] is False

#     def test_enumerate_multiple_models(self, client: TestClient) -> None:
#         """Test enumerate returns multiple models."""
#         # Register multiple models
#         model_ids = []
#         for i in range(3):
#             response = client.post(
#                 "/api/models/upload",
#                 data={
#                     "name": f"TestModel{i}",
#                     "model_url": f"https://example.com/model{i}.zip",
#                     "version": "1.0.0",
#                 },
#             )
#             assert response.status_code == 200
#             model_ids.append(response.json()["model_id"])

#         # Enumerate models
#         response = client.get("/api/models/enumerate")
#         assert response.status_code == 200
#         data = response.json()
#         assert isinstance(data, list)
#         assert len(data) >= 3

#         # Verify all models are present
#         for model_id in model_ids:
#             assert any(m["id"] == model_id for m in data)

#     def test_enumerate_with_pagination_skip(self, client: TestClient) -> None:
#         """Test enumerate with skip parameter."""
#         # Register 5 models
#         for i in range(5):
#             client.post(
#                 "/api/models/upload",
#                 data={
#                     "name": f"PaginatedModel{i}",
#                     "model_url": f"https://example.com/pmodel{i}.zip",
#                 },
#             )

#         # Get first 2 models
#         response = client.get("/api/models/enumerate?skip=0&limit=2")
#         assert response.status_code == 200
#         data = response.json()
#         assert len(data) == 2

#         # Get next 2 models
#         response = client.get("/api/models/enumerate?skip=2&limit=2")
#         assert response.status_code == 200
#         data = response.json()
#         assert len(data) == 2

#     def test_enumerate_with_limit(self, client: TestClient) -> None:
#         """Test enumerate with limit parameter."""
#         # Register 10 models
#         for i in range(10):
#             client.post(
#                 "/api/models/upload",
#                 data={
#                     "name": f"LimitModel{i}",
#                     "model_url": f"https://example.com/lmodel{i}.zip",
#                 },
#             )

#         # Get with limit
#         response = client.get("/api/models/enumerate?limit=5")
#         assert response.status_code == 200
#         data = response.json()
#         assert len(data) <= 5

#     def test_enumerate_max_limit_enforced(self, client: TestClient) -> None:
#         """Test that enumerate enforces maximum limit."""
#         # Request with limit > 1000
#         response = client.get("/api/models/enumerate?limit=5000")
#         assert response.status_code == 200
#         data = response.json()
#         # Should be limited to 1000 or fewer available models
#         assert len(data) <= 1000

#     def test_enumerate_response_structure(self, client: TestClient) -> None:
#         """Test enumerate response has correct structure."""
#         # Register a model with all fields
#         client.post(
#             "/api/models/upload",
#             data={
#                 "name": "StructureTest",
#                 "model_url": "https://example.com/struct.zip",
#                 "description": "Structure test model",
#                 "version": "2.0.0",
#                 "artifact_type": "checkpoint",
#                 "is_sensitive": "true",
#             },
#         )

#         # Enumerate and check structure
#         response = client.get("/api/models/enumerate")
#         assert response.status_code == 200
#         data = response.json()
#         assert len(data) >= 1

#         model = data[0]
#         # Check required fields
#         required_fields = [
#             "id",
#             "name",
#             "description",
#             "version",
#             "model_url",
#             "artifact_type",
#             "uploader_id",
#             "is_sensitive",
#             "created_at",
#             "updated_at",
#         ]
#         for field in required_fields:
#             assert field in model, f"Missing field: {field}"

#     def test_enumerate_no_auth_required(self, client: TestClient) -> None:
#         """Test that enumerate endpoint does not require authentication."""
#         # Register a model first (requires auth)
#         client.post(
#             "/api/models/upload",
#             data={
#                 "name": "NoAuthTest",
#                 "model_url": "https://example.com/noauth.zip",
#             },
#         )

#         # Enumerate without auth should still work
#         response = client.get("/api/models/enumerate")
#         assert response.status_code == 200
#         data = response.json()
#         assert isinstance(data, list)

#     def test_enumerate_negative_skip(self, client: TestClient) -> None:
#         """Test enumerate handles negative skip by treating as 0."""
#         response = client.get("/api/models/enumerate?skip=-5")
#         assert response.status_code == 200
#         data = response.json()
#         assert isinstance(data, list)

#     def test_enumerate_zero_limit(self, client: TestClient) -> None:
#         """Test enumerate with zero limit."""
#         response = client.get("/api/models/enumerate?limit=0")
#         assert response.status_code == 200
#         data = response.json()
#         assert len(data) == 0

#     def test_enumerate_returns_model_details(self, client: TestClient) -> None:
#         """Test enumerate returns all model details."""
#         # Register model with metadata
#         response = client.post(
#             "/api/models/upload",
#             data={
#                 "name": "DetailedModel",
#                 "model_url": "https://huggingface.co/user/model",
#                 "description": "A detailed test model",
#                 "version": "3.1.4",
#                 "artifact_type": "weights",
#             },
#         )
#         assert response.status_code == 200
#         registered_model = response.json()

#         # Enumerate and verify details
#         response = client.get("/api/models/enumerate")
#         assert response.status_code == 200
#         data = response.json()

#         model = next((m for m in data if m["id"] == registered_model["model_id"]), None)
#         assert model is not None
#         assert model["name"] == "DetailedModel"
#         assert model["model_url"] == "https://huggingface.co/user/model"
#         assert model["description"] == "A detailed test model"
#         assert model["version"] == "3.1.4"
#         assert model["artifact_type"] == "weights"
