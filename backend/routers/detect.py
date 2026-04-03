"""
backend/routers/detect.py
=========================
POST /detect — runs ML eavesdropper detection and updates DB row.
"""

import sys
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

from backend.schemas  import DetectRequest, DetectResponse
from backend.models   import SimulationRun
from backend.database import get_db
from ml.inference     import predict, AVAILABLE_MODELS

router = APIRouter(prefix="/detect", tags=["detection"])


@router.post("", response_model=DetectResponse)
def run_detection(
    req: DetectRequest,
    db: Session = Depends(get_db),
):
    """
    Run ML eavesdropper detection on BB84 simulation metrics.

    - Validates model_type (422 if not in AVAILABLE_MODELS)
    - Calls ml.inference.predict() with all 4-feature computation
    - Updates the DB row created by /simulate (if session_id provided)
    - Returns threat_level, confidence_score, model_used, eve_contribution
    """
    # Validate model_type manually for a cleaner 422 message
    if req.model_type and req.model_type not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=422,
            detail={
                "error":        "Invalid model_type",
                "received":     req.model_type,
                "valid_options": AVAILABLE_MODELS,
            }
        )

    # Run ML inference
    try:
        result = predict(
            qber              = req.qber,
            noise_level       = req.noise_level,
            sifted_key_length = req.sifted_key_length,
            model_type        = req.model_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Update DB row (non-fatal if row not found or DB unavailable)
    if req.session_id:
        try:
            row = db.query(SimulationRun).filter(
                SimulationRun.session_id == req.session_id
            ).first()
            if row:
                row.ml_prediction  = result["threat_level"]
                row.confidence_score = result["confidence_score"]
                row.model_used     = result["model_used"]
                db.commit()
        except Exception:
            db.rollback()

    return DetectResponse(
        session_id       = req.session_id,
        threat_level     = result["threat_level"],
        confidence_score = result["confidence_score"],
        model_used       = result["model_used"],
        eve_contribution = result["eve_contribution"],
    )
