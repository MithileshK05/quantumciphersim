"""
backend/routers/history.py
==========================
GET  /history         — returns recent simulation runs from DB
POST /history/record  — frontend calls this every ~10s to persist a snapshot
GET  /history/test-write — diagnostic: attempts a DB insert, returns exact result
GET  /models          — returns model registry for frontend dropdown
GET  /health          — returns app health status
"""

import sys
import os

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

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


# ── Pydantic schema for /history/record body ─────────────────────────────────
class RecordPayload(BaseModel):
    noise_level:           Optional[float] = None
    attack_probability:    Optional[float] = None
    final_qber:            Optional[float] = None
    sifted_key_length:     Optional[int]   = None
    eve_qber_contribution: Optional[float] = None
    ml_prediction:         Optional[str]   = None
    confidence_score:      Optional[float] = None
    model_used:            Optional[str]   = None
    actual_attack_status:  Optional[bool]  = None


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


@router.post("/history/record")
def record_simulation(
    payload: RecordPayload,
    db: Session = Depends(get_db),
):
    """
    Persist one simulation snapshot to PostgreSQL.
    Called by the frontend useHistoryRecorder hook every ~10 seconds.
    This is the AUTHORITATIVE write path — more reliable than writing
    from the GET /metrics endpoint.
    Returns {"ok": true, "session_id": "..."} on success.
    Raises HTTP 500 with exact error string on failure (no silent swallowing).
    """
    from fastapi import HTTPException
    try:
        run = SimulationRun(
            noise_level           = payload.noise_level,
            attack_probability    = payload.attack_probability,
            final_qber            = payload.final_qber,
            sifted_key_length     = payload.sifted_key_length,
            eve_qber_contribution = payload.eve_qber_contribution,
            ml_prediction         = payload.ml_prediction,
            confidence_score      = payload.confidence_score,
            model_used            = payload.model_used,
            actual_attack_status  = payload.actual_attack_status,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        print(f"[history/record] OK session_id={run.session_id} "
              f"qber={payload.final_qber} threat={payload.ml_prediction}")
        return {"ok": True, "session_id": run.session_id}
    except Exception as exc:
        print(f"[history/record] FAIL: {exc}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


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


@router.get("/history/migrate-db")
def migrate_db():
    """
    Diagnostic & repair endpoint: recreates the simulation_runs table on PostgreSQL.
    Guarantees the table has the latest schema matching models.py.
    """
    from backend.database import engine
    from backend.models import SimulationRun
    try:
        SimulationRun.__table__.drop(engine, checkfirst=True)
        SimulationRun.__table__.create(engine, checkfirst=True)
        return {"ok": True, "message": "simulation_runs table dropped and recreated successfully with latest schema."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

