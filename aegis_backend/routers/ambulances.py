"""Ambulance Fleet Management API Router."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from aegis_backend.database import get_db
from aegis_backend.models import Ambulance
from aegis_backend.schemas import AmbulanceResponse, AmbulanceCreate, AmbulanceLocationUpdate
from aegis_backend.events import record_event, manager

router = APIRouter(prefix="/api/ambulances", tags=["Ambulances"])


@router.get("", response_model=List[AmbulanceResponse])
def list_ambulances(
    status: Optional[str] = Query(None, description="Filter by status"),
    vehicle_type: Optional[str] = Query(None, description="Filter by BLS, ALS, MICU, AIR"),
    db: Session = Depends(get_db)
):
    """Retrieves all registered ambulances and their current telemetry coordinates."""
    query = db.query(Ambulance)
    if status:
        query = query.filter(Ambulance.status == status)
    if vehicle_type:
        query = query.filter(Ambulance.vehicle_type == vehicle_type)
    return query.all()


@router.get("/{ambulance_id}", response_model=AmbulanceResponse)
def get_ambulance(ambulance_id: int, db: Session = Depends(get_db)):
    """Retrieves single ambulance details."""
    amb = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    if not amb:
        raise HTTPException(status_code=404, detail="Ambulance not found")
    return amb


@router.patch("/{ambulance_id}/location", response_model=AmbulanceResponse)
async def update_ambulance_location(
    ambulance_id: int,
    payload: AmbulanceLocationUpdate,
    db: Session = Depends(get_db)
):
    """Updates GPS coordinates, speed, and status for an ambulance unit."""
    amb = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    if not amb:
        raise HTTPException(status_code=404, detail="Ambulance not found")

    amb.latitude = payload.latitude
    amb.longitude = payload.longitude
    if payload.speed_kmh is not None:
        amb.speed_kmh = payload.speed_kmh
    if payload.status is not None:
        amb.status = payload.status
        amb.last_status_change = datetime.now(timezone.utc)

    amb.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(amb)

    await manager.broadcast({
        "type": "AMBULANCE_TELEMETRY",
        "ambulance_id": amb.id,
        "call_sign": amb.call_sign,
        "latitude": amb.latitude,
        "longitude": amb.longitude,
        "status": amb.status,
        "speed_kmh": amb.speed_kmh
    })

    return amb


@router.post("/{ambulance_id}/reset", response_model=AmbulanceResponse)
def reset_ambulance(ambulance_id: int, db: Session = Depends(get_db)):
    """Resets an ambulance to AVAILABLE state and clears current emergency assignment."""
    amb = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    if not amb:
        raise HTTPException(status_code=404, detail="Ambulance not found")

    amb.status = "AVAILABLE"
    amb.current_emergency_id = None
    amb.target_latitude = None
    amb.target_longitude = None
    amb.last_status_change = datetime.now(timezone.utc)
    db.commit()
    db.refresh(amb)

    record_event(db, "AMBULANCE_RESET", f"Ambulance {amb.call_sign} reset to AVAILABLE.", actor="OPERATOR")
    return amb
