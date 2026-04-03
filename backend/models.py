"""
backend/models.py
=================
SQLAlchemy ORM table definitions.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String as SA_String

from backend.database import Base


def _uuid_default():
    return str(uuid.uuid4())


class SimulationRun(Base):
    """
    One row per /simulate call.
    ml_prediction and confidence_score are NULL until /detect is called.
    """
    __tablename__ = "simulation_runs"

    session_id            = Column(SA_String(36), primary_key=True,
                                   default=_uuid_default)
    timestamp             = Column(DateTime(timezone=True),
                                   default=lambda: datetime.now(timezone.utc),
                                   nullable=False)

    # Simulation parameters
    num_qubits            = Column(Integer,  nullable=True)
    noise_level           = Column(Float,    nullable=True)
    attack_probability    = Column(Float,    nullable=True)

    # Simulation outputs
    final_qber            = Column(Float,    nullable=True)
    sifted_key_length     = Column(Integer,  nullable=True)
    eve_qber_contribution = Column(Float,    nullable=True)

    # ML detection outputs (filled by /detect)
    ml_prediction         = Column(SA_String(10), nullable=True)  # HIGH | LOW
    confidence_score      = Column(Float,    nullable=True)
    model_used            = Column(SA_String(50), nullable=True)

    # Ground truth (known because we control the simulation)
    actual_attack_status  = Column(Boolean,  nullable=True)

    def to_dict(self) -> dict:
        return {
            "session_id":            self.session_id,
            "timestamp":             self.timestamp.isoformat()
                                     if self.timestamp else None,
            "num_qubits":            self.num_qubits,
            "noise_level":           self.noise_level,
            "attack_probability":    self.attack_probability,
            "final_qber":            self.final_qber,
            "sifted_key_length":     self.sifted_key_length,
            "eve_qber_contribution": self.eve_qber_contribution,
            "ml_prediction":         self.ml_prediction,
            "confidence_score":      self.confidence_score,
            "model_used":            self.model_used,
            "actual_attack_status":  self.actual_attack_status,
        }
