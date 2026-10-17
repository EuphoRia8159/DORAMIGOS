"""IBM Z Mainframe Integration API Router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aegis_backend.database import get_db
from aegis_backend.ibm_z.status import IBMZStatusService
from aegis_backend.ibm_z.health_records import IBMZHealthRecordsService
from aegis_backend.ibm_z.capacity_sync import IBMZCapacitySyncService
from aegis_backend.schemas import (
    IBMZStatusResponse,
    IBMZPatientLookupRequest,
    IBMZPatientRecordResponse,
    IBMZCapacitySyncRequest,
    IBMZCapacitySyncResponse
)

router = APIRouter(prefix="/api/ibm-z", tags=["IBM Z Integration"])


@router.get("/status", response_model=IBMZStatusResponse)
async def get_ibm_z_status():
    """Returns the operational status, latency, and integration mode of the IBM Z enterprise layer."""
    status_data = await IBMZStatusService.get_status()
    return status_data


@router.post("/patient-lookup", response_model=IBMZPatientRecordResponse)
async def lookup_patient_history(payload: IBMZPatientLookupRequest):
    """Executes a mainframe EHR Master Patient Index query (CICS Transaction EHR1)

    to retrieve verified allergies, blood group, prior cardiac events, and advance directives.
    """
    record = await IBMZHealthRecordsService.lookup_patient(
        national_health_id=payload.national_health_id,
        patient_name=payload.patient_name
    )
    return record


@router.post("/sync-capacity", response_model=IBMZCapacitySyncResponse)
async def sync_hospital_capacity(payload: IBMZCapacitySyncRequest, db: Session = Depends(get_db)):
    """Pushes hospital capacity metrics to the IBM z/OS CICS hospital ledger (Transaction CAP1)

    and records enterprise verification.
    """
    result = await IBMZCapacitySyncService.sync_hospital(db, payload.hospital_code)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Sync failed"))
    return result
