#!/usr/bin/env python
"""Production-like server launcher without automatic reloading.

Per OpenAPI v3.4.4 - API Server Configuration

PURPOSE:
Run FastAPI application in stable mode suitable for integration testing and production-like scenarios.
Differs from run_app.py by disabling automatic code reloading to ensure consistent behavior.

USAGE:
    python src/crud/upload/run_app_stable.py

Server Configuration:
- Host: 127.0.0.1 (localhost only)
- Port: 8000
- Reload: False (no automatic restarts)
- Workers: 1 (single process for testing)

When to Use:
1. Integration Testing: Stable environment for end-to-end tests
2. Production Simulation: Closest to production deployment
3. Load Testing: Consistent server state for benchmarking
4. Debugging Complex Issues: No interference from reloading

Differences from run_app.py:
- NO hot reload: Code changes require manual restart
- NO file watching: Better performance for testing
- STABLE process state: More predictable behavior
- BETTER for: Long-running tests, CI/CD pipelines

Key Endpoints (same as run_app.py):
- POST /auth/register: User registration
- PUT /authenticate: User login (generates JWT)
- POST /api/models/upload: Register model from URL
- GET /api/models/enumerate: List models with pagination
- POST /api/models/upload-file: Single file upload (Phase 3)
- POST /api/models/upload-batch: Batch file upload (Phase 4)
- POST /api/models/chunked-upload/init: Initiate chunked upload (Phase 4)
- GET /api/models/chunked-upload/{id}/progress: Track upload progress (Phase 4)

Performance:
- Faster startup (no file watcher initialization)
- Lower CPU usage (no filesystem monitoring)
- Stable memory usage (no reload cycles)
- Better for sustained load testing

Restart Required:
- After code changes, manual restart needed
- Kill process: Ctrl+C
- Start again: python run_app_stable.py

Production Migration:
- This configuration is recommended for production
- For real production: Use gunicorn with multiple workers
- Configure reverse proxy (nginx) for load balancing
- Enable HTTPS/TLS for security
- Use environment-based configuration
- Enable structured logging and monitoring

See Also:
- run_app.py: Development version with hot reload
- src/logging_config.py: Logging configuration
- requirements.txt: Dependencies list
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "crud.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False  # No hot reload to prevent disruptions during testing
    )
