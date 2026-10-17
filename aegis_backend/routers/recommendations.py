"""Recommendation Engine API Router."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aegis_backend.database import get_db
from aegis_backend.models import Emergency
from aegis_backend.schemas import RecommendationResponse, RecommendationItem
from aegis_backend.recommendation_engine import RecommendationEngine
from aegis_backend.events import record_event, manager

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


@router.get("/{emergency_id}", response_model=RecommendationResponse)
def get_recommendations_for_emergency(emergency_id: int, db: Session = Depends(get_db)):
    """Retrieves ranked hospital recommendations with explainable score breakdowns."""
    emrg = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emrg:
        raise HTTPException(status_code=404, detail="Emergency incident not found")

    # Evaluate dynamic recommendations
    evaluated = RecommendationEngine.compute_recommendations(db, emrg, save_to_db=False)

    rec_items = [RecommendationItem(**item) for item in evaluated]
    return RecommendationResponse(
        emergency_id=emrg.id,
        emergency_code=emrg.emergency_code,
        severity=emrg.severity,
        category=emrg.category,
        computed_at=datetime.now(timezone.utc),
        total_evaluated=len(rec_items),
        recommendations=rec_items
    )


@router.post("/{emergency_id}/recalculate", response_model=RecommendationResponse)
async def recalculate_recommendations(emergency_id: int, db: Session = Depends(get_db)):
    """Forces dynamic re-computation of hospital recommendations based on current real-time

    bed counts, ER surges, and transit factors.
    """
    emrg = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not emrg:
        raise HTTPException(status_code=404, detail="Emergency incident not found")

    evaluated = RecommendationEngine.compute_recommendations(db, emrg, save_to_db=True)
    rec_items = [RecommendationItem(**item) for item in evaluated]

    summary = f"Recommendations dynamically recalculated for {emrg.emergency_code}: Top choice {evaluated[0]['hospital_name']} ({evaluated[0]['composite_score']} pts)."
    record_event(db, "RECOMMENDATIONS_RECALCULATED", summary, emergency_id=emrg.id, actor="RECOMMENDER")

    await manager.broadcast({
        "type": "RECOMMENDATIONS_UPDATED",
        "emergency_id": emrg.id,
        "emergency_code": emrg.emergency_code,
        "top_hospital": evaluated[0]["hospital_name"] if evaluated else None,
        "top_score": evaluated[0]["composite_score"] if evaluated else 0,
        "recommendations": evaluated
    })

    return RecommendationResponse(
        emergency_id=emrg.id,
        emergency_code=emrg.emergency_code,
        severity=emrg.severity,
        category=emrg.category,
        computed_at=datetime.now(timezone.utc),
        total_evaluated=len(rec_items),
        recommendations=rec_items
    )
