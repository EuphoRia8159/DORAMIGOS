"""Unit tests for Dynamic Hospital Recommendation Engine."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aegis_backend.database import Base
from aegis_backend.models import Hospital, Emergency
from aegis_backend.recommendation_engine import (
    haversine_distance_km,
    estimate_transit_time_minutes,
    RecommendationEngine
)


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


def test_distance_and_transit_calculation():
    # NYC Coordinates: Midtown (40.7580, -73.9855) to Downtown (40.7128, -74.0060)
    dist = haversine_distance_km(40.7580, -73.9855, 40.7128, -74.0060)
    assert 4.0 <= dist <= 6.5
    eta = estimate_transit_time_minutes(dist)
    assert eta > 5.0


def test_recommendation_scoring_and_ranking(test_db):
    # Hospital A: Specialized Level 1 Trauma, Cath Lab, 10 ICU beds open, IBM Z verified
    hosp_a = Hospital(
        name="St. Alpha Trauma Center",
        code="ALPHA-1",
        address="100 Main St",
        latitude=40.7300,
        longitude=-73.9900,
        contact_phone="555-0001",
        trauma_level="Level 1",
        total_beds=200,
        available_beds=40,
        icu_total=30,
        icu_available=10,
        er_capacity=40,
        er_current_load=20,
        has_cath_lab=True,
        has_stroke_center=True,
        has_ct_scanner=True,
        ibm_z_connected=True,
        status="OPERATIONAL"
    )
    hosp_a.specialties = ["Cardiology", "Trauma Surgery", "Critical Care"]

    # Hospital B: Community Hospital, No Cath Lab, 0 ICU beds, ER at 100% load
    hosp_b = Hospital(
        name="Beta Community Clinic",
        code="BETA-2",
        address="200 West St",
        latitude=40.7310,
        longitude=-73.9910,
        contact_phone="555-0002",
        trauma_level="Community",
        total_beds=50,
        available_beds=2,
        icu_total=5,
        icu_available=0,
        er_capacity=20,
        er_current_load=20,
        has_cath_lab=False,
        has_stroke_center=False,
        has_ct_scanner=True,
        ibm_z_connected=False,
        status="OPERATIONAL"
    )
    hosp_b.specialties = ["Internal Medicine"]

    test_db.add(hosp_a)
    test_db.add(hosp_b)
    test_db.commit()

    # Emergency: Cardiac STEMI
    emrg = Emergency(
        emergency_code="TEST-EMRG-01",
        location_name="Downtown Square",
        latitude=40.7305,
        longitude=-73.9905,
        category="CARDIAC_ARREST",
        severity="CRITICAL",
        chief_complaint="Chest pain, STEMI suspected",
        status="REPORTED"
    )
    emrg.required_specialties = ["Cardiology", "Critical Care"]
    emrg.required_resources = ["CATH_LAB", "ICU_BED"]
    test_db.add(emrg)
    test_db.commit()

    # Evaluate recommendations
    recs = RecommendationEngine.compute_recommendations(test_db, emrg, save_to_db=True)
    assert len(recs) == 2
    # Alpha should be ranked #1 with significantly higher score
    assert recs[0]["hospital_name"] == "St. Alpha Trauma Center"
    assert recs[0]["rank"] == 1
    assert recs[0]["composite_score"] > recs[1]["composite_score"]
    assert recs[0]["ibm_z_verified"] is True
    assert "Active Cath Lab available" in recs[0]["rationale"]
    assert "Lacks dedicated Cardiac Cath Lab" in recs[1]["rationale"]
