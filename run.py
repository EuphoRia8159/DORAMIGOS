"""AEGIS Emergency Care Orchestration Platform Runner.

Starts the FastAPI server with Uvicorn.
"""

import uvicorn
from aegis_backend.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.APP_NAME} on http://{settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "aegis_backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
