"""
FastAPI Core Application and Routing.
Exposes AWR parsing and diagnostic engines as RESTful endpoints.
"""

import hashlib
import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.engine.cpu import analyze_cpu
from src.engine.io import analyze_io
from src.engine.memory import analyze_memory
from src.parser.core import AWRParser
from src.services.db import initialize_warehouse
from src.services.repository import AWRRepository

logger = logging.getLogger(__name__)


# --- Models ---
class UploadResponse(BaseModel):
    """Schema for the successful upload response."""

    message: str
    awr_hash: str
    db_name: str
    elapsed_mins: float


class AnalysisResponse(BaseModel):
    """Schema for the diagnostic analysis response."""

    awr_hash: str
    diagnostics: List[Any]


# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events for the API."""
    logger.info("Initializing DuckDB Warehouse...")
    initialize_warehouse()
    yield
    logger.info("Shutting down AWR Expert API...")


# --- API Bootstrap ---
app = FastAPI(
    title="AWR Expert API",
    description="Enterprise API for Oracle AWR telemetry extraction and heuristics.",
    version="1.0.0",
    lifespan=lifespan,
)


# --- Routes ---
@app.get("/health")
def health_check() -> dict:
    """Standard health check endpoint for container orchestrators (e.g., Kubernetes)."""
    return {"status": "up", "version": "1.0.0"}


@app.post("/upload", response_model=UploadResponse)
async def upload_awr(file: UploadFile = File(...)):
    """
    Receives an AWR HTML file, parses it, stores the JSON in DuckDB,
    and returns an idempotency hash for future diagnostic querying.
    """
    if not file.filename or not file.filename.endswith(".html"):
        raise HTTPException(status_code=400, detail="Only HTML files are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file provided.")

    # 1. Calculate idempotency hash
    awr_hash = hashlib.sha256(content).hexdigest()

    # 2. Parse the AWR using a secure temporary file
    parser = AWRParser()
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        report = parser.parse(tmp_path)
        tmp_path.unlink()  # Clean up immediately after parsing

    except Exception as e:
        logger.error(f"Failed to parse AWR: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to parse AWR report: {str(e)}"
        )

    # 3. Save to DuckDB Warehouse
    repo = AWRRepository()
    try:
        repo.save_report(awr_hash, report)
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to save parsed metrics to the warehouse."
        )

    # 4. Extract basic info for the response payload
    db_name = (
        report.db_info.db_name
        if report.db_info and report.db_info.db_name
        else "UNKNOWN"
    )
    elapsed = (
        report.db_info.elapsed_time_min
        if report.db_info and report.db_info.elapsed_time_min
        else 0.0
    )

    return UploadResponse(
        message="AWR report successfully parsed and stored.",
        awr_hash=awr_hash,
        db_name=db_name,
        elapsed_mins=elapsed,
    )


@app.get("/analyze/{awr_hash}", response_model=AnalysisResponse)
def analyze_awr(awr_hash: str):
    """
    Retrieves a previously parsed AWR report by its hash,
    runs the heuristic engines, and returns the diagnostics.
    """
    repo = AWRRepository()
    report = repo.get_report(awr_hash)

    if not report:
        raise HTTPException(
            status_code=404, detail=f"AWR report with hash {awr_hash} not found."
        )

    # 1. Run all heuristic engines
    cpu_diagnosis = analyze_cpu(report)
    io_diagnosis = analyze_io(report)
    memory_diagnosis = analyze_memory(report)

    # 2. Filter out skipped engines
    active_diagnoses = [d for d in (cpu_diagnosis, io_diagnosis, memory_diagnosis) if d]

    return AnalysisResponse(
        awr_hash=awr_hash,
        diagnostics=active_diagnoses,
    )
