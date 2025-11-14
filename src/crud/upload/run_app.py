#!/usr/bin/env python
"""Development server launcher for FastAPI application.

Per OpenAPI v3.4.4 - API Server Configuration

PURPOSE:
Entry point to run the FastAPI application with automatic code reloading for development.
Useful during development to test endpoints with live code updates.

USAGE:
    python src/crud/upload/run_app.py

Server Configuration:
- Host: 127.0.0.1 (localhost only)
- Port: 8000
- Reload: True (automatic restart on file changes)
- Workers: 1 (single process for development)

Access Points:
- API: http://127.0.0.1:8000
- OpenAPI Docs: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

Key Endpoints Available:
- POST /auth/register: User registration
- PUT /authenticate: User login (generates JWT)
- POST /api/models/upload: Register model from URL
- GET /api/models/enumerate: List models with pagination
- POST /api/models/upload-file: Single file upload (Phase 3)
- POST /api/models/upload-batch: Batch file upload (Phase 4)
- POST /api/models/chunked-upload/init: Initiate chunked upload (Phase 4)
- GET /api/models/chunked-upload/{id}/progress: Track upload progress (Phase 4)

Hot Reload:
- Enabled: Any changes to Python files trigger automatic restart
- Watch paths: All files in src/crud/ directory
- Graceful restart: Current requests completed before reload
- Warnings: File syntax errors prevent reload (logged to console)

Authentication Notes:
- All protected endpoints require X-Authorization header
- Format: X-Authorization: bearer <JWT_TOKEN>
- Obtain token from PUT /authenticate endpoint first
- Token expires after 30 minutes

Production Notes:
- This development server is NOT suitable for production
- Use gunicorn or uvicorn with multiple workers for production
- Set reload=False for production deployments
- Run run_app_stable.py for production-like testing

Debugging:
- Use standard Python debugger (pdb, debugpy, PyCharm)
- Set breakpoints in routes and models
- Uvicorn will pause execution at breakpoints
- Use /docs endpoint to test endpoints interactively

Database Notes:
- SQLite in-memory or file-based (configurable)
- All tables created on startup
- Test data can be loaded from sample_input.txt
- See LOGGING_README.md for database logging configuration
"""

import uvicorn

if __name__ == "__main__":
    # Run on localhost:8000 so you can access it at http://127.0.0.1:8000
    uvicorn.run(
        "crud.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
