"""
utils/governance.py -- Local governance evidence layer for AgentX.

Creates structured validation-run records after each pipeline execution.
Records are stored in data/governance/validation_runs/ with a "latest" copy
at data/governance/latest_validation_run.json.

IMPORTANT: These records are local governance evidence for development and portfolio
purposes. They are not production regulatory records and do not constitute
regulatory approval.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.config import (
    COMPLIANCE_REPORT_PATH,
    DATA_VALIDATION_PATH,
    DRIFT_REPORT_PATH,
    EVIDENCE_DIR,
    GOVERNANCE_LATEST_PATH,
    GOVERNANCE_RUNS_DIR,
    MODEL_PATH,
    PERFORMANCE_METRICS_PATH,
    PROJECT_ROOT,
    REPORT_MD_PATH,
    SHAP_SUMMARY_PATH,
    VERIFIED_METRICS_JSON_PATH,
    VERIFIED_METRICS_MD_PATH,
)
from utils.logging_utils import setup_logger

logger = setup_logger("agentx.governance")

GOVERNANCE_CLAIM_SAFETY = (
    "Local governance evidence record for development and portfolio evidence. "
    "Not a production regulatory approval record."
)

SYSTEM_NAME = "AgentX Risk Validator"
SYSTEM_VERSION = "1.0.0"

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


def generate_validation_run_id() -> str:
    now = datetime.now(timezone.utc)
    uid = uuid.uuid4().hex[:8]
    return f"vrun_{now.strftime('%Y%m%d_%H%M%S')}_{uid}"


def collect_artifact_status() -> List[Dict[str, Any]]:
    results = []
    for p in _ARTIFACT_PATHS:
        exists = p.exists()
        size = p.stat().st_size if exists else None
        try:
            rel = str(p.relative_to(PROJECT_ROOT))
        except ValueError:
            rel = str(p)
        results.append({"path": rel, "exists": exists, "size_bytes": size})
    return results


def load_metrics_snapshot() -> Dict[str, Any]:
    if not VERIFIED_METRICS_JSON_PATH.exists():
        return {"available": False}
    try:
        with open(VERIFIED_METRICS_JSON_PATH, encoding="utf-8") as f:
            data = json.load(f)
        m = data.get("metrics", {})
        return {
            "available": True,
            "roc_auc": m.get("roc_auc"),
            "accuracy": m.get("accuracy"),
            "precision": m.get("precision"),
            "recall": m.get("recall"),
            "f1_score": m.get("f1_score"),
            "dataset_rows": data.get("total_rows"),
            "feature_count": data.get("feature_count"),
            "model_type": data.get("model_type"),
            "run_timestamp": data.get("run_timestamp"),
            "source": "docs/evidence/verified_metrics.json",
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def load_drift_status() -> Dict[str, Any]:
    if not DRIFT_REPORT_PATH.exists():
        return {"available": False}
    try:
        with open(DRIFT_REPORT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        details = data.get("details", [])
        drifted = [d["feature"] for d in details if d.get("drifted")]
        return {
            "available": True,
            "drift_detected": data.get("drift_detected", False),
            "drifted_features": drifted,
            "total_features_tested": len(details),
            "source": "data/validation_outputs/drift_report.json",
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def load_compliance_status() -> Dict[str, Any]:
    if not COMPLIANCE_REPORT_PATH.exists():
        return {"available": False, "status": "not_run"}
    try:
        with open(COMPLIANCE_REPORT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        report_source = data.get("source", "unknown")
        return {
            "available": True,
            "status": "completed_advisory",
            "report_source": report_source,
            "note": (
                "Compliance output is advisory and illustrative. "
                "Not a regulatory determination."
            ),
            "source": "data/validation_outputs/last_compliance.json",
        }
    except Exception as exc:
        return {"available": False, "status": "error", "error": str(exc)}


def load_benchmark_summary() -> Dict[str, Any]:
    bench_path = EVIDENCE_DIR / "benchmark_results.json"
    if not bench_path.exists():
        return {"available": False}
    try:
        with open(bench_path, encoding="utf-8") as f:
            data = json.load(f)
        eps = data.get("endpoints", {})
        pipe = data.get("pipeline_direct", {})
        return {
            "available": True,
            "benchmark_date": (data.get("benchmark_date") or "")[:10],
            "get_health_median_ms": eps.get("GET /health", {}).get("median_ms"),
            "get_metrics_median_ms": eps.get("GET /metrics", {}).get("median_ms"),
            "get_evidence_median_ms": eps.get("GET /evidence", {}).get("median_ms"),
            "post_validate_median_ms": eps.get("POST /validate", {}).get("median_ms"),
            "pipeline_direct_median_ms": pipe.get("median_ms"),
            "disclaimer": data.get("disclaimer"),
            "source": "docs/evidence/benchmark_results.json",
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def create_validation_run_record(
    run_id: Optional[str] = None,
    run_type: str = "full_pipeline",
) -> Dict[str, Any]:
    if run_id is None:
        run_id = generate_validation_run_id()
    now_utc = datetime.now(timezone.utc).isoformat()

    metrics_snap = load_metrics_snapshot()
    drift = load_drift_status()
    compliance = load_compliance_status()
    bench = load_benchmark_summary()
    artifacts = collect_artifact_status()

    try:
        model_artifact_rel = str(MODEL_PATH.relative_to(PROJECT_ROOT))
    except ValueError:
        model_artifact_rel = str(MODEL_PATH)

    model_info: Dict[str, Any] = {
        "type": metrics_snap.get("model_type", "unknown"),
        "artifact_path": model_artifact_rel,
        "artifact_exists": MODEL_PATH.exists(),
    }

    dataset_info: Dict[str, Any] = {
        "name": "LendingClub public loan data (2007-2018Q4 sample)",
        "total_rows": metrics_snap.get("dataset_rows"),
        "feature_count": metrics_snap.get("feature_count"),
        "source": "data/raw_data/lending_club_clean_sample.csv",
    }

    risk_flags: List[str] = []
    if drift.get("drift_detected"):
        drifted = drift.get("drifted_features", [])
        risk_flags.append(f"Feature drift detected in: {', '.join(drifted)}")
    if not metrics_snap.get("available"):
        risk_flags.append(
            "Verified metrics file not available at record creation time"
        )

    return {
        "validation_run_id": run_id,
        "created_at_utc": now_utc,
        "system_name": SYSTEM_NAME,
        "system_version": SYSTEM_VERSION,
        "run_type": run_type,
        "model": model_info,
        "dataset": dataset_info,
        "metrics_snapshot": metrics_snap,
        "drift_status": drift,
        "compliance_status": compliance,
        "artifact_status": artifacts,
        "benchmark_summary": bench,
        "reviewer_status": "pending_review",
        "reviewer_notes": None,
        "risk_flags": risk_flags,
        "claim_safety_note": GOVERNANCE_CLAIM_SAFETY,
        "limitations": [
            "This record is generated by a local development pipeline.",
            "Reviewer status is a placeholder; no independent review has been performed.",
            "Compliance outputs are advisory only and are not regulatory determinations.",
            "Drift detection uses simulated drift data, not live production data.",
            "Benchmark figures reflect local in-process measurements, not production latency.",
        ],
        "source_files": [
            "main.py",
            "utils/governance.py",
            "docs/evidence/verified_metrics.json",
            "data/validation_outputs/drift_report.json",
            "data/validation_outputs/last_compliance.json",
        ],
    }


def write_validation_run_record(record: Dict[str, Any]) -> Dict[str, str]:
    GOVERNANCE_RUNS_DIR.mkdir(parents=True, exist_ok=True)

    run_id = record["validation_run_id"]
    run_path = GOVERNANCE_RUNS_DIR / f"{run_id}.json"

    with open(run_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    logger.info("Governance run record written to %s", run_path)

    GOVERNANCE_LATEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GOVERNANCE_LATEST_PATH, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    logger.info("Latest governance record updated at %s", GOVERNANCE_LATEST_PATH)

    return {
        "run_path": str(run_path),
        "latest_path": str(GOVERNANCE_LATEST_PATH),
    }


def load_latest_validation_run() -> Optional[Dict[str, Any]]:
    if not GOVERNANCE_LATEST_PATH.exists():
        return None
    try:
        with open(GOVERNANCE_LATEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def list_validation_runs(limit: int = 10) -> List[Dict[str, Any]]:
    if not GOVERNANCE_RUNS_DIR.exists():
        return []
    runs = []
    for p in sorted(GOVERNANCE_RUNS_DIR.iterdir(), reverse=True):
        if p.is_file() and p.suffix == ".json":
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                runs.append({
                    "validation_run_id": data.get("validation_run_id"),
                    "created_at_utc": data.get("created_at_utc"),
                    "run_type": data.get("run_type"),
                    "reviewer_status": data.get("reviewer_status"),
                    "risk_flags": data.get("risk_flags", []),
                    "roc_auc": data.get("metrics_snapshot", {}).get("roc_auc"),
                    "drift_detected": data.get("drift_status", {}).get("drift_detected"),
                    "file": p.name,
                })
            except Exception:
                continue
            if len(runs) >= limit:
                break
    return runs
