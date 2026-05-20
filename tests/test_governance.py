"""
Tests for utils/governance.py -- local governance evidence layer.

All write tests use tmp_path and monkeypatch to avoid polluting
data/governance/ during unit test runs.
"""

import json

import pytest

from utils.governance import (
    GOVERNANCE_CLAIM_SAFETY,
    collect_artifact_status,
    create_validation_run_record,
    generate_validation_run_id,
    list_validation_runs,
    load_benchmark_summary,
    load_compliance_status,
    load_drift_status,
    load_latest_validation_run,
    load_metrics_snapshot,
    write_validation_run_record,
)


# ---------------------------------------------------------------------------
# generate_validation_run_id
# ---------------------------------------------------------------------------

def test_run_id_starts_with_vrun():
    assert generate_validation_run_id().startswith("vrun_")


def test_run_id_has_four_parts():
    parts = generate_validation_run_id().split("_")
    assert len(parts) == 4


def test_run_id_date_segment_is_eight_digits():
    parts = generate_validation_run_id().split("_")
    assert parts[1].isdigit() and len(parts[1]) == 8


def test_run_id_time_segment_is_six_digits():
    parts = generate_validation_run_id().split("_")
    assert parts[2].isdigit() and len(parts[2]) == 6


def test_run_id_uid_segment_is_eight_hex_chars():
    parts = generate_validation_run_id().split("_")
    uid = parts[3]
    assert len(uid) == 8
    int(uid, 16)  # raises if not valid hex


def test_run_ids_are_unique():
    ids = {generate_validation_run_id() for _ in range(5)}
    assert len(ids) == 5


# ---------------------------------------------------------------------------
# load_metrics_snapshot
# ---------------------------------------------------------------------------

def test_load_metrics_snapshot_returns_dict():
    result = load_metrics_snapshot()
    assert isinstance(result, dict)


def test_load_metrics_snapshot_has_available_key():
    result = load_metrics_snapshot()
    assert "available" in result


def test_load_metrics_snapshot_roc_auc_if_available():
    result = load_metrics_snapshot()
    if result.get("available"):
        assert result.get("roc_auc") == 0.6776


# ---------------------------------------------------------------------------
# load_drift_status
# ---------------------------------------------------------------------------

def test_load_drift_status_returns_dict():
    result = load_drift_status()
    assert isinstance(result, dict)


def test_load_drift_status_has_available_key():
    result = load_drift_status()
    assert "available" in result


def test_load_drift_status_drifted_features_is_list_if_available():
    result = load_drift_status()
    if result.get("available"):
        assert isinstance(result.get("drifted_features"), list)


# ---------------------------------------------------------------------------
# load_compliance_status
# ---------------------------------------------------------------------------

def test_load_compliance_status_returns_dict():
    result = load_compliance_status()
    assert isinstance(result, dict)


def test_load_compliance_status_has_available_key():
    result = load_compliance_status()
    assert "available" in result


def test_load_compliance_status_has_status_key():
    result = load_compliance_status()
    assert "status" in result


def test_load_compliance_status_note_if_available():
    result = load_compliance_status()
    if result.get("available"):
        note = result.get("note", "").lower()
        assert "advisory" in note


# ---------------------------------------------------------------------------
# load_benchmark_summary
# ---------------------------------------------------------------------------

def test_load_benchmark_summary_returns_dict():
    result = load_benchmark_summary()
    assert isinstance(result, dict)


def test_load_benchmark_summary_has_available_key():
    result = load_benchmark_summary()
    assert "available" in result


def test_load_benchmark_summary_has_disclaimer_if_available():
    result = load_benchmark_summary()
    if result.get("available"):
        disc = result.get("disclaimer", "").lower()
        assert "local development machine" in disc


# ---------------------------------------------------------------------------
# collect_artifact_status
# ---------------------------------------------------------------------------

def test_collect_artifact_status_returns_list():
    result = collect_artifact_status()
    assert isinstance(result, list)


def test_collect_artifact_status_items_have_required_keys():
    result = collect_artifact_status()
    for item in result:
        assert "path" in item
        assert "exists" in item
        assert "size_bytes" in item


def test_collect_artifact_status_exists_is_bool():
    result = collect_artifact_status()
    for item in result:
        assert isinstance(item["exists"], bool)


# ---------------------------------------------------------------------------
# create_validation_run_record
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "validation_run_id",
    "created_at_utc",
    "system_name",
    "system_version",
    "run_type",
    "model",
    "dataset",
    "metrics_snapshot",
    "drift_status",
    "compliance_status",
    "artifact_status",
    "benchmark_summary",
    "reviewer_status",
    "reviewer_notes",
    "risk_flags",
    "claim_safety_note",
    "limitations",
    "source_files",
]


def test_create_record_has_all_required_fields():
    record = create_validation_run_record()
    for field in REQUIRED_FIELDS:
        assert field in record, f"Missing field: {field}"


def test_create_record_run_id_starts_with_vrun():
    record = create_validation_run_record()
    assert record["validation_run_id"].startswith("vrun_")


def test_create_record_custom_run_id():
    record = create_validation_run_record(run_id="vrun_test_id")
    assert record["validation_run_id"] == "vrun_test_id"


def test_create_record_reviewer_status_is_pending():
    record = create_validation_run_record()
    assert record["reviewer_status"] == "pending_review"


def test_create_record_reviewer_notes_is_none():
    record = create_validation_run_record()
    assert record["reviewer_notes"] is None


def test_create_record_claim_safety_note_is_safe():
    record = create_validation_run_record()
    note = record["claim_safety_note"].lower()
    assert "local" in note
    assert "not a production" in note


def test_create_record_risk_flags_is_list():
    record = create_validation_run_record()
    assert isinstance(record["risk_flags"], list)


def test_create_record_limitations_is_non_empty_list():
    record = create_validation_run_record()
    lims = record["limitations"]
    assert isinstance(lims, list)
    assert len(lims) > 0


def test_create_record_artifact_status_is_list():
    record = create_validation_run_record()
    assert isinstance(record["artifact_status"], list)


def test_create_record_does_not_expose_secrets():
    record = create_validation_run_record()
    text = json.dumps(record)
    assert "GROQ_API_KEY" not in text
    assert "sk-" not in text


def test_create_record_system_name_is_agentx():
    record = create_validation_run_record()
    assert "AgentX" in record["system_name"]


def test_create_record_dataset_has_name():
    record = create_validation_run_record()
    assert record["dataset"].get("name")


# ---------------------------------------------------------------------------
# write_validation_run_record and load_latest_validation_run
# ---------------------------------------------------------------------------

def test_write_creates_run_file(tmp_path, monkeypatch):
    import utils.governance as gov
    runs_dir = tmp_path / "runs"
    latest_path = tmp_path / "latest.json"
    monkeypatch.setattr(gov, "GOVERNANCE_RUNS_DIR", runs_dir)
    monkeypatch.setattr(gov, "GOVERNANCE_LATEST_PATH", latest_path)

    record = create_validation_run_record(run_id="vrun_test_write")
    paths = gov.write_validation_run_record(record)

    assert (runs_dir / "vrun_test_write.json").exists()
    assert latest_path.exists()
    assert "run_path" in paths
    assert "latest_path" in paths


def test_write_latest_is_readable(tmp_path, monkeypatch):
    import utils.governance as gov
    runs_dir = tmp_path / "runs"
    latest_path = tmp_path / "latest.json"
    monkeypatch.setattr(gov, "GOVERNANCE_RUNS_DIR", runs_dir)
    monkeypatch.setattr(gov, "GOVERNANCE_LATEST_PATH", latest_path)

    record = create_validation_run_record(run_id="vrun_readback")
    gov.write_validation_run_record(record)

    monkeypatch.setattr(gov, "GOVERNANCE_LATEST_PATH", latest_path)
    loaded = gov.load_latest_validation_run()
    assert loaded is not None
    assert loaded["validation_run_id"] == "vrun_readback"


def test_load_latest_returns_none_if_missing(tmp_path, monkeypatch):
    import utils.governance as gov
    monkeypatch.setattr(gov, "GOVERNANCE_LATEST_PATH", tmp_path / "nonexistent.json")
    result = gov.load_latest_validation_run()
    assert result is None


# ---------------------------------------------------------------------------
# list_validation_runs
# ---------------------------------------------------------------------------

def test_list_validation_runs_empty_when_no_dir(tmp_path, monkeypatch):
    import utils.governance as gov
    monkeypatch.setattr(gov, "GOVERNANCE_RUNS_DIR", tmp_path / "nonexistent_runs")
    result = gov.list_validation_runs()
    assert result == []


def test_list_validation_runs_returns_summaries(tmp_path, monkeypatch):
    import utils.governance as gov
    runs_dir = tmp_path / "runs"
    latest_path = tmp_path / "latest.json"
    monkeypatch.setattr(gov, "GOVERNANCE_RUNS_DIR", runs_dir)
    monkeypatch.setattr(gov, "GOVERNANCE_LATEST_PATH", latest_path)

    for i in range(3):
        record = create_validation_run_record(run_id=f"vrun_list_{i:02d}")
        gov.write_validation_run_record(record)

    result = gov.list_validation_runs(limit=10)
    assert len(result) == 3
    for item in result:
        assert "validation_run_id" in item
        assert "created_at_utc" in item
        assert "reviewer_status" in item


def test_list_validation_runs_respects_limit(tmp_path, monkeypatch):
    import utils.governance as gov
    runs_dir = tmp_path / "runs"
    latest_path = tmp_path / "latest.json"
    monkeypatch.setattr(gov, "GOVERNANCE_RUNS_DIR", runs_dir)
    monkeypatch.setattr(gov, "GOVERNANCE_LATEST_PATH", latest_path)

    for i in range(5):
        record = create_validation_run_record(run_id=f"vrun_lim_{i:02d}")
        gov.write_validation_run_record(record)

    result = gov.list_validation_runs(limit=2)
    assert len(result) <= 2


# ---------------------------------------------------------------------------
# GOVERNANCE_CLAIM_SAFETY constant
# ---------------------------------------------------------------------------

def test_governance_claim_safety_constant_is_safe():
    note = GOVERNANCE_CLAIM_SAFETY.lower()
    assert "local" in note
    assert "not a production" in note
