"""
Tests for individual AgentX agents.

Design principles:
- DataValidator, Performance, Drift, FeedbackMemory, ReportWriter:
  tested with real data, assertions on structure.
- ExplainabilityAgent: tested on 20 rows to keep SHAP runtime short;
  SHAP_SUMMARY_PATH redirected to tmp_path so production PNG is not overwritten.
- ComplianceAgent: fallback path tested without a live Groq API call by
  removing GROQ_API_KEY from the environment.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from agents.data_validator_agent import validate_data
from agents.performance_agent import evaluate_model
from utils.config import DRIFT_INCOMING_PATH, RAW_SAMPLE_PATH


# ---------------------------------------------------------------------------
# Data Validator Agent
# ---------------------------------------------------------------------------

def test_validate_data_returns_expected_keys(preprocessed_df):
    report = validate_data(preprocessed_df)
    required = {"missing_values", "duplicate_rows", "class_distribution", "summary_statistics"}
    assert required.issubset(set(report.keys()))


def test_validate_data_missing_values_is_integer(preprocessed_df):
    report = validate_data(preprocessed_df)
    assert isinstance(report["missing_values"], int)


def test_validate_data_reports_zero_missing_on_clean_data(preprocessed_df):
    report = validate_data(preprocessed_df)
    assert report["missing_values"] == 0


def test_validate_data_class_distribution_sums_to_one(preprocessed_df):
    report = validate_data(preprocessed_df)
    total = sum(report["class_distribution"].values())
    assert abs(total - 1.0) < 1e-3


# ---------------------------------------------------------------------------
# Performance Agent
# ---------------------------------------------------------------------------

def test_performance_agent_returns_all_metric_keys(trained_model_and_test):
    model, X_test, y_test = trained_model_and_test
    metrics = evaluate_model(model, X_test, y_test)
    for key in ("accuracy", "precision", "recall", "f1_score", "roc_auc"):
        assert key in metrics


def test_performance_agent_roc_auc_above_random(trained_model_and_test):
    model, X_test, y_test = trained_model_and_test
    metrics = evaluate_model(model, X_test, y_test)
    assert metrics["roc_auc"] > 0.5, "ROC-AUC should exceed random-chance baseline of 0.5"


# ---------------------------------------------------------------------------
# Explainability Agent (SHAP)
# ---------------------------------------------------------------------------

def test_explain_model_returns_expected_structure(trained_model_and_test, tmp_path, monkeypatch):
    import agents.explainability_agent as ea
    monkeypatch.setattr(ea, "SHAP_SUMMARY_PATH", tmp_path / "shap_summary.png")
    from agents.explainability_agent import explain_model
    model, X_test, _ = trained_model_and_test
    result = explain_model(model, X_test.iloc[:20])
    for key in ("mean_vector", "feature_names", "shap_values", "vector_dim", "norm_factor"):
        assert key in result, f"Missing key in SHAP result: {key}"


def test_explain_model_mean_vector_is_list(trained_model_and_test, tmp_path, monkeypatch):
    import agents.explainability_agent as ea
    monkeypatch.setattr(ea, "SHAP_SUMMARY_PATH", tmp_path / "shap_summary.png")
    from agents.explainability_agent import explain_model
    model, X_test, _ = trained_model_and_test
    result = explain_model(model, X_test.iloc[:20])
    assert isinstance(result["mean_vector"], list)
    assert len(result["mean_vector"]) > 0


def test_explain_model_mean_vector_is_normalized(trained_model_and_test, tmp_path, monkeypatch):
    import agents.explainability_agent as ea
    monkeypatch.setattr(ea, "SHAP_SUMMARY_PATH", tmp_path / "shap_summary.png")
    from agents.explainability_agent import explain_model
    model, X_test, _ = trained_model_and_test
    result = explain_model(model, X_test.iloc[:20])
    vec = np.array(result["mean_vector"], dtype="float32")
    norm = float(np.linalg.norm(vec))
    assert abs(norm - 1.0) < 1e-4, f"Mean SHAP vector is not unit-normalized (norm={norm:.6f})"


def test_explain_model_saves_png(trained_model_and_test, tmp_path, monkeypatch):
    import agents.explainability_agent as ea
    png_path = tmp_path / "shap_summary.png"
    monkeypatch.setattr(ea, "SHAP_SUMMARY_PATH", png_path)
    from agents.explainability_agent import explain_model
    model, X_test, _ = trained_model_and_test
    explain_model(model, X_test.iloc[:20])
    assert png_path.exists(), "SHAP summary PNG was not written"
    assert png_path.stat().st_size > 0


def test_explain_model_feature_names_match_x_columns(trained_model_and_test, tmp_path, monkeypatch):
    import agents.explainability_agent as ea
    monkeypatch.setattr(ea, "SHAP_SUMMARY_PATH", tmp_path / "shap_summary.png")
    from agents.explainability_agent import explain_model
    model, X_test, _ = trained_model_and_test
    sample = X_test.iloc[:20]
    result = explain_model(model, sample)
    assert result["feature_names"] == list(sample.columns)


# ---------------------------------------------------------------------------
# Compliance Agent (fallback path -- no live API call)
# ---------------------------------------------------------------------------

def test_compliance_cached_response_is_non_empty_string():
    from agents.compliance_agent import _cached_response
    result = _cached_response()
    assert isinstance(result, str)
    assert len(result) > 0


def test_compliance_fallback_when_no_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    from agents.compliance_agent import generate_compliance_report
    report, source = generate_compliance_report()
    assert isinstance(report, str)
    assert len(report) > 0
    assert source == "LocalFallback"


def test_compliance_fallback_report_does_not_expose_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    from agents.compliance_agent import generate_compliance_report
    report, _ = generate_compliance_report()
    assert "GROQ_API_KEY" not in report
    assert "sk-" not in report


def test_compliance_fallback_advisory_contains_advisory_note(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    from agents.compliance_agent import _fallback_advisory
    report = _fallback_advisory(None)
    assert "advisory" in report.lower()
    assert "regulatory approval" not in report.lower().replace("not constitute regulatory approval", "")


def test_compliance_fallback_with_evidence_context_includes_roc_auc(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    from agents.compliance_agent import generate_compliance_report
    ctx = {
        "metrics": {
            "available": True,
            "roc_auc": 0.6776,
            "accuracy": 0.804,
            "precision": 0.35,
            "recall": 0.037,
            "f1_score": 0.067,
            "dataset_rows": 5000,
            "feature_count": 12,
            "class_balance": {"0": 0.8098, "1": 0.1902},
            "class_imbalance_present": True,
            "low_recall_flag": True,
            "roc_auc_preferred_metric": True,
        },
        "drift": {"available": False},
        "governance": {"available": False},
        "benchmark": {"available": False},
        "risk_flags": [],
        "limitations": [],
        "claim_safety_note": "Advisory only.",
        "advisory_only": True,
        "not_regulatory_approval": True,
    }
    report, source = generate_compliance_report(evidence_context=ctx)
    assert source == "LocalFallback"
    assert "0.6776" in report
    assert "0.804" in report


def test_compliance_fallback_with_evidence_context_does_not_expose_secrets(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    from agents.compliance_agent import generate_compliance_report
    ctx = {
        "metrics": {"available": True, "roc_auc": 0.6776, "recall": 0.037,
                    "accuracy": 0.804, "precision": 0.35, "f1_score": 0.067,
                    "dataset_rows": 5000, "feature_count": 12,
                    "class_balance": {"0": 0.8098, "1": 0.1902},
                    "class_imbalance_present": True, "low_recall_flag": True,
                    "roc_auc_preferred_metric": True},
        "drift": {"available": False},
        "governance": {"available": False},
        "benchmark": {"available": False},
        "risk_flags": [],
        "limitations": [],
        "claim_safety_note": "Advisory only.",
        "advisory_only": True,
        "not_regulatory_approval": True,
    }
    report, _ = generate_compliance_report(evidence_context=ctx)
    assert "GROQ_API_KEY" not in report
    assert "sk-" not in report


# ---------------------------------------------------------------------------
# Drift Monitor Agent
# ---------------------------------------------------------------------------

def test_detect_drift_returns_expected_keys(tmp_path):
    from agents.drift_monitor_agent import detect_drift
    report = detect_drift(
        reference_path=RAW_SAMPLE_PATH,
        incoming_path=DRIFT_INCOMING_PATH,
        save_path=tmp_path / "drift_report.json",
    )
    assert "drift_detected" in report
    assert "details" in report


def test_detect_drift_details_is_a_list(tmp_path):
    from agents.drift_monitor_agent import detect_drift
    report = detect_drift(
        reference_path=RAW_SAMPLE_PATH,
        incoming_path=DRIFT_INCOMING_PATH,
        save_path=tmp_path / "drift_report.json",
    )
    assert isinstance(report["details"], list)


def test_detect_drift_each_detail_has_required_fields(tmp_path):
    from agents.drift_monitor_agent import detect_drift
    report = detect_drift(
        reference_path=RAW_SAMPLE_PATH,
        incoming_path=DRIFT_INCOMING_PATH,
        save_path=tmp_path / "drift_report.json",
    )
    for item in report["details"]:
        assert "feature" in item
        assert "p_value" in item
        assert "drifted" in item


def test_detect_drift_saves_json_file(tmp_path):
    from agents.drift_monitor_agent import detect_drift
    save_path = tmp_path / "drift_report.json"
    detect_drift(
        reference_path=RAW_SAMPLE_PATH,
        incoming_path=DRIFT_INCOMING_PATH,
        save_path=save_path,
    )
    assert save_path.exists()
    with open(save_path) as f:
        data = json.load(f)
    assert "drift_detected" in data


def test_detect_drift_detects_known_drift(tmp_path):
    # The drifted CSV was simulated to have drift in annual_inc and loan_amnt
    from agents.drift_monitor_agent import detect_drift
    report = detect_drift(
        reference_path=RAW_SAMPLE_PATH,
        incoming_path=DRIFT_INCOMING_PATH,
        save_path=tmp_path / "drift_report.json",
    )
    assert report["drift_detected"] is True, "Known-drifted dataset should trigger drift_detected=True"


# ---------------------------------------------------------------------------
# Feedback Memory Agent
# ---------------------------------------------------------------------------

def test_model_memory_add_and_retrieve(tmp_path):
    from agents.feedback_memory_agent import ModelMemory
    dim = 8
    memory = ModelMemory(dim)
    memory.memory_path = tmp_path
    vec = np.random.rand(dim).astype("float32")
    memory.add_model(vec, "test_model", {"tag": "unit_test"})
    results = memory.find_similar(vec, k=1)
    assert len(results) == 1
    assert results[0]["model_name"] == "test_model"
    assert "similarity" in results[0]


def test_model_memory_similarity_is_bounded(tmp_path):
    from agents.feedback_memory_agent import ModelMemory
    dim = 8
    memory = ModelMemory(dim)
    memory.memory_path = tmp_path
    vec = np.random.rand(dim).astype("float32")
    memory.add_model(vec, "test_model", {})
    results = memory.find_similar(vec, k=1)
    assert 0.0 <= results[0]["similarity"] <= 1.01  # cosine similarity, small float tolerance


def test_model_memory_save_and_load(tmp_path):
    from agents.feedback_memory_agent import ModelMemory
    dim = 6
    memory = ModelMemory(dim)
    memory.memory_path = tmp_path
    vec = np.random.rand(dim).astype("float32")
    memory.add_model(vec, "saved_model", {})
    memory.save()
    loaded = ModelMemory.load(dim)
    loaded.memory_path = tmp_path
    # Reload explicitly
    import faiss
    loaded.index = faiss.read_index(str(tmp_path / "model_memory.index"))
    import json as _json
    with open(tmp_path / "model_memory.json") as f:
        loaded.metadata = _json.load(f)
    assert len(loaded.metadata) == 1
    assert loaded.metadata[0]["model_name"] == "saved_model"


def test_run_feedback_memory_agent_returns_list(trained_model_and_test, tmp_path, monkeypatch):
    from agents import feedback_memory_agent as fma
    monkeypatch.setattr(fma, "MEMORY_INDEX_DIR", tmp_path)
    from agents.feedback_memory_agent import run_feedback_memory_agent
    _, X_test, _ = trained_model_and_test
    # Build minimal shap_data dict
    dim = X_test.shape[1]
    shap_data = {
        "mean_vector": list(np.random.rand(dim).astype("float32")),
        "feature_names": list(X_test.columns),
        "norm_factor": 1.0,
    }
    result = run_feedback_memory_agent(shap_data, model_name="unit_test_model")
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Report Writer Agent
# ---------------------------------------------------------------------------

def test_write_report_creates_file(tmp_path):
    from agents.report_writer_agent import write_report
    validation = {"missing_values": 0, "duplicate_rows": 0}
    performance = {
        "accuracy": 0.80, "precision": 0.35, "recall": 0.04,
        "f1_score": 0.07, "roc_auc": 0.68, "confusion_matrix": [[800, 0], [195, 5]],
    }
    out = write_report(validation, performance, report_path=tmp_path / "test_report.md")
    assert Path(out).exists()


def test_write_report_output_is_non_empty(tmp_path):
    from agents.report_writer_agent import write_report
    validation = {"missing_values": 0, "duplicate_rows": 0}
    performance = {
        "accuracy": 0.80, "precision": 0.35, "recall": 0.04,
        "f1_score": 0.07, "roc_auc": 0.68, "confusion_matrix": [[800, 0], [195, 5]],
    }
    out = write_report(validation, performance, report_path=tmp_path / "test_report.md")
    assert Path(out).stat().st_size > 0


def test_write_report_contains_agentx_header(tmp_path):
    from agents.report_writer_agent import write_report
    validation = {"missing_values": 0, "duplicate_rows": 0}
    performance = {
        "accuracy": 0.80, "precision": 0.35, "recall": 0.04,
        "f1_score": 0.07, "roc_auc": 0.68, "confusion_matrix": [[800, 0], [195, 5]],
    }
    out = write_report(validation, performance, report_path=tmp_path / "test_report.md")
    content = Path(out).read_text(encoding="utf-8")
    assert "AgentX" in content
