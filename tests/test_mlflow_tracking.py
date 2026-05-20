"""
Tests for utils/mlflow_tracking.py -- local MLflow validation tracking.

All tests that write MLflow data use tmp_path to avoid polluting the real
mlruns/ directory. No live Groq API calls are made.
"""

import json

import mlflow
import pytest


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

def test_mlflow_tracking_module_imports():
    from utils.mlflow_tracking import (
        configure_mlflow,
        log_agentx_artifacts,
        log_benchmark_results,
        log_compliance_output,
        log_governance_record,
        log_model_metrics,
        log_validation_params,
        mlflow_tracking_available,
        run_mlflow_tracking_summary,
    )


def test_mlflow_experiment_name_non_empty():
    from utils.mlflow_tracking import MLFLOW_EXPERIMENT_NAME
    assert isinstance(MLFLOW_EXPERIMENT_NAME, str)
    assert len(MLFLOW_EXPERIMENT_NAME) > 0


def test_mlflow_experiment_name_value():
    from utils.mlflow_tracking import MLFLOW_EXPERIMENT_NAME
    assert MLFLOW_EXPERIMENT_NAME == "agentx_risk_validation"


# ---------------------------------------------------------------------------
# _is_safe_artifact_path
# ---------------------------------------------------------------------------

def test_is_safe_artifact_path_allows_json():
    from utils.mlflow_tracking import _is_safe_artifact_path
    from pathlib import Path
    assert _is_safe_artifact_path(Path("verified_metrics.json")) is True


def test_is_safe_artifact_path_allows_png():
    from utils.mlflow_tracking import _is_safe_artifact_path
    from pathlib import Path
    assert _is_safe_artifact_path(Path("shap_summary.png")) is True


def test_is_safe_artifact_path_blocks_env():
    from utils.mlflow_tracking import _is_safe_artifact_path
    from pathlib import Path
    assert _is_safe_artifact_path(Path(".env")) is False


def test_is_safe_artifact_path_blocks_credentials():
    from utils.mlflow_tracking import _is_safe_artifact_path
    from pathlib import Path
    assert _is_safe_artifact_path(Path("credentials.json")) is False


# ---------------------------------------------------------------------------
# configure_mlflow
# ---------------------------------------------------------------------------

def test_configure_mlflow_sets_tracking_uri(tmp_path, monkeypatch):
    mlruns = tmp_path / "mlruns"
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", mlruns)
    from utils.mlflow_tracking import configure_mlflow
    configure_mlflow()
    uri = mlflow.get_tracking_uri()
    # URI is file:///path/to/mlruns on all platforms
    assert "mlruns" in uri or str(mlruns).replace("\\", "/") in uri


def test_configure_mlflow_creates_directory(tmp_path, monkeypatch):
    mlruns = tmp_path / "mlruns_new"
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", mlruns)
    from utils.mlflow_tracking import configure_mlflow
    configure_mlflow()
    assert mlruns.exists()


def test_configure_mlflow_idempotent(tmp_path, monkeypatch):
    mlruns = tmp_path / "mlruns"
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", mlruns)
    from utils.mlflow_tracking import configure_mlflow
    configure_mlflow()
    configure_mlflow()  # second call must not raise


# ---------------------------------------------------------------------------
# log_model_metrics
# ---------------------------------------------------------------------------

def test_log_model_metrics_does_not_raise(tmp_path, monkeypatch):
    mlruns = tmp_path / "mlruns"
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", mlruns)
    from utils.mlflow_tracking import configure_mlflow, log_model_metrics
    configure_mlflow()
    metrics = {
        "roc_auc": 0.6776,
        "accuracy": 0.804,
        "precision": 0.35,
        "recall": 0.037,
        "f1_score": 0.067,
    }
    with mlflow.start_run():
        log_model_metrics(metrics)


def test_log_model_metrics_empty_dict_does_not_crash(tmp_path, monkeypatch):
    mlruns = tmp_path / "mlruns"
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", mlruns)
    from utils.mlflow_tracking import configure_mlflow, log_model_metrics
    configure_mlflow()
    with mlflow.start_run():
        log_model_metrics({})


# ---------------------------------------------------------------------------
# log_validation_params
# ---------------------------------------------------------------------------

def test_log_validation_params_does_not_raise(tmp_path, monkeypatch):
    mlruns = tmp_path / "mlruns"
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", mlruns)
    from utils.mlflow_tracking import configure_mlflow, log_validation_params
    configure_mlflow()
    ctx = {
        "dataset_rows": 5000,
        "feature_count": 12,
        "model_type": "Pipeline(StandardScaler + LogisticRegression)",
        "target": "loan_status",
        "validation_run_id": "vrun_test_123",
    }
    with mlflow.start_run():
        log_validation_params(ctx)


def test_log_validation_params_empty_dict_does_not_crash(tmp_path, monkeypatch):
    mlruns = tmp_path / "mlruns"
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", mlruns)
    from utils.mlflow_tracking import configure_mlflow, log_validation_params
    configure_mlflow()
    with mlflow.start_run():
        log_validation_params({})


# ---------------------------------------------------------------------------
# log_agentx_artifacts
# ---------------------------------------------------------------------------

def test_log_agentx_artifacts_missing_file_returns_false(tmp_path, monkeypatch):
    mlruns = tmp_path / "mlruns"
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", mlruns)
    from utils.mlflow_tracking import configure_mlflow, log_agentx_artifacts
    configure_mlflow()
    with mlflow.start_run():
        result = log_agentx_artifacts({"missing": tmp_path / "does_not_exist.json"})
    assert result["missing"] is False


def test_log_agentx_artifacts_present_file_returns_true(tmp_path, monkeypatch):
    mlruns = tmp_path / "mlruns"
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", mlruns)
    from utils.mlflow_tracking import configure_mlflow, log_agentx_artifacts
    configure_mlflow()
    artifact = tmp_path / "test_metrics.json"
    artifact.write_text('{"roc_auc": 0.6776}', encoding="utf-8")
    with mlflow.start_run():
        result = log_agentx_artifacts({"test_metrics": artifact})
    assert result["test_metrics"] is True


def test_log_agentx_artifacts_list_form_does_not_crash(tmp_path, monkeypatch):
    mlruns = tmp_path / "mlruns"
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", mlruns)
    from utils.mlflow_tracking import configure_mlflow, log_agentx_artifacts
    configure_mlflow()
    with mlflow.start_run():
        result = log_agentx_artifacts([tmp_path / "no_file_1.json", tmp_path / "no_file_2.json"])
    assert all(v is False for v in result.values())


# ---------------------------------------------------------------------------
# run_mlflow_tracking_summary
# ---------------------------------------------------------------------------

SAMPLE_METRICS = {
    "roc_auc": 0.6776,
    "accuracy": 0.804,
    "precision": 0.35,
    "recall": 0.037,
    "f1_score": 0.067,
}


def _patch_all_paths(monkeypatch, tmp_path):
    mlruns = tmp_path / "mlruns"
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", mlruns)
    monkeypatch.setattr("utils.mlflow_tracking.VERIFIED_METRICS_JSON_PATH", tmp_path / "no_metrics.json")
    monkeypatch.setattr("utils.mlflow_tracking.GOVERNANCE_LATEST_PATH", tmp_path / "no_gov.json")
    monkeypatch.setattr("utils.mlflow_tracking.SHAP_SUMMARY_PATH", tmp_path / "no_shap.png")
    monkeypatch.setattr("utils.mlflow_tracking.COMPLIANCE_REPORT_PATH", tmp_path / "no_comp.json")
    monkeypatch.setattr("utils.mlflow_tracking.DRIFT_REPORT_PATH", tmp_path / "no_drift.json")
    monkeypatch.setattr("utils.mlflow_tracking.EVIDENCE_DIR", tmp_path)
    return mlruns


def test_run_mlflow_tracking_summary_returns_ok(tmp_path, monkeypatch):
    mlruns = _patch_all_paths(monkeypatch, tmp_path)
    from utils.mlflow_tracking import run_mlflow_tracking_summary
    result = run_mlflow_tracking_summary(
        performance_report=SAMPLE_METRICS,
        governance_run_id="vrun_test_abc",
    )
    assert result.get("status") == "ok"
    assert result.get("run_id") is not None
    assert result.get("metrics_logged") is True


def test_run_mlflow_tracking_summary_creates_mlruns(tmp_path, monkeypatch):
    mlruns = _patch_all_paths(monkeypatch, tmp_path)
    from utils.mlflow_tracking import run_mlflow_tracking_summary
    run_mlflow_tracking_summary(performance_report=SAMPLE_METRICS)
    assert mlruns.exists()


def test_run_mlflow_tracking_summary_no_perf_report(tmp_path, monkeypatch):
    _patch_all_paths(monkeypatch, tmp_path)
    from utils.mlflow_tracking import run_mlflow_tracking_summary
    result = run_mlflow_tracking_summary()
    assert result.get("status") == "ok"
    assert result.get("metrics_logged") is False


def test_run_mlflow_tracking_summary_no_secrets_in_result(tmp_path, monkeypatch):
    _patch_all_paths(monkeypatch, tmp_path)
    from utils.mlflow_tracking import run_mlflow_tracking_summary
    result = run_mlflow_tracking_summary(performance_report=SAMPLE_METRICS)
    result_str = json.dumps(result)
    assert "GROQ_API_KEY" not in result_str
    assert ".env" not in result_str


def test_run_mlflow_tracking_summary_missing_artifacts_not_false_positive(tmp_path, monkeypatch):
    _patch_all_paths(monkeypatch, tmp_path)
    from utils.mlflow_tracking import run_mlflow_tracking_summary
    result = run_mlflow_tracking_summary(performance_report=SAMPLE_METRICS)
    artifacts = result.get("artifacts_logged", {})
    # All artifact results should be bool (True or False), never an exception
    for key, val in artifacts.items():
        assert isinstance(val, bool), f"{key} should be bool, got {type(val)}"


def test_run_mlflow_tracking_summary_with_real_artifact(tmp_path, monkeypatch):
    mlruns = _patch_all_paths(monkeypatch, tmp_path)
    # Create a real evidence file
    metrics_file = tmp_path / "verified_metrics.json"
    metrics_file.write_text(json.dumps({"roc_auc": 0.6776, "total_rows": 5000}), encoding="utf-8")
    monkeypatch.setattr("utils.mlflow_tracking.VERIFIED_METRICS_JSON_PATH", metrics_file)
    monkeypatch.setattr("utils.mlflow_tracking.EVIDENCE_DIR", tmp_path)

    from utils.mlflow_tracking import run_mlflow_tracking_summary
    result = run_mlflow_tracking_summary(performance_report=SAMPLE_METRICS)
    assert result.get("status") == "ok"
    assert result["artifacts_logged"].get("verified_metrics_json") is True


# ---------------------------------------------------------------------------
# mlflow_tracking_available
# ---------------------------------------------------------------------------

def test_mlflow_tracking_available_false_when_no_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", tmp_path / "no_mlruns")
    from utils.mlflow_tracking import mlflow_tracking_available
    assert mlflow_tracking_available() is False


def test_mlflow_tracking_available_true_after_run(tmp_path, monkeypatch):
    mlruns = _patch_all_paths(monkeypatch, tmp_path)
    from utils.mlflow_tracking import run_mlflow_tracking_summary, mlflow_tracking_available
    run_mlflow_tracking_summary(performance_report=SAMPLE_METRICS)
    monkeypatch.setattr("utils.mlflow_tracking.MLFLOW_TRACKING_DIR", mlruns)
    assert mlflow_tracking_available() is True