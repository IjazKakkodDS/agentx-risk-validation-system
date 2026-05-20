# AgentX Risk Validator -- Local MLflow Validation Tracking Report

**Phase:** 5B.8
**Date:** 2026-05-20
**Status:** COMPLETE -- local MLflow tracking wired into main.py pipeline

---

## Summary

Local MLflow file-based tracking has been added to the AgentX validation pipeline.
Each pipeline run now logs model metrics, validation parameters, and evidence
artifacts to a local MLflow file store under `mlruns/`. This is local development
tracking only. No remote server, no model registry, no production MLflow deployment.

---

## MLflow Configuration

| Setting | Value |
|---|---|
| Tracking backend | Local file store (`mlruns/` directory) |
| Tracking URI | `file:///C:/.../<project>/mlruns` (file URI via `Path.as_uri()`) |
| Experiment name | `agentx_risk_validation` |
| Model registry | None (not used) |
| Remote server | None (not used) |
| MLflow version | See requirements.txt |

The tracking URI is set using `Path.as_uri()` which produces a `file:///` URI.
This is required on Windows; bare Windows paths (e.g., `C:\...\mlruns`) are
rejected by MLflow's tracking URI parser.

---

## What Is Logged Per Run

### Metrics (5)

| Key | Example value | Source |
|---|---|---|
| `roc_auc` | 0.6776 | performance_report from main.py |
| `accuracy` | 0.804 | performance_report from main.py |
| `precision` | 0.350 | performance_report from main.py |
| `recall` | 0.037 | performance_report from main.py |
| `f1_score` | 0.067 | performance_report from main.py |

### Parameters (8)

| Key | Example value | Source |
|---|---|---|
| `dataset_rows` | 5000 | verified_metrics.json |
| `feature_count` | 12 | verified_metrics.json |
| `model_type` | Pipeline(StandardScaler + LogisticRegression) | verified_metrics.json |
| `target` | loan_status | verified_metrics.json |
| `class_balance` | {0: 0.81, 1: 0.19} | verified_metrics.json |
| `test_size` | 0.2 | hardcoded from pipeline config |
| `random_state` | 42 | hardcoded from pipeline config |
| `validation_run_id` | vrun_20260520_... | governance record |

### Artifacts (up to 8)

| Label | Source path | Notes |
|---|---|---|
| verified_metrics_json | docs/evidence/verified_metrics.json | Main evidence file |
| verified_metrics_md | docs/evidence/verified_metrics.md | Human-readable metrics |
| benchmark_results_json | docs/evidence/benchmark_results.json | Benchmark timing evidence |
| benchmark_report_md | docs/evidence/benchmark_report.md | Benchmark human report |
| shap_summary_png | data/validation_outputs/shap_summary.png | SHAP global importance |
| governance_record | data/governance/latest_validation_run.json | Latest governance record |
| compliance_output | data/validation_outputs/last_compliance.json | Compliance advisory |
| drift_report | data/validation_outputs/drift_report.json | KS-test drift results |

Artifacts are only logged if the source file exists and the filename does not
contain any secret-related keyword (`.env`, `credential`, `api_key`, `secret`,
`password`, `token`). Missing files return `False` in the artifact status map
without raising an exception.

---

## Verified Run (2026-05-20)

First MLflow run produced after wiring:

| Field | Value |
|---|---|
| Run ID | 96bb66e40b5242bca667ef38ab39aba0 |
| Experiment | agentx_risk_validation |
| Metrics logged | 5 (all verified values confirmed) |
| Params logged | 8 |
| Artifacts logged | 8 |
| ROC-AUC in MLflow | 0.6776 (matches verified_metrics.json) |

---

## Integration Architecture

MLflow tracking is Step 13 of `run_agentx_pipeline()` in `main.py`:

```python
# Step 13 -- local MLflow validation tracking
try:
    from utils.mlflow_tracking import run_mlflow_tracking_summary
    mlflow_result = run_mlflow_tracking_summary(
        performance_report=performance_report,
        governance_run_id=gov_record["validation_run_id"],
    )
except Exception as exc:
    logger.warning("MLflow tracking did not complete (pipeline not affected): %s", exc)
    warnings.append(f"MLflow tracking skipped: {exc}")
```

The entire step is wrapped in a try/except block. Any MLflow failure
(import error, URI error, disk issue) logs a warning and appends to
`result["warnings"]` but does not stop or fail the pipeline.

---

## New Utility Module

`utils/mlflow_tracking.py` provides:

| Function | Purpose |
|---|---|
| `configure_mlflow()` | Sets tracking URI and experiment; creates mlruns/ directory |
| `_is_safe_artifact_path(path)` | Returns False if filename contains secret-related keyword |
| `_log_artifact_safely(path, label)` | Logs one artifact; returns True/False; never raises |
| `log_model_metrics(metrics)` | Logs 5 standard metrics to active run |
| `log_validation_params(context)` | Logs 8 validation params to active run |
| `log_agentx_artifacts(artifact_paths)` | Logs a dict or list of artifacts; returns label->bool map |
| `log_governance_record(path)` | Logs latest governance record JSON |
| `log_benchmark_results(path)` | Logs benchmark results JSON |
| `log_compliance_output(path)` | Logs compliance advisory JSON |
| `run_mlflow_tracking_summary(...)` | Orchestrates full run; returns summary dict; never raises |
| `mlflow_tracking_available()` | Returns True if mlruns/ exists and is non-empty |

---

## API Integration

`GET /evidence` now includes `mlflow_tracking_available` in its response:

```json
{
  "evidence_files": [...],
  "generated_artifacts": [...],
  "governance_available": true,
  "mlflow_tracking_available": true
}
```

Added to `api/schemas.py` (EvidenceResponse field) and `api/service.py`
(lazy import of mlflow_tracking_available from utils.mlflow_tracking).

---

## Test Coverage

`tests/test_mlflow_tracking.py` contains 25 tests:

| Test Group | Count | Coverage |
|---|---|---|
| Module imports | 3 | All public exports present, MLFLOW_EXPERIMENT_NAME value |
| `_is_safe_artifact_path` | 4 | .json/.png allowed, .env/credentials blocked |
| `configure_mlflow` | 3 | Sets URI, creates directory, idempotent |
| `log_model_metrics` | 2 | Valid dict and empty dict |
| `log_validation_params` | 2 | Valid dict and empty dict |
| `log_agentx_artifacts` | 3 | Missing file, present file, list form |
| `run_mlflow_tracking_summary` | 6 | Returns ok, creates mlruns, no perf report, no secrets in result, bool artifacts, real artifact |
| `mlflow_tracking_available` | 2 | False when no dir, True after run |

All 25 tests pass. Tests use `tmp_path` and `monkeypatch.setattr` to isolate
from the real `mlruns/` directory. No live Groq API calls are made.

After this addition: total passing fast tests = 237.

---

## Limitations

- Local file tracking only. No remote MLflow server, no model registry, no artifact store on S3 or GCS.
- MLflow filesystem tracking backend is deprecated as of MLflow 2.x (February 2026 per FutureWarning). It remains functional for local development use.
- `mlruns/` is excluded from git via `.gitignore`. MLflow run history does not persist across git clones.
- `mlartifacts/` is also excluded from git.
- No model registration, no model versioning via MLflow, no MLflow UI deployment.

---

## Claim-Safe Wording

Safe to state:
- "Each AgentX pipeline run logs verified metrics, validation parameters, and evidence artifacts to a local MLflow file store."
- "MLflow experiment: `agentx_risk_validation`. Metrics logged: ROC-AUC, accuracy, precision, recall, F1. Params logged: dataset rows, feature count, model type, target, class balance, test size, random state, validation run ID."
- "MLflow tracking is local development tracking only. No remote server, no model registry, no production MLflow deployment."
- "MLflow tracking failure does not affect pipeline execution. Failure is caught, logged as a warning, and appended to the pipeline result warnings list."

Not safe to state:
- "MLflow model registry in use" -- registry is not configured.
- "MLflow model serving" -- not deployed.
- "Remote MLflow tracking server" -- tracking is local file-based only.
- "Production MLflow deployment" -- not deployed.