"""Small, self-contained AEGIS recommendation API for the Streamlit demo.

Run with: uvicorn backend_api:app --host 127.0.0.1 --port 8000
This API accepts the current demo resource snapshot from Streamlit and performs
eligibility checks/ranking server-side. All values and ETA estimates are synthetic.
"""
from math import inf
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="AEGIS Demo Recommendation API",
    version="1.0.0",
    description="Backend service for the AEGIS Streamlit hackathon prototype. Synthetic data only.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SCENARIOS = {
    "Cardiac emergency (demo)": {"specialty": "cardiology", "requires_icu": True, "ambulance_equipment": "Advanced"},
    "Severe respiratory distress (demo)": {"specialty": "respiratory", "requires_icu": True, "ambulance_equipment": "Advanced"},
    "Major trauma (demo)": {"specialty": "trauma", "requires_icu": False, "ambulance_equipment": "Advanced"},
    "Critical pediatric emergency (demo)": {"specialty": "pediatric", "requires_icu": True, "ambulance_equipment": "Advanced"},
}
WORKLOAD_SCORE = {"Low": 1, "Medium": 2, "High": 3}


class RecommendationRequest(BaseModel):
    scenario_name: str
    hospitals: list[dict[str, Any]] = Field(default_factory=list)
    ambulances: list[dict[str, Any]] = Field(default_factory=list)


@app.get("/")
def root():
    return {"service": "AEGIS Demo Recommendation API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "healthy", "service": "aegis-demo-api", "mode": "SIMULATED"}


@app.get("/api/hospitals")
def list_hospitals():
    return {"mode": "client-supplied-demo-state", "items": []}


@app.get("/api/ambulances")
def list_ambulances():
    return {"mode": "client-supplied-demo-state", "items": []}


@app.post("/api/v1/recommendations")
def recommend(request: RecommendationRequest):
    """Return eligibility and ranked recommendations for the submitted demo snapshot."""
    if request.scenario_name not in SCENARIOS:
        return {"scenario": request.scenario_name, "recommendations": [], "error": "Unknown demo scenario"}
    req = SCENARIOS[request.scenario_name]
    compatible = [
        a for a in request.ambulances
        if str(a.get("status", "")).lower() == "available"
        and (req["ambulance_equipment"] != "Advanced" or a.get("equipment") == "Advanced")
    ]
    results = []
    for original in request.hospitals:
        hospital = dict(original)
        reasons = []
        eligible = True
        if not hospital.get("emergency_department", False):
            eligible = False
            reasons.append("Emergency department unavailable")
        if req["specialty"] not in hospital.get("specialties", []):
            eligible = False
            reasons.append(f"Required service unavailable: {req['specialty']}")
        if req["requires_icu"] and int(hospital.get("icu_available", 0)) < 1:
            eligible = False
            reasons.append("No simulated ICU beds available")
        if int(hospital.get("emergency_beds_available", 0)) < 1:
            eligible = False
            reasons.append("No simulated emergency beds available")
        if not compatible:
            eligible = False
            reasons.append("No available ambulance meets the configured equipment requirement")

        if eligible:
            offsets = {"HOSP-A": 8, "HOSP-B": 12, "HOSP-C": 17, "HOSP-D": 14}
            ambulance = min(
                compatible,
                key=lambda a: int(a.get("eta_to_patient_min", 999)) + offsets.get(str(hospital.get("id")), 12),
            )
            travel = int(ambulance.get("eta_to_patient_min", 0)) + offsets.get(str(hospital.get("id")), 12)
            score = travel + WORKLOAD_SCORE.get(str(hospital.get("workload", "Medium")), 2) * 3
            reasons = [
                "Configured service requirement matched",
                "Simulated emergency capacity available",
                "Simulated ICU capacity available" if req["requires_icu"] else "ICU not required by this demo scenario",
                f"Compatible ambulance: {ambulance.get('id', 'Unknown')}",
                f"Simulated estimated arrival: {travel} minutes",
            ]
        else:
            ambulance, travel, score = None, None, None
        results.append({
            "hospital": hospital, "eligible": eligible, "ambulance": ambulance,
            "travel": travel, "score": score, "reasons": reasons,
        })
    results.sort(key=lambda r: (not r["eligible"], r["score"] if r["score"] is not None else inf))
    return {"scenario": request.scenario_name, "engine": "backend-api", "recommendations": results}
