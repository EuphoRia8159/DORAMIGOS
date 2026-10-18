"""End-to-End Live Server Verification Script.

Tests the live running server at http://127.0.0.1:8000.
"""

import httpx

def main():
    print("Testing live AEGIS server...")
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=10.0) as client:
        # 1. Health & Root HTML
        r_root = client.get("/")
        assert r_root.status_code == 200
        assert "AEGIS" in r_root.text
        print(f"[PASS] Root index.html served successfully ({len(r_root.text)} bytes)")

        # 2. Static CSS and JS
        for asset in [
            "/static/css/styles.css",
            "/static/js/api.js",
            "/static/js/websocket.js",
            "/static/js/map.js",
            "/static/js/app.js"
        ]:
            r = client.get(asset)
            assert r.status_code == 200
            print(f"[PASS] Static asset {asset} loaded ({len(r.text)} bytes)")

        # 3. Hospitals API
        r_hosp = client.get("/api/hospitals")
        assert r_hosp.status_code == 200
        hospitals = r_hosp.json()
        assert len(hospitals) >= 8
        print(f"[PASS] Hospitals API returned {len(hospitals)} facilities")

        # 4. Ambulances API
        r_amb = client.get("/api/ambulances")
        assert r_amb.status_code == 200
        ambulances = r_amb.json()
        assert len(ambulances) >= 12
        print(f"[PASS] Ambulances API returned {len(ambulances)} fleet units")

        # 5. Emergencies & Recommendation Engine
        emrg_payload = {
            "caller_name": "Highway Patrol",
            "caller_phone": "911-DIRECT",
            "location_name": "Route 9A / West Side Highway",
            "latitude": 40.7450,
            "longitude": -74.0080,
            "chief_complaint": "Multi-car collision, entrapped driver with crushed extremity and suspected internal hemorrhage",
            "patient_age": 35,
            "patient_gender": "M",
            "vitals_bp": "80/50",
            "vitals_hr": 142,
            "vitals_spo2": 88,
            "vitals_gcs": 9
        }
        r_emrg = client.post("/api/emergencies", json=emrg_payload)
        assert r_emrg.status_code == 201
        new_emrg = r_emrg.json()
        code = new_emrg["emergency_code"]
        cat = new_emrg["category"]
        sev = new_emrg["severity"]
        print(f"[PASS] Created emergency: {code} [{cat}] ({sev})")

        # 6. Recommendations
        r_rec = client.get(f"/api/recommendations/{new_emrg['id']}")
        assert r_rec.status_code == 200
        recs = r_rec.json()
        top = recs["recommendations"][0]
        h_name = top["hospital_name"]
        h_score = top["composite_score"]
        h_eta = top["estimated_transit_minutes"]
        print(f"[PASS] Top recommendation: Rank #{top['rank']} - {h_name} (Score: {h_score}, ETA: {h_eta}m)")

        # 7. Simulation Tick & Status
        r_sim = client.post("/api/simulation/tick")
        assert r_sim.status_code == 200
        print(f"[PASS] Simulation tick executed: {r_sim.json()['type']}")

        # 8. Surge Incident Simulation
        r_surge = client.post("/api/simulation/surge", json={
            "hospital_id": hospitals[0]["id"],
            "incoming_patients": 8,
            "incident_name": "Live Surge Test"
        })
        assert r_surge.status_code == 200
        print(f"[PASS] Mass casualty surge simulated at {r_surge.json()['hospital_name']}: new load {r_surge.json()['new_er_load']}")

        # 9. IBM Z Status & CICS Transaction
        r_ibm = client.get("/api/ibm-z/status")
        assert r_ibm.status_code == 200
        ibm_status = r_ibm.json()
        print(f"[PASS] IBM Z status: Mode={ibm_status['mode']}, Sysplex={ibm_status['active_sysplex_node']}, Latency={ibm_status['average_latency_ms']}ms")

        r_ehr = client.post("/api/ibm-z/patient-lookup", json={"national_health_id": "NHID-9921-A"})
        assert r_ehr.status_code == 200
        ehr = r_ehr.json()
        p_name = ehr["patient_name"]
        b_type = ehr["blood_type"]
        c_tok = ehr["cics_audit_token"]
        print(f"[PASS] IBM Z CICS EHR Lookup: Patient={p_name}, Blood={b_type}, CICS Token={c_tok}")

        # 10. Capacity Sync to IBM Z
        r_sync = client.post("/api/ibm-z/sync-capacity", json={"hospital_code": "STJUDE-01"})
        assert r_sync.status_code == 200
        seq = r_sync.json()["mainframe_sequence_no"]
        print(f"[PASS] Capacity Sync committed to z/OS Sysplex with sequence #{seq}")

        print("\n=======================================================")
        print("ALL 10 LIVE SERVER VERIFICATION CHECKS PASSED PERFECTLY!")
        print("=======================================================")

if __name__ == "__main__":
    main()
