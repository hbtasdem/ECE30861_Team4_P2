#!/usr/bin/env python
"""Run the FastAPI app locally on localhost:8000"""

import uvicorn

if __name__ == "__main__":
    # Run on localhost:8000 so you can access it at http://127.0.0.1:8000
    uvicorn.run("crud.app:app", host="127.0.0.1", port=8000, reload=True)
