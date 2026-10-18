"""AEGIS — Emergency Care Orchestration API.

Main FastAPI Application Entrypoint.
"""

from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from aegis_backend.config import settings
from aegis_backend.database import init_db, SessionLocal
from aegis_backend.seed_data import seed_database
from aegis_backend.events import manager
from aegis_backend.simulation import simulation_engine
from aegis_backend.routers import (
    hospitals,
    ambulances,
    emergencies,
    recommendations,
    demo_recommendations,
    simulation_api,
    ibm_z_api,
    analytics
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("aegis")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info("Initializing AEGIS database tables...")
    init_db()

    # Seed baseline hospital, ambulance, and emergency data
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    # Launch real-time simulation engine if configured
    if settings.AUTO_SIMULATION_ENABLED:
        simulation_engine.start()
        logger.info("Simulation engine started automatically.")

    yield

    # Clean shutdown
    simulation_engine.stop()
    logger.info("AEGIS Backend shutdown completed.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AEGIS is an intelligent emergency coordination platform connecting emergency requests "
        "with suitable hospitals and available ambulance services through dynamic clinical classification, "
        "multi-factor recommendation scoring, real-time telemetry, and an IBM Z enterprise integration layer."
    ),
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(hospitals.router)
app.include_router(ambulances.router)
app.include_router(emergencies.router)
app.include_router(recommendations.router)
app.include_router(demo_recommendations.router)
app.include_router(simulation_api.router)
app.include_router(ibm_z_api.router)
app.include_router(analytics.router)


# WebSocket Channel for Real-time Telemetry & Events
@app.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket):
    """Real-time bi-directional WebSocket connection for emergency and telemetry events."""
    await manager.connect(websocket)
    try:
        while True:
            # Receive client ping or commands
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type": "pong"}')
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection error: {e}")
        manager.disconnect(websocket)


# Mount Static Assets & Serve Website Frontend
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serves the AEGIS Emergency Care Orchestration frontend application."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AEGIS API is active. Website assets loading...", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for container orchestrators and load balancers."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "simulation_running": simulation_engine.is_running
    }
