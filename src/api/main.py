"""
FastAPI Core Application and Routing.
Exposes AWR parsing and diagnostic engines as RESTful endpoints.
"""

import hashlib
import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.engine.cpu import analyze_cpu
from src.engine.io import analyze_io
from src.engine.memory import analyze_memory
from src.engine.workload import classify_workload
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
    workload_profile: Dict[str, Any]
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

    max_bytes = 20 * 1024 * 1024  # 20 MB Limit
    size = 0
    hasher = hashlib.sha256()
    parser = AWRParser()
    tmp_path: Path | None = None

    try:
        # 1. Stream the file directly to disk while hashing it
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            tmp_path = Path(tmp.name)  # <-- Assigned immediately to prevent leaks

            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(status_code=413, detail="File too large.")
                hasher.update(chunk)
                tmp.write(chunk)

            if size == 0:
                raise HTTPException(status_code=400, detail="Empty file provided.")

        awr_hash = hasher.hexdigest()

        # 2. Parse the AWR from the local temporary file
        report = parser.parse(tmp_path)

    except HTTPException:
        # Re-raise known API errors to prevent wrapping them in a 500
        raise
    except Exception as e:
        logger.error(f"Failed to parse AWR: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to parse AWR report: {str(e)}"
        )
    finally:
        # 3. ALWAYS clean up the temporary file
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    # 4. Save to DuckDB Warehouse
    repo = AWRRepository()
    try:
        repo.save_report(awr_hash, report)
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to save parsed metrics to the warehouse."
        )

    # 5. Extract basic info for the response payload
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

    try:
        report = repo.get_report(awr_hash)
    except Exception:
        raise HTTPException(
            status_code=500, detail="Internal server error during database retrieval."
        )

    if not report:
        raise HTTPException(
            status_code=404, detail=f"AWR report with hash {awr_hash} not found."
        )

    # 1. Level 2: Context-Awareness (Workload Classifier + DYNAMIC BASELINES)
    db_name = (
        report.db_info.db_name if report.db_info and report.db_info.db_name else None
    )

    baselines = {}
    if db_name:
        try:
            # Query DuckDB for historical averages of this specific database
            baselines = repo.get_historical_baselines(db_name)
        except Exception as e:
            logger.warning(f"Could not retrieve baselines for {db_name}: {e}")

    # Pass the history to the engine so it can calculate deviations
    workload_context = classify_workload(report, baselines)

    # 2. Run all heuristic engines
    cpu_diagnosis = analyze_cpu(report)
    io_diagnosis = analyze_io(report)
    memory_diagnosis = analyze_memory(report)

    # 3. Filter out skipped engines
    active_diagnoses = [d for d in (cpu_diagnosis, io_diagnosis, memory_diagnosis) if d]

    return AnalysisResponse(
        awr_hash=awr_hash,
        workload_profile=workload_context,
        diagnostics=active_diagnoses,
    )
