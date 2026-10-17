"""AEGIS SQLAlchemy Database Models.

Defines schemas for Hospitals, Resources, Ambulances, Emergencies,
Recommendations, Assignments, and Real-Time Audit Events.
"""

from datetime import datetime, timezone
import json
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship
from aegis_backend.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Hospital(Base):
    """Hospital facility registered in the emergency care network."""
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True, index=True)
    code = Column(String(20), nullable=False, unique=True, index=True)
    address = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    contact_phone = Column(String(50), nullable=False)
    
    # Clinical capabilities & Trauma certification
    trauma_level = Column(String(20), default="Level 2")  # Level 1, Level 2, Level 3, Community
    specialties_json = Column(Text, default="[]")  # JSON array of medical specialties
    
    # Bed & Capacity Metrics
    total_beds = Column(Integer, default=100)
    available_beds = Column(Integer, default=20)
    icu_total = Column(Integer, default=20)
    icu_available = Column(Integer, default=5)
    er_capacity = Column(Integer, default=30)
    er_current_load = Column(Integer, default=15)
    
    # Key Diagnostic / Treatment Capabilities
    has_cath_lab = Column(Boolean, default=False)
    has_stroke_center = Column(Boolean, default=False)
    has_ct_scanner = Column(Boolean, default=True)
    has_mri = Column(Boolean, default=False)
    has_burn_unit = Column(Boolean, default=False)
    has_pediatric_icu = Column(Boolean, default=False)
    has_hyperbaric_chamber = Column(Boolean, default=False)
    
    # Operational Status
    status = Column(String(30), default="OPERATIONAL")  # OPERATIONAL, SURGE, ON_DIVERSION, RESTRICTED
    
    # IBM Z Mainframe Integration Flags
    ibm_z_connected = Column(Boolean, default=False)
    ibm_z_node_id = Column(String(50), default="SYS1-ZOS-CICS")
    last_ibm_z_sync = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    resources = relationship("HospitalResource", back_populates="hospital", cascade="all, delete-orphan")
    recommendations = relationship("HospitalRecommendation", back_populates="hospital")

    @property
    def specialties(self):
        try:
            return json.loads(self.specialties_json) if self.specialties_json else []
        except Exception:
            return []

    @specialties.setter
    def specialties(self, val):
        self.specialties_json = json.dumps(val)

    @property
    def er_occupancy_rate(self) -> float:
        if self.er_capacity <= 0:
            return 1.0
        return min(round(self.er_current_load / self.er_capacity, 2), 1.5)

    @property
    def bed_occupancy_rate(self) -> float:
        if self.total_beds <= 0:
            return 1.0
        occupied = self.total_beds - self.available_beds
        return min(round(occupied / self.total_beds, 2), 1.5)


class HospitalResource(Base):
    """Granular medical resources tracked within a hospital."""
    __tablename__ = "hospital_resources"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)  # ICU_BED, VENTILATOR, CATH_LAB, CT_SCANNER, OPERATING_ROOM, BLOOD_O_NEG
    total_units = Column(Integer, default=10)
    available_units = Column(Integer, default=5)
    status = Column(String(30), default="OPERATIONAL")  # OPERATIONAL, MAINTENANCE, DEPLETED
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    hospital = relationship("Hospital", back_populates="resources")


class Ambulance(Base):
    """EMS Ambulance units tracked with GPS coordinates and clinical capability."""
    __tablename__ = "ambulances"

    id = Column(Integer, primary_key=True, index=True)
    call_sign = Column(String(50), nullable=False, unique=True, index=True)
    vehicle_type = Column(String(30), default="ALS")  # BLS (Basic Life Support), ALS (Advanced Life Support), MICU (Mobile ICU), AIR (Helicopter)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String(30), default="AVAILABLE")  # AVAILABLE, DISPATCHED, EN_ROUTE_SCENE, AT_SCENE, EN_ROUTE_HOSPITAL, AT_HOSPITAL, OUT_OF_SERVICE
    paramedic_crew = Column(String(150), default="Primary Paramedic Unit")
    equipment_level = Column(String(50), default="Advanced Cardiac Care")
    speed_kmh = Column(Float, default=45.0)
    current_emergency_id = Column(Integer, ForeignKey("emergencies.id", use_alter=True), nullable=True)
    target_latitude = Column(Float, nullable=True)
    target_longitude = Column(Float, nullable=True)
    last_status_change = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    current_emergency = relationship("Emergency", foreign_keys=[current_emergency_id], post_update=True)
    assignments = relationship("AmbulanceAssignment", back_populates="ambulance")


class Emergency(Base):
    """Emergency dispatch incidents managed by AEGIS."""
    __tablename__ = "emergencies"

    id = Column(Integer, primary_key=True, index=True)
    emergency_code = Column(String(30), unique=True, index=True, nullable=False)
    caller_name = Column(String(100), default="Anonymous Caller")
    caller_phone = Column(String(50), default="911-DIRECT")
    location_name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Clinical Triage & AI Classification
    severity = Column(String(20), default="CRITICAL")  # CRITICAL, URGENT, MODERATE, LOW
    category = Column(String(50), default="GENERAL_MEDICAL")  # CARDIAC_ARREST, ACUTE_STROKE, POLYTRAUMA, RESPIRATORY_FAILURE, SEVERE_BURN, PEDIATRIC_CRITICAL, GENERAL_MEDICAL
    patient_age = Column(Integer, nullable=True)
    patient_gender = Column(String(20), nullable=True)
    chief_complaint = Column(Text, nullable=False)
    
    # Clinical vitals
    vitals_bp = Column(String(30), nullable=True)  # e.g., "85/50"
    vitals_hr = Column(Integer, nullable=True)      # Heart rate (e.g., 135)
    vitals_spo2 = Column(Integer, nullable=True)    # Oxygen saturation (e.g., 88)
    vitals_gcs = Column(Integer, nullable=True)     # Glasgow Coma Scale (3-15)
    
    # AI Analysis & Requirements
    ai_classification = Column(Text, nullable=True)  # Summary generated by AI engine
    required_specialties_json = Column(Text, default="[]")
    required_resources_json = Column(Text, default="[]")
    
    # Life Cycle Status
    status = Column(String(30), default="REPORTED")  # REPORTED, TRIAGED, AMBULANCE_DISPATCHED, HOSPITAL_ASSIGNED, IN_TRANSIT, ARRIVED_HOSPITAL, RESOLVED, CANCELLED
    
    # Assigned Resources
    assigned_hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    assigned_ambulance_id = Column(Integer, ForeignKey("ambulances.id", use_alter=True), nullable=True)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    assigned_hospital = relationship("Hospital", foreign_keys=[assigned_hospital_id])
    assigned_ambulance = relationship("Ambulance", foreign_keys=[assigned_ambulance_id], post_update=True)
    recommendations = relationship("HospitalRecommendation", back_populates="emergency", cascade="all, delete-orphan")
    events = relationship("EmergencyEvent", back_populates="emergency", cascade="all, delete-orphan", order_by="EmergencyEvent.timestamp.desc()")
    assignments = relationship("AmbulanceAssignment", back_populates="emergency", cascade="all, delete-orphan")

    @property
    def required_specialties(self):
        try:
            return json.loads(self.required_specialties_json) if self.required_specialties_json else []
        except Exception:
            return []

    @required_specialties.setter
    def required_specialties(self, val):
        self.required_specialties_json = json.dumps(val)

    @property
    def required_resources(self):
        try:
            return json.loads(self.required_resources_json) if self.required_resources_json else []
        except Exception:
            return []

    @required_resources.setter
    def required_resources(self, val):
        self.required_resources_json = json.dumps(val)


class HospitalRecommendation(Base):
    """Ranked hospital recommendations dynamically produced for an emergency."""
    __tablename__ = "hospital_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    emergency_id = Column(Integer, ForeignKey("emergencies.id"), nullable=False, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    rank = Column(Integer, nullable=False)
    composite_score = Column(Float, nullable=False)  # 0.0 to 100.0
    
    # Component scores (0.0 to 100.0)
    capability_score = Column(Float, default=0.0)
    transit_score = Column(Float, default=0.0)
    bed_score = Column(Float, default=0.0)
    congestion_penalty = Column(Float, default=0.0)
    ibm_z_bonus = Column(Float, default=0.0)
    
    # Distance and travel time
    distance_km = Column(Float, nullable=False)
    estimated_transit_minutes = Column(Float, nullable=False)
    
    # Explainable Rationale
    rationale = Column(Text, nullable=False)
    ibm_z_verified = Column(Boolean, default=False)
    
    # Recommendation Status
    status = Column(String(30), default="RECOMMENDED")  # RECOMMENDED, SELECTED, REJECTED, BYPASSED
    created_at = Column(DateTime, default=utc_now)

    emergency = relationship("Emergency", back_populates="recommendations")
    hospital = relationship("Hospital", back_populates="recommendations")


class AmbulanceAssignment(Base):
    """Tracks ambulance deployment lifecycle for an incident."""
    __tablename__ = "ambulance_assignments"

    id = Column(Integer, primary_key=True, index=True)
    emergency_id = Column(Integer, ForeignKey("emergencies.id"), nullable=False, index=True)
    ambulance_id = Column(Integer, ForeignKey("ambulances.id"), nullable=False, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    
    dispatch_time = Column(DateTime, default=utc_now)
    arrival_scene_time = Column(DateTime, nullable=True)
    departure_scene_time = Column(DateTime, nullable=True)
    arrival_hospital_time = Column(DateTime, nullable=True)
    
    distance_to_scene_km = Column(Float, default=0.0)
    eta_scene_minutes = Column(Float, default=0.0)
    status = Column(String(30), default="ACTIVE")  # ACTIVE, COMPLETED, CANCELLED

    emergency = relationship("Emergency", back_populates="assignments")
    ambulance = relationship("Ambulance", back_populates="assignments")


class EmergencyEvent(Base):
    """Audit log and event stream for real-time tracking."""
    __tablename__ = "emergency_events"

    id = Column(Integer, primary_key=True, index=True)
    emergency_id = Column(Integer, ForeignKey("emergencies.id"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False)  # EMERGENCY_REPORTED, AI_TRIAGED, RECOMMENDATION_COMPUTED, AMBULANCE_DISPATCHED, HOSPITAL_ASSIGNED, CAPACITY_UPDATED, SIMULATION_TICK, IBM_Z_SYNC
    summary = Column(String(255), nullable=False)
    details_json = Column(Text, default="{}")
    actor = Column(String(50), default="AEGIS_CORE")  # SYSTEM, OPERATOR, AI_ENGINE, SIMULATOR, IBM_Z_BRIDGE
    timestamp = Column(DateTime, default=utc_now, index=True)

    emergency = relationship("Emergency", back_populates="events")

    @property
    def details(self):
        try:
            return json.loads(self.details_json) if self.details_json else {}
        except Exception:
            return {}

    @details.setter
    def details(self, val):
        self.details_json = json.dumps(val)
