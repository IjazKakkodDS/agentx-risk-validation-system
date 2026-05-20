"""
Tests for utils/audit_pack.py -- local audit pack generation.

All tests that write files use tmp_path to avoid polluting real output directories.
No live Groq API calls are made.
"""

import json

import pytest


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

def test_audit_pack_module_imports():
    from utils.audit_pack import (
        CLAIM_SAFETY_NOTE,
        LIMITATIONS,
        collect_audit_pack_context,
        generate_audit_pack,
        render_audit_markdown,
        write_audit_html,
        write_audit_markdown,
        write_audit_pdf,
    )


def test_claim_safety_note_non_empty():
    from utils.audit_pack import CLAIM_SAFETY_NOTE
    assert isinstance(CLAIM_SAFETY_NOTE, str)
    assert len(CLAIM_SAFETY_NOTE) > 20


def test_claim_safety_note_does_not_claim_regulatory_approval():
    from utils.audit_pack import CLAIM_SAFETY_NOTE
    lower = CLAIM_SAFETY_NOTE.lower()
    assert "regulatory approval" not in lower or "not constitute" in lower


def test_limitations_is_non_empty_list():
    from utils.audit_pack import LIMITATIONS
    assert isinstance(LIMITATIONS, list)
    assert len(LIMITATIONS) >= 3


# ---------------------------------------------------------------------------
# collect_audit_pack_context
# ---------------------------------------------------------------------------

def _patch_audit_paths(monkeypatch, tmp_path):
    """Patch all Path constants used by collect_audit_pack_context."""
    monkeypatch.setattr("utils.audit_pack.VERIFIED_METRICS_JSON_PATH", tmp_path / "no_metrics.json")
    monkeypatch.setattr("utils.audit_pack.DRIFT_REPORT_PATH", tmp_path / "no_drift.json")
    monkeypatch.setattr("utils.audit_pack.GOVERNANCE_LATEST_PATH", tmp_path / "no_gov.json")
    monkeypatch.setattr("utils.audit_pack.COMPLIANCE_REPORT_PATH", tmp_path / "no_comp.json")
    monkeypatch.setattr("utils.audit_pack.EVIDENCE_DIR", tmp_path)
    monkeypatch.setattr("utils.audit_pack.MLFLOW_TRACKING_DIR", tmp_path / "no_mlruns")
    monkeypatch.setattr("utils.audit_pack.AUDIT_PACK_DIR", tmp_path / "audit_pack")
    monkeypatch.setattr("utils.audit_pack.AUDIT_PACK_MD_PATH", tmp_path / "audit_pack" / "audit_pack.md")
    monkeypatch.setattr("utils.audit_pack.AUDIT_PACK_HTML_PATH", tmp_path / "audit_pack" / "audit_pack.html")
    monkeypatch.setattr("utils.audit_pack.AUDIT_PACK_PDF_PATH", tmp_path / "audit_pack" / "audit_pack.pdf")
    monkeypatch.setattr("utils.audit_pack.AUDIT_PACK_JSON_PATH", tmp_path / "audit_pack" / "audit_pack_context.json")


EXPECTED_CONTEXT_KEYS = [
    "generated_at_utc",
    "validation_run_id",
    "system_name",
    "system_version",
    "roc_auc",
    "accuracy",
    "precision",
    "recall",
    "f1_score",
    "dataset_rows",
    "feature_count",
    "model_type",
    "drift_detected",
    "drifted_features",
    "reviewer_status",
    "risk_flags",
    "compliance_source",
    "evidence_grounded",
    "compliance_summary",
    "mlflow_available",
    "claim_safety_note",
    "limitations",
]


def test_collect_audit_pack_context_has_expected_keys(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import collect_audit_pack_context
    ctx = collect_audit_pack_context()
    for key in EXPECTED_CONTEXT_KEYS:
        assert key in ctx, f"Missing key: {key}"


def test_collect_audit_pack_context_no_secrets(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import collect_audit_pack_context
    ctx = collect_audit_pack_context()
    ctx_str = json.dumps(ctx, default=str)
    assert "GROQ_API_KEY" not in ctx_str
    assert ".env" not in ctx_str
    assert "password" not in ctx_str.lower()


def test_collect_audit_pack_context_no_files_does_not_crash(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import collect_audit_pack_context
    ctx = collect_audit_pack_context()
    assert isinstance(ctx, dict)


def test_collect_audit_pack_context_roc_auc_from_real_metrics(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    metrics_file = tmp_path / "no_metrics.json"
    metrics_file.write_text(
        json.dumps({"metrics": {"roc_auc": 0.6776, "accuracy": 0.804}, "total_rows": 5000, "feature_count": 12}),
        encoding="utf-8",
    )
    monkeypatch.setattr("utils.audit_pack.VERIFIED_METRICS_JSON_PATH", metrics_file)
    from utils.audit_pack import collect_audit_pack_context
    ctx = collect_audit_pack_context()
    assert ctx["roc_auc"] == 0.6776
    assert ctx["dataset_rows"] == 5000


def test_collect_audit_pack_context_system_name(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import collect_audit_pack_context
    ctx = collect_audit_pack_context()
    assert ctx["system_name"] == "AgentX Risk Validator"


def test_collect_audit_pack_context_limitations_is_list(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import collect_audit_pack_context
    ctx = collect_audit_pack_context()
    assert isinstance(ctx["limitations"], list)
    assert len(ctx["limitations"]) >= 3


# ---------------------------------------------------------------------------
# render_audit_markdown
# ---------------------------------------------------------------------------

SAMPLE_CONTEXT = {
    "generated_at_utc": "2026-05-20T12:00:00+00:00",
    "validation_run_id": "vrun_test_abc",
    "system_name": "AgentX Risk Validator",
    "system_version": "1.0.0",
    "roc_auc": 0.6776,
    "accuracy": 0.804,
    "precision": 0.35,
    "recall": 0.037,
    "f1_score": 0.067,
    "dataset_rows": 5000,
    "feature_count": 12,
    "model_type": "Pipeline(StandardScaler + LogisticRegression)",
    "class_balance": {"0": 0.81, "1": 0.19},
    "drift_detected": True,
    "drifted_features": ["annual_inc", "loan_amnt"],
    "reviewer_status": "pending_review",
    "risk_flags": ["Feature drift detected"],
    "compliance_source": "LocalFallback",
    "evidence_grounded": True,
    "compliance_summary": "Advisory: ROC-AUC 0.6776 meets threshold.",
    "benchmark_health_median_ms": 1.9,
    "benchmark_validate_median_ms": 2399,
    "mlflow_available": True,
    "mlflow_experiment": "agentx_risk_validation",
    "claim_safety_note": "This is a local development document.",
    "limitations": ["Low recall is expected.", "Not production deployed."],
}


def test_render_audit_markdown_non_empty():
    from utils.audit_pack import render_audit_markdown
    md = render_audit_markdown(SAMPLE_CONTEXT)
    assert isinstance(md, str)
    assert len(md) > 200


def test_render_audit_markdown_contains_claim_safety():
    from utils.audit_pack import render_audit_markdown, CLAIM_SAFETY_NOTE
    md = render_audit_markdown(SAMPLE_CONTEXT)
    assert "Claim Safety" in md
    assert CLAIM_SAFETY_NOTE in md


def test_render_audit_markdown_contains_roc_auc():
    from utils.audit_pack import render_audit_markdown
    md = render_audit_markdown(SAMPLE_CONTEXT)
    assert "0.6776" in md


def test_render_audit_markdown_contains_metrics_heading():
    from utils.audit_pack import render_audit_markdown
    md = render_audit_markdown(SAMPLE_CONTEXT)
    assert "Verified Model Metrics" in md


def test_render_audit_markdown_contains_drift_features():
    from utils.audit_pack import render_audit_markdown
    md = render_audit_markdown(SAMPLE_CONTEXT)
    assert "annual_inc" in md or "loan_amnt" in md


def test_render_audit_markdown_contains_limitations():
    from utils.audit_pack import render_audit_markdown
    md = render_audit_markdown(SAMPLE_CONTEXT)
    assert "Limitations" in md


def test_render_audit_markdown_contains_validation_run_id():
    from utils.audit_pack import render_audit_markdown
    md = render_audit_markdown(SAMPLE_CONTEXT)
    assert "vrun_test_abc" in md


# ---------------------------------------------------------------------------
# write_audit_markdown
# ---------------------------------------------------------------------------

def test_write_audit_markdown_creates_file(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import write_audit_markdown
    path = write_audit_markdown(SAMPLE_CONTEXT)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "AgentX" in content


def test_write_audit_markdown_returns_path_object(tmp_path, monkeypatch):
    from pathlib import Path
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import write_audit_markdown
    result = write_audit_markdown(SAMPLE_CONTEXT)
    assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# write_audit_html
# ---------------------------------------------------------------------------

def test_write_audit_html_non_empty(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import render_audit_markdown, write_audit_html
    md = render_audit_markdown(SAMPLE_CONTEXT)
    path = write_audit_html(md)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert len(content) > 100


def test_write_audit_html_contains_html_tag(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import render_audit_markdown, write_audit_html
    md = render_audit_markdown(SAMPLE_CONTEXT)
    path = write_audit_html(md)
    content = path.read_text(encoding="utf-8")
    assert "<html" in content


def test_write_audit_html_contains_roc_auc(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import render_audit_markdown, write_audit_html
    md = render_audit_markdown(SAMPLE_CONTEXT)
    path = write_audit_html(md)
    content = path.read_text(encoding="utf-8")
    assert "0.6776" in content


# ---------------------------------------------------------------------------
# write_audit_pdf
# ---------------------------------------------------------------------------

def test_write_audit_pdf_returns_status_dict(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import write_audit_pdf
    result = write_audit_pdf(SAMPLE_CONTEXT)
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] in ("ok", "skipped", "error")


def test_write_audit_pdf_does_not_raise(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import write_audit_pdf
    result = write_audit_pdf(SAMPLE_CONTEXT)
    assert result is not None


def test_write_audit_pdf_graceful_when_fpdf_missing(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "fpdf":
            raise ImportError("fpdf2 not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    from utils.audit_pack import write_audit_pdf
    result = write_audit_pdf(SAMPLE_CONTEXT)
    assert result["status"] in ("skipped", "error")


# ---------------------------------------------------------------------------
# generate_audit_pack
# ---------------------------------------------------------------------------

def test_generate_audit_pack_returns_ok(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import generate_audit_pack
    result = generate_audit_pack()
    assert result.get("status") == "ok"


def test_generate_audit_pack_creates_markdown(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import generate_audit_pack
    result = generate_audit_pack()
    assert result.get("markdown_path") is not None
    from pathlib import Path
    assert Path(result["markdown_path"]).exists()


def test_generate_audit_pack_status_dict_keys(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import generate_audit_pack
    result = generate_audit_pack()
    for key in ("status", "markdown_path", "html_path", "pdf_status", "pdf_path", "warnings"):
        assert key in result, f"Missing key: {key}"


def test_generate_audit_pack_no_secrets(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import generate_audit_pack
    result = generate_audit_pack()
    result_str = json.dumps(result, default=str)
    assert "GROQ_API_KEY" not in result_str
    assert ".env" not in result_str


def test_generate_audit_pack_warnings_is_list(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    from utils.audit_pack import generate_audit_pack
    result = generate_audit_pack()
    assert isinstance(result.get("warnings"), list)


def test_generate_audit_pack_with_real_metrics(tmp_path, monkeypatch):
    _patch_audit_paths(monkeypatch, tmp_path)
    metrics_file = tmp_path / "no_metrics.json"
    metrics_file.write_text(
        json.dumps({
            "metrics": {"roc_auc": 0.6776, "accuracy": 0.804, "precision": 0.35, "recall": 0.037, "f1_score": 0.067},
            "total_rows": 5000,
            "feature_count": 12,
            "model_type": "Pipeline(StandardScaler + LogisticRegression)",
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr("utils.audit_pack.VERIFIED_METRICS_JSON_PATH", metrics_file)
    from utils.audit_pack import generate_audit_pack
    result = generate_audit_pack()
    assert result["status"] == "ok"
    from pathlib import Path
    md_content = Path(result["markdown_path"]).read_text(encoding="utf-8")
    assert "0.6776" in md_content