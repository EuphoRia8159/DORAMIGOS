"""Analytics, Audit Logs, and System KPIs API Router."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from aegis_backend.database import get_db
from aegis_backend.models import Hospital, Ambulance, Emergency, EmergencyEvent
from aegis_backend.schemas import EmergencyEventResponse

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Events"])


@router.get("/overview")
def get_system_overview(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Provides high-level operational metrics across all hospitals, ambulances, and emergencies."""
    # Fast database aggregations
    total_hospitals = db.query(func.count(Hospital.id)).scalar() or 0
    live_count = db.query(func.count(Hospital.id)).filter(Hospital.is_live_monitored == True).scalar() or 0
    directory_count = db.query(func.count(Hospital.id)).filter(Hospital.data_source == "EXCEL_DIRECTORY").scalar() or 0

    # Capacity aggregation: prefer live monitored facilities if present, else aggregate all
    filter_condition = (Hospital.is_live_monitored == True) if live_count > 0 else True
    metrics = db.query(
        func.coalesce(func.sum(Hospital.total_beds), 0),
        func.coalesce(func.sum(Hospital.available_beds), 0),
        func.coalesce(func.sum(Hospital.icu_total), 0),
        func.coalesce(func.sum(Hospital.icu_available), 0),
        func.coalesce(func.sum(Hospital.er_capacity), 0),
        func.coalesce(func.sum(Hospital.er_current_load), 0),
        func.coalesce(func.sum(case((Hospital.ibm_z_connected == True, 1), else_=0)), 0)
    ).filter(filter_condition).first()

    total_beds = int(metrics[0])
    available_beds = int(metrics[1])
    icu_total = int(metrics[2])
    icu_available = int(metrics[3])
    er_capacity = int(metrics[4])
    er_current_load = int(metrics[5])
    ibm_z_synced_count = int(metrics[6])

    # Ambulance metrics
    ambulances = db.query(Ambulance).all()
    total_fleet = len(ambulances)
    available_ambulances = sum(1 for a in ambulances if a.status == "AVAILABLE")
    dispatched_ambulances = sum(1 for a in ambulances if a.status in ["DISPATCHED", "EN_ROUTE_SCENE", "EN_ROUTE_HOSPITAL"])

    # Emergency metrics
    total_emergencies = db.query(Emergency).count()
    active_emergencies = db.query(Emergency).filter(
        Emergency.status.in_(["REPORTED", "TRIAGED", "AMBULANCE_DISPATCHED", "IN_TRANSIT"])
    ).count()
    critical_count = db.query(Emergency).filter(
        Emergency.severity == "CRITICAL",
        Emergency.status.in_(["REPORTED", "TRIAGED", "AMBULANCE_DISPATCHED", "IN_TRANSIT"])
    ).count()

    return {
        "hospitals": {
            "total": total_hospitals,
            "live_monitored": live_count,
            "directory_facilities": directory_count,
            "total_beds": total_beds,
            "available_beds": available_beds,
            "bed_occupancy_pct": round(((total_beds - available_beds) / max(total_beds, 1)) * 100, 1),
            "icu_total": icu_total,
            "icu_available": icu_available,
            "icu_occupancy_pct": round(((icu_total - icu_available) / max(icu_total, 1)) * 100, 1),
            "er_capacity": er_capacity,
            "er_load": er_current_load,
            "er_occupancy_pct": round((er_current_load / max(er_capacity, 1)) * 100, 1),
            "ibm_z_connected": ibm_z_synced_count
        },
        "fleet": {
            "total": total_fleet,
            "available": available_ambulances,
            "dispatched": dispatched_ambulances,
            "utilization_pct": round(((total_fleet - available_ambulances) / max(total_fleet, 1)) * 100, 1)
        },
        "emergencies": {
            "total": total_emergencies,
            "active": active_emergencies,
            "critical": critical_count
        }
    }


@router.get("/events", response_model=List[EmergencyEventResponse])
def get_recent_events(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieves recent event audit trail records."""
    events = db.query(EmergencyEvent).order_by(EmergencyEvent.timestamp.desc()).limit(limit).all()
    return events
