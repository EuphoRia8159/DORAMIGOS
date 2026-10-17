"""Simulation Controls API Router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from aegis_backend.database import get_db
from aegis_backend.models import Hospital, Ambulance, Emergency
from aegis_backend.simulation import simulation_engine
from aegis_backend.schemas import SimulationStatusResponse, SurgeIncidentRequest

router = APIRouter(prefix="/api/simulation", tags=["Simulation"])


@router.get("/status", response_model=SimulationStatusResponse)
def get_simulation_status(db: Session = Depends(get_db)):
    """Returns the operational status and telemetry tick metrics of the simulation engine."""
    ambulances_count = db.query(Ambulance).count()
    hospitals_count = db.query(Hospital).count()
    emergencies_count = db.query(Emergency).filter(
        Emergency.status.in_(["REPORTED", "TRIAGED", "AMBULANCE_DISPATCHED", "IN_TRANSIT"])
    ).count()

    return SimulationStatusResponse(
        active=simulation_engine.is_running,
        tick_count=simulation_engine.tick_count,
        interval_seconds=simulation_engine.interval_seconds,
        last_tick=datetime.now(timezone.utc) if simulation_engine.tick_count > 0 else None,
        tracked_ambulances=ambulances_count,
        tracked_hospitals=hospitals_count,
        pending_emergencies=emergencies_count
    )


@router.post("/start")
def start_simulation():
    """Starts the real-time background simulation engine."""
    simulation_engine.start()
    return {"status": "started", "active": simulation_engine.is_running}


@router.post("/stop")
def stop_simulation():
    """Pauses the real-time background simulation engine."""
    simulation_engine.stop()
    return {"status": "stopped", "active": simulation_engine.is_running}


@router.post("/tick")
async def step_simulation():
    """Executes a single discrete simulation tick immediately."""
    result = await simulation_engine.tick()
    return result


@router.post("/surge")
def trigger_surge(payload: SurgeIncidentRequest, db: Session = Depends(get_db)):
    """Simulates a sudden mass-casualty incident or ER surge at a specific hospital,

    forcing dynamic recommendation updates and ambulance rerouting.
    """
    res = simulation_engine.trigger_mass_casualty(
        db=db,
        hospital_id=payload.hospital_id,
        incoming_count=payload.incoming_patients
    )
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res
