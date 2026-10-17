"""Emergency Dispatch and Incident Triage API Router."""

from typing import List, Optional
from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from aegis_backend.database import get_db
from aegis_backend.models import Emergency, Ambulance, Hospital, AmbulanceAssignment, HospitalRecommendation
from aegis_backend.schemas import (
    EmergencyCreate, EmergencyResponse, EmergencyDispatchAction
)
from aegis_backend.classifier import EmergencyClassifier
from aegis_backend.recommendation_engine import RecommendationEngine, haversine_distance_km, estimate_transit_time_minutes
from aegis_backend.events import record_event, manager

router = APIRouter(prefix="/api/emergencies", tags=["Emergencies"])


@router.post("", response_model=EmergencyResponse, status_code=201)
async def create_emergency(payload: EmergencyCreate, db: Session = Depends(get_db)):
    """Intakes an emergency call, executes AI triage classification, and generates

    real-time hospital recommendation rankings.
    """
    # 1. AI-assisted triage
    triage = EmergencyClassifier.classify(
        chief_complaint=payload.chief_complaint,
        patient_age=payload.patient_age,
        patient_gender=payload.patient_gender,
        vitals_bp=payload.vitals_bp,
        vitals_hr=payload.vitals_hr,
        vitals_spo2=payload.vitals_spo2,
        vitals_gcs=payload.vitals_gcs
    )

    code = f"EMRG-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    emrg = Emergency(
        emergency_code=code,
        caller_name=payload.caller_name,
        caller_phone=payload.caller_phone,
        location_name=payload.location_name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        severity=triage["severity"],
        category=triage["category"],
        patient_age=payload.patient_age,
        patient_gender=payload.patient_gender,
        chief_complaint=payload.chief_complaint,
        vitals_bp=payload.vitals_bp,
        vitals_hr=payload.vitals_hr,
        vitals_spo2=payload.vitals_spo2,
        vitals_gcs=payload.vitals_gcs,
        ai_classification=triage["ai_classification"],
        status="REPORTED"
    )
    emrg.required_specialties = triage["required_specialties"]
    emrg.required_resources = triage["required_resources"]

    db.add(emrg)
    db.commit()
    db.refresh(emrg)

    # 2. Compute baseline recommendations
    recs = RecommendationEngine.compute_recommendations(db, emrg, save_to_db=True)

    # 3. Log event
    summary = f"Emergency {emrg.emergency_code} reported: {triage['category']} ({triage['severity']}) at {emrg.location_name}."
    record_event(db, "EMERGENCY_REPORTED", summary, emergency_id=emrg.id, details={
        "category": triage["category"],
        "severity": triage["severity"],
        "top_hospital": recs[0]["hospital_name"] if recs else None
    }, actor="AI_TRIAGE")

    # 4. Broadcast live notification
    await manager.broadcast({
        "type": "NEW_EMERGENCY",
        "emergency_id": emrg.id,
        "emergency_code": emrg.emergency_code,
        "category": emrg.category,
        "severity": emrg.severity,
        "location_name": emrg.location_name,
        "top_hospital": recs[0]["hospital_name"] if recs else None,
        "top_score": recs[0]["composite_score"] if recs else 0
    })

    return emrg


@router.get("", response_model=List[EmergencyResponse])
def list_emergencies(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    db: Session = Depends(get_db)
):
    """Lists emergency incidents in the system."""
    query = db.query(Emergency).order_by(Emergency.created_at.desc())
    if status:
        query = query.filter(Emergency.status == status)
    if severity:
        query = query.filter(Emergency.severity == severity)
    return query.all()


@router.get("/{emergency_id}", response_model=EmergencyResponse)
def get_emergency(emergency_id: int, db: Session = Depends(get_db)):
    """Retrieves full details of an emergency incident."""
    emrg = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emrg:
        raise HTTPException(status_code=404, detail="Emergency incident not found")
    return emrg


@router.post("/{emergency_id}/dispatch", response_model=EmergencyResponse)
async def dispatch_emergency(
    emergency_id: int,
    payload: EmergencyDispatchAction,
    db: Session = Depends(get_db)
):
    """Dispatches an ambulance and reserves destination hospital for an emergency."""
    emrg = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emrg:
        raise HTTPException(status_code=404, detail="Emergency not found")

    amb = db.query(Ambulance).filter(Ambulance.id == payload.ambulance_id).first()
    if not amb:
        raise HTTPException(status_code=404, detail="Ambulance not found")

    hosp = db.query(Hospital).filter(Hospital.id == payload.hospital_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Destination hospital not found")

    # Update emergency assignment
    emrg.assigned_ambulance_id = amb.id
    emrg.assigned_hospital_id = hosp.id
    emrg.status = "AMBULANCE_DISPATCHED"

    # Set ambulance navigation target to emergency location
    amb.status = "DISPATCHED"
    amb.current_emergency_id = emrg.id
    amb.target_latitude = emrg.latitude
    amb.target_longitude = emrg.longitude
    amb.last_status_change = datetime.now(timezone.utc)

    # Calculate distance & ETA to scene
    dist_to_scene = haversine_distance_km(amb.latitude, amb.longitude, emrg.latitude, emrg.longitude)
    eta_scene = estimate_transit_time_minutes(dist_to_scene)

    # Create assignment record
    assignment = AmbulanceAssignment(
        emergency_id=emrg.id,
        ambulance_id=amb.id,
        hospital_id=hosp.id,
        distance_to_scene_km=dist_to_scene,
        eta_scene_minutes=eta_scene,
        status="ACTIVE"
    )
    db.add(assignment)

    # Update recommendation status
    db.query(HospitalRecommendation).filter(
        HospitalRecommendation.emergency_id == emrg.id,
        HospitalRecommendation.hospital_id == hosp.id
    ).update({"status": "SELECTED"})

    db.commit()
    db.refresh(emrg)

    summary = f"Ambulance {amb.call_sign} dispatched to {emrg.location_name} (ETA {eta_scene} min); Destination: {hosp.name}."
    record_event(db, "AMBULANCE_DISPATCHED", summary, emergency_id=emrg.id, details={
        "ambulance": amb.call_sign,
        "hospital": hosp.name,
        "eta_scene_min": eta_scene
    }, actor="DISPATCHER")

    await manager.broadcast({
        "type": "DISPATCH_CONFIRMED",
        "emergency_id": emrg.id,
        "emergency_code": emrg.emergency_code,
        "ambulance_id": amb.id,
        "ambulance_call_sign": amb.call_sign,
        "hospital_id": hosp.id,
        "hospital_name": hosp.name,
        "eta_scene_min": eta_scene
    })

    return emrg


@router.patch("/{emergency_id}/status", response_model=EmergencyResponse)
async def update_emergency_status(
    emergency_id: int,
    status: str = Query(..., description="Target status"),
    db: Session = Depends(get_db)
):
    """Advances emergency incident lifecycle status."""
    emrg = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emrg:
        raise HTTPException(status_code=404, detail="Emergency not found")

    old_status = emrg.status
    emrg.status = status
    emrg.updated_at = datetime.now(timezone.utc)

    if status in ["RESOLVED", "CANCELLED"] and emrg.assigned_ambulance:
        emrg.assigned_ambulance.status = "AVAILABLE"
        emrg.assigned_ambulance.current_emergency_id = None
        emrg.assigned_ambulance.target_latitude = None
        emrg.assigned_ambulance.target_longitude = None

    db.commit()
    db.refresh(emrg)

    summary = f"Emergency {emrg.emergency_code} status transitioned from {old_status} to {status}."
    record_event(db, "STATUS_CHANGE", summary, emergency_id=emrg.id, actor="OPERATOR")

    await manager.broadcast({
        "type": "EMERGENCY_STATUS_UPDATED",
        "emergency_id": emrg.id,
        "status": emrg.status
    })

    return emrg
