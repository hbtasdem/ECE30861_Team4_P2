# app.py# app.py

import osimport os

from fastapi import FastAPIfrom fastapi import FastAPI

from database import init_dbfrom database import init_db

from upload.routes import router as upload_routerfrom upload.routes import router as upload_router



# Initialize FastAPI app# Initialize FastAPI app

app = FastAPI(app = FastAPI(

    title="Model Registry API",    title="Model Registry API",

    description="Upload and manage ML models in ZIP format",    description="Upload and manage ML models in ZIP format",

    version="1.0.0"    version="1.0.0",

))



# Initialize database only if not in test mode# Initialize database only if not in test mode

if os.getenv("TESTING") != "true":if os.getenv("TESTING") != "true":

    init_db()    init_db()



# Include routers# Include routers

app.include_router(upload_router)app.include_router(upload_router)



@app.get("/health")

async def health_check():@app.get("/health")

    """Health check endpoint"""async def health_check():

    return {"status": "ok"}    """Health check endpoint"""

    return {"status": "ok"}

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
