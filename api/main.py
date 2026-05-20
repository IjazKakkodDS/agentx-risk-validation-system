"""
AgentX Risk Validator -- FastAPI local service boundary.

This API provides a programmatic interface to the AgentX validation pipeline
for local development, integration testing, and portfolio evidence.

It is NOT a production deployment and does NOT constitute regulatory approval.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from api.schemas import (
    EvidenceFileInfo,
    EvidenceResponse,
    GovernanceHistoryResponse,
    GovernanceLatestResponse,
    GovernanceRunHistoryItem,
    HealthResponse,
    MetricsResponse,
    ValidationRunRequest,
    ValidationRunResponse,
)
from api.service import (
    governance_available,
    list_evidence_files,
    list_generated_artifacts,
    list_governance_history,
    load_latest_governance_record,
    load_verified_metrics,
    mlflow_tracking_available,
    run_validation_pipeline,
)
from utils.config import EVIDENCE_DIR, VERIFIED_METRICS_JSON_PATH
from utils.logging_utils import setup_logger

logger = setup_logger("agentx.api")

APP_VERSION = "1.0.0"
APP_SYSTEM = "AgentX Risk Validator"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s API service starting (v%s)", APP_SYSTEM, APP_VERSION)
    yield
    logger.info("%s API service stopping", APP_SYSTEM)


app = FastAPI(
    title="AgentX Risk Validator API",
    description=(
        "Local API service for the AgentX multi-agent model validation pipeline. "
        "For development, portfolio evidence, and integration testing. "
        "Not a production regulatory platform."
    ),
    version=APP_VERSION,
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000)
    logger.info("%s %s -> %d (%dms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


@app.get("/health", response_model=HealthResponse, summary="Service health check")
def health():
    """
    Fast liveness check. Does not run the pipeline.
    Returns service metadata and whether key files are present.
    """
    return HealthResponse(
        status="ok",
        system=APP_SYSTEM,
        version=APP_VERSION,
        metrics_available=VERIFIED_METRICS_JSON_PATH.exists(),
        evidence_available=EVIDENCE_DIR.exists(),
    )


@app.get("/metrics", response_model=MetricsResponse, summary="Verified model metrics")
def metrics():
    """
    Return verified model metrics from docs/evidence/verified_metrics.json.
    Read-only. Does not trigger a pipeline run.
    Returns 503 if the metrics file has not been generated yet.
    """
    try:
        data = load_verified_metrics()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    m = data.get("metrics", {})
    return MetricsResponse(
        roc_auc=m.get("roc_auc", 0.0),
        accuracy=m.get("accuracy", 0.0),
        precision=m.get("precision", 0.0),
        recall=m.get("recall", 0.0),
        f1_score=m.get("f1_score", 0.0),
        dataset_rows=data.get("total_rows", 0),
        feature_count=data.get("feature_count", 0),
        model_type=data.get("model_type", ""),
        evidence_source="docs/evidence/verified_metrics.json",
    )


@app.get("/evidence", response_model=EvidenceResponse, summary="Evidence files and artifact status")
def evidence():
    """
    List evidence documentation files and current artifact status.
    Read-only. Does not trigger a pipeline run.
    """
    evidence_files = [EvidenceFileInfo(**f) for f in list_evidence_files()]
    generated_artifacts = list_generated_artifacts()
    return EvidenceResponse(
        evidence_files=evidence_files,
        generated_artifacts=generated_artifacts,
        governance_available=governance_available(),
        mlflow_tracking_available=mlflow_tracking_available(),
    )


@app.get(
    "/governance/latest",
    response_model=GovernanceLatestResponse,
    summary="Latest governance validation-run record",
)
def governance_latest():
    """
    Return the latest governance validation-run record.
    Read-only. Does not trigger a pipeline run.

    Returns 503 if no governance records have been generated yet.
    Run python main.py or POST /validate first to generate a record.

    Note: This is a local governance evidence endpoint. Records are not
    production regulatory records and do not constitute regulatory approval.
    """
    record = load_latest_governance_record()
    if not record:
        raise HTTPException(
            status_code=503,
            detail=(
                "No governance record found. "
                "Run python main.py or POST /validate to generate one."
            ),
        )
    drift = record.get("drift_status", {})
    compliance = record.get("compliance_status", {})
    arts = record.get("artifact_status", [])
    metrics_snap = record.get("metrics_snapshot", {})

    return GovernanceLatestResponse(
        available=True,
        validation_run_id=record.get("validation_run_id"),
        created_at_utc=record.get("created_at_utc"),
        system_name=record.get("system_name"),
        system_version=record.get("system_version"),
        run_type=record.get("run_type"),
        roc_auc=metrics_snap.get("roc_auc"),
        drift_detected=drift.get("drift_detected"),
        drifted_features=drift.get("drifted_features", []),
        compliance_status=compliance.get("status"),
        reviewer_status=record.get("reviewer_status"),
        risk_flags=record.get("risk_flags", []),
        artifacts_present=sum(1 for a in arts if a.get("exists")),
        artifacts_total=len(arts),
    )


@app.get(
    "/governance/history",
    response_model=GovernanceHistoryResponse,
    summary="Governance validation-run history",
)
def governance_history(limit: int = 10):
    """
    Return a list of recent governance validation-run summaries.
    Read-only. Does not trigger a pipeline run.
    Returns an empty list if no records exist.

    Note: This is a local governance evidence endpoint. Records are not
    production regulatory records and do not constitute regulatory approval.
    """
    runs_raw = list_governance_history(limit=limit)
    runs = [GovernanceRunHistoryItem(**r) for r in runs_raw]
    return GovernanceHistoryResponse(
        available=len(runs) > 0,
        count=len(runs),
        runs=runs,
    )


@app.post("/validate", response_model=ValidationRunResponse, summary="Run validation pipeline")
def validate(request: ValidationRunRequest):
    """
    Trigger the AgentX validation pipeline.

    Runs data loading, preprocessing, model training, all configured agents,
    and writes artifacts to their standard output paths.

    This endpoint can take 10-30 seconds. Compliance agent requires
    GROQ_API_KEY; uses a cached fallback response when the key is absent.
    Set run_compliance_agent=false to skip the LLM call entirely.

    Note: This is a local development endpoint. It is not suitable for
    concurrent requests and does not persist state across restarts.
    """
    try:
        result = run_validation_pipeline(request)
    except Exception as e:
        logger.error("Pipeline run failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Pipeline run failed: {e}")

    return ValidationRunResponse(
        status=result["status"],
        message="AgentX validation pipeline completed successfully.",
        metrics=result["metrics"],
        artifacts=result["artifacts"],
        warnings=result["warnings"],
    )
