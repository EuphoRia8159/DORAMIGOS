"""Integration tests for AEGIS FastAPI endpoints."""

import pytest
from starlette.testclient import TestClient
from aegis_backend.main import app
from aegis_backend.database import init_db


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "AEGIS" in data["app"]


def test_hospitals_endpoints(client):
    # List hospitals
    response = client.get("/api/hospitals")
    assert response.status_code == 200
    hospitals = response.json()
    assert len(hospitals) >= 1
    hosp_id = hospitals[0]["id"]

    # Get single hospital
    single_res = client.get(f"/api/hospitals/{hosp_id}")
    assert single_res.status_code == 200
    assert single_res.json()["name"] == hospitals[0]["name"]

    # Update hospital capacity
    cap_update = client.patch(f"/api/hospitals/{hosp_id}/capacity", json={
        "available_beds": 25,
        "icu_available": 6,
        "er_current_load": 18
    })
    assert cap_update.status_code == 200
    assert cap_update.json()["available_beds"] == 25
    assert cap_update.json()["icu_available"] == 6


def test_ambulances_endpoints(client):
    response = client.get("/api/ambulances")
    assert response.status_code == 200
    fleet = response.json()
    assert len(fleet) >= 1
    amb_id = fleet[0]["id"]

    # Update location
    loc_res = client.patch(f"/api/ambulances/{amb_id}/location", json={
        "latitude": 40.7350,
        "longitude": -73.9920,
        "speed_kmh": 48.0
    })
    assert loc_res.status_code == 200
    assert loc_res.json()["latitude"] == 40.7350


def test_emergency_intake_and_recommendation_flow(client):
    # 1. Report new emergency
    emrg_payload = {
        "caller_name": "Test Dispatcher",
        "caller_phone": "555-TEST",
        "location_name": "Times Square Intersection",
        "latitude": 40.7580,
        "longitude": -73.9855,
        "chief_complaint": "Acute severe crushing chest pain, dyspneic, diaphoresis, suspected STEMI",
        "patient_age": 62,
        "patient_gender": "M",
        "vitals_bp": "82/50",
        "vitals_hr": 138,
        "vitals_spo2": 88,
        "vitals_gcs": 14
    }
    create_res = client.post("/api/emergencies", json=emrg_payload)
    assert create_res.status_code == 201
    emrg_data = create_res.json()
    emrg_id = emrg_data["id"]
    assert emrg_data["category"] == "CARDIAC_ARREST"
    assert emrg_data["severity"] == "CRITICAL"

    # 2. Query recommendations
    recs_res = client.get(f"/api/recommendations/{emrg_id}")
    assert recs_res.status_code == 200
    recs_data = recs_res.json()
    assert len(recs_data["recommendations"]) >= 1
    top_rec = recs_data["recommendations"][0]
    assert top_rec["rank"] == 1
    assert top_rec["composite_score"] > 0

    # 3. Force recalculate
    recalc_res = client.post(f"/api/recommendations/{emrg_id}/recalculate")
    assert recalc_res.status_code == 200

    # 4. Dispatch available ambulance
    amb_res = client.get("/api/ambulances?status=AVAILABLE")
    ambulances = amb_res.json()
    assert len(ambulances) >= 1
    assigned_amb = ambulances[0]

    dispatch_res = client.post(f"/api/emergencies/{emrg_id}/dispatch", json={
        "ambulance_id": assigned_amb["id"],
        "hospital_id": top_rec["hospital_id"],
        "notes": "Code STEMI priority dispatch"
    })
    assert dispatch_res.status_code == 200
    dispatched_emrg = dispatch_res.json()
    assert dispatched_emrg["status"] == "AMBULANCE_DISPATCHED"
    assert dispatched_emrg["assigned_ambulance_id"] == assigned_amb["id"]
    assert dispatched_emrg["assigned_hospital_id"] == top_rec["hospital_id"]


def test_analytics_endpoints(client):
    overview_res = client.get("/api/analytics/overview")
    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert "hospitals" in overview
    assert "fleet" in overview
    assert "emergencies" in overview
    assert overview["hospitals"]["total"] >= 1

    events_res = client.get("/api/analytics/events?limit=10")
    assert events_res.status_code == 200
    assert isinstance(events_res.json(), list)
