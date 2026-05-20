"""
Tests for pipeline-generated artifacts and evidence files.

These tests verify that output files exist, are non-empty, and contain
the expected verified metrics. They assume at least one pipeline run has
completed (which is required before this phase anyway).
"""

import json

import pytest

from utils.config import (
    COMPLIANCE_REPORT_PATH,
    DATA_VALIDATION_PATH,
    DRIFT_REPORT_PATH,
    EVIDENCE_DIR,
    LOG_DIR,
    MODEL_PATH,
    PERFORMANCE_METRICS_PATH,
    REPORT_MD_PATH,
    SHAP_SUMMARY_PATH,
    VALIDATION_OUTPUTS_DIR,
    VERIFIED_METRICS_JSON_PATH,
    VERIFIED_METRICS_MD_PATH,
)

VERIFIED_ROC_AUC = 0.6776


# ---------------------------------------------------------------------------
# Evidence files
# ---------------------------------------------------------------------------

def test_verified_metrics_md_exists():
    assert VERIFIED_METRICS_MD_PATH.exists(), f"Missing: {VERIFIED_METRICS_MD_PATH}"


def test_verified_metrics_md_is_non_empty():
    assert VERIFIED_METRICS_MD_PATH.stat().st_size > 0


def test_verified_metrics_json_exists():
    assert VERIFIED_METRICS_JSON_PATH.exists(), f"Missing: {VERIFIED_METRICS_JSON_PATH}"


def test_verified_metrics_json_is_non_empty():
    assert VERIFIED_METRICS_JSON_PATH.stat().st_size > 0


def test_verified_metrics_json_has_metrics_key():
    with open(VERIFIED_METRICS_JSON_PATH) as f:
        data = json.load(f)
    assert "metrics" in data, "verified_metrics.json missing 'metrics' key"


def test_verified_roc_auc_is_unchanged():
    with open(VERIFIED_METRICS_JSON_PATH) as f:
        data = json.load(f)
    recorded = data["metrics"].get("roc_auc")
    assert recorded == VERIFIED_ROC_AUC, (
        f"ROC-AUC changed from verified value {VERIFIED_ROC_AUC}: got {recorded}. "
        "If the pipeline was rerun and the metric changed, update verified_metrics docs."
    )


def test_verified_metrics_md_contains_roc_auc():
    content = VERIFIED_METRICS_MD_PATH.read_text(encoding="utf-8")
    assert str(VERIFIED_ROC_AUC) in content, "Verified ROC-AUC not found in verified_metrics.md"


def test_evidence_dir_contains_upgrade_plan():
    assert (EVIDENCE_DIR / "upgrade_plan.md").exists()


def test_evidence_dir_contains_claim_safety():
    assert (EVIDENCE_DIR / "claim_safety.md").exists()


def test_evidence_dir_contains_code_cleanup_report():
    assert (EVIDENCE_DIR / "code_cleanup_report.md").exists()


# ---------------------------------------------------------------------------
# Validation output artifacts
# ---------------------------------------------------------------------------

def test_validation_outputs_dir_exists():
    assert VALIDATION_OUTPUTS_DIR.exists()


def test_data_validation_json_exists():
    assert DATA_VALIDATION_PATH.exists(), f"Missing: {DATA_VALIDATION_PATH}"
    assert DATA_VALIDATION_PATH.stat().st_size > 0


def test_performance_metrics_json_exists():
    assert PERFORMANCE_METRICS_PATH.exists(), f"Missing: {PERFORMANCE_METRICS_PATH}"
    assert PERFORMANCE_METRICS_PATH.stat().st_size > 0


def test_performance_metrics_json_has_roc_auc():
    with open(PERFORMANCE_METRICS_PATH) as f:
        data = json.load(f)
    assert "roc_auc" in data


def test_shap_summary_png_exists():
    assert SHAP_SUMMARY_PATH.exists(), (
        f"SHAP summary PNG missing at {SHAP_SUMMARY_PATH}. "
        "This was fixed in Phase 5B.3 -- run main.py to regenerate."
    )
    assert SHAP_SUMMARY_PATH.stat().st_size > 0


def test_drift_report_json_exists():
    assert DRIFT_REPORT_PATH.exists(), f"Missing: {DRIFT_REPORT_PATH}"
    assert DRIFT_REPORT_PATH.stat().st_size > 0


def test_compliance_report_json_exists():
    assert COMPLIANCE_REPORT_PATH.exists(), f"Missing: {COMPLIANCE_REPORT_PATH}"
    assert COMPLIANCE_REPORT_PATH.stat().st_size > 0


# ---------------------------------------------------------------------------
# Report artifacts
# ---------------------------------------------------------------------------

def test_validation_report_md_exists():
    assert REPORT_MD_PATH.exists(), f"Missing: {REPORT_MD_PATH}"
    assert REPORT_MD_PATH.stat().st_size > 0


# ---------------------------------------------------------------------------
# Model artifact
# ---------------------------------------------------------------------------

def test_model_artifact_exists():
    assert MODEL_PATH.exists(), f"Missing: {MODEL_PATH}"
    assert MODEL_PATH.stat().st_size > 0


# ---------------------------------------------------------------------------
# Log artifact
# ---------------------------------------------------------------------------

def test_log_dir_exists():
    assert LOG_DIR.exists(), f"Log directory missing: {LOG_DIR}"


def test_agentx_log_file_exists():
    log_file = LOG_DIR / "agentx.log"
    assert log_file.exists(), f"Log file missing: {log_file}"
    assert log_file.stat().st_size > 0
