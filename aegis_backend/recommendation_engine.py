"""AEGIS Dynamic Hospital Recommendation Engine.

Computes multi-criteria ranked hospital recommendations by evaluating
clinical capabilities, real-time travel transit, bed & ICU headroom,
emergency department congestion, and IBM Z enterprise verification.
"""

import math
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from aegis_backend.config import settings
from aegis_backend.models import Hospital, Emergency, HospitalRecommendation, HospitalResource
from aegis_backend.classifier import CATEGORY_REQUIREMENTS


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the great-circle distance between two points in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)


def estimate_transit_time_minutes(distance_km: float) -> float:
    """Estimates emergency transit time in minutes incorporating urban speed and traffic factor."""
    adjusted_speed = settings.AVERAGE_AMBULANCE_SPEED_KMH / settings.RUSH_HOUR_TRAFFIC_MULTIPLIER
    travel_hours = distance_km / max(adjusted_speed, 10.0)
    travel_minutes = travel_hours * 60.0
    # Add standard dispatch & route acquisition buffer (2.0 min)
    return round(travel_minutes + 2.0, 1)


class RecommendationEngine:
    """Dynamic hospital scoring and optimization engine."""

    @classmethod
    def evaluate_hospital(
        cls,
        hospital: Hospital,
        emergency: Emergency,
    ) -> Dict[str, Any]:
        """Calculates multi-dimensional suitability scores for a given hospital and emergency."""
        # 1. Geographic Distance & Travel Time (only when coordinates are valid)
        has_valid_coords = (
            hospital.latitude is not None
            and hospital.longitude is not None
            and emergency.latitude is not None
            and emergency.longitude is not None
        )
        if has_valid_coords:
            dist_km = haversine_distance_km(
                emergency.latitude, emergency.longitude,
                hospital.latitude, hospital.longitude
            )
            eta_minutes = estimate_transit_time_minutes(dist_km)
            # Transit score: decays as ETA increases (100 at 0 min, 0 at 45+ min)
            transit_score = max(0.0, min(100.0, 100.0 - (eta_minutes * 2.2)))
        else:
            dist_km = None
            eta_minutes = None
            # Location coordinates unverified: low baseline transit score
            transit_score = 15.0

        # 2. Clinical Capability & Specialty Matching
        req_category = emergency.category or "GENERAL_MEDICAL"
        category_meta = CATEGORY_REQUIREMENTS.get(req_category, CATEGORY_REQUIREMENTS["GENERAL_MEDICAL"])
        
        capability_score = 100.0
        rationale_points = []
        
        # Check specific critical facilities
        if category_meta.get("needs_cath_lab"):
            if hospital.has_cath_lab:
                rationale_points.append("Active Cath Lab available for PCI")
            else:
                capability_score -= 45.0
                rationale_points.append("Lacks dedicated Cardiac Cath Lab")

        if category_meta.get("needs_stroke_center"):
            if hospital.has_stroke_center:
                rationale_points.append("Comprehensive Stroke Center certified")
            else:
                capability_score -= 45.0
                rationale_points.append("Not a certified Primary Stroke Center")

        if req_category == "POLYTRAUMA":
            if hospital.trauma_level == "Level 1":
                rationale_points.append("Level 1 Comprehensive Trauma Center")
            elif hospital.trauma_level == "Level 2":
                capability_score -= 15.0
                rationale_points.append("Level 2 Trauma Center (Surgical capabilities available)")
            else:
                capability_score -= 50.0
                rationale_points.append("Non-trauma center unsuitable for severe polytrauma")

        if req_category == "SEVERE_BURN":
            if hospital.has_burn_unit:
                rationale_points.append("Specialized Burn ICU operational")
            else:
                capability_score -= 40.0
                rationale_points.append("No specialized Burn Center")

        if req_category == "PEDIATRIC_CRITICAL":
            if hospital.has_pediatric_icu:
                rationale_points.append("Pediatric ICU (PICU) equipped")
            else:
                capability_score -= 45.0
                rationale_points.append("Lacks dedicated Pediatric Intensive Care Unit")

        # Specialty overlap calculation
        hospital_specialties = set(s.lower() for s in hospital.specialties)
        required_specialties = set(s.lower() for s in emergency.required_specialties)
        if required_specialties:
            matched = hospital_specialties.intersection(required_specialties)
            if not matched:
                for req in required_specialties:
                    if any(req in h_s or h_s in req for h_s in hospital_specialties):
                        matched.add(req)
            specialty_match_pct = len(matched) / len(required_specialties)
            capability_score = (capability_score * 0.7) + (specialty_match_pct * 30.0)
        
        capability_score = max(10.0, min(100.0, capability_score))

        # 3. Bed & Critical Capacity Score
        if hospital.is_live_monitored:
            icu_ratio = min(1.0, hospital.icu_available / max(hospital.icu_total, 1)) if hospital.icu_total > 0 else 0.0
            bed_ratio = min(1.0, hospital.available_beds / max(hospital.total_beds, 1)) if hospital.total_beds > 0 else 0.0
            bed_score = (icu_ratio * 60.0) + (bed_ratio * 40.0)
            if hospital.icu_available <= 0 and emergency.severity == "CRITICAL":
                bed_score = max(5.0, bed_score - 40.0)
                rationale_points.append("WARNING: Critical ICU beds at zero capacity")
            else:
                rationale_points.append(f"{hospital.icu_available} ICU beds, {hospital.available_beds} inpatient beds available")
        else:
            # Directory records: NEVER interpret total beds as available beds
            # Never invent ICU availability.
            bed_score = 35.0  # Baseline unverified capacity
            if hospital.total_beds > 0:
                rationale_points.append(f"Directory listing: {hospital.total_beds} total beds recorded (live availability unverified)")
            else:
                rationale_points.append("Directory listing: Bed count unverified (live telemetry offline)")

        # 4. Emergency Department Congestion Penalty
        if hospital.is_live_monitored:
            er_ratio = hospital.er_occupancy_rate
            if er_ratio <= 0.75:
                congestion_penalty = 0.0
            elif er_ratio <= 1.0:
                congestion_penalty = (er_ratio - 0.75) * 40.0
                rationale_points.append(f"ER at {int(er_ratio * 100)}% load")
            else:
                # Over-capacity surge
                congestion_penalty = 15.0 + ((er_ratio - 1.0) * 80.0)
                rationale_points.append(f"CRITICAL ER SURGE ({int(er_ratio * 100)}% capacity)")

            if hospital.status == "ON_DIVERSION":
                congestion_penalty += 50.0
                rationale_points.append("HOSPITAL ON OFFICIAL DIVERSION")
            congestion_penalty = min(80.0, max(0.0, congestion_penalty))
        else:
            congestion_penalty = 10.0
            rationale_points.append("ED queue telemetry offline (directory listing)")

        # 5. IBM Z Enterprise Verification Bonus
        ibm_z_bonus = 0.0
        if hospital.ibm_z_connected:
            ibm_z_bonus = 100.0  # Fully normalized bonus
            rationale_points.append("Verified via IBM z/OS CICS enterprise ledger")
        elif hospital.is_live_monitored:
            rationale_points.append("Telemetry awaiting IBM z/OS Connect verification")
        else:
            rationale_points.append("Directory facility (external enterprise ledger unconnected)")

        # 6. Composite Weighted Calculation
        composite = (
            (capability_score * settings.WEIGHT_CAPABILITY)
            + (transit_score * settings.WEIGHT_TRAVEL_TIME)
            + (bed_score * settings.WEIGHT_BED_AVAILABILITY)
            - (congestion_penalty * settings.WEIGHT_ER_CONGESTION)
            + (ibm_z_bonus * settings.WEIGHT_IBM_Z_VERIFIED)
        )
        composite_score = round(max(5.0, min(99.9, composite)), 1)

        # Build concise rationale summary
        if dist_km is not None and eta_minutes is not None:
            lead_summary = f"{hospital.name} ({hospital.trauma_level}): {dist_km} km / {eta_minutes} min ETA."
        else:
            lead_summary = f"{hospital.name} ({hospital.trauma_level}): Coordinates unverified; distance estimation unavailable."
        full_rationale = f"{lead_summary} " + " | ".join(rationale_points)

        return {
            "hospital_id": hospital.id,
            "hospital_name": hospital.name,
            "hospital_code": hospital.code,
            "trauma_level": hospital.trauma_level,
            "composite_score": composite_score,
            "capability_score": round(capability_score, 1),
            "transit_score": round(transit_score, 1),
            "bed_score": round(bed_score, 1),
            "congestion_penalty": round(congestion_penalty, 1),
            "ibm_z_bonus": round(ibm_z_bonus, 1),
            "distance_km": dist_km,
            "estimated_transit_minutes": eta_minutes,
            "rationale": full_rationale,
            "ibm_z_verified": hospital.ibm_z_connected,
            "available_beds": hospital.available_beds,
            "icu_available": hospital.icu_available,
            "er_current_load": hospital.er_current_load,
            "er_capacity": hospital.er_capacity,
            "has_cath_lab": hospital.has_cath_lab,
            "has_stroke_center": hospital.has_stroke_center,
            "latitude": hospital.latitude,
            "longitude": hospital.longitude,
            "data_source": hospital.data_source,
            "is_live_monitored": hospital.is_live_monitored,
            "status": "OFFERED"
        }

    @classmethod
    def compute_recommendations(
        cls,
        db: Session,
        emergency: Emergency,
        candidate_hospitals: Optional[List[Hospital]] = None,
        save_to_db: bool = True
    ) -> List[Dict[str, Any]]:
        """Evaluates registered hospitals, ranks them by composite score,

        and optionally updates the database recommendations table.
        """
        if candidate_hospitals is not None:
            hospitals = candidate_hospitals
        else:
            total_count = db.query(Hospital).count()
            if total_count <= 100:
                hospitals = db.query(Hospital).all()
            else:
                live_hospitals = db.query(Hospital).filter(Hospital.is_live_monitored == True).all()

                lat = emergency.latitude
                lon = emergency.longitude
                dist_expr = (Hospital.latitude - lat) * (Hospital.latitude - lat) + (Hospital.longitude - lon) * (Hospital.longitude - lon)
                closest_directory = db.query(Hospital).filter(
                    Hospital.is_live_monitored == False,
                    Hospital.latitude.isnot(None),
                    Hospital.longitude.isnot(None)
                ).order_by(dist_expr.asc()).limit(50).all()

                unverified_directory = db.query(Hospital).filter(
                    Hospital.is_live_monitored == False,
                    Hospital.latitude.is_(None)
                ).limit(10).all()

                seen_ids = set()
                hospitals = []
                for h in (live_hospitals + closest_directory + unverified_directory):
                    if h.id not in seen_ids:
                        seen_ids.add(h.id)
                        hospitals.append(h)

        if not hospitals:
            return []

        evaluated = []
        for hosp in hospitals:
            score_data = cls.evaluate_hospital(hosp, emergency)
            evaluated.append(score_data)

        # Sort descending by composite score, breaking ties by transit time
        evaluated.sort(
            key=lambda x: (
                x["composite_score"],
                -(x["estimated_transit_minutes"] if x["estimated_transit_minutes"] is not None else 9999.0)
            ),
            reverse=True
        )

        # Assign ranks
        for idx, item in enumerate(evaluated, start=1):
            item["rank"] = idx
            item["status"] = "RECOMMENDED" if idx == 1 else "OFFERED"

        if save_to_db:
            # Clear old recommendations for this emergency
            db.query(HospitalRecommendation).filter(
                HospitalRecommendation.emergency_id == emergency.id
            ).delete()

            # Persist top recommendations (up to 50)
            for item in evaluated[:50]:
                rec = HospitalRecommendation(
                    emergency_id=emergency.id,
                    hospital_id=item["hospital_id"],
                    rank=item["rank"],
                    composite_score=item["composite_score"],
                    capability_score=item["capability_score"],
                    transit_score=item["transit_score"],
                    bed_score=item["bed_score"],
                    congestion_penalty=item["congestion_penalty"],
                    ibm_z_bonus=item["ibm_z_bonus"],
                    distance_km=item["distance_km"],
                    estimated_transit_minutes=item["estimated_transit_minutes"],
                    rationale=item["rationale"],
                    ibm_z_verified=item["ibm_z_verified"],
                    status="RECOMMENDED" if item["rank"] == 1 else "OFFERED"
                )
                db.add(rec)
            db.commit()

        return evaluated
