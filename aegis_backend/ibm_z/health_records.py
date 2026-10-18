"""IBM Z Health Records Adapter.

Integrates with mainframe EHR / Master Patient Index systems via z/OS Connect
to retrieve critical baseline records, allergies, blood type, and directives.
"""

import time
import uuid
from typing import Dict, Any, Optional
from aegis_backend.ibm_z.client import ibm_z_client


# Realistic simulated mainframe health records for demonstration & testing
MOCK_PATIENT_DB = {
    "NHID-9921-A": {
        "mainframe_id": "MF-PAT-009921",
        "patient_name": "Eleanor Vance",
        "blood_type": "O-NEG",
        "allergies": ["Penicillin", "Morphine", "Iodine Contrast"],
        "critical_conditions": ["Coronary Artery Disease (CAD)", "Type 2 Diabetes"],
        "dnr_order": False,
        "cardiac_history": True,
        "prior_surgeries": ["Coronary Angioplasty (2022)", "Appendectomy (2010)"],
        "emergency_contacts": ["Marcus Vance (Spouse) - 555-0192"]
    },
    "NHID-4410-B": {
        "mainframe_id": "MF-PAT-004410",
        "patient_name": "David Sterling",
        "blood_type": "A-POS",
        "allergies": ["Latex", "Sulfa Drugs"],
        "critical_conditions": ["Atrial Fibrillation", "Hypertension"],
        "dnr_order": False,
        "cardiac_history": True,
        "prior_surgeries": ["Pacemaker Implantation (2021)"],
        "emergency_contacts": ["Sarah Sterling (Daughter) - 555-0834"]
    },
    "NHID-1088-C": {
        "mainframe_id": "MF-PAT-001088",
        "patient_name": "Elena Rostova",
        "blood_type": "B-POS",
        "allergies": ["Aspirin", "NSAIDs"],
        "critical_conditions": ["Severe Asthma", "Peanut Anaphylaxis"],
        "dnr_order": False,
        "cardiac_history": False,
        "prior_surgeries": ["None reported"],
        "emergency_contacts": ["Dmitri Rostov (Brother) - 555-0421"]
    }
}


class IBMZHealthRecordsService:
    """Queries mainframe EHR systems for verified patient medical history."""

    @classmethod
    async def lookup_patient(
        cls,
        national_health_id: str,
        patient_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Queries z/OS Connect EHR service `GetPatientEmergencyProfile` or mock database."""
        start_time = time.perf_counter()
        
        # Payload structured to match CPYEMERG copybook COMMAREA
        cics_payload = {
            "CPYEMERG_IN": {
                "REQ_HEADER": {
                    "SYSTEM_ID": "AEGIS01",
                    "QUERY_TYPE": "EMERG_PROFILE",
                    "TIMESTAMP": time.strftime("%Y%m%d%H%M%S")
                },
                "PATIENT_QUERY": {
                    "NAT_HEALTH_ID": national_health_id.strip().upper(),
                    "PATIENT_NAME": (patient_name or "").upper()[:30]
                }
            }
        }

        # Execute through z/OS Connect adapter
        cics_response = await ibm_z_client.execute_cics_transaction(
            service_name="GetPatientEmergencyProfile",
            payload=cics_payload,
            transaction_id="EHR1"
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        audit_token = f"ZOS-{uuid.uuid4().hex[:8].upper()}-CICS"

        # Check mock records
        key = national_health_id.strip().upper()
        if key in MOCK_PATIENT_DB:
            rec = MOCK_PATIENT_DB[key]
            return {
                "record_found": True,
                "mainframe_id": rec["mainframe_id"],
                "patient_name": rec["patient_name"],
                "blood_type": rec["blood_type"],
                "allergies": rec["allergies"],
                "critical_conditions": rec["critical_conditions"],
                "dnr_order": rec["dnr_order"],
                "cardiac_history": rec["cardiac_history"],
                "prior_surgeries": rec["prior_surgeries"],
                "emergency_contacts": rec["emergency_contacts"],
                "cics_audit_token": audit_token,
                "response_latency_ms": elapsed_ms,
                "integration_mode": cics_response.get("zos_header", {}).get("mode", "MOCK_SANDBOX")
            }
        else:
            # Synthetic fallback for unrecognized patient ID
            return {
                "record_found": False,
                "mainframe_id": f"MF-UNKNOWN-{key[-4:] if len(key) >= 4 else '0000'}",
                "patient_name": patient_name or "Unknown Patient",
                "blood_type": "UNKNOWN (Crossmatch required)",
                "allergies": ["No verified mainframe record"],
                "critical_conditions": ["Record not registered in enterprise index"],
                "dnr_order": False,
                "cardiac_history": False,
                "prior_surgeries": [],
                "emergency_contacts": [],
                "cics_audit_token": audit_token,
                "response_latency_ms": elapsed_ms,
                "integration_mode": cics_response.get("zos_header", {}).get("mode", "MOCK_SANDBOX")
            }
