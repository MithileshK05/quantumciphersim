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
