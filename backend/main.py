"""
backend/main.py
===============
FastAPI application — entry point for the QuantumCipherSim backend.

Startup sequence:
  1. Load .env (DATABASE_URL, etc.)
  2. ML models loaded into memory via ml.inference import
  3. DB tables created if they don't exist
  4. CORS middleware applied for React frontend
  5. All routers registered

Run:
  uvicorn backend.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database         import create_tables, check_connection
from backend.routers.simulate import router as simulate_router
from backend.routers.detect   import router as detect_router
from backend.routers.history  import router as history_router
from backend.routers.metrics  import router as metrics_router

# ml.inference is imported at module level so all 4 models load at startup.
# If any model file is missing this will raise FileNotFoundError immediately
# (fail-fast is correct — don't start a half-broken server).
from ml.inference import AVAILABLE_MODELS


# ---------------------------------------------------------------------------
# Lifespan: startup + shutdown logic
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    print("[startup] QuantumCipherSim API starting ...")
    print(f"[startup] ML models loaded: {AVAILABLE_MODELS}")

    try:
        create_tables()
        print("[startup] Database tables verified/created.")
    except Exception as exc:
        print(f"[startup] WARNING: DB table creation failed: {exc}")
        print("[startup] API will run without database persistence.")

    db_ok = check_connection()
    print(f"[startup] Database connected: {db_ok}")
    print("[startup] Server ready.")

    yield   # <-- application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────
    print("[shutdown] QuantumCipherSim API shutting down.")


# ---------------------------------------------------------------------------
# App definition
# ---------------------------------------------------------------------------

app = FastAPI(
    title       = "QuantumCipherSim API",
    description = (
        "Quantum Key Distribution (BB84) simulator with real-time ML "
        "eavesdropper detection. Supports 4 selectable ML models."
    ),
    version     = "1.0.0",
    lifespan    = lifespan,
    docs_url    = "/docs",     # Swagger UI
    redoc_url   = "/redoc",    # ReDoc UI
)

# ---------------------------------------------------------------------------
# CORS: allow React frontend on localhost (dev) and Vercel (production)
# ---------------------------------------------------------------------------

# Read additional allowed origins from environment (set on Render dashboard)
_extra_origins = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # Vite dev
        "http://localhost:5174",    # Vite dev fallback
        "http://localhost:3000",    # CRA dev (fallback)
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "https://quantumciphersim.vercel.app",       # Vercel (primary)
        "https://quantumciphersim-zeta.vercel.app",  # Vercel (actual deployed URL)
        *_extra_origins,            # Any extra origins set via env var
    ],
    allow_credentials = True,
    allow_methods     = ["GET", "POST", "OPTIONS"],
    allow_headers     = ["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(simulate_router)
app.include_router(detect_router)
app.include_router(history_router)
app.include_router(metrics_router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/", tags=["root"])
def root():
    return {
        "name":    "QuantumCipherSim API",
        "version": "1.0.0",
        "docs":    "/docs",
        "health":  "/health",
    }
