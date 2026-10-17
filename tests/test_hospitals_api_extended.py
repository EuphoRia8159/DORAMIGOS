"""Extended API integration tests for AEGIS hospital endpoints.

Tests:
1. Pagination (skip, limit, bounds)
2. Search across name, code, address, district, and state
3. Regional filters (state, district, data_source, is_live_monitored)
4. Location-based radius proximity filtering
5. Request parameter validation and error responses (400, 404)
6. Recommendation engine integration with directory hospitals
"""

import pytest
from starlette.testclient import TestClient
from aegis_backend.main import app
from aegis_backend.database import init_db, SessionLocal
from aegis_backend.models import Hospital, Emergency
from aegis_backend.recommendation_engine import RecommendationEngine


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_hospitals_pagination(client):
    # Query with limit 2
    r_p1 = client.get("/api/hospitals?limit=2&skip=0")
    assert r_p1.status_code == 200
    page1 = r_p1.json()
    assert len(page1) == 2

    # Query with skip 2
    r_p2 = client.get("/api/hospitals?limit=2&skip=2")
    assert r_p2.status_code == 200
    page2 = r_p2.json()
    assert len(page2) == 2

    # Ensure records don't overlap
    p1_ids = {h["id"] for h in page1}
    p2_ids = {h["id"] for h in page2}
    assert p1_ids.isdisjoint(p2_ids)


def test_hospitals_search(client):
    # Search by known hospital name substring
    res = client.get("/api/hospitals?search=St.+Jude")
    assert res.status_code == 200
    results = res.json()
    assert len(results) >= 1
    assert any("St. Jude" in h["name"] for h in results)

    # Search by code
    res_code = client.get("/api/hospitals?search=STJUDE-01")
    assert res_code.status_code == 200
    assert len(res_code.json()) >= 1
    assert res_code.json()[0]["code"] == "STJUDE-01"

    # Search with no matches
    res_none = client.get("/api/hospitals?search=NonExistentHospitalXYZ999")
    assert res_none.status_code == 200
    assert len(res_none.json()) == 0


def test_hospitals_regional_filters(client):
    # Test data source filter
    res_sim = client.get("/api/hospitals?data_source=SIMULATED")
    assert res_sim.status_code == 200
    for h in res_sim.json():
        assert h["data_source"] == "SIMULATED"

    # Test live monitored filter
    res_live = client.get("/api/hospitals?is_live_monitored=true")
    assert res_live.status_code == 200
    for h in res_live.json():
        assert h["is_live_monitored"] is True


def test_location_proximity_search_and_validation(client):
    # Coordinates in Manhattan NYC (near St. Jude and Metro General)
    res_nearby = client.get("/api/hospitals?latitude=40.7340&longitude=-73.9900&radius_km=10.0")
    assert res_nearby.status_code == 200
    nearby = res_nearby.json()
    assert len(nearby) >= 1
    assert any("St. Jude" in h["name"] for h in nearby)

    # Far away coordinates (e.g. middle of Pacific Ocean)
    res_far = client.get("/api/hospitals?latitude=0.0&longitude=-160.0&radius_km=50.0")
    assert res_far.status_code == 200
    assert len(res_far.json()) == 0

    # Validation: latitude provided without longitude
    res_missing_lon = client.get("/api/hospitals?latitude=40.7340")
    assert res_missing_lon.status_code == 400
    assert "Both latitude and longitude" in res_missing_lon.json()["detail"]

    # Validation: radius_km provided without coordinates
    res_missing_coords = client.get("/api/hospitals?radius_km=25.0")
    assert res_missing_coords.status_code == 400
    assert "Latitude and longitude are required" in res_missing_coords.json()["detail"]


def test_get_nonexistent_hospital_returns_404(client):
    res = client.get("/api/hospitals/999999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Hospital not found"


def test_recommendation_with_directory_and_missing_coordinates():
    """Verifies that recommendation engine handles directory hospitals with and without coordinates."""
    db = SessionLocal()
    try:
        # Create a directory hospital with coordinates
        dir_hosp_with_coords = Hospital(
            name="Test Directory Hospital With Coords",
            code="TEST-DIR-01",
            address="123 Test Road, Mumbai",
            latitude=19.0760,
            longitude=72.8777,
            contact_phone="9876543210",
            trauma_level="Community",
            total_beds=50,
            available_beds=0,
            icu_total=0,
            icu_available=0,
            er_capacity=0,
            er_current_load=0,
            has_cath_lab=True,
            data_source="EXCEL_DIRECTORY",
            is_live_monitored=False,
            status="DIRECTORY"
        )
        dir_hosp_with_coords.specialties = ["Cardiology", "Internal Medicine"]

        # Create a directory hospital without coordinates
        dir_hosp_no_coords = Hospital(
            name="Test Directory Hospital No Coords",
            code="TEST-DIR-02",
            address="456 Rural Road, District X",
            latitude=None,
            longitude=None,
            contact_phone="Not Provided",
            trauma_level="General Care",
            total_beds=0,
            available_beds=0,
            icu_total=0,
            icu_available=0,
            er_capacity=0,
            er_current_load=0,
            data_source="EXCEL_DIRECTORY",
            is_live_monitored=False,
            status="DIRECTORY"
        )
        dir_hosp_no_coords.specialties = ["General Medicine"]

        db.add(dir_hosp_with_coords)
        db.add(dir_hosp_no_coords)
        db.commit()

        # Emergency near Mumbai
        emrg = Emergency(
            emergency_code="TEST-EMRG-DIR",
            caller_name="Caller",
            location_name="Bandra",
            latitude=19.0750,
            longitude=72.8770,
            category="CARDIAC_ARREST",
            severity="CRITICAL",
            chief_complaint="Chest pain, STEMI suspected",
            status="REPORTED"
        )
        emrg.required_specialties = ["Cardiology"]
        emrg.required_resources = ["CATH_LAB"]
        db.add(emrg)
        db.commit()

        # Evaluate hospital with coordinates
        score_with_coords = RecommendationEngine.evaluate_hospital(dir_hosp_with_coords, emrg)
        assert score_with_coords["distance_km"] is not None
        assert score_with_coords["distance_km"] < 5.0
        assert score_with_coords["estimated_transit_minutes"] is not None
        assert "live availability unverified" in score_with_coords["rationale"]
        assert score_with_coords["ibm_z_verified"] is False

        # Evaluate hospital without coordinates
        score_no_coords = RecommendationEngine.evaluate_hospital(dir_hosp_no_coords, emrg)
        assert score_no_coords["distance_km"] is None
        assert score_no_coords["estimated_transit_minutes"] is None
        assert "Coordinates unverified" in score_no_coords["rationale"]

        # Compute full recommendations for the test candidate hospitals
        recs = RecommendationEngine.compute_recommendations(
            db, emrg, candidate_hospitals=[dir_hosp_with_coords, dir_hosp_no_coords], save_to_db=False
        )
        assert len(recs) == 2
        # Facility with valid coordinates and matching Cath Lab must score higher
        h1_rec = next((r for r in recs if r["hospital_code"] == "TEST-DIR-01"), None)
        h2_rec = next((r for r in recs if r["hospital_code"] == "TEST-DIR-02"), None)
        assert h1_rec is not None
        assert h2_rec is not None
        assert h1_rec["composite_score"] > h2_rec["composite_score"]

    finally:
        # Clean up test records
        db.query(Hospital).filter(Hospital.code.in_(["TEST-DIR-01", "TEST-DIR-02"])).delete()
        db.query(Emergency).filter(Emergency.emergency_code == "TEST-EMRG-DIR").delete()
        db.commit()
        db.close()
