#!/usr/bin/env python
"""Run FastAPI app without hot reload"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "crud.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False  # No hot reload to prevent disruptions during testing
    )
