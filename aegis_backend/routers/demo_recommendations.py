"""Backend API for the Streamlit demo recommendation workflow."""

import math

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from aegis_backend.ibm_z.client import ibm_z_client


router = APIRouter(tags=["Demo Recommendations"])


SCENARIOS = {
    "Cardiac emergency (demo)": {
        "specialty": "cardiology",
        "requires_icu": True,
        "ambulance_equipment": "Advanced",
    },
    "Severe respiratory distress (demo)": {
        "specialty": "respiratory",
        "requires_icu": True,
        "ambulance_equipment": "Advanced",
    },
    "Major trauma (demo)": {
        "specialty": "trauma",
        "requires_icu": False,
        "ambulance_equipment": "Advanced",
    },
    "Critical pediatric emergency (demo)": {
        "specialty": "pediatric",
        "requires_icu": True,
        "ambulance_equipment": "Advanced",
    },
}

WORKLOAD_SCORE = {"Low": 1, "Medium": 2, "High": 3}
HOSPITAL_OFFSETS = {
    "HOSP-A": 8,
    "HOSP-B": 12,
    "HOSP-C": 17,
    "HOSP-D": 14,
}


class DemoRecommendationRequest(BaseModel):
    scenario_name: str
    hospitals: list[dict[str, Any]] = Field(default_factory=list)
    ambulances: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/api/v1/recommendations")
async def recommend_demo_hospitals(payload: DemoRecommendationRequest):
    """Rank the frontend's demo snapshot without creating database incidents."""

    requirements = SCENARIOS.get(payload.scenario_name)
    if requirements is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported demo scenario: {payload.scenario_name}",
        )

    available_ambulances = [
        ambulance
        for ambulance in payload.ambulances
        if ambulance.get("status") == "Available"
        and (
            requirements["ambulance_equipment"] != "Advanced"
            or ambulance.get("equipment") == "Advanced"
        )
    ]

    results = []

    for hospital in payload.hospitals:
        reasons = []
        eligible = True

        if not hospital.get("emergency_department", False):
            eligible = False
            reasons.append("Emergency department unavailable")

        specialties = hospital.get("specialties") or []
        if requirements["specialty"] not in specialties:
            eligible = False
            reasons.append(
                f"Required service unavailable: {requirements['specialty']}"
            )

        if requirements["requires_icu"] and hospital.get("icu_available", 0) < 1:
            eligible = False
            reasons.append("No simulated ICU beds available")

        if hospital.get("emergency_beds_available", 0) < 1:
            eligible = False
            reasons.append("No simulated emergency beds available")

        if not available_ambulances:
            eligible = False
            reasons.append(
                "No available ambulance meets the configured equipment requirement"
            )

        ambulance = None
        travel = None
        score = None

        if eligible:
            def travel_time(candidate):
                return (
                    candidate.get("eta_to_patient_min", 0)
                    + HOSPITAL_OFFSETS.get(hospital.get("id"), 14)
                )

            ambulance = min(available_ambulances, key=travel_time)
            travel = travel_time(ambulance)
            score = travel + WORKLOAD_SCORE.get(
                hospital.get("workload"), 1
            ) * 3

            reasons = [
                "Configured service requirement matched",
                "Simulated emergency capacity available",
                (
                    "Simulated ICU capacity available"
                    if requirements["requires_icu"]
                    else "ICU not required by this demo scenario"
                ),
                f"Compatible ambulance: {ambulance['id']}",
                f"Simulated estimated arrival: {travel} minutes",
            ]

        results.append({
            "hospital": hospital,
            "eligible": eligible,
            "ambulance": ambulance,
            "travel": travel,
            "score": score,
            "reasons": reasons,
        })

    results.sort(
        key=lambda result: (
            not result["eligible"],
            result["score"] if result["score"] is not None else math.inf,
        )
    )

    # Invoke the IBM Z adapter with the calculated demo decision.
    # Recommendation scoring remains in Python; this is not live mainframe scoring.
    ibm_z_integration = {
        "service": "EvaluateEmergencyDecision",
        "transaction_id": "AEG1",
        "mode": "UNKNOWN",
        "success": False,
        "latency_ms": None,
        "sysplex_node": None,
        "decision_computation": "Python demo scoring",
    }

    try:
        cics_result = await ibm_z_client.execute_cics_transaction(
            service_name="EvaluateEmergencyDecision",
            transaction_id="AEG1",
            payload={
                "scenario_name": payload.scenario_name,
                "decision_output": [
                    {
                        "hospital_id": item["hospital"].get("id"),
                        "eligible": item["eligible"],
                        "score": item["score"],
                        "reasons": item["reasons"],
                    }
                    for item in results
                ],
            },
        )

        zos_header = cics_result.get("zos_header", {})
        ibm_z_integration.update({
            "mode": zos_header.get(
                "mode", cics_result.get("mode", "UNKNOWN")
            ),
            "success": cics_result.get("success", False),
            "latency_ms": zos_header.get("execution_time_ms"),
            "sysplex_node": zos_header.get("sysplex_id"),
        })

    except Exception as exc:
        ibm_z_integration["error"] = str(exc)

    return {
        "engine": "backend-api",
        "recommendations": results,
        "ibm_z_integration": ibm_z_integration,
    }
