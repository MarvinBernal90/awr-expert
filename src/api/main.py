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

from src.analytics.anomaly_detection import BehavioralAnalyzer
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
    behavioral_analysis: Dict[str, Any]  # <-- NUEVO: Contexto Estadístico Cognitivo
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
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            tmp_path = Path(tmp.name)

            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(status_code=413, detail="File too large.")
                hasher.update(chunk)
                tmp.write(chunk)

            if size == 0:
                raise HTTPException(status_code=400, detail="Empty file provided.")

        awr_hash = hasher.hexdigest()
        report = parser.parse(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to parse AWR: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to parse AWR report: {str(e)}"
        )
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    repo = AWRRepository()
    try:
        repo.save_report(awr_hash, report)
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to save parsed metrics to the warehouse."
        )

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

    db_name = (
        report.db_info.db_name if report.db_info and report.db_info.db_name else None
    )

    # --- SPRINT 13: BEHAVIORAL ANALYTICS LAYER ---
    behavioral_data = {}
    if db_name:
        try:
            # 1. Fetch the raw time-series movie (Last 30 snapshots)
            time_series = repo.get_time_series(db_name, limit=30)

            # 2. Extract current snapshot metrics cleanly
            lp = report.load_profile or report.load_profile_raw
            if lp:
                current_metrics = {
                    "logical_reads_ps": (
                        lp.logical_reads_ps
                        if lp.logical_reads_ps is not None
                        else (lp.logical_reads or 0.0)
                    ),
                    "physical_reads_ps": (
                        lp.physical_reads_ps
                        if lp.physical_reads_ps is not None
                        else (lp.physical_reads or 0.0)
                    ),
                    "executes_ps": (
                        lp.executes_ps
                        if lp.executes_ps is not None
                        else (lp.executes or 0.0)
                    ),
                    "transactions_ps": (
                        lp.transactions_ps
                        if lp.transactions_ps is not None
                        else (lp.transactions or 0.0)
                    ),
                }

                # 3. Ignite the Cognitive Statistical Engine
                analyzer = BehavioralAnalyzer(min_samples=3)
                behavioral_data = analyzer.analyze_workload(
                    current_metrics, time_series
                )

                # Inyectamos el raw array para que UI lo dibuje (Plotly)
                behavioral_data["raw_time_series"] = time_series

        except Exception as e:
            logger.warning(f"Could not calculate behavioral analytics: {e}")

    workload_context = classify_workload(report)

    cpu_diagnosis = analyze_cpu(report)
    io_diagnosis = analyze_io(report)
    memory_diagnosis = analyze_memory(report)

    active_diagnoses = [d for d in (cpu_diagnosis, io_diagnosis, memory_diagnosis) if d]

    return AnalysisResponse(
        awr_hash=awr_hash,
        workload_profile=workload_context,
        behavioral_analysis=behavioral_data,
        diagnostics=active_diagnoses,
    )
