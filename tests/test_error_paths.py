"""Tests for error paths and edge cases to improve code coverage."""

from fastapi.testclient import TestClient

from src.crud.app import app

client = TestClient(app)


class TestAuthenticationErrors:
    """Test authentication error scenarios."""

    def test_authenticate_missing_user(self):
        """Test authentication with missing user field."""
        response = client.put(
            "/authenticate",
            json={"secret": {"password": "test"}},  # Missing user
        )
        assert response.status_code == 422  # Validation error

    def test_authenticate_missing_password(self):
        """Test authentication with missing password."""
        response = client.put(
            "/authenticate",
            json={"user": {"name": "test", "is_admin": False}},  # Missing secret
        )
        assert response.status_code == 422

    def test_authenticate_invalid_credentials(self):
        """Test authentication with invalid username/password."""
        response = client.put(
            "/authenticate",
            json={
                "user": {"name": "invalid_user", "is_admin": False},
                "secret": {"password": "wrong_password"},
            },
        )
        assert response.status_code == 401

    def test_register_duplicate_user(self):
        """Test registering a user that already exists."""
        import time
        unique_name = f"duplicate_user_{int(time.time() * 1000)}"

        # First registration
        response = client.post(
            "/register",
            json={
                "user": {"name": unique_name, "is_admin": False},
                "secret": {"password": "test123"},
            },
        )
        assert response.status_code in [200, 201, 409]  # 409 if user already exists

        # Attempt duplicate with same unique name
        response = client.post(
            "/register",
            json={
                "user": {"name": unique_name, "is_admin": False},
                "secret": {"password": "test123"},
            },
        )
        assert response.status_code in [400, 409]  # Conflict or bad request


class TestArtifactEndpointErrors:
    """Test artifact endpoint error scenarios."""

    def test_enumerate_missing_auth_header(self):
        """Test POST /artifacts without X-Authorization header."""
        response = client.post(
            "/artifacts",
            json=[{"name": "*"}],
        )
        assert response.status_code == 403

    def test_enumerate_invalid_auth_token(self):
        """Test POST /artifacts with invalid token."""
        response = client.post(
            "/artifacts",
            json=[{"name": "*"}],
            headers={"X-Authorization": "invalid_token"},
        )
        assert response.status_code == 403

    def test_create_artifact_missing_auth(self):
        """Test POST /artifact/{type} without auth."""
        response = client.post(
            "/artifact/model",
            json={"url": "https://example.com/model.tar.gz"},
        )
        assert response.status_code == 403

    def test_create_artifact_invalid_url(self):
        """Test creating artifact with invalid URL format."""
        # Get a valid token first
        auth_response = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": True},
                "secret": {
                    "password": "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
                },
            },
        )
        token = auth_response.json()["token"]

        response = client.post(
            "/artifact/model",
            json={"url": "not_a_valid_url"},
            headers={"X-Authorization": token},
        )
        assert response.status_code in [400, 422]

    def test_get_artifact_missing_auth(self):
        """Test GET /artifacts/{type}/{id} without auth."""
        response = client.get("/artifacts/model/123")
        assert response.status_code == 403

    def test_get_nonexistent_artifact(self):
        """Test getting an artifact that doesn't exist."""
        auth_response = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": True},
                "secret": {
                    "password": "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
                },
            },
        )
        token = auth_response.json()["token"]

        response = client.get(
            "/artifacts/model/nonexistent_id",
            headers={"X-Authorization": token},
        )
        # Per spec: 400 for invalid ID format, 404 for non-existent artifact
        assert response.status_code in [400, 404]


class TestRatingEndpointErrors:
    """Test rating endpoint error scenarios."""

    def test_rate_artifact_missing_auth(self):
        """Test GET /artifact/model/{id}/rate without auth."""
        response = client.get("/artifact/model/123/rate")
        assert response.status_code == 403

    def test_rate_nonexistent_artifact(self):
        """Test rating an artifact that doesn't exist - S3 errors are expected."""
        auth_response = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": True},
                "secret": {
                    "password": "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
                },
            },
        )
        token = auth_response.json()["token"]

        # S3 may throw AccessDenied for non-existent artifacts
        # This is expected behavior - we just verify the endpoint exists and requires auth
        try:
            response = client.get(
                "/artifact/model/nonexistent_id/rate",
                headers={"X-Authorization": token},
            )
            # If we get here, accept 404 or 500
            assert response.status_code in [404, 500]
        except Exception as e:
            # S3 access errors or missing credentials are acceptable - the endpoint is protected and called
            assert (
                "AccessDenied" in str(e)
                or "Access Denied" in str(e)
                or "Unable to locate credentials" in str(e)
                or "NoCredentialsError" in str(e)
            )


class TestRegexSearchErrors:
    """Test regex search error scenarios."""

    def test_regex_search_missing_auth(self):
        """Test POST /artifact/byRegEx without auth."""
        response = client.post(
            "/artifact/byRegEx",
            json={"regex": ".*test.*"},
        )
        # Validation error (422) comes before auth check in FastAPI
        assert response.status_code in [403, 422]

    def test_regex_search_invalid_regex(self):
        """Test regex search with invalid regex pattern."""
        auth_response = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": True},
                "secret": {
                    "password": "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
                },
            },
        )
        token = auth_response.json()["token"]

        response = client.post(
            "/artifact/byRegEx",
            json={"regex": "[invalid(regex"},
            headers={"X-Authorization": token},
        )
        # FastAPI validation (422) or custom validation error (400)
        assert response.status_code in [400, 422]

    def test_regex_search_missing_regex_field(self):
        """Test regex search without regex field."""
        auth_response = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": True},
                "secret": {
                    "password": "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
                },
            },
        )
        token = auth_response.json()["token"]

        response = client.post(
            "/artifact/byRegEx",
            json={},  # Missing regex field
            headers={"X-Authorization": token},
        )
        assert response.status_code == 422


class TestLicenseCheckErrors:
    """Test license check endpoint error scenarios."""

    def test_license_check_missing_auth(self):
        """Test POST /artifact/model/{id}/license-check without auth."""
        response = client.post(
            "/artifact/model/123/license-check",
            json={"github_url": "https://github.com/example/repo"},
        )
        assert response.status_code == 403

    def test_license_check_missing_github_url(self):
        """Test license check without github_url field."""
        auth_response = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": True},
                "secret": {
                    "password": "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
                },
            },
        )
        token = auth_response.json()["token"]

        response = client.post(
            "/artifact/model/123/license-check",
            json={},  # Missing github_url
            headers={"X-Authorization": token},
        )
        # Validation error expected (422 is per FastAPI validation)
        assert response.status_code in [400, 422]


class TestHealthEndpoints:
    """Test health endpoints."""

    def test_health_no_auth_required(self):
        """Test that /health doesn't require authentication."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_components_with_valid_window(self):
        """Test /health/components with valid window parameter."""
        response = client.get("/health/components?windowMinutes=60")
        assert response.status_code == 200
        data = response.json()
        assert "components" in data
        assert "generated_at" in data

    def test_health_components_with_timeline(self):
        """Test /health/components with timeline included."""
        response = client.get(
            "/health/components?windowMinutes=60&includeTimeline=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert "components" in data

    def test_health_components_invalid_window(self):
        """Test /health/components with invalid window (too small) - FastAPI validates with 422."""
        response = client.get("/health/components?windowMinutes=2")
        # FastAPI Query validation returns 422 for values outside ge=5, le=1440
        assert response.status_code == 422


class TestCostEndpoint:
    """Test cost calculation endpoint."""

    def test_cost_missing_auth(self):
        """Test GET /artifact/{type}/{id}/cost without auth."""
        response = client.get("/artifact/model/123/cost")
        assert response.status_code == 403

    def test_cost_nonexistent_artifact(self):
        """Test cost for non-existent artifact."""
        auth_response = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": True},
                "secret": {
                    "password": "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
                },
            },
        )
        token = auth_response.json()["token"]

        try:
            response = client.get(
                "/artifact/model/nonexistent_id/cost",
                headers={"X-Authorization": token},
            )
            # Per spec: 400 for invalid ID format, 404 for non-existent artifact
            assert response.status_code in [400, 404]
        except Exception as e:
            # S3 credential errors are acceptable in CI/CD environment
            assert "Unable to locate credentials" in str(e) or "NoCredentialsError" in str(e)


class TestLineageEndpoint:
    """Test lineage endpoint."""

    def test_lineage_missing_auth(self):
        """Test GET /artifact/model/{id}/lineage without auth."""
        response = client.get("/artifact/model/123/lineage")
        assert response.status_code == 403

    def test_lineage_nonexistent_artifact(self):
        """Test lineage for non-existent artifact."""
        auth_response = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": True},
                "secret": {
                    "password": "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
                },
            },
        )
        token = auth_response.json()["token"]

        try:
            response = client.get(
                "/artifact/model/nonexistent_id/lineage",
                headers={"X-Authorization": token},
            )
            # Per spec: 400 for invalid ID format, 404 for non-existent artifact
            assert response.status_code in [400, 404]
        except Exception as e:
            # Accept AWS credential errors in CI/CD environment
            assert "Unable to locate credentials" in str(e) or "NoCredentialsError" in str(e)


class TestTracksEndpoint:
    """Test /tracks endpoint."""

    def test_tracks_endpoint(self):
        """Test GET /tracks returns planned tracks."""
        response = client.get("/tracks")
        assert response.status_code == 200
        data = response.json()
        assert "plannedTracks" in data
        assert isinstance(data["plannedTracks"], list)
