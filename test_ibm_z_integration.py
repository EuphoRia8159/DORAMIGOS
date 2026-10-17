"""Integration tests for IBM Z Enterprise Mainframe Integration Layer."""

import pytest
from starlette.testclient import TestClient
from aegis_backend.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_ibm_z_status_diagnostics(client):
    response = client.get("/api/ibm-z/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["mode"] in ["MOCK_SANDBOX", "LIVE_ZOS_CONNECT"]
    assert "CICS" in data["cics_tran_id"] or "AEG1" in data["cics_tran_id"]
    assert "services_ready" in data
    assert data["services_ready"]["zos_connect_gateway"] is True
    assert "notice" in data
    # Verify honest transparency about mock sandbox vs live z/OS Connect
    assert "Sandbox" in data["notice"] or "z/OS" in data["notice"]


def test_ibm_z_patient_record_lookup(client):
    # Lookup registered patient
    req_payload = {
        "national_health_id": "NHID-9921-A",
        "patient_name": "Eleanor Vance"
    }
    response = client.post("/api/ibm-z/patient-lookup", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["record_found"] is True
    assert data["patient_name"] == "Eleanor Vance"
    assert data["blood_type"] == "O-NEG"
    assert "Penicillin" in data["allergies"]
    assert data["cardiac_history"] is True
    assert "cics_audit_token" in data


def test_ibm_z_capacity_ledger_sync(client):
    req_payload = {
        "hospital_code": "STJUDE-01"
    }
    response = client.post("/api/ibm-z/sync-capacity", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["hospital_code"] == "STJUDE-01"
    assert data["mainframe_sequence_no"] > 0
    assert "COMMITTED" in data["sync_status"]
