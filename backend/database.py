"""
backend/database.py
===================
SQLAlchemy engine + session factory.

Uses DATABASE_URL from .env file.
Falls back to SQLite if DATABASE_URL is not set (dev convenience).
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

# Fallback to SQLite for local dev if PostgreSQL not configured
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./quantumciphersim.db"
)

# PostgreSQL needs different connect_args than SQLite
_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,   # reconnect if DB went away
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_db():
    """
    FastAPI dependency: yields a DB session, closes it on request end.
    Usage:
        @router.post("/simulate")
        def simulate(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> bool:
    """Return True if DB is reachable, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def create_tables() -> None:
    """Create all tables defined in models.py (if they don't exist)."""
    # Import here to avoid circular imports
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
