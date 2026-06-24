"""
backend/routers/history.py
==========================
GET /history  — returns recent simulation runs from DB
GET /models   — returns model registry for frontend dropdown
GET /health   — returns app health status
"""

import sys
import os

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

from backend.schemas   import (
    HealthResponse, ModelListResponse, ModelInfo,
    HistoryResponse, HistoryRow,
)
from backend.models    import SimulationRun
from backend.database  import get_db, check_connection
from ml.inference      import AVAILABLE_MODELS, get_model_registry

router = APIRouter(tags=["utility"])

APP_VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    Returns model load count and DB connectivity status.
    """
    return HealthResponse(
        status        = "ok",
        models_loaded = len(AVAILABLE_MODELS),
        db_connected  = check_connection(),
        version       = APP_VERSION,
    )


@router.get("/models", response_model=ModelListResponse)
def list_models():
    """
    Returns all available ML models with their metrics.
    Used by the frontend to populate the model selector dropdown.
    """
    registry = get_model_registry()
    models   = [ModelInfo(**info) for info in registry.values()]
    # Sort: default model first, then by ROC-AUC descending
    models.sort(key=lambda m: (not m.is_default, -m.roc_auc))
    return ModelListResponse(models=models)


@router.get("/history", response_model=HistoryResponse)
def get_history(
    limit: int = Query(default=20, ge=1, le=200,
                       description="Number of recent runs to return"),
    db: Session = Depends(get_db),
):
    """
    Returns the last `limit` simulation runs ordered by timestamp descending.
    Used by the frontend dashboard to plot QBER over time.
    """
    rows = (
        db.query(SimulationRun)
        .order_by(SimulationRun.timestamp.desc())
        .limit(limit)
        .all()
    )
    total = db.query(SimulationRun).count()

    return HistoryResponse(
        runs  = [HistoryRow(**r.to_dict()) for r in rows],
        total = total,
    )


@router.get("/history/test-write")
def test_write():
    """
    Diagnostic endpoint: attempts a real DB INSERT and returns the result.
    Returns {"ok": true, "session_id": "..."} on success.
    Returns {"ok": false, "error": "<exception text>"} on failure.
    This bypasses all silent try/except so we can see the real error.
    Remove this endpoint once history recording is confirmed working.
    """
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        run = SimulationRun(
            noise_level           = 0.05,
            attack_probability    = 1.0,
            final_qber            = 0.2500,
            sifted_key_length     = 0,
            eve_qber_contribution = 0.22,
            ml_prediction         = "HIGH",
            confidence_score      = 0.99,
            model_used            = "test_write",
            actual_attack_status  = True,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        session_id = run.session_id
        return {"ok": True, "session_id": session_id,
                "message": "Row inserted successfully"}
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        return {"ok": False, "error": str(exc),
                "error_type": type(exc).__name__}
    finally:
        db.close()
