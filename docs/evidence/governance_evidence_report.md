# AgentX Governance Evidence Report

**System:** AgentX Risk Validator v1.0.0
**Report type:** Local governance evidence layer documentation
**Date:** 2026-05-20
**Status:** Active -- governance records written on each pipeline run

---

## Purpose

This document describes the local governance evidence layer added in Phase 5B.6B of
the AgentX Risk Validator project. The layer writes a structured JSON record each
time the validation pipeline runs, providing audit-style traceability of model
validation runs during local development and portfolio demonstration.

This is NOT enterprise governance tooling, a regulatory audit system, or an
MCP-compliant governance platform. It is a local-only, file-based traceability
layer for development and portfolio evidence purposes.

---

## What Is Recorded

Each pipeline run writes a validation-run record to:

- `data/governance/validation_runs/{run_id}.json` -- individual run record
- `data/governance/latest_validation_run.json` -- pointer to most recent run

Records are excluded from version control via `.gitignore` (`data/governance/`).

### Record Schema

| Field | Type | Description |
|---|---|---|
| `validation_run_id` | string | Unique ID: `vrun_YYYYMMDD_HHMMSS_xxxxxxxx` |
| `created_at_utc` | string | ISO 8601 UTC timestamp |
| `system_name` | string | "AgentX Risk Validator" |
| `system_version` | string | Semantic version string |
| `run_type` | string | "full_pipeline" |
| `model` | object | Model type, artifact path, artifact presence |
| `dataset` | object | Dataset name, row count, feature count, source |
| `metrics_snapshot` | object | ROC-AUC, accuracy, precision, recall, F1 |
| `drift_status` | object | Drift detected flag, drifted feature list |
| `compliance_status` | object | Compliance agent output summary |
| `artifact_status` | list | Existence and size of each output artifact |
| `benchmark_summary` | object | Benchmark timing summary if available |
| `reviewer_status` | string | Placeholder: "pending_review" |
| `reviewer_notes` | null | Reserved for future human reviewer annotation |
| `risk_flags` | list | Automatically populated (e.g., drift warnings) |
| `claim_safety_note` | string | Claim-safety disclaimer |
| `limitations` | list | Documented system limitations |
| `source_files` | list | Key source file paths |

---

## Verified Sample Record (2026-05-20)

The first governance record was generated on 2026-05-20 at 03:35 UTC.

```
validation_run_id: vrun_20260520_033532_ba10841b
created_at_utc:   2026-05-20T03:35:32.988690+00:00
run_type:         full_pipeline
roc_auc:          0.6776
reviewer_status:  pending_review
risk_flags:       ["Feature drift detected in: annual_inc, loan_amnt"]
drift_detected:   true
compliance_status: completed_advisory
artifacts present: 8 / 8
```

---

## API Endpoints

Two read-only FastAPI endpoints expose the governance records:

### GET /governance/latest

Returns the most recent validation-run record summary.

Returns 200 if a record exists; 503 if no pipeline run has been completed yet.

Sample response fields:
- `available` (bool)
- `validation_run_id` (string)
- `created_at_utc` (string)
- `roc_auc` (float)
- `drift_detected` (bool)
- `drifted_features` (list of strings)
- `compliance_status` (string)
- `reviewer_status` (string)
- `risk_flags` (list of strings)
- `artifacts_present` / `artifacts_total` (int)
- `claim_safety_note` (string)

### GET /governance/history

Returns a list of recent validation-run summaries (default limit: 10).

Always returns 200. Returns empty `runs` list if no records exist.

Sample response fields:
- `available` (bool)
- `count` (int)
- `runs` (list of run summaries)
- `claim_safety_note` (string)

---

## Implementation

| Component | File | Notes |
|---|---|---|
| Governance utilities | `utils/governance.py` | Run ID generation, record assembly, file I/O |
| Config paths | `utils/config.py` | GOVERNANCE_DIR, GOVERNANCE_RUNS_DIR, GOVERNANCE_LATEST_PATH |
| Pipeline integration | `main.py` | Step 12: writes record after verified_metrics |
| API schemas | `api/schemas.py` | GovernanceLatestResponse, GovernanceHistoryResponse |
| API service | `api/service.py` | load_latest_governance_record, list_governance_history |
| API routes | `api/main.py` | GET /governance/latest, GET /governance/history |

---

## Test Coverage

| Test file | Tests | Coverage area |
|---|---|---|
| `tests/test_governance.py` | ~60 tests | utils/governance.py -- all functions, monkeypatched I/O |
| `tests/test_api.py` | 15 new tests | /governance/latest, /governance/history, /evidence governance_available |

Total pytest suite after Phase 5B.6B: 173 fast tests, all passing.

Governance write/load tests use `tmp_path` and `monkeypatch.setattr` to redirect
file I/O to a temporary directory, avoiding pollution of `data/governance/` during
test runs.

---

## Risk Flags

The governance layer automatically populates `risk_flags` when drift is detected.
In the current verified run:

```
["Feature drift detected in: annual_inc, loan_amnt"]
```

This flag is informational. The current model is not used in production and these
flags have no operational consequences. They demonstrate the governance layer's
ability to surface model health signals.

---

## Claim Safety

This governance evidence layer is a local development tool. It does not constitute:

- Regulatory approval of any kind
- Production-grade model governance
- Enterprise MCP-compliant audit logging
- A substitute for human review

The `reviewer_status` field is set to `"pending_review"` on all records. No
automated approval is granted. All records carry a `claim_safety_note` field with
the full claim-safety disclaimer.

---

## Limitations

- Records are local-only and excluded from version control.
- No automated reviewer assignment or workflow.
- No record retention policy or archival mechanism.
- `reviewer_notes` field is reserved but not populated.
- Governance history is bounded only by local disk storage.
- Not integrated with any external governance platform.
- Docker container does not persist governance records across restarts (no volume mount).
