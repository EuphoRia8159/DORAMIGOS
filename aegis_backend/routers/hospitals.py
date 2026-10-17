import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timezone

from aegis_backend.database import get_db
from aegis_backend.models import Hospital
from aegis_backend.schemas import HospitalResponse, HospitalCreate, HospitalCapacityUpdate
from aegis_backend.events import record_event, manager
from aegis_backend.recommendation_engine import haversine_distance_km

router = APIRouter(prefix="/api/hospitals", tags=["Hospitals"])


@router.get("", response_model=List[HospitalResponse])
def list_hospitals(
    search: Optional[str] = Query(None, description="Search by hospital name, address, district, state, or code"),
    state: Optional[str] = Query(None, description="Filter by state"),
    district: Optional[str] = Query(None, description="Filter by district"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    trauma_level: Optional[str] = Query(None, description="Filter by trauma level"),
    status: Optional[str] = Query(None, description="Filter by operational status"),
    data_source: Optional[str] = Query(None, description="Filter by data source (SIMULATED, EXCEL_DIRECTORY)"),
    is_live_monitored: Optional[bool] = Query(None, description="Filter by live telemetry monitoring status"),
    has_coordinates: Optional[bool] = Query(None, description="Filter hospitals that have valid GPS coordinates"),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Latitude for proximity search"),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Longitude for proximity search"),
    radius_km: Optional[float] = Query(None, gt=0, le=2000.0, description="Radius in kilometers (requires coordinates)"),
    skip: int = Query(0, ge=0, description="Number of records to skip (pagination offset)"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return (page size)"),
    db: Session = Depends(get_db)
):
    """Retrieves registered hospital facilities with search, regional filtering,

    proximity radius calculation, and pagination.
    """
    # Validate location parameters
    if (latitude is not None and longitude is None) or (latitude is None and longitude is not None):
        raise HTTPException(
            status_code=400,
            detail="Both latitude and longitude must be provided for proximity filtering"
        )
    if radius_km is not None and latitude is None:
        raise HTTPException(
            status_code=400,
            detail="Latitude and longitude are required when radius_km is specified"
        )

    query = db.query(Hospital)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Hospital.name.ilike(search_pattern),
                Hospital.address.ilike(search_pattern),
                Hospital.district.ilike(search_pattern),
                Hospital.state.ilike(search_pattern),
                Hospital.code.ilike(search_pattern)
            )
        )

    if state:
        query = query.filter(Hospital.state.ilike(f"%{state.strip()}%"))
    if district:
        query = query.filter(Hospital.district.ilike(f"%{district.strip()}%"))
    if trauma_level:
        query = query.filter(Hospital.trauma_level == trauma_level)
    if status:
        query = query.filter(Hospital.status == status)
    if data_source:
        query = query.filter(Hospital.data_source == data_source)
    if is_live_monitored is not None:
        query = query.filter(Hospital.is_live_monitored == is_live_monitored)

    if has_coordinates is True:
        query = query.filter(Hospital.latitude.isnot(None), Hospital.longitude.isnot(None))
    elif has_coordinates is False:
        query = query.filter(or_(Hospital.latitude.is_(None), Hospital.longitude.is_(None)))

    # Location proximity filtering
    if latitude is not None and longitude is not None:
        effective_radius = radius_km or 50.0
        # Bounding box pre-filter in SQL for efficiency
        lat_delta = effective_radius / 111.0
        lon_delta = effective_radius / max(111.0 * math.cos(math.radians(latitude)), 1.0)
        query = query.filter(
            Hospital.latitude.isnot(None),
            Hospital.longitude.isnot(None),
            Hospital.latitude.between(latitude - lat_delta, latitude + lat_delta),
            Hospital.longitude.between(longitude - lon_delta, longitude + lon_delta)
        )
        hospitals = query.all()
        # Refine with exact Haversine distance and sort by distance
        nearby = []
        for h in hospitals:
            d = haversine_distance_km(latitude, longitude, h.latitude, h.longitude)
            if d <= effective_radius:
                nearby.append((d, h))
        nearby.sort(key=lambda x: x[0])
        hospitals = [item[1] for item in nearby]

        if specialty:
            hospitals = [h for h in hospitals if specialty.lower() in [s.lower() for s in h.specialties]]

        return hospitals[skip : skip + limit]

    if specialty:
        query = query.filter(Hospital.specialties_json.ilike(f"%{specialty.strip()}%"))

    return query.offset(skip).limit(limit).all()


@router.get("/{hospital_id}", response_model=HospitalResponse)
def get_hospital(hospital_id: int, db: Session = Depends(get_db)):
    """Retrieves single hospital facility details."""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return hospital


@router.patch("/{hospital_id}/capacity", response_model=HospitalResponse)
async def update_hospital_capacity(
    hospital_id: int,
    payload: HospitalCapacityUpdate,
    db: Session = Depends(get_db)
):
    """Updates real-time capacity and ER load for a hospital, broadcasting changes."""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    if payload.available_beds is not None:
        hospital.available_beds = payload.available_beds
    if payload.icu_available is not None:
        hospital.icu_available = payload.icu_available
    if payload.er_current_load is not None:
        hospital.er_current_load = payload.er_current_load
    if payload.status is not None:
        hospital.status = payload.status

    hospital.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(hospital)

    summary = f"Capacity updated for {hospital.name}: {hospital.available_beds} beds, {hospital.icu_available} ICU, ER load {hospital.er_current_load}/{hospital.er_capacity}."
    record_event(db, "CAPACITY_UPDATED", summary, actor="OPERATOR")

    await manager.broadcast({
        "type": "HOSPITAL_UPDATED",
        "hospital_id": hospital.id,
        "hospital_name": hospital.name,
        "available_beds": hospital.available_beds,
        "icu_available": hospital.icu_available,
        "er_current_load": hospital.er_current_load,
        "er_occupancy_rate": hospital.er_occupancy_rate,
        "status": hospital.status
    })

    return hospital


@router.post("", response_model=HospitalResponse, status_code=201)
def create_hospital(payload: HospitalCreate, db: Session = Depends(get_db)):
    """Registers a new hospital facility in the AEGIS coordination network."""
    existing = db.query(Hospital).filter(Hospital.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Hospital code already exists")

    data = payload.model_dump(exclude={"resources"})
    hospital = Hospital(**data)
    hospital.specialties = payload.specialties
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return hospital
