"""AEGIS Pydantic Schemas for Request & Response Validation."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ----------------- Hospital Schemas -----------------

class HospitalResourceBase(BaseModel):
    resource_type: str
    total_units: int = Field(ge=0)
    available_units: int = Field(ge=0)
    status: str = "OPERATIONAL"


class HospitalResourceResponse(HospitalResourceBase):
    id: int
    hospital_id: int
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class HospitalBase(BaseModel):
    name: str
    code: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_phone: str
    trauma_level: str = "Level 2"
    specialties: List[str] = []
    facilities: List[str] = []
    total_beds: int = Field(ge=0, default=100)
    available_beds: int = Field(ge=0, default=20)
    icu_total: int = Field(ge=0, default=20)
    icu_available: int = Field(ge=0, default=5)
    er_capacity: int = Field(ge=0, default=30)
    er_current_load: int = Field(ge=0, default=15)
    has_cath_lab: bool = False
    has_stroke_center: bool = False
    has_ct_scanner: bool = True
    has_mri: bool = False
    has_burn_unit: bool = False
    has_pediatric_icu: bool = False
    has_hyperbaric_chamber: bool = False
    status: str = "OPERATIONAL"
    ibm_z_connected: bool = False
    ibm_z_node_id: str = "SYS1-ZOS-CICS"
    state: Optional[str] = None
    district: Optional[str] = None
    pincode: Optional[str] = None
    data_source: str = "SIMULATED"
    is_live_monitored: bool = False


class HospitalCreate(HospitalBase):
    resources: Optional[List[HospitalResourceBase]] = None


class HospitalCapacityUpdate(BaseModel):
    available_beds: Optional[int] = Field(None, ge=0)
    icu_available: Optional[int] = Field(None, ge=0)
    er_current_load: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None


class HospitalResponse(HospitalBase):
    id: int
    er_occupancy_rate: float
    bed_occupancy_rate: float
    last_ibm_z_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    resources: List[HospitalResourceResponse] = []
    model_config = ConfigDict(from_attributes=True)


# ----------------- Ambulance Schemas -----------------

class AmbulanceBase(BaseModel):
    call_sign: str
    vehicle_type: str = "ALS"
    latitude: float
    longitude: float
    status: str = "AVAILABLE"
    paramedic_crew: str = "Primary Paramedic Unit"
    equipment_level: str = "Advanced Cardiac Care"
    speed_kmh: float = 45.0


class AmbulanceCreate(AmbulanceBase):
    pass


class AmbulanceLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    speed_kmh: Optional[float] = None
    status: Optional[str] = None


class AmbulanceResponse(AmbulanceBase):
    id: int
    current_emergency_id: Optional[int] = None
    target_latitude: Optional[float] = None
    target_longitude: Optional[float] = None
    last_status_change: datetime
    model_config = ConfigDict(from_attributes=True)


# ----------------- Emergency Schemas -----------------

class EmergencyCreate(BaseModel):
    caller_name: str = "Anonymous Caller"
    caller_phone: str = "911-DIRECT"
    location_name: str
    latitude: float
    longitude: float
    chief_complaint: str
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    vitals_bp: Optional[str] = None
    vitals_hr: Optional[int] = None
    vitals_spo2: Optional[int] = None
    vitals_gcs: Optional[int] = None


class EmergencyDispatchAction(BaseModel):
    ambulance_id: int
    hospital_id: int
    notes: Optional[str] = None


class EmergencyResponse(BaseModel):
    id: int
    emergency_code: str
    caller_name: str
    caller_phone: str
    location_name: str
    latitude: float
    longitude: float
    severity: str
    category: str
    patient_age: Optional[int]
    patient_gender: Optional[str]
    chief_complaint: str
    vitals_bp: Optional[str]
    vitals_hr: Optional[int]
    vitals_spo2: Optional[int]
    vitals_gcs: Optional[int]
    ai_classification: Optional[str]
    required_specialties: List[str] = []
    required_resources: List[str] = []
    status: str
    assigned_hospital_id: Optional[int] = None
    assigned_ambulance_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ----------------- Recommendation Schemas -----------------

class RecommendationItem(BaseModel):
    id: Optional[int] = None
    hospital_id: int
    hospital_name: str
    hospital_code: str
    trauma_level: str
    rank: int
    composite_score: float
    capability_score: float
    transit_score: float
    bed_score: float
    congestion_penalty: float
    ibm_z_bonus: float
    distance_km: Optional[float] = None
    estimated_transit_minutes: Optional[float] = None
    rationale: str
    ibm_z_verified: bool
    status: str
    available_beds: int
    icu_available: int
    er_current_load: int
    er_capacity: int
    has_cath_lab: bool
    has_stroke_center: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    data_source: Optional[str] = "SIMULATED"
    is_live_monitored: Optional[bool] = False


class RecommendationResponse(BaseModel):
    emergency_id: int
    emergency_code: str
    severity: str
    category: str
    computed_at: datetime
    total_evaluated: int
    recommendations: List[RecommendationItem]


# ----------------- Event Schemas -----------------

class EmergencyEventResponse(BaseModel):
    id: int
    emergency_id: Optional[int]
    event_type: str
    summary: str
    details: Dict[str, Any]
    actor: str
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


# ----------------- Simulation Schemas -----------------

class SimulationStatusResponse(BaseModel):
    active: bool
    tick_count: int
    interval_seconds: float
    last_tick: Optional[datetime] = None
    tracked_ambulances: int
    tracked_hospitals: int
    pending_emergencies: int


class SurgeIncidentRequest(BaseModel):
    hospital_id: int
    incoming_patients: int = Field(ge=1, le=50, default=10)
    incident_name: str = "Mass Casualty Incident Simulation"


# ----------------- IBM Z Schemas -----------------

class IBMZStatusResponse(BaseModel):
    connected: bool
    mode: str  # "MOCK_SANDBOX" or "LIVE_ZOS_CONNECT"
    zos_connect_url: str
    cics_tran_id: str
    active_sysplex_node: str
    average_latency_ms: float
    last_heartbeat: datetime
    services_ready: Dict[str, bool]
    notice: str


class IBMZPatientLookupRequest(BaseModel):
    national_health_id: str
    patient_name: Optional[str] = None
    date_of_birth: Optional[str] = None


class IBMZPatientRecordResponse(BaseModel):
    record_found: bool
    mainframe_id: str
    patient_name: str
    blood_type: str
    allergies: List[str]
    critical_conditions: List[str]
    dnr_order: bool
    cardiac_history: bool
    prior_surgeries: List[str]
    emergency_contacts: List[str]
    cics_audit_token: str
    response_latency_ms: float


class IBMZCapacitySyncRequest(BaseModel):
    hospital_code: str


class IBMZCapacitySyncResponse(BaseModel):
    success: bool
    hospital_code: str
    mainframe_sequence_no: int
    cics_timestamp: str
    sync_status: str
    synced_metrics: Dict[str, Any]
