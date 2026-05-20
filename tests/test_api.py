"""
Tests for the AgentX FastAPI service boundary (api/main.py).

Fast tests (GET /health, /metrics, /evidence) use a TestClient and complete
in under a second each -- no pipeline execution required.

The POST /validate test runs the full pipeline and is marked @pytest.mark.slow.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

VERIFIED_ROC_AUC = 0.6776


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_status_is_ok():
    response = client.get("/health")
    assert response.json()["status"] == "ok"


def test_health_returns_system_name():
    response = client.get("/health")
    data = response.json()
    assert "system" in data
    assert "AgentX" in data["system"]


def test_health_returns_version():
    response = client.get("/health")
    data = response.json()
    assert "version" in data
    assert len(data["version"]) > 0


def test_health_metrics_available_is_bool():
    response = client.get("/health")
    assert isinstance(response.json()["metrics_available"], bool)


def test_health_evidence_available_is_bool():
    response = client.get("/health")
    assert isinstance(response.json()["evidence_available"], bool)


def test_health_does_not_expose_secrets():
    response = client.get("/health")
    text = response.text
    assert "GROQ_API_KEY" not in text
    assert "sk-" not in text


# ---------------------------------------------------------------------------
# GET /metrics
# ---------------------------------------------------------------------------

def test_metrics_returns_200():
    response = client.get("/metrics")
    # 200 if metrics file exists, 503 if not yet generated (both are correct)
    assert response.status_code in (200, 503)


def test_metrics_returns_verified_roc_auc():
    response = client.get("/metrics")
    if response.status_code == 503:
        pytest.skip("verified_metrics.json not yet generated -- run main.py first")
    data = response.json()
    assert "roc_auc" in data
    assert data["roc_auc"] == VERIFIED_ROC_AUC, (
        f"ROC-AUC changed from {VERIFIED_ROC_AUC}: got {data['roc_auc']}"
    )


def test_metrics_returns_all_required_fields():
    response = client.get("/metrics")
    if response.status_code == 503:
        pytest.skip("verified_metrics.json not yet generated -- run main.py first")
    data = response.json()
    for field in ("roc_auc", "accuracy", "precision", "recall", "f1_score",
                  "dataset_rows", "feature_count", "model_type", "evidence_source"):
        assert field in data, f"Missing field in /metrics response: {field}"


def test_metrics_roc_auc_is_float():
    response = client.get("/metrics")
    if response.status_code == 503:
        pytest.skip("verified_metrics.json not yet generated -- run main.py first")
    assert isinstance(response.json()["roc_auc"], float)


def test_metrics_dataset_rows_is_5000():
    response = client.get("/metrics")
    if response.status_code == 503:
        pytest.skip("verified_metrics.json not yet generated -- run main.py first")
    assert response.json()["dataset_rows"] == 5000


def test_metrics_does_not_expose_secrets():
    response = client.get("/metrics")
    text = response.text
    assert "GROQ_API_KEY" not in text
    assert "sk-" not in text


# ---------------------------------------------------------------------------
# GET /evidence
# ---------------------------------------------------------------------------

def test_evidence_returns_200():
    response = client.get("/evidence")
    assert response.status_code == 200


def test_evidence_returns_evidence_files_list():
    response = client.get("/evidence")
    data = response.json()
    assert "evidence_files" in data
    assert isinstance(data["evidence_files"], list)


def test_evidence_files_list_is_non_empty():
    response = client.get("/evidence")
    data = response.json()
    # Should have at least the verified_metrics files
    assert len(data["evidence_files"]) > 0


def test_evidence_returns_generated_artifacts():
    response = client.get("/evidence")
    data = response.json()
    assert "generated_artifacts" in data
    assert isinstance(data["generated_artifacts"], list)


def test_evidence_claim_safety_note_is_present():
    response = client.get("/evidence")
    data = response.json()
    assert "claim_safety_note" in data
    assert len(data["claim_safety_note"]) > 0


def test_evidence_claim_safety_note_is_not_unsafe():
    response = client.get("/evidence")
    note = response.json()["claim_safety_note"].lower()
    assert "not a production" in note or "not production" in note


def test_evidence_does_not_expose_secrets():
    response = client.get("/evidence")
    text = response.text
    assert "GROQ_API_KEY" not in text
    assert "sk-" not in text


# ---------------------------------------------------------------------------
# POST /validate (slow -- runs full pipeline)
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_validate_returns_200():
    response = client.post(
        "/validate",
        json={"run_compliance_agent": False, "run_drift_monitor": True, "regenerate_reports": True},
        timeout=300,
    )
    assert response.status_code == 200


@pytest.mark.slow
def test_validate_returns_complete_status():
    response = client.post(
        "/validate",
        json={"run_compliance_agent": False, "run_drift_monitor": True, "regenerate_reports": True},
        timeout=300,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"


@pytest.mark.slow
def test_validate_returns_metrics():
    response = client.post(
        "/validate",
        json={"run_compliance_agent": False, "run_drift_monitor": False, "regenerate_reports": False},
        timeout=300,
    )
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "roc_auc" in data["metrics"]
    assert data["metrics"]["roc_auc"] == VERIFIED_ROC_AUC


@pytest.mark.slow
def test_validate_returns_artifacts_list():
    response = client.post(
        "/validate",
        json={"run_compliance_agent": False, "run_drift_monitor": False, "regenerate_reports": False},
        timeout=300,
    )
    assert response.status_code == 200
    data = response.json()
    assert "artifacts" in data
    assert isinstance(data["artifacts"], list)
    assert len(data["artifacts"]) > 0


@pytest.mark.slow
def test_validate_does_not_expose_secrets():
    response = client.post(
        "/validate",
        json={"run_compliance_agent": False, "run_drift_monitor": False, "regenerate_reports": False},
        timeout=300,
    )
    text = response.text
    assert "GROQ_API_KEY" not in text
    assert "sk-" not in text


@pytest.mark.slow
def test_validate_evidence_note_is_claim_safe():
    response = client.post(
        "/validate",
        json={"run_compliance_agent": False, "run_drift_monitor": False, "regenerate_reports": False},
        timeout=300,
    )
    assert response.status_code == 200
    note = response.json()["evidence_note"].lower()
    assert "not a production" in note or "not production" in note


# ---------------------------------------------------------------------------
# GET /evidence (governance_available field)
# ---------------------------------------------------------------------------

def test_evidence_has_governance_available_field():
    response = client.get("/evidence")
    data = response.json()
    assert "governance_available" in data


def test_evidence_governance_available_is_bool():
    response = client.get("/evidence")
    assert isinstance(response.json()["governance_available"], bool)


# ---------------------------------------------------------------------------
# GET /governance/latest
# ---------------------------------------------------------------------------

def test_governance_latest_returns_valid_status():
    response = client.get("/governance/latest")
    # 200 if governance record exists, 503 if not yet generated (both correct)
    assert response.status_code in (200, 503)


def test_governance_latest_200_has_required_fields():
    response = client.get("/governance/latest")
    if response.status_code == 503:
        pytest.skip("No governance record yet -- run python main.py first")
    data = response.json()
    assert data["available"] is True
    assert "validation_run_id" in data
    assert "created_at_utc" in data
    assert "roc_auc" in data
    assert "reviewer_status" in data
    assert "claim_safety_note" in data


def test_governance_latest_roc_auc_matches_verified():
    response = client.get("/governance/latest")
    if response.status_code == 503:
        pytest.skip("No governance record yet")
    data = response.json()
    assert data["roc_auc"] == VERIFIED_ROC_AUC


def test_governance_latest_reviewer_status_is_pending():
    response = client.get("/governance/latest")
    if response.status_code == 503:
        pytest.skip("No governance record yet")
    assert response.json()["reviewer_status"] == "pending_review"


def test_governance_latest_claim_safety_note_is_safe():
    response = client.get("/governance/latest")
    if response.status_code == 503:
        pytest.skip("No governance record yet")
    note = response.json()["claim_safety_note"].lower()
    assert "local" in note
    assert "not a production" in note


def test_governance_latest_does_not_expose_secrets():
    response = client.get("/governance/latest")
    text = response.text
    assert "GROQ_API_KEY" not in text
    assert "sk-" not in text


# ---------------------------------------------------------------------------
# GET /governance/history
# ---------------------------------------------------------------------------

def test_governance_history_returns_200():
    response = client.get("/governance/history")
    assert response.status_code == 200


def test_governance_history_has_required_fields():
    response = client.get("/governance/history")
    data = response.json()
    assert "available" in data
    assert "count" in data
    assert "runs" in data
    assert "claim_safety_note" in data


def test_governance_history_count_matches_runs_length():
    response = client.get("/governance/history")
    data = response.json()
    assert data["count"] == len(data["runs"])


def test_governance_history_runs_is_list():
    response = client.get("/governance/history")
    assert isinstance(response.json()["runs"], list)


def test_governance_history_claim_safety_note_is_safe():
    response = client.get("/governance/history")
    note = response.json()["claim_safety_note"].lower()
    assert "local" in note
    assert "not a production" in note


def test_governance_history_does_not_expose_secrets():
    response = client.get("/governance/history")
    text = response.text
    assert "GROQ_API_KEY" not in text
    assert "sk-" not in text
