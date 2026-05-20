"""
Service functions for the AgentX FastAPI layer.

Each function is a thin adapter between the FastAPI route handlers and the
existing AgentX agent/utility layer. No pipeline logic is duplicated here.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

from utils.config import (
    COMPLIANCE_REPORT_PATH,
    DATA_VALIDATION_PATH,
    DRIFT_REPORT_PATH,
    EVIDENCE_DIR,
    GOVERNANCE_LATEST_PATH,
    GOVERNANCE_RUNS_DIR,
    PERFORMANCE_METRICS_PATH,
    REPORT_MD_PATH,
    SHAP_SUMMARY_PATH,
    VERIFIED_METRICS_JSON_PATH,
    VERIFIED_METRICS_MD_PATH,
)
from utils.governance import list_validation_runs, load_latest_validation_run
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)

_ARTIFACT_PATHS = [
    DATA_VALIDATION_PATH,
    PERFORMANCE_METRICS_PATH,
    SHAP_SUMMARY_PATH,
    DRIFT_REPORT_PATH,
    COMPLIANCE_REPORT_PATH,
    REPORT_MD_PATH,
    VERIFIED_METRICS_JSON_PATH,
    VERIFIED_METRICS_MD_PATH,
]


def load_verified_metrics() -> Dict[str, Any]:
    """Read docs/evidence/verified_metrics.json and return the parsed dict."""
    if not VERIFIED_METRICS_JSON_PATH.exists():
        raise FileNotFoundError(
            f"verified_metrics.json not found at {VERIFIED_METRICS_JSON_PATH}. "
            "Run the pipeline first (python main.py)."
        )
    with open(VERIFIED_METRICS_JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def list_evidence_files() -> List[Dict[str, Any]]:
    """Return a list of dicts describing files in docs/evidence/."""
    if not EVIDENCE_DIR.exists():
        return []
    return [
        {"name": p.name, "size_bytes": p.stat().st_size}
        for p in sorted(EVIDENCE_DIR.iterdir())
        if p.is_file()
    ]


def list_generated_artifacts() -> List[Dict[str, Any]]:
    """Return existence and size for each configured artifact path."""
    results = []
    for p in _ARTIFACT_PATHS:
        exists = p.exists()
        results.append(
            {
                "path": str(p.relative_to(Path.cwd()) if p.is_absolute() else p),
                "exists": exists,
                "size_bytes": p.stat().st_size if exists else None,
            }
        )
    return results


def load_latest_governance_record() -> Dict[str, Any]:
    """Return the latest governance validation-run record, or an empty dict if none exists."""
    record = load_latest_validation_run()
    return record or {}


def list_governance_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Return a list of recent governance run summaries."""
    return list_validation_runs(limit=limit)


def governance_available() -> bool:
    """Return True if at least one governance run record exists."""
    return GOVERNANCE_LATEST_PATH.exists()


def mlflow_tracking_available() -> bool:
    """Return True if local MLflow tracking has at least one run recorded."""
    from utils.mlflow_tracking import mlflow_tracking_available as _check
    return _check()


def run_validation_pipeline(request) -> Dict[str, Any]:
    """
    Invoke run_agentx_pipeline() from main.py with flags from the API request.

    The pipeline trains the model, runs all configured agents, and writes
    artifacts to the standard output paths. This call can take 10-30 seconds
    depending on SHAP computation and network availability for compliance.
    """
    from main import run_agentx_pipeline

    logger.info(
        "API-triggered pipeline run -- compliance=%s, drift=%s, reports=%s",
        request.run_compliance_agent,
        request.run_drift_monitor,
        request.regenerate_reports,
    )
    result = run_agentx_pipeline(
        run_compliance=request.run_compliance_agent,
        run_drift=request.run_drift_monitor,
        regenerate_reports=request.regenerate_reports,
    )
    logger.info("API-triggered pipeline run complete -- %d artifacts written", len(result["artifacts"]))
    return result
