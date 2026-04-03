"""
backend/schemas.py
==================
Pydantic v2 request/response models for all API endpoints.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# POST /simulate
# ---------------------------------------------------------------------------

class SimulateRequest(BaseModel):
    num_qubits:         int   = Field(..., ge=1,   le=2000,
                                description="Number of qubits Alice transmits (max 2000 keeps runtime under 30s)")
    noise_level:        float = Field(..., ge=0.0, le=1.0,
                                description="Depolarising noise level [0, 1]")
    attack_probability: float = Field(..., ge=0.0, le=1.0,
                                description="Probability each qubit is intercepted by Eve")
    seed:               Optional[int] = Field(None,
                                description="Optional RNG seed for reproducibility")

    model_config = {"json_schema_extra": {
        "example": {
            "num_qubits": 500,
            "noise_level": 0.05,
            "attack_probability": 0.8,
            "seed": None,
        }
    }}


class SimulateResponse(BaseModel):
    session_id:            str
    qber:                  float
    initial_key_length:    int
    sifted_key_length:     int
    eve_qber_contribution: float
    noise_level:           float
    attack_probability:    float


# ---------------------------------------------------------------------------
# POST /detect
# ---------------------------------------------------------------------------

class DetectRequest(BaseModel):
    session_id:       Optional[str]   = Field(None,
                            description="Session ID from /simulate (used to update DB row)")
    qber:             float           = Field(..., ge=0.0, le=1.0)
    noise_level:      float           = Field(..., ge=0.0, le=1.0)
    sifted_key_length: int            = Field(..., ge=0)
    model_type:       Optional[str]   = Field(None,
                            description="ML model to use. Defaults to best model.")

    model_config = {"json_schema_extra": {
        "example": {
            "session_id": "abc123",
            "qber": 0.271,
            "noise_level": 0.05,
            "sifted_key_length": 248,
            "model_type": "gradient_boosting",
        }
    }}


class DetectResponse(BaseModel):
    session_id:       Optional[str]
    threat_level:     str    # "HIGH" | "LOW"
    confidence_score: float
    model_used:       str
    eve_contribution: float


# ---------------------------------------------------------------------------
# GET /models
# ---------------------------------------------------------------------------

class ModelInfo(BaseModel):
    model_type:    str
    description:   str
    accuracy:      float
    recall_attack: float
    roc_auc:       float
    is_default:    bool


class ModelListResponse(BaseModel):
    models: List[ModelInfo]


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status:        str    # "ok" | "degraded"
    models_loaded: int
    db_connected:  bool
    version:       str


# ---------------------------------------------------------------------------
# GET /history
# ---------------------------------------------------------------------------

class HistoryRow(BaseModel):
    session_id:            str
    timestamp:             Optional[str]
    num_qubits:            Optional[int]
    noise_level:           Optional[float]
    attack_probability:    Optional[float]
    final_qber:            Optional[float]
    sifted_key_length:     Optional[int]
    eve_qber_contribution: Optional[float]
    ml_prediction:         Optional[str]
    confidence_score:      Optional[float]
    model_used:            Optional[str]
    actual_attack_status:  Optional[bool]


class HistoryResponse(BaseModel):
    runs:  List[HistoryRow]
    total: int
