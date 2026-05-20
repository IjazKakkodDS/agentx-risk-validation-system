"""
Tests for utils/compliance_context.py -- compliance evidence context builder.

All tests that read files use the existing local artifacts. Tests that check
metrics expect verified_metrics.json to be present (it is committed as evidence).
Tests do not make live Groq API calls.
"""

import pytest

from utils.compliance_context import (
    ADVISORY_CLAIM_SAFETY,
    LIMITATIONS,
    build_compliance_context,
    format_compliance_context_for_prompt,
    load_artifact_context,
    load_benchmark_context,
    load_drift_context,
    load_governance_context,
    load_verified_metrics_context,
)


# ---------------------------------------------------------------------------
# load_verified_metrics_context
# ---------------------------------------------------------------------------

def test_load_verified_metrics_context_returns_dict():
    result = load_verified_metrics_context()
    assert isinstance(result, dict)


def test_load_verified_metrics_context_has_available_key():
    result = load_verified_metrics_context()
    assert "available" in result


def test_load_verified_metrics_context_roc_auc_if_available():
    result = load_verified_metrics_context()
    if result.get("available"):
        assert result.get("roc_auc") == 0.6776


def test_load_verified_metrics_context_has_low_recall_flag_if_available():
    result = load_verified_metrics_context()
    if result.get("available"):
        assert "low_recall_flag" in result
        assert result["low_recall_flag"] is True


def test_load_verified_metrics_context_has_class_imbalance_flag():
    result = load_verified_metrics_context()
    if result.get("available"):
        assert result.get("class_imbalance_present") is True
        assert result.get("roc_auc_preferred_metric") is True


# ---------------------------------------------------------------------------
# load_drift_context
# ---------------------------------------------------------------------------

def test_load_drift_context_returns_dict():
    result = load_drift_context()
    assert isinstance(result, dict)


def test_load_drift_context_has_available_key():
    result = load_drift_context()
    assert "available" in result


def test_load_drift_context_drifted_features_is_list_if_available():
    result = load_drift_context()
    if result.get("available"):
        assert isinstance(result.get("drifted_features"), list)


# ---------------------------------------------------------------------------
# load_artifact_context
# ---------------------------------------------------------------------------

def test_load_artifact_context_returns_dict():
    result = load_artifact_context()
    assert isinstance(result, dict)


def test_load_artifact_context_has_required_keys():
    result = load_artifact_context()
    for key in ("shap_explainability_present", "performance_evidence_present",
                "verified_metrics_present", "drift_evidence_present"):
        assert key in result


def test_load_artifact_context_values_are_bool():
    result = load_artifact_context()
    for key in ("shap_explainability_present", "performance_evidence_present",
                "verified_metrics_present", "drift_evidence_present"):
        assert isinstance(result[key], bool)


# ---------------------------------------------------------------------------
# load_governance_context
# ---------------------------------------------------------------------------

def test_load_governance_context_returns_dict():
    result = load_governance_context()
    assert isinstance(result, dict)


def test_load_governance_context_has_available_key():
    result = load_governance_context()
    assert "available" in result


def test_load_governance_context_has_run_id_if_available():
    result = load_governance_context()
    if result.get("available"):
        assert "validation_run_id" in result
        assert result["validation_run_id"].startswith("vrun_")


# ---------------------------------------------------------------------------
# load_benchmark_context
# ---------------------------------------------------------------------------

def test_load_benchmark_context_returns_dict():
    result = load_benchmark_context()
    assert isinstance(result, dict)


def test_load_benchmark_context_has_available_key():
    result = load_benchmark_context()
    assert "available" in result


# ---------------------------------------------------------------------------
# build_compliance_context
# ---------------------------------------------------------------------------

def test_build_compliance_context_returns_dict():
    ctx = build_compliance_context()
    assert isinstance(ctx, dict)


def test_build_compliance_context_has_required_top_level_keys():
    ctx = build_compliance_context()
    for key in ("metrics", "drift", "artifacts", "governance", "benchmark",
                "risk_flags", "limitations", "claim_safety_note",
                "advisory_only", "not_regulatory_approval"):
        assert key in ctx, f"Missing key: {key}"


def test_build_compliance_context_advisory_only_is_true():
    ctx = build_compliance_context()
    assert ctx["advisory_only"] is True


def test_build_compliance_context_not_regulatory_approval_is_true():
    ctx = build_compliance_context()
    assert ctx["not_regulatory_approval"] is True


def test_build_compliance_context_claim_safety_note_is_non_empty():
    ctx = build_compliance_context()
    assert len(ctx["claim_safety_note"]) > 0


def test_build_compliance_context_claim_safety_note_contains_advisory():
    ctx = build_compliance_context()
    assert "advisory" in ctx["claim_safety_note"].lower()


def test_build_compliance_context_limitations_is_non_empty_list():
    ctx = build_compliance_context()
    lims = ctx["limitations"]
    assert isinstance(lims, list)
    assert len(lims) > 0


def test_build_compliance_context_risk_flags_is_list():
    ctx = build_compliance_context()
    assert isinstance(ctx["risk_flags"], list)


def test_build_compliance_context_roc_auc_in_metrics_if_available():
    ctx = build_compliance_context()
    m = ctx.get("metrics", {})
    if m.get("available"):
        assert m.get("roc_auc") == 0.6776


def test_build_compliance_context_low_recall_flag_in_metrics():
    ctx = build_compliance_context()
    m = ctx.get("metrics", {})
    if m.get("available"):
        assert "low_recall_flag" in m
        assert m["low_recall_flag"] is True


def test_build_compliance_context_with_perf_report_override():
    perf = {
        "roc_auc": 0.6776,
        "accuracy": 0.804,
        "precision": 0.35,
        "recall": 0.037,
        "f1_score": 0.067,
        "confusion_matrix": [[797, 13], [183, 7]],
    }
    ctx = build_compliance_context(perf_report=perf)
    m = ctx["metrics"]
    assert m["available"] is True
    assert m["roc_auc"] == 0.6776
    assert m["low_recall_flag"] is True


def test_build_compliance_context_does_not_expose_secrets():
    import json
    ctx = build_compliance_context()
    text = json.dumps(ctx)
    assert "GROQ_API_KEY" not in text


# ---------------------------------------------------------------------------
# format_compliance_context_for_prompt
# ---------------------------------------------------------------------------

def test_format_context_returns_string():
    ctx = build_compliance_context()
    result = format_compliance_context_for_prompt(ctx)
    assert isinstance(result, str)


def test_format_context_contains_roc_auc_value():
    ctx = build_compliance_context()
    if ctx.get("metrics", {}).get("available"):
        result = format_compliance_context_for_prompt(ctx)
        assert "0.6776" in result


def test_format_context_contains_advisory_phrase():
    ctx = build_compliance_context()
    result = format_compliance_context_for_prompt(ctx)
    assert "advisory" in result.lower()


def test_format_context_contains_evidence_header():
    ctx = build_compliance_context()
    result = format_compliance_context_for_prompt(ctx)
    assert "EVIDENCE CONTEXT" in result


def test_format_context_does_not_expose_secrets():
    ctx = build_compliance_context()
    result = format_compliance_context_for_prompt(ctx)
    assert "GROQ_API_KEY" not in result
    assert "sk-" not in result


# ---------------------------------------------------------------------------
# ADVISORY_CLAIM_SAFETY and LIMITATIONS constants
# ---------------------------------------------------------------------------

def test_advisory_claim_safety_constant_contains_advisory():
    assert "advisory" in ADVISORY_CLAIM_SAFETY.lower()


def test_advisory_claim_safety_does_not_claim_regulatory_approval():
    text = ADVISORY_CLAIM_SAFETY.lower()
    assert "not constitute regulatory approval" in text or "does not constitute" in text


def test_limitations_is_non_empty_list():
    assert isinstance(LIMITATIONS, list)
    assert len(LIMITATIONS) > 0
