# AgentX Risk Validator -- L2 Engineering Upgrade Plan
Audit date: 2026-05-19
Last updated: 2026-05-20 (Phase 5B.8 complete)
Scope: Phase 5B recommended engineering upgrades

---

## Upgrade Philosophy

Upgrades are sequenced by dependency. Security and correctness gaps must be resolved before capability gaps. No new features until the existing pipeline is correct and reproducible.

---

## Wave 1: Security and Correctness [STATUS: COMPLETE -- Phase 5B.1]

### U1.1 -- Create .gitignore [DONE]
Created at project root. Excludes: .env, *.pkl, *.joblib, large CSVs, generated reports,
__pycache__, virtual environments, OS artifacts, FAISS index files.

### U1.2 -- Rotate Groq API key [OWNER ACTION REQUIRED]
.gitignore now protects .env from git tracking.
.env.example created with safe placeholder values.
Owner must rotate the Groq API key at console.groq.com before running git init.

### U1.3 -- Fix model pipeline inconsistency (GAP-004) [DONE]
Root cause diagnosed in docs/evidence/metric_inconsistency_diagnosis.md.

Changes made:
- utils/load_data.py: added load_clean_data(), removed StandardScaler from preprocess_uploaded_data()
- utils/model_utils.py: replaced raw LR with Pipeline(StandardScaler + LR), switched to joblib
- agents/performance_agent.py: added precision, recall, f1 to returned metrics
- agents/feedback_memory_agent.py: fixed FAISS dimension mismatch on fresh runs
- agents/drift_monitor_agent.py: removed emoji from print (Windows encoding fix)
- agents/compliance_agent.py: updated Groq model to llama-3.3-70b-versatile (decommissioned model replaced)
- main.py: calls preprocess_uploaded_data() before train_model(); writes verified metrics

Verified metrics (2026-05-19):
- ROC-AUC: 0.6776
- Accuracy: 0.804
- Precision: 0.35, Recall: 0.037, F1: 0.067
- Full details in docs/evidence/verified_metrics.md

### U1.4 -- Initialize git repository [PENDING -- owner action after key rotation]
After API key rotation:
```
git init
git add .
git commit -m "Initial commit: AgentX Risk Validator -- Phase 5B.1 security and metric fix"
```

---

## Wave 2: Documentation [STATUS: COMPLETE -- Phase 5B.2]

### U2.1 -- Write README.md [DONE]
README.md written from scratch (was empty before Phase 5B.2).

Sections written:
- Title: AgentX: Autonomous Risk Model Validation Assistant
- Executive summary
- Business problem and MRM context
- Target users table
- Full system architecture ASCII diagram
- Agent layer table (all 7 agents, status, output files)
- Verified model evidence table (Phase 5B.1 metrics with interpretation)
- SHAP and FAISS explainability and memory section
- Compliance agent description with limitations
- Drift monitoring with planned module note
- How to run locally (environment, .env setup, CLI and Streamlit)
- Evidence files table
- Security notes
- Current limitations table (framed as engineering targets)
- Engineering roadmap: Implemented / In Progress / Planned Product Modules
- Claim safety section
- Original vision alignment (SR 11-7, Basel IV)
- Dataset citation
- Key dependencies table

Planned product modules named in roadmap (not vague "future" items):
FastAPI boundary, Docker, MLflow, MCP governance log, PDF audit pack,
drift-triggered revalidation, compliance grounding, benchmark script,
class-weighted and XGBoost models.

### U2.2 -- Write docs/evidence/verified_metrics.md [DONE in Phase 5B.1]
Completed in Phase 5B.1 as part of pipeline fix.
ROC-AUC: 0.6776, Accuracy: 0.804, Precision: 0.350, Recall: 0.037, F1: 0.067

### U2.3 -- README upgrade report [DONE]
Created docs/evidence/readme_upgrade_report.md covering:
- sections added
- verified metrics used
- old metrics confirmed absent
- vision preservation strategy
- em dash and claim-safety checks

---

## Wave 3: Code Quality [STATUS: COMPLETE -- Phase 5B.3]

### U3.1 -- Delete empty stub files [DONE]
Removed:
- `utils/shap_explainer.py` (was empty, 0 imports)
- `utils/model_metrics.py` (was empty, 0 imports)
- `frontend/app_ui.py` (was empty, 0 imports)

### U3.2 -- Consolidate duplicate implementations [DONE]
Removed:
- `utils/vector_store.py` (IndexFlatL2, 0 imports, superseded by feedback_memory_agent.py)
- `reports/generate_report.py` (minimal duplicate, main.py import updated to agents/report_writer_agent.py)

### U3.3 -- Add config.py [DONE]
Created `utils/config.py` with all paths derived from PROJECT_ROOT using pathlib.
All agents, main.py, and streamlit_app.py import paths from utils.config.
GROQ_DEFAULT_MODEL consolidated to config (removed duplicate constant from compliance_agent.py).

### U3.4 -- Replace print() with logging [DONE]
Created `utils/logging_utils.py` exposing setup_logger(name).
All agents and main.py import setup_logger and call logger.info/warning/error.
Log file written to logs/agentx.log on every pipeline run.
SHAP PNG save bug fixed: plt.savefig(SHAP_SUMMARY_PATH) added to explainability_agent.py.

Full validation run after Wave 3 changes: all 7 agents complete, ROC-AUC 0.6776 unchanged.
See docs/evidence/code_cleanup_report.md for full change log.

---

## Wave 4: Test Suite [STATUS: COMPLETE -- Phase 5B.4]

### U4.1 -- Create test files [DONE]

Files created:
- tests/conftest.py (session-scoped fixtures)
- tests/test_config.py (10 tests)
- tests/test_data_pipeline.py (11 tests)
- tests/test_model_pipeline.py (14 tests)
- tests/test_agents.py (32 tests -- all 7 agents)
- tests/test_artifacts.py (18 tests)
- tests/test_main_smoke.py (3 tests, marked slow)
- pytest.ini

Run fast tests: `python -m pytest -m "not slow"`
Run all tests: `python -m pytest`

### U4.2 -- Pipeline smoke test [DONE]

tests/test_main_smoke.py runs main.py via subprocess and verifies exit code 0
and all 9 artifacts present. Marked @pytest.mark.slow.

Results: 85 passed, 0 failed. ROC-AUC 0.6776 locked as regression guard.
Full report: docs/evidence/test_suite_report.md

---

## Wave 5: Deployment Readiness [STATUS: COMPLETE -- Phase 5B.5]

### U5.1 -- Dockerfile [DONE]

Created at project root. Base: `python:3.11-slim`. System deps: gcc, g++, libgomp1
(required for SHAP and faiss-cpu). Exposes port 8000. Default command: uvicorn.

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`.dockerignore` created to exclude: `.env`, `.git/`, `__pycache__/`, large CSV,
`reports/*.pdf`, `reports/*.html`, `logs/`, virtual envs, notebooks.

Verified: `docker build -t agentx-risk-validator .` and container test confirmed
GET /health and GET /metrics return correct values including ROC-AUC 0.6776.

### U5.2 -- FastAPI serving boundary [DONE]

Created `api/` package with:
- `api/__init__.py` -- package marker
- `api/schemas.py` -- Pydantic v2 models: HealthResponse, MetricsResponse, EvidenceResponse, ValidationRunRequest, ValidationRunResponse, EvidenceFileInfo; CLAIM_SAFETY_NOTE constant
- `api/service.py` -- service functions: load_verified_metrics, list_evidence_files, list_generated_artifacts, run_validation_pipeline
- `api/main.py` -- FastAPI app with lifespan, HTTP middleware, GET /health, GET /metrics, GET /evidence, POST /validate

Refactored `main.py` from script to callable module: all logic wrapped in
`run_agentx_pipeline()`, `if __name__ == "__main__":` guard preserves `python main.py`.

26 API tests added in `tests/test_api.py`. Total test suite: 111 passing, 0 failed.

Full details in `docs/evidence/api_boundary_report.md`.

---

## Wave 6: Governance Evidence -- Planned Product Module

### U6.1 -- Ground compliance in model outputs
Modify compliance_agent to receive actual metrics dict and pass it as context to the Groq prompt. Reference SR11-7 and Basel docs via RAG using the existing FAISS infrastructure.

### U6.2 -- MLflow integration [DONE -- Phase 5B.8]

Created `utils/mlflow_tracking.py` with full local tracking utility:
- `configure_mlflow()`: sets tracking URI (`file:///` format, required on Windows) and experiment
- `run_mlflow_tracking_summary(performance_report, governance_run_id)`: orchestrates full run logging
- Safe artifact filtering: filenames containing `.env`, `credential`, `api_key`, `secret`, `password`, or `token` are skipped
- `mlflow_tracking_available()`: returns True if mlruns/ exists and is non-empty

Added Step 13 to `run_agentx_pipeline()` in main.py:
```python
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

Added to `utils/config.py`:
```python
MLFLOW_TRACKING_DIR: Path = PROJECT_ROOT / "mlruns"
MLFLOW_ARTIFACTS_DIR: Path = PROJECT_ROOT / "mlartifacts"
MLFLOW_EXPERIMENT_NAME: str = "agentx_risk_validation"
```

Metrics logged per run: roc_auc, accuracy, precision, recall, f1_score.
Params logged per run: dataset_rows, feature_count, model_type, target, class_balance, test_size, random_state, validation_run_id.
Artifacts logged: up to 8 evidence files (missing files skipped gracefully).

API: `GET /evidence` now returns `mlflow_tracking_available` field.
Tests: 25 new tests in `tests/test_mlflow_tracking.py`. All isolated via tmp_path and monkeypatch.
Total test suite after Phase 5B.8: 237 passing.

Verified first run: run_id=96bb66e40b5242bca667ef38ab39aba0, experiment=agentx_risk_validation,
5 metrics logged, 8 params logged, 8 artifacts logged. ROC-AUC confirmed 0.6776.

.gitignore: `mlruns/` and `mlartifacts/` added (local run history not committed).

Limitations: Local file tracking only. No remote server. No model registry. No MLflow UI deployment.
Full documentation: docs/evidence/mlflow_tracking_report.md

### U6.3 -- Benchmark script [DONE -- Phase 5B.6A]

Created `scripts/benchmark_agentx.py`:
- Benchmarks GET /health, GET /metrics, GET /evidence via TestClient (30 iterations each)
- Benchmarks POST /validate via TestClient (3 iterations -- full pipeline per call)
- Benchmarks pipeline direct call via run_agentx_pipeline() (3 iterations)
- Checks all 8 expected artifacts: present and non-empty
- Saves machine-readable output to `docs/evidence/benchmark_results.json`
- Saves human-readable report to `docs/evidence/benchmark_report.md`
- Docker smoke test performed manually: build success, health and metrics verified

16 benchmark tests added in `tests/test_benchmark_script.py`.
Total test suite after Phase 5B.6A: 127 tests, all passing.

Results (local Windows machine, Python 3.13.1, Intel Core Ultra):
- GET /health median: 1.9ms, p95: 2.4ms
- GET /metrics median: 2.0ms, p95: 2.9ms
- GET /evidence median: 2.5ms, p95: 2.9ms
- POST /validate median: 2399ms (full pipeline including SHAP and drift)
- Pipeline direct median: 2340ms

### U6.4 -- Local Governance Evidence Layer [DONE -- Phase 5B.6B]

Created `utils/governance.py`:
- generate_validation_run_id(): unique ID format `vrun_YYYYMMDD_HHMMSS_xxxxxxxx`
- create_validation_run_record(): assembles full governance record with metrics snapshot,
  drift status, compliance status, artifact status, benchmark summary, risk flags,
  claim-safety note, limitations, reviewer_status="pending_review"
- write_validation_run_record(): writes to data/governance/validation_runs/{run_id}.json
  and data/governance/latest_validation_run.json
- load_latest_validation_run(): reads latest governance record
- list_validation_runs(limit): returns list of run summaries

Added GOVERNANCE_DIR, GOVERNANCE_RUNS_DIR, GOVERNANCE_LATEST_PATH to utils/config.py.

Updated main.py: Step 12 writes governance record after verified metrics.
Added data/governance/ to .gitignore.

API endpoints added:
- GET /governance/latest: latest validation-run record (503 if none)
- GET /governance/history: list of recent run summaries (always 200)

New schemas in api/schemas.py: GovernanceLatestResponse, GovernanceHistoryResponse,
GovernanceRunHistoryItem.

Tests:
- tests/test_governance.py: ~60 tests covering all governance utility functions,
  write/load round-trips using tmp_path + monkeypatch
- tests/test_api.py: 15 new governance endpoint tests added
- Total test suite after Phase 5B.6B: 173 tests, all passing

First governance record generated: vrun_20260520_033532_ba10841b
- roc_auc: 0.6776, reviewer_status: pending_review
- risk_flags: ["Feature drift detected in: annual_inc, loan_amnt"]
- 8/8 artifacts present

Full documentation: docs/evidence/governance_evidence_report.md

### U6.5 -- Compliance Agent Grounding [DONE -- Phase 5B.6C]

Created `utils/compliance_context.py`:
- load_verified_metrics_context(), load_drift_context(), load_artifact_context()
- load_governance_context(), load_benchmark_context()
- build_compliance_context(perf_report=None): assembles full evidence context
- format_compliance_context_for_prompt(): formats context as structured string for LLM

Modified `agents/compliance_agent.py`:
- generate_compliance_report(evidence_context=None): builds grounded Groq prompt with actual metrics
- _fallback_advisory(evidence_context=None): structured fallback citing real evidence values
- run_compliance_agent(evidence_context=None): builds context if not provided
- Source string changed from "Cache" to "LocalFallback"
- Saved JSON includes advisory_only, not_regulatory_approval, evidence_grounded, evidence_sources, key_validation_concerns

Modified `main.py`:
- Imports build_compliance_context
- Builds compliance_context from current performance_report before Step 9
- Passes evidence_context to run_compliance_agent

Tests:
- tests/test_compliance_context.py: ~39 tests covering all context builder functions
- tests/test_agents.py: updated source assertion + 4 new grounded compliance tests
- Total test suite after Phase 5B.6C: 212 fast tests, all passing

Verified compliance record (2026-05-20):
- source: API, evidence_grounded: True
- evidence_sources: [verified_metrics_json, drift_report, governance_record, benchmark_results]
- ROC-AUC 0.6776 cited in report content
- No secrets in output

Full documentation: docs/evidence/compliance_grounding_report.md

---

## Upgrade Sequence Summary

| Wave | Status | Upgrades | Unlocks |
|---|---|---|---|
| Wave 1 | COMPLETE (Phase 5B.1) | .gitignore, .env.example, pipeline fix, FAISS fix, Groq model update | Security, correct verified metrics |
| Wave 2 | COMPLETE (Phase 5B.2) | README rewrite, readme_upgrade_report.md, upgrade_plan update | Self-documenting system, citable metrics |
| Wave 3 | COMPLETE (Phase 5B.3) | Delete stubs, consolidate duplicates, config.py, structured logging | Engineering maturity claim |
| Wave 4 | COMPLETE (Phase 5B.4) | 85 pytest tests: config, data, model, agents, artifacts, smoke | Quality and reliability claim |
| Wave 5 | COMPLETE (Phase 5B.5) | Dockerfile, .dockerignore, FastAPI boundary (GET /health, GET /metrics, GET /evidence, POST /validate), 26 API tests, main.py refactor | Deployment and API claim |
| Wave 6 | COMPLETE (Phase 5B.8) | Benchmark script (6A); local governance evidence layer + /governance API (6B); compliance grounding (6C); evidence consolidation (6D); git init + first commit (5B.7); local MLflow tracking (5B.8) | Benchmark, governance, compliance grounding, MLflow tracking claims all unlocked |
