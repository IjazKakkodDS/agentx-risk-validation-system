"""
Local MLflow validation tracking for AgentX.

Logs each validation run to a local MLflow file store (mlruns/).
This is local development tracking only -- no remote server, no model registry,
no production MLflow deployment.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import mlflow

from utils.config import (
    COMPLIANCE_REPORT_PATH,
    DRIFT_REPORT_PATH,
    EVIDENCE_DIR,
    GOVERNANCE_LATEST_PATH,
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_TRACKING_DIR,
    SHAP_SUMMARY_PATH,
    VERIFIED_METRICS_JSON_PATH,
)
from utils.logging_utils import setup_logger

logger = setup_logger("agentx.mlflow")

# Substrings that indicate a file should never be logged as an artifact
_UNSAFE_NAME_PATTERNS = {".env", "credential", "api_key", "secret", "password", "token"}


def configure_mlflow() -> None:
    """Configure local file-based MLflow tracking URI and experiment."""
    MLFLOW_TRACKING_DIR.mkdir(parents=True, exist_ok=True)
    # Use file:/// URI so MLflow recognizes it as a local file store on all platforms
    tracking_uri = MLFLOW_TRACKING_DIR.as_uri()
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    logger.info("MLflow tracking configured at: %s", tracking_uri)


def _is_safe_artifact_path(path: Path) -> bool:
    """Return False if the filename contains a secret-related keyword."""
    name_lower = path.name.lower()
    return not any(pattern in name_lower for pattern in _UNSAFE_NAME_PATTERNS)


def _log_artifact_safely(path: Union[str, Path], label: str) -> bool:
    """Log a single artifact file if it exists and passes the safety check.

    Returns True if the artifact was logged, False otherwise.
    """
    p = Path(path)
    if not p.exists():
        logger.debug("Artifact absent, skipping: %s", label)
        return False
    if not _is_safe_artifact_path(p):
        logger.warning("Artifact skipped (unsafe filename): %s", label)
        return False
    try:
        mlflow.log_artifact(str(p))
        logger.debug("Artifact logged: %s", label)
        return True
    except Exception as exc:
        logger.warning("Could not log artifact %s: %s", label, exc)
        return False


def log_model_metrics(metrics: Dict[str, Any]) -> None:
    """Log the five standard model metrics to the active MLflow run."""
    metric_keys = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]
    logged = []
    for key in metric_keys:
        val = metrics.get(key)
        if val is not None:
            try:
                mlflow.log_metric(key, float(val))
                logged.append(key)
            except Exception as exc:
                logger.warning("Could not log metric %s: %s", key, exc)
    logger.info("MLflow metrics logged: %s", logged)


def log_validation_params(context: Dict[str, Any]) -> None:
    """Log validation parameters to the active MLflow run."""
    param_keys = [
        "dataset_rows",
        "feature_count",
        "model_type",
        "target",
        "class_balance",
        "validation_run_id",
        "test_size",
        "random_state",
    ]
    for key in param_keys:
        val = context.get(key)
        if val is not None:
            try:
                mlflow.log_param(key, str(val)[:250])
            except Exception as exc:
                logger.warning("Could not log param %s: %s", key, exc)


def log_agentx_artifacts(
    artifact_paths: Union[Dict[str, Union[str, Path]], List[Union[str, Path]]],
) -> Dict[str, bool]:
    """Log a collection of artifacts. Returns label -> success mapping."""
    results: Dict[str, bool] = {}
    if isinstance(artifact_paths, list):
        for p in artifact_paths:
            label = Path(p).name
            results[label] = _log_artifact_safely(p, label)
    else:
        for label, p in artifact_paths.items():
            results[label] = _log_artifact_safely(p, label)
    return results


def log_governance_record(path: Union[str, Path, None] = None) -> bool:
    """Log the latest governance validation-run record if present."""
    target = Path(path) if path else GOVERNANCE_LATEST_PATH
    return _log_artifact_safely(target, "governance_record")


def log_benchmark_results(path: Union[str, Path, None] = None) -> bool:
    """Log benchmark results JSON if present."""
    target = Path(path) if path else EVIDENCE_DIR / "benchmark_results.json"
    return _log_artifact_safely(target, "benchmark_results")


def log_compliance_output(path: Union[str, Path, None] = None) -> bool:
    """Log compliance advisory output JSON if present."""
    target = Path(path) if path else COMPLIANCE_REPORT_PATH
    return _log_artifact_safely(target, "compliance_output")


def _build_params_context(governance_run_id: Optional[str] = None) -> Dict[str, Any]:
    """Assemble params context from the verified metrics file and run metadata."""
    ctx: Dict[str, Any] = {}
    if VERIFIED_METRICS_JSON_PATH.exists():
        try:
            data = json.loads(VERIFIED_METRICS_JSON_PATH.read_text(encoding="utf-8"))
            ctx["dataset_rows"] = data.get("total_rows")
            ctx["feature_count"] = data.get("feature_count")
            ctx["model_type"] = data.get("model_type")
            ctx["target"] = data.get("target")
            ctx["class_balance"] = str(data.get("class_balance", {}))
            ctx["test_size"] = 0.2
            ctx["random_state"] = 42
        except Exception as exc:
            logger.warning("Could not read verified_metrics.json for MLflow params: %s", exc)
    if governance_run_id:
        ctx["validation_run_id"] = governance_run_id
    return ctx


def run_mlflow_tracking_summary(
    performance_report: Optional[Dict[str, Any]] = None,
    governance_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Log a complete AgentX validation run to local MLflow tracking.

    Configures the local tracking URI, opens a run, logs metrics, params,
    and all available artifacts, then closes the run.

    Returns a summary dict. Never raises -- exceptions are caught and
    returned in the summary so the calling pipeline is not disrupted.
    """
    configure_mlflow()

    run_name = governance_run_id or "agentx_validation"
    artifact_results: Dict[str, bool] = {}
    run_id: Optional[str] = None

    try:
        with mlflow.start_run(run_name=run_name) as active_run:
            run_id = active_run.info.run_id

            if performance_report:
                log_model_metrics(performance_report)

            params_ctx = _build_params_context(governance_run_id=governance_run_id)
            log_validation_params(params_ctx)

            # Standard evidence artifacts
            evidence_artifacts: Dict[str, Union[str, Path]] = {
                "verified_metrics_json": VERIFIED_METRICS_JSON_PATH,
                "verified_metrics_md": EVIDENCE_DIR / "verified_metrics.md",
                "benchmark_results_json": EVIDENCE_DIR / "benchmark_results.json",
                "benchmark_report_md": EVIDENCE_DIR / "benchmark_report.md",
            }
            artifact_results.update(log_agentx_artifacts(evidence_artifacts))

            # Optional pipeline output artifacts
            artifact_results["shap_summary_png"] = _log_artifact_safely(
                SHAP_SUMMARY_PATH, "shap_summary_png"
            )
            artifact_results["governance_record"] = log_governance_record()
            artifact_results["compliance_output"] = log_compliance_output()
            artifact_results["drift_report"] = _log_artifact_safely(
                DRIFT_REPORT_PATH, "drift_report"
            )

        logger.info("MLflow run complete: run_id=%s experiment=%s", run_id, MLFLOW_EXPERIMENT_NAME)

    except Exception as exc:
        logger.error("MLflow tracking error: %s", exc)
        return {
            "status": "error",
            "error": str(exc),
            "run_id": run_id,
            "experiment": MLFLOW_EXPERIMENT_NAME,
            "tracking_uri": MLFLOW_TRACKING_DIR.as_uri(),
            "metrics_logged": False,
            "artifacts_logged": artifact_results,
        }

    return {
        "status": "ok",
        "run_id": run_id,
        "experiment": MLFLOW_EXPERIMENT_NAME,
        "tracking_uri": MLFLOW_TRACKING_DIR.as_uri(),
        "metrics_logged": performance_report is not None,
        "artifacts_logged": artifact_results,
    }


def mlflow_tracking_available() -> bool:
    """Return True if the local mlruns directory exists with at least one run."""
    return MLFLOW_TRACKING_DIR.exists() and any(MLFLOW_TRACKING_DIR.iterdir())