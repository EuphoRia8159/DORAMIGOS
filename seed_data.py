"""AEGIS Seed Data Generator.

Populates initial production-like hospital facilities, medical resources,
ambulance fleet units, and baseline emergency incidents.
"""

import logging
from sqlalchemy.orm import Session
from aegis_backend.models import Hospital, HospitalResource, Ambulance, Emergency
from aegis_backend.classifier import EmergencyClassifier
from aegis_backend.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)

# Base Metropolitan Center: Downtown Metro City (Lat: 40.7306, Lon: -73.9925)
INITIAL_HOSPITALS = [
    {
        "name": "St. Jude Regional Trauma & Heart Center",
        "code": "STJUDE-01",
        "address": "100 St. Jude Plaza, Downtown",
        "latitude": 40.7340,
        "longitude": -73.9900,
        "contact_phone": "+1-555-0101",
        "trauma_level": "Level 1",
        "specialties": ["Trauma Surgery", "Cardiology", "Interventional Cardiology", "Cardiothoracic Surgery", "Critical Care", "Neurology", "Orthopedics"],
        "total_beds": 280,
        "available_beds": 48,
        "icu_total": 42,
        "icu_available": 9,
        "er_capacity": 45,
        "er_current_load": 26,
        "has_cath_lab": True,
        "has_stroke_center": True,
        "has_ct_scanner": True,
        "has_mri": True,
        "has_burn_unit": False,
        "has_pediatric_icu": False,
        "status": "OPERATIONAL",
        "ibm_z_connected": True,
        "ibm_z_node_id": "SYS1-ZOS-CICS-STJUDE"
    },
    {
        "name": "Metro General Hospital & Comprehensive Stroke Center",
        "code": "METRO-02",
        "address": "450 Medical Blvd, Midtown East",
        "latitude": 40.7510,
        "longitude": -73.9740,
        "contact_phone": "+1-555-0102",
        "trauma_level": "Level 2",
        "specialties": ["Neurology", "Interventional Neuroradiology", "Neurosurgery", "Cardiology", "Critical Care", "Emergency Medicine"],
        "total_beds": 220,
        "available_beds": 34,
        "icu_total": 30,
        "icu_available": 7,
        "er_capacity": 38,
        "er_current_load": 21,
        "has_cath_lab": True,
        "has_stroke_center": True,
        "has_ct_scanner": True,
        "has_mri": True,
        "has_burn_unit": False,
        "has_pediatric_icu": False,
        "status": "OPERATIONAL",
        "ibm_z_connected": True,
        "ibm_z_node_id": "SYS1-ZOS-CICS-METRO"
    },
    {
        "name": "University Academic Medical & Burn Pavilion",
        "code": "UNIV-03",
        "address": "800 University Way, North Quarter",
        "latitude": 40.7680,
        "longitude": -73.9850,
        "contact_phone": "+1-555-0103",
        "trauma_level": "Level 1",
        "specialties": ["Burn Care", "Plastic & Reconstructive Surgery", "Trauma Surgery", "Critical Care", "Vascular Surgery", "Internal Medicine"],
        "total_beds": 350,
        "available_beds": 62,
        "icu_total": 50,
        "icu_available": 12,
        "er_capacity": 55,
        "er_current_load": 32,
        "has_cath_lab": True,
        "has_stroke_center": False,
        "has_ct_scanner": True,
        "has_mri": True,
        "has_burn_unit": True,
        "has_pediatric_icu": False,
        "status": "OPERATIONAL",
        "ibm_z_connected": True,
        "ibm_z_node_id": "SYS1-ZOS-CICS-UNIV"
    },
    {
        "name": "Children's Mercy Pediatric Hospital",
        "code": "PED-04",
        "address": "320 Hope Street, Westside Park",
        "latitude": 40.7420,
        "longitude": -74.0040,
        "contact_phone": "+1-555-0104",
        "trauma_level": "Level 1",
        "specialties": ["Pediatrics", "Pediatric Intensive Care", "Pediatric Surgery", "Pediatric Cardiology", "Critical Care"],
        "total_beds": 160,
        "available_beds": 29,
        "icu_total": 32,
        "icu_available": 8,
        "er_capacity": 25,
        "er_current_load": 12,
        "has_cath_lab": False,
        "has_stroke_center": False,
        "has_ct_scanner": True,
        "has_mri": True,
        "has_burn_unit": False,
        "has_pediatric_icu": True,
        "status": "OPERATIONAL",
        "ibm_z_connected": True,
        "ibm_z_node_id": "SYS1-ZOS-CICS-CHLD"
    },
    {
        "name": "Mercy West Community Hospital",
        "code": "WEST-05",
        "address": "120 10th Avenue, Riverfront",
        "latitude": 40.7290,
        "longitude": -74.0100,
        "contact_phone": "+1-555-0105",
        "trauma_level": "Level 3",
        "specialties": ["Emergency Medicine", "Internal Medicine", "General Surgery"],
        "total_beds": 110,
        "available_beds": 11,
        "icu_total": 12,
        "icu_available": 2,
        "er_capacity": 28,
        "er_current_load": 24,
        "has_cath_lab": False,
        "has_stroke_center": False,
        "has_ct_scanner": True,
        "has_mri": False,
        "has_burn_unit": False,
        "has_pediatric_icu": False,
        "status": "OPERATIONAL",
        "ibm_z_connected": False,
        "ibm_z_node_id": "SYS1-ZOS-CICS-WEST"
    },
    {
        "name": "Harborview Acute Care & Hyperbaric Center",
        "code": "HARBOR-06",
        "address": "90 Harbor Drive, South Bay",
        "latitude": 40.7080,
        "longitude": -74.0150,
        "contact_phone": "+1-555-0106",
        "trauma_level": "Level 2",
        "specialties": ["Trauma Surgery", "Cardiology", "Pulmonology", "Critical Care", "Hyperbaric Medicine"],
        "total_beds": 190,
        "available_beds": 31,
        "icu_total": 24,
        "icu_available": 5,
        "er_capacity": 35,
        "er_current_load": 29,
        "has_cath_lab": True,
        "has_stroke_center": False,
        "has_ct_scanner": True,
        "has_mri": True,
        "has_burn_unit": False,
        "has_pediatric_icu": False,
        "status": "OPERATIONAL",
        "ibm_z_connected": True,
        "ibm_z_node_id": "SYS1-ZOS-CICS-HARB"
    },
    {
        "name": "St. Luke's Eastside Surgical Hospital",
        "code": "EAST-07",
        "address": "610 1st Avenue, East River",
        "latitude": 40.7440,
        "longitude": -73.9680,
        "contact_phone": "+1-555-0107",
        "trauma_level": "Level 2",
        "specialties": ["Orthopedics", "General Surgery", "Internal Medicine", "Critical Care"],
        "total_beds": 140,
        "available_beds": 18,
        "icu_total": 16,
        "icu_available": 3,
        "er_capacity": 30,
        "er_current_load": 27,
        "has_cath_lab": False,
        "has_stroke_center": False,
        "has_ct_scanner": True,
        "has_mri": True,
        "has_burn_unit": False,
        "has_pediatric_icu": False,
        "status": "OPERATIONAL",
        "ibm_z_connected": False,
        "ibm_z_node_id": "SYS1-ZOS-CICS-EAST"
    },
    {
        "name": "Midtown Memorial Urgent Care Center",
        "code": "MIDTOWN-08",
        "address": "250 Broadway, Civic Center",
        "latitude": 40.7160,
        "longitude": -74.0020,
        "contact_phone": "+1-555-0108",
        "trauma_level": "Community",
        "specialties": ["Emergency Medicine", "Family Practice"],
        "total_beds": 50,
        "available_beds": 6,
        "icu_total": 6,
        "icu_available": 1,
        "er_capacity": 20,
        "er_current_load": 19,
        "has_cath_lab": False,
        "has_stroke_center": False,
        "has_ct_scanner": True,
        "has_mri": False,
        "has_burn_unit": False,
        "has_pediatric_icu": False,
        "status": "SURGE",
        "ibm_z_connected": False,
        "ibm_z_node_id": "SYS1-ZOS-CICS-MID"
    }
]

INITIAL_AMBULANCES = [
    {"call_sign": "RESCUE-101", "vehicle_type": "ALS", "latitude": 40.7320, "longitude": -73.9910, "status": "AVAILABLE", "crew": "Paramedic Unit Alpha", "equipment": "Advanced Cardiac Care & Monitor Defib"},
    {"call_sign": "RESCUE-102", "vehicle_type": "ALS", "latitude": 40.7480, "longitude": -73.9780, "status": "AVAILABLE", "crew": "Paramedic Unit Bravo", "equipment": "Advanced Cardiac Care & Monitor Defib"},
    {"call_sign": "RESCUE-103", "vehicle_type": "ALS", "latitude": 40.7650, "longitude": -73.9820, "status": "AVAILABLE", "crew": "Paramedic Unit Charlie", "equipment": "Advanced Cardiac Care & Monitor Defib"},
    {"call_sign": "MICU-201", "vehicle_type": "MICU", "latitude": 40.7360, "longitude": -73.9870, "status": "AVAILABLE", "crew": "Mobile Intensive Care Critical Team", "equipment": "Mechanical Ventilator & Intra-Aortic Support"},
    {"call_sign": "MICU-202", "vehicle_type": "MICU", "latitude": 40.7550, "longitude": -73.9710, "status": "AVAILABLE", "crew": "Mobile Intensive Care Critical Team", "equipment": "Mechanical Ventilator & Blood Warming Sys"},
    {"call_sign": "MEDIC-301", "vehicle_type": "BLS", "latitude": 40.7250, "longitude": -74.0050, "status": "AVAILABLE", "crew": "Basic Life Support Crew 1", "equipment": "AED, O2, Splints, Hemostatic Dressings"},
    {"call_sign": "MEDIC-302", "vehicle_type": "BLS", "latitude": 40.7120, "longitude": -74.0120, "status": "AVAILABLE", "crew": "Basic Life Support Crew 2", "equipment": "AED, O2, Splints, Hemostatic Dressings"},
    {"call_sign": "MEDIC-303", "vehicle_type": "BLS", "latitude": 40.7410, "longitude": -73.9960, "status": "AVAILABLE", "crew": "Basic Life Support Crew 3", "equipment": "AED, O2, Splints, Hemostatic Dressings"},
    {"call_sign": "MEDIC-304", "vehicle_type": "BLS", "latitude": 40.7620, "longitude": -73.9650, "status": "AVAILABLE", "crew": "Basic Life Support Crew 4", "equipment": "AED, O2, Splints, Hemostatic Dressings"},
    {"call_sign": "SKYMED-1", "vehicle_type": "AIR", "latitude": 40.7720, "longitude": -73.9550, "status": "AVAILABLE", "crew": "Flight Paramedic / Flight Nurse", "equipment": "Air Critical Care / Full ICU Suite"},
    {"call_sign": "SKYMED-2", "vehicle_type": "AIR", "latitude": 40.7020, "longitude": -74.0200, "status": "AVAILABLE", "crew": "Flight Paramedic / Flight Nurse", "equipment": "Air Critical Care / Full ICU Suite"},
    {"call_sign": "RESCUE-104", "vehicle_type": "ALS", "latitude": 40.7180, "longitude": -73.9980, "status": "AVAILABLE", "crew": "Paramedic Unit Delta", "equipment": "Advanced Cardiac Care & Monitor Defib"}
]

INITIAL_EMERGENCIES = [
    {
        "code": "EMRG-2026-901",
        "caller_name": "Officer Miller",
        "caller_phone": "911-DIRECT-CH2",
        "location_name": "7th Ave & 34th St, Penn Station Plaza",
        "latitude": 40.7505,
        "longitude": -73.9934,
        "chief_complaint": "64-year-old male with sudden crushing chest pain radiating to left jaw and left arm. Diaphoretic, pale, acute shortness of breath. History of coronary stenting.",
        "patient_age": 64,
        "patient_gender": "M",
        "vitals_bp": "85/54",
        "vitals_hr": 132,
        "vitals_spo2": 90,
        "vitals_gcs": 14
    },
    {
        "code": "EMRG-2026-902",
        "caller_name": "Dr. Sarah Chen",
        "caller_phone": "555-0199",
        "location_name": "Washington Square Park North",
        "latitude": 40.7315,
        "longitude": -73.9970,
        "chief_complaint": "58-year-old female with acute onset right facial droop, slurred expressive speech, and complete right hemiparesis. Symptoms began 22 minutes ago. Suspected acute ischemic stroke.",
        "patient_age": 58,
        "patient_gender": "F",
        "vitals_bp": "178/104",
        "vitals_hr": 92,
        "vitals_spo2": 96,
        "vitals_gcs": 12
    },
    {
        "code": "EMRG-2026-903",
        "caller_name": "Highway Patrol Unit 4",
        "caller_phone": "911-NYSP-04",
        "location_name": "FDR Drive & Houston St Exit",
        "latitude": 40.7210,
        "longitude": -73.9720,
        "chief_complaint": "Major motor vehicle collision, entrapped 29-year-old driver with severe polytrauma, open bilateral femur fractures, significant blood loss, and blunt chest trauma.",
        "patient_age": 29,
        "patient_gender": "M",
        "vitals_bp": "78/45",
        "vitals_hr": 144,
        "vitals_spo2": 86,
        "vitals_gcs": 9
    }
]


def seed_database(db: Session):
    """Checks database content and seeds default facilities, fleet, and incidents if empty."""
    if db.query(Hospital).first() is not None:
        logger.info("Database already seeded with hospitals. Skipping seed.")
        return

    logger.info("Seeding AEGIS database with default hospitals, resources, and fleet...")

    # 1. Seed Hospitals & Granular Resources
    hosp_map = {}
    for h_data in INITIAL_HOSPITALS:
        hosp = Hospital(
            name=h_data["name"],
            code=h_data["code"],
            address=h_data["address"],
            latitude=h_data["latitude"],
            longitude=h_data["longitude"],
            contact_phone=h_data["contact_phone"],
            trauma_level=h_data["trauma_level"],
            total_beds=h_data["total_beds"],
            available_beds=h_data["available_beds"],
            icu_total=h_data["icu_total"],
            icu_available=h_data["icu_available"],
            er_capacity=h_data["er_capacity"],
            er_current_load=h_data["er_current_load"],
            has_cath_lab=h_data["has_cath_lab"],
            has_stroke_center=h_data["has_stroke_center"],
            has_ct_scanner=h_data["has_ct_scanner"],
            has_mri=h_data["has_mri"],
            has_burn_unit=h_data["has_burn_unit"],
            has_pediatric_icu=h_data["has_pediatric_icu"],
            status=h_data["status"],
            ibm_z_connected=h_data["ibm_z_connected"],
            ibm_z_node_id=h_data["ibm_z_node_id"]
        )
        hosp.specialties = h_data["specialties"]
        db.add(hosp)
        db.flush()
        hosp_map[h_data["code"]] = hosp

        # Add resources
        db.add(HospitalResource(hospital_id=hosp.id, resource_type="ICU_BED", total_units=hosp.icu_total, available_units=hosp.icu_available))
        db.add(HospitalResource(hospital_id=hosp.id, resource_type="VENTILATOR", total_units=15, available_units=6))
        if hosp.has_cath_lab:
            db.add(HospitalResource(hospital_id=hosp.id, resource_type="CATH_LAB", total_units=3, available_units=1))
        if hosp.has_stroke_center:
            db.add(HospitalResource(hospital_id=hosp.id, resource_type="STROKE_UNIT", total_units=8, available_units=3))
        if hosp.has_ct_scanner:
            db.add(HospitalResource(hospital_id=hosp.id, resource_type="CT_SCANNER", total_units=2, available_units=2))
        db.add(HospitalResource(hospital_id=hosp.id, resource_type="BLOOD_O_NEG", total_units=30, available_units=18))

    # 2. Seed Fleet
    for a_data in INITIAL_AMBULANCES:
        amb = Ambulance(
            call_sign=a_data["call_sign"],
            vehicle_type=a_data["vehicle_type"],
            latitude=a_data["latitude"],
            longitude=a_data["longitude"],
            status=a_data["status"],
            paramedic_crew=a_data["crew"],
            equipment_level=a_data["equipment"]
        )
        db.add(amb)

    db.commit()

    # 3. Seed Initial Emergencies & Compute Baseline Recommendations
    for e_data in INITIAL_EMERGENCIES:
        triage = EmergencyClassifier.classify(
            chief_complaint=e_data["chief_complaint"],
            patient_age=e_data.get("patient_age"),
            patient_gender=e_data.get("patient_gender"),
            vitals_bp=e_data.get("vitals_bp"),
            vitals_hr=e_data.get("vitals_hr"),
            vitals_spo2=e_data.get("vitals_spo2"),
            vitals_gcs=e_data.get("vitals_gcs")
        )

        emrg = Emergency(
            emergency_code=e_data["code"],
            caller_name=e_data["caller_name"],
            caller_phone=e_data["caller_phone"],
            location_name=e_data["location_name"],
            latitude=e_data["latitude"],
            longitude=e_data["longitude"],
            severity=triage["severity"],
            category=triage["category"],
            patient_age=e_data.get("patient_age"),
            patient_gender=e_data.get("patient_gender"),
            chief_complaint=e_data["chief_complaint"],
            vitals_bp=e_data.get("vitals_bp"),
            vitals_hr=e_data.get("vitals_hr"),
            vitals_spo2=e_data.get("vitals_spo2"),
            vitals_gcs=e_data.get("vitals_gcs"),
            ai_classification=triage["ai_classification"],
            status="REPORTED"
        )
        emrg.required_specialties = triage["required_specialties"]
        emrg.required_resources = triage["required_resources"]
        db.add(emrg)
        db.flush()

        # Generate recommendation leaderboard
        RecommendationEngine.compute_recommendations(db, emrg, save_to_db=True)

    db.commit()
    logger.info("AEGIS database seed complete.")
