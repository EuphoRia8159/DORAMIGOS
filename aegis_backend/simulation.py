"""AEGIS Real-time Simulation Engine.

Simulates hospital capacity turnover, ER patient influx, ambulance telemetry,
dispatch routes, and triggers dynamic recommendation updates.
"""

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from aegis_backend.database import SessionLocal
from aegis_backend.models import Hospital, Ambulance, Emergency, AmbulanceAssignment
from aegis_backend.events import manager, record_event
from aegis_backend.recommendation_engine import RecommendationEngine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Orchestrates continuous and on-demand simulations."""

    def __init__(self):
        self.is_running: bool = False
        self.tick_count: int = 0
        self.task: Optional[asyncio.Task] = None
        self.interval_seconds: float = 3.5

    def start(self):
        """Starts background simulation loop if not already running."""
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self._simulation_loop())
            logger.info("AEGIS Real-time simulation engine started.")

    def stop(self):
        """Stops background simulation loop."""
        self.is_running = False
        if self.task:
            self.task.cancel()
            self.task = None
        logger.info("AEGIS Real-time simulation engine stopped.")

    async def _simulation_loop(self):
        """Continuous simulation cycle."""
        while self.is_running:
            try:
                await self.tick()
            except Exception as e:
                logger.error(f"Error during simulation tick: {e}", exc_info=True)
            await asyncio.sleep(self.interval_seconds)

    async def tick(self) -> Dict[str, Any]:
        """Executes a single discrete simulation cycle."""
        self.tick_count += 1
        db = SessionLocal()
        events_fired = []

        try:
            # 1. Update Ambulance Movements
            ambulances = db.query(Ambulance).filter(
                Ambulance.status.in_(["DISPATCHED", "EN_ROUTE_SCENE", "EN_ROUTE_HOSPITAL"])
            ).all()

            for amb in ambulances:
                if amb.target_latitude is not None and amb.target_longitude is not None:
                    # Move towards target (lerp by ~15% per tick for visible, smooth real-time progress)
                    d_lat = amb.target_latitude - amb.latitude
                    d_lon = amb.target_longitude - amb.longitude
                    dist_to_target = (d_lat ** 2 + d_lon ** 2) ** 0.5

                    step_ratio = 0.20
                    if dist_to_target < 0.003:  # Close enough to consider arrived (~300m)
                        amb.latitude = amb.target_latitude
                        amb.longitude = amb.target_longitude

                        # Advance state
                        if amb.status in ["DISPATCHED", "EN_ROUTE_SCENE"]:
                            amb.status = "AT_SCENE"
                            summary = f"Ambulance {amb.call_sign} arrived at emergency scene."
                            events_fired.append(summary)
                            record_event(db, "AMBULANCE_AT_SCENE", summary, amb.current_emergency_id, actor="SIMULATOR")
                            
                            # If emergency has an assigned hospital, set next target to hospital
                            if amb.current_emergency and amb.current_emergency.assigned_hospital:
                                hosp = amb.current_emergency.assigned_hospital
                                amb.target_latitude = hosp.latitude
                                amb.target_longitude = hosp.longitude
                                amb.status = "EN_ROUTE_HOSPITAL"
                                if amb.current_emergency:
                                    amb.current_emergency.status = "IN_TRANSIT"
                        elif amb.status == "EN_ROUTE_HOSPITAL":
                            amb.status = "AT_HOSPITAL"
                            summary = f"Ambulance {amb.call_sign} arrived at destination hospital."
                            events_fired.append(summary)
                            record_event(db, "AMBULANCE_AT_HOSPITAL", summary, amb.current_emergency_id, actor="SIMULATOR")

                            # Transition emergency to ARRIVED_HOSPITAL
                            if amb.current_emergency:
                                amb.current_emergency.status = "ARRIVED_HOSPITAL"
                                if amb.current_emergency.assigned_hospital:
                                    # Intake patient: increment hospital ER load
                                    amb.current_emergency.assigned_hospital.er_current_load += 1
                                    if amb.current_emergency.severity == "CRITICAL" and amb.current_emergency.assigned_hospital.icu_available > 0:
                                        amb.current_emergency.assigned_hospital.icu_available -= 1

                            # Free ambulance after arrival
                            amb.target_latitude = None
                            amb.target_longitude = None
                            amb.status = "AVAILABLE"
                            amb.current_emergency_id = None
                    else:
                        amb.latitude += d_lat * step_ratio
                        amb.longitude += d_lon * step_ratio

                    amb.updated_at = datetime.now(timezone.utc)

            # 2. Simulate Minor Hospital Capacity Variations (Every ~3 ticks for live-monitored facilities only)
            if self.tick_count % 3 == 0:
                hospitals = db.query(Hospital).filter(Hospital.is_live_monitored == True).all()
                for hosp in hospitals:
                    # Small random fluctuate in ER load (-1, 0, or +1)
                    load_delta = random.choice([-1, 0, 0, 1])
                    new_load = max(2, min(hosp.er_capacity + 5, hosp.er_current_load + load_delta))
                    hosp.er_current_load = new_load

                    # Occasional ICU bed release or admission
                    if random.random() < 0.25:
                        icu_delta = random.choice([-1, 1])
                        hosp.icu_available = max(0, min(hosp.icu_total, hosp.icu_available + icu_delta))

                    # Occasional inpatient bed discharge
                    if random.random() < 0.35:
                        bed_delta = random.choice([-1, 1])
                        hosp.available_beds = max(0, min(hosp.total_beds, hosp.available_beds + bed_delta))

            db.commit()

            # 3. Dynamic Re-evaluation for Pending Emergencies
            active_emergencies = db.query(Emergency).filter(
                Emergency.status.in_(["REPORTED", "TRIAGED"])
            ).all()

            updated_recs = []
            for emrg in active_emergencies:
                recs = RecommendationEngine.compute_recommendations(db, emrg, save_to_db=True)
                updated_recs.append({
                    "emergency_id": emrg.id,
                    "top_hospital": recs[0]["hospital_name"] if recs else None,
                    "top_score": recs[0]["composite_score"] if recs else 0
                })

            # 4. Broadcast Telemetry to WebSocket Subscribers
            telemetry_data = {
                "type": "SIMULATION_TICK",
                "tick": self.tick_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "events": events_fired,
                "updated_emergencies": len(active_emergencies)
            }
            await manager.broadcast(telemetry_data)

            return telemetry_data

        finally:
            db.close()

    def trigger_mass_casualty(self, db: Session, hospital_id: int, incoming_count: int = 8) -> Dict[str, Any]:
        """Simulates a sudden mass-casualty surge at a hospital to demonstrate dynamic rerouting."""
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            return {"error": "Hospital not found"}

        old_load = hospital.er_current_load
        old_icu = hospital.icu_available

        hospital.er_current_load = min(hospital.er_capacity + 10, hospital.er_current_load + incoming_count)
        hospital.icu_available = max(0, hospital.icu_available - (incoming_count // 2))
        if hospital.er_current_load >= hospital.er_capacity:
            hospital.status = "SURGE"

        db.commit()

        summary = f"Mass Casualty Surge triggered at {hospital.name}: ER load increased from {old_load} to {hospital.er_current_load} ({int(hospital.er_occupancy_rate * 100)}%)."
        record_event(db, "SURGE_ALERT", summary, details={
            "hospital_id": hospital.id,
            "incoming_patients": incoming_count,
            "status": hospital.status
        }, actor="SIMULATOR")

        # Recalculate all open recommendations
        open_emergencies = db.query(Emergency).filter(
            Emergency.status.in_(["REPORTED", "TRIAGED"])
        ).all()
        for emrg in open_emergencies:
            RecommendationEngine.compute_recommendations(db, emrg, save_to_db=True)

        return {
            "success": True,
            "hospital_id": hospital.id,
            "hospital_name": hospital.name,
            "previous_load": old_load,
            "new_er_load": hospital.er_current_load,
            "er_capacity": hospital.er_capacity,
            "icu_available": hospital.icu_available,
            "status": hospital.status,
            "recalculated_emergencies": len(open_emergencies)
        }


simulation_engine = SimulationEngine()
