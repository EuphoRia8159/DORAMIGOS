"""Unit & Integration tests for Simulation Engine."""

import pytest
from starlette.testclient import TestClient
from aegis_backend.main import app
from aegis_backend.simulation import simulation_engine


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_simulation_status_and_tick(client):
    status_res = client.get("/api/simulation/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "active" in status_data
    assert "tracked_ambulances" in status_data

    # Manual tick
    tick_res = client.post("/api/simulation/tick")
    assert tick_res.status_code == 200
    tick_data = tick_res.json()
    assert tick_data["type"] == "SIMULATION_TICK"
    assert "tick" in tick_data


def test_mass_casualty_surge_trigger(client):
    hosp_res = client.get("/api/hospitals")
    hospitals = hosp_res.json()
    assert len(hospitals) >= 1
    target_hosp = hospitals[0]

    surge_res = client.post("/api/simulation/surge", json={
        "hospital_id": target_hosp["id"],
        "incoming_patients": 10,
        "incident_name": "Mass Transit Collision Drill"
    })
    assert surge_res.status_code == 200
    surge_data = surge_res.json()
    assert surge_data["success"] is True
    assert surge_data["new_er_load"] >= surge_data["previous_load"]
