"""
utils/compliance_context.py -- Compliance evidence context builder for AgentX.

Loads local validation artifacts and assembles a structured evidence context
that grounds the advisory compliance review in actual model validation data.

The context is advisory only and does not constitute regulatory approval,
regulatory certification, or a production compliance determination.
"""

import json
from typing import Any, Dict, List, Optional

from utils.config import (
    COMPLIANCE_REPORT_PATH,
    DRIFT_REPORT_PATH,
    EVIDENCE_DIR,
    GOVERNANCE_LATEST_PATH,
    PERFORMANCE_METRICS_PATH,
    SHAP_SUMMARY_PATH,
    VERIFIED_METRICS_JSON_PATH,
)
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)

ADVISORY_CLAIM_SAFETY = (
    "This compliance review is advisory only. It is generated from structured "
    "local validation evidence and does not constitute regulatory approval, "
    "regulatory certification, or a production compliance determination."
)

LIMITATIONS = [
    "Baseline model: LogisticRegression with no class weighting. Low recall on the default "
    "class is a known limitation of unweighted classification on an 81/19 imbalanced target.",
    "Dataset is a 5,000-row public LendingClub sample, not a live production portfolio.",
    "Compliance review is illustrative and advisory; it is not a regulatory determination.",
    "Drift detection uses a simulated incoming dataset, not live data streams.",
    "SHAP explainability is computed on a 100-row sample for performance reasons.",
    "This system is a local validation prototype; it is not a production credit scoring model.",
]


def load_verified_metrics_context() -> Dict[str, Any]:
    """Load verified model metrics from docs/evidence/verified_metrics.json."""
    if not VERIFIED_METRICS_JSON_PATH.exists():
        return {"available": False}
    try:
        with open(VERIFIED_METRICS_JSON_PATH, encoding="utf-8") as f:
            data = json.load(f)
        m = data.get("metrics", {})
        cb = data.get("class_balance", {})
        recall = m.get("recall", 1.0) or 1.0
        return {
            "available": True,
            "model_type": data.get("model_type", ""),
            "dataset_rows": data.get("total_rows", 0),
            "feature_count": data.get("feature_count", 0),
            "train_rows": data.get("train_rows", 0),
            "test_rows": data.get("test_rows", 0),
            "class_balance": cb,
            "class_imbalance_present": True,
            "roc_auc": m.get("roc_auc"),
            "accuracy": m.get("accuracy"),
            "precision": m.get("precision"),
            "recall": m.get("recall"),
            "f1_score": m.get("f1_score"),
            "low_recall_flag": recall < 0.1,
            "roc_auc_preferred_metric": True,
            "run_timestamp": data.get("run_timestamp"),
        }
    except Exception as exc:
        logger.warning("Failed to load verified metrics for compliance context: %s", exc)
        return {"available": False}


def _metrics_from_perf_report(perf_report: Dict[str, Any]) -> Dict[str, Any]:
    """Build metrics context from a live pipeline performance_report dict."""
    recall = perf_report.get("recall", 1.0) or 1.0
    base = {
        "available": True,
        "roc_auc": perf_report.get("roc_auc"),
        "accuracy": perf_report.get("accuracy"),
        "precision": perf_report.get("precision"),
        "recall": perf_report.get("recall"),
        "f1_score": perf_report.get("f1_score"),
        "low_recall_flag": recall < 0.1,
        "class_imbalance_present": True,
        "roc_auc_preferred_metric": True,
        "model_type": "sklearn Pipeline: StandardScaler + LogisticRegression(max_iter=1000, random_state=42)",
        "dataset_rows": 5000,
        "feature_count": 12,
        "class_balance": {"0": 0.8098, "1": 0.1902},
    }
    # Enrich from file if possible
    file_ctx = load_verified_metrics_context()
    if file_ctx.get("available"):
        base.update({
            "model_type": file_ctx.get("model_type", base["model_type"]),
            "dataset_rows": file_ctx.get("dataset_rows", base["dataset_rows"]),
            "feature_count": file_ctx.get("feature_count", base["feature_count"]),
            "class_balance": file_ctx.get("class_balance", base["class_balance"]),
            "train_rows": file_ctx.get("train_rows"),
            "test_rows": file_ctx.get("test_rows"),
        })
    return base


def load_drift_context() -> Dict[str, Any]:
    """Load drift report from data/validation_outputs/drift_report.json."""
    if not DRIFT_REPORT_PATH.exists():
        return {"available": False}
    try:
        with open(DRIFT_REPORT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        details = data.get("details", [])
        drifted = [
            d.get("feature", "")
            for d in details
            if d.get("drifted") or d.get("drift_detected")
        ]
        return {
            "available": True,
            "drift_detected": data.get("drift_detected", False),
            "drifted_features": drifted,
            "total_features_tested": len(details),
        }
    except Exception as exc:
        logger.warning("Failed to load drift report for compliance context: %s", exc)
        return {"available": False}


def load_artifact_context() -> Dict[str, Any]:
    """Check existence of key validation artifacts."""
    return {
        "available": True,
        "shap_explainability_present": SHAP_SUMMARY_PATH.exists(),
        "performance_evidence_present": PERFORMANCE_METRICS_PATH.exists(),
        "verified_metrics_present": VERIFIED_METRICS_JSON_PATH.exists(),
        "drift_evidence_present": DRIFT_REPORT_PATH.exists(),
        "compliance_report_present": COMPLIANCE_REPORT_PATH.exists(),
    }


def load_governance_context() -> Dict[str, Any]:
    """Load the latest governance validation-run record."""
    if not GOVERNANCE_LATEST_PATH.exists():
        return {"available": False}
    try:
        with open(GOVERNANCE_LATEST_PATH, encoding="utf-8") as f:
            record = json.load(f)
        return {
            "available": True,
            "validation_run_id": record.get("validation_run_id"),
            "created_at_utc": record.get("created_at_utc"),
            "reviewer_status": record.get("reviewer_status"),
            "risk_flags": record.get("risk_flags", []),
        }
    except Exception as exc:
        logger.warning("Failed to load governance record for compliance context: %s", exc)
        return {"available": False}


def load_benchmark_context() -> Dict[str, Any]:
    """Load benchmark summary if available."""
    bench_path = EVIDENCE_DIR / "benchmark_results.json"
    if not bench_path.exists():
        return {"available": False}
    try:
        with open(bench_path, encoding="utf-8") as f:
            data = json.load(f)
        eps = data.get("endpoints", {})
        pipeline = data.get("pipeline_direct", {})
        return {
            "available": True,
            "health_median_ms": eps.get("GET /health", {}).get("median_ms"),
            "validate_median_ms": eps.get("POST /validate", {}).get("median_ms"),
            "pipeline_median_ms": pipeline.get("median_ms"),
            "artifacts_all_present": data.get("artifacts", {}).get("all_present", False),
        }
    except Exception as exc:
        logger.warning("Failed to load benchmark results for compliance context: %s", exc)
        return {"available": False}


def build_compliance_context(perf_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Assemble the full compliance evidence context.

    Args:
        perf_report: Optional live performance_report dict from the current pipeline run.
                     If provided, metrics are taken from this dict (most current).
                     If None, metrics are loaded from docs/evidence/verified_metrics.json.

    Returns:
        Structured dict with metrics, drift, artifacts, governance, benchmark,
        risk_flags, limitations, claim_safety_note, advisory_only, not_regulatory_approval.
    """
    metrics = _metrics_from_perf_report(perf_report) if perf_report is not None else load_verified_metrics_context()
    drift = load_drift_context()
    artifacts = load_artifact_context()
    governance = load_governance_context()
    benchmark = load_benchmark_context()

    risk_flags: List[str] = []
    if metrics.get("low_recall_flag"):
        risk_flags.append(
            f"Low recall ({metrics.get('recall')}) on the default class due to class imbalance. "
            "Class weighting or a tree-based model is recommended."
        )
    if drift.get("drift_detected"):
        drifted = drift.get("drifted_features", [])
        risk_flags.append(
            f"Feature drift detected in: {', '.join(drifted)}. "
            "Model stability should be re-assessed against the incoming distribution."
        )
    if metrics.get("available") and not artifacts.get("shap_explainability_present"):
        risk_flags.append(
            "SHAP explainability artifact not found. Explainability review is incomplete."
        )
    for flag in governance.get("risk_flags", []):
        if flag not in risk_flags:
            risk_flags.append(flag)

    return {
        "metrics": metrics,
        "drift": drift,
        "artifacts": artifacts,
        "governance": governance,
        "benchmark": benchmark,
        "risk_flags": risk_flags,
        "limitations": LIMITATIONS,
        "claim_safety_note": ADVISORY_CLAIM_SAFETY,
        "advisory_only": True,
        "not_regulatory_approval": True,
    }


def format_compliance_context_for_prompt(context: Dict[str, Any]) -> str:
    """Format the compliance evidence context as a structured string for LLM prompts."""
    m = context.get("metrics", {})
    d = context.get("drift", {})
    gov = context.get("governance", {})
    flags = context.get("risk_flags", [])
    lims = context.get("limitations", [])

    cb = m.get("class_balance", {})
    pct_non_default = round((cb.get("0") or 0.81) * 100)
    pct_default = round((cb.get("1") or 0.19) * 100)

    lines = [
        "=== AGENTX VALIDATION EVIDENCE CONTEXT ===",
        "",
        "This review is advisory only. It does not constitute regulatory approval.",
        "",
        "--- Model Evidence ---",
    ]

    if m.get("available"):
        lines += [
            f"Model: {m.get('model_type', 'LogisticRegression Pipeline')}",
            f"Dataset: LendingClub public sample, {m.get('dataset_rows', 'N/A')} rows, "
            f"{m.get('feature_count', 'N/A')} features",
            f"Class balance: ~{pct_non_default}% non-default / ~{pct_default}% default",
            f"ROC-AUC (preferred metric): {m.get('roc_auc', 'N/A')}",
            f"Accuracy: {m.get('accuracy', 'N/A')} (reflects class imbalance -- not the headline metric)",
            f"Precision: {m.get('precision', 'N/A')}",
            f"Recall: {m.get('recall', 'N/A')} (low -- baseline limitation; see limitations below)",
            f"F1 Score: {m.get('f1_score', 'N/A')}",
            f"Class imbalance present: {m.get('class_imbalance_present', True)}",
            f"Low recall flag: {m.get('low_recall_flag', 'N/A')}",
            f"ROC-AUC is the preferred headline metric: {m.get('roc_auc_preferred_metric', True)}",
        ]
    else:
        lines.append("Verified metrics: not yet available (run the pipeline first)")

    lines += ["", "--- Drift Status ---"]
    if d.get("available"):
        lines += [
            f"Drift detected: {d.get('drift_detected', False)}",
            f"Drifted features: {', '.join(d.get('drifted_features', [])) or 'none'}",
            f"Features tested: {d.get('total_features_tested', 'N/A')}",
        ]
    else:
        lines.append("Drift report: not yet available")

    lines += ["", "--- Governance Context ---"]
    if gov.get("available"):
        lines += [
            f"Validation run ID: {gov.get('validation_run_id', 'N/A')}",
            f"Run timestamp: {gov.get('created_at_utc', 'N/A')}",
            f"Reviewer status: {gov.get('reviewer_status', 'N/A')}",
            f"Governance risk flags: {', '.join(gov.get('risk_flags', [])) or 'none'}",
        ]
    else:
        lines.append("Governance record: not yet available")

    if flags:
        lines += ["", "--- Risk Flags ---"]
        for flag in flags:
            lines.append(f"- {flag}")

    lines += ["", "--- Limitations ---"]
    for lim in lims:
        lines.append(f"- {lim}")

    lines += [
        "",
        "--- Claim Safety ---",
        context.get("claim_safety_note", ADVISORY_CLAIM_SAFETY),
        "",
        "=== END OF EVIDENCE CONTEXT ===",
    ]
    return "\n".join(lines)
