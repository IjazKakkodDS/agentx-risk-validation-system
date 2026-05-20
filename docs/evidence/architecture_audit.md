# AgentX Risk Validator -- Architecture Audit
Audit date: 2026-05-19
Last updated: 2026-05-20 (Phase 5B.9 -- portable audit pack added; all 15 gaps closed)

---

## 1. Current Architecture Description

AgentX is a multi-agent autonomous risk model validation system built around a LendingClub credit portfolio dataset. The system has three entry points:

**Entry Point A: main.py (CLI pipeline)**
Executes agents sequentially: load data -> train model -> validate data -> evaluate performance -> explain with SHAP -> run feedback memory -> write report -> run compliance -> detect drift -> write final report. Refactored in Phase 5B.5 to expose `run_agentx_pipeline()` callable; `python main.py` still works via `if __name__ == "__main__":` guard.

**Entry Point B: streamlit_app.py (8-page UI)**
Provides an interactive validation dashboard where a user uploads CSV data, triggers the full pipeline through the UI, and views results across 8 pages: Upload, Overview, Performance, Explainability, Compliance, Drift, Export, Compare Models.

**Entry Point C: api/main.py (FastAPI local service, Phase 5B.5)**
REST API boundary exposing GET /health, GET /metrics, GET /evidence, and POST /validate. Served via uvicorn on port 8000. Also available as a Docker image (agentx-risk-validator).

---

## 2. Agent Layer

Six autonomous agents exist with clear functional separation:

| Agent | Technology | Input | Output |
|---|---|---|---|
| DataValidatorAgent | pandas | DataFrame | JSON: missing, duplicates, class distribution, stats |
| PerformanceAgent | scikit-learn | model, X_test, y_test | JSON: accuracy, ROC-AUC, confusion matrix |
| ExplainabilityAgent | SHAP | model, X_sample | JSON: shap_values, mean_vector, feature_names, PNG |
| ComplianceAgent | Groq LLM (llama-3.3-70b-versatile) | Evidence context (metrics, drift, governance) | Grounded advisory Markdown compliance report |
| DriftMonitorAgent | scipy KS test | reference CSV, incoming CSV | JSON: per-feature p-values, drift flag |
| FeedbackMemoryAgent | FAISS (IndexFlatIP) | SHAP mean vector | Similar model records by cosine similarity |

---

## 3. Data Flow

```
Raw CSV (LendingClub 5,000 rows)
  -> load_data.preprocess_uploaded_data()
     - Drop ID columns
     - Impute medians (numeric), "Unknown" (categorical)
     - LabelEncode categoricals
     - StandardScale numeric features
     - Reattach loan_status
  -> DataValidatorAgent
  -> model_utils.train_model() [LogisticRegression]
  -> PerformanceAgent
  -> ExplainabilityAgent (SHAP)
  -> FeedbackMemoryAgent (FAISS)
  -> ComplianceAgent (Groq API)
  -> DriftMonitorAgent (KS test vs drifted CSV)
  -> ReportWriter (Markdown -> PDF)
```

---

## 4. Memory / RAG Layer

FAISS is used as a vector memory store for model similarity search:
- Stores normalized mean SHAP vectors per model run
- Uses inner product (cosine similarity) for retrieval
- Two separate FAISS implementations exist (vector_store.py and feedback_memory_agent.py) -- architectural duplication

Compliance agent uses static prompt engineering (not retrieval-augmented). The SR11-7 and Basel docs exist as reference files but are not currently ingested into a RAG pipeline.

---

## 5. UI Layer

Streamlit app (streamlit_app.py v1.2.5) is substantive and well-implemented:
- Theme switching (Auto/Light/Dark)
- Streamlit cache decorators properly applied (cache_resource for model, cache_data for computed results)
- Session state management across 8 pages
- File upload with MIME type and size validation
- PDF export via FPDF
- Model comparison page (upload second model, compare metrics)
- SHAP image display
- Compliance markdown render
- Drift pie chart and table
- Duplicate detection in FAISS memory (vec_hash check)

---

## 6. Report Generation

Three report mechanisms exist:
1. reports/generate_report.py -- minimal Markdown writer
2. agents/report_writer_agent.py -- richer Markdown writer with compliance and drift sections
3. generate_pdf.py -- pdfkit conversion (requires wkhtmltopdf, path hardcoded to C:\Program Files\wkhtmltopdf)
4. streamlit_app.py Page 7 -- FPDF in-browser PDF generation

Only mechanisms 2 and 4 are wired into the active execution paths. Mechanism 1 and 3 are legacy or standalone.

---

## 7. Compliance Layer

Compliance agent calls Groq API (llama-3.3-70b-versatile) with grounded prompts built from local validation evidence:
1. System prompt includes full evidence context: ROC-AUC 0.6776, accuracy, recall, class balance, drift status, governance run ID, artifact status
2. Checklist prompt instructs the LLM to cite actual evidence values (not generic commentary)
3. Fallback generates a structured advisory using real evidence values when the API is unavailable

`utils/compliance_context.py` assembles the evidence context from local artifact files before the agent is called. `main.py` passes the live `performance_report` dict so the compliance review reflects the current pipeline run's metrics.

The saved compliance record includes: advisory_only, not_regulatory_approval, evidence_grounded, evidence_sources, key_validation_concerns, validation_run_id, and limitations. All outputs are advisory only and do not constitute regulatory approval.

---

## 8. Model Training

LogisticRegression trained in model_utils.train_model():
- 80/20 train/test split, random_state=42
- StandardScaler applied inside preprocess_uploaded_data (not saved with model)
- Model saved as .pkl via pickle

Critical issue: the scaler is fit on the uploaded data but not saved alongside the model. When the model is reloaded for inference, the preprocessing step is reapplied fresh. This is internally consistent if the same data is used, but creates a discrepancy when training occurs on raw data and evaluation occurs on preprocessed data.

---

## 9. Separation of Concerns Assessment

| Concern | Status |
|---|---|
| Agent isolation | Good -- each agent has a single function |
| Data loading vs preprocessing | Partially separated (load_data.py handles both) |
| Training vs inference | main.py trains and immediately evaluates (local scope acceptable) |
| Config vs code | RESOLVED (Phase 5B.3) -- utils/config.py centralizes all paths |
| API secrets vs code | RESOLVED (Phase 5B.1) -- .gitignore and .dockerignore protect .env |
| Report writing | Consolidation done (Phase 5B.3) -- agents/report_writer_agent.py is primary |
| FAISS store | Consolidation done (Phase 5B.3) -- vector_store.py deleted |
| API boundary | ADDED (Phase 5B.5) -- api/ package isolates route handlers from agent logic |

---

## 10. Identified Architectural Risks -- Status

1. **Model ROC-AUC inconsistency:** RESOLVED (Phase 5B.1). Pipeline fixed to Pipeline(StandardScaler + LR). Verified ROC-AUC: 0.6776.

2. **Live API key in .env with no .gitignore:** RESOLVED (Phase 5B.1). .gitignore and .dockerignore both exclude .env.

3. **Compliance agent generates non-model-specific outputs:** RESOLVED (Phase 5B.6C). utils/compliance_context.py builds evidence context; compliance agent uses actual ROC-AUC, recall, class balance, drift status, and governance run ID in both the LLM prompt and the fallback advisory.

4. **Empty stub files:** RESOLVED (Phase 5B.3). shap_explainer.py, model_metrics.py, and frontend/app_ui.py deleted.

5. **No test suite:** RESOLVED (Phase 5B.4 + 5B.5 + 5B.6B + 5B.6C + 5B.8 + 5B.9). 268 passing pytest tests.

6. **No MLflow tracking:** RESOLVED (Phase 5B.8). utils/mlflow_tracking.py wired into pipeline as Step 13. See Section 15.

7. **PDF system dependency (GAP-014):** RESOLVED (Phase 5B.9). utils/audit_pack.py generates MD, HTML, PDF using markdown2 and fpdf2 (pure Python, no system binary). See Section 16.

---

## 11. API Layer (Phase 5B.5)

| Component | File | Role |
|---|---|---|
| Schemas | api/schemas.py | Pydantic v2 models for all request/response types |
| Service adapters | api/service.py | Thin adapters; no pipeline logic duplicated |
| Route handlers | api/main.py | FastAPI app with lifespan, middleware, 4 endpoints |
| Container | Dockerfile | python:3.11-slim, port 8000 |
| Exclusions | .dockerignore | Keeps .env, large CSV, caches out of image |

The lazy import pattern in api/service.py prevents pipeline execution at startup.
The API layer does not duplicate any agent or pipeline logic; it adapts existing
functions from main.py and utils/.

---

## 12. Benchmark Layer (Phase 5B.6A)

| Component | File | Role |
|---|---|---|
| Benchmark script | scripts/benchmark_agentx.py | Times all 4 endpoints (TestClient), pipeline direct call, artifact check |
| Machine-readable output | docs/evidence/benchmark_results.json | Structured timing results |
| Human-readable report | docs/evidence/benchmark_report.md | Narrative benchmark report with disclaimer and limitations |

Measured results (local Windows machine, Python 3.13.1):
- GET /health: 1.9ms median, 2.4ms p95 (in-process, not network)
- GET /metrics: 2.0ms median, 2.9ms p95
- GET /evidence: 2.5ms median, 2.9ms p95
- POST /validate: 2399ms median (full pipeline per call)
- Pipeline direct: 2340ms median

These are local development measurements only. They do not represent production,
container, or cloud deployment performance.

---

## 13. Governance Evidence Layer (Phase 5B.6B)

| Component | File | Role |
|---|---|---|
| Governance utilities | utils/governance.py | Run ID generation, record assembly, file I/O, list functions |
| Governance paths | utils/config.py | GOVERNANCE_DIR, GOVERNANCE_RUNS_DIR, GOVERNANCE_LATEST_PATH |
| Pipeline integration | main.py | Step 12: writes governance record after verified_metrics |
| Record store | data/governance/ | Excluded from git; local-only file store |
| API schemas | api/schemas.py | GovernanceLatestResponse, GovernanceHistoryResponse, GovernanceRunHistoryItem |
| API service | api/service.py | load_latest_governance_record, list_governance_history, governance_available |
| API routes | api/main.py | GET /governance/latest, GET /governance/history |
| Tests | tests/test_governance.py | ~60 tests; all write/load tests use tmp_path + monkeypatch |
| API tests | tests/test_api.py | 15 governance endpoint tests added in Phase 5B.6B |

First verified record: vrun_20260520_033532_ba10841b
- ROC-AUC: 0.6776, reviewer_status: pending_review
- risk_flags: ["Feature drift detected in: annual_inc, loan_amnt"]
- 8/8 artifacts present

The governance layer is local-only evidence tooling. It is not a regulatory audit
system, enterprise governance platform, or MCP-compliant service.

---

## 14. Compliance Grounding Layer (Phase 5B.6C)

| Component | File | Role |
|---|---|---|
| Context builder | utils/compliance_context.py | Loads verified_metrics.json, drift_report.json, governance record, benchmark_results.json; assembles structured evidence dict |
| Prompt formatter | utils/compliance_context.py | format_compliance_context_for_prompt(): formats evidence as structured string for LLM system prompt |
| Grounded agent | agents/compliance_agent.py | generate_compliance_report(evidence_context): injects evidence into Groq system prompt |
| Grounded fallback | agents/compliance_agent.py | _fallback_advisory(evidence_context): advisory report using actual metric values |
| Pipeline integration | main.py | Step 9: builds context from live performance_report, passes to run_compliance_agent |
| Context tests | tests/test_compliance_context.py | ~39 tests for all context builder functions and constants |
| Agent tests | tests/test_agents.py | 4 new grounded compliance tests; source assertion updated to "LocalFallback" |

Verified output (2026-05-20):
- source: API, evidence_grounded: True
- evidence_sources: [verified_metrics_json, drift_report, governance_record, benchmark_results]
- ROC-AUC 0.6776 cited in compliance report content

The compliance grounding layer is advisory evidence tooling. It does not constitute
regulatory approval, certification, or a production compliance determination.

---

## 15. Local MLflow Tracking Layer (Phase 5B.8)

| Component | File | Role |
|---|---|---|
| Tracking utility | utils/mlflow_tracking.py | configure_mlflow, log_model_metrics, log_validation_params, log_agentx_artifacts, run_mlflow_tracking_summary, mlflow_tracking_available |
| MLflow paths | utils/config.py | MLFLOW_TRACKING_DIR, MLFLOW_ARTIFACTS_DIR, MLFLOW_EXPERIMENT_NAME |
| Pipeline integration | main.py | Step 13: wrapped in try/except; failure does not stop pipeline |
| API integration | api/service.py | mlflow_tracking_available() lazy import |
| API schema | api/schemas.py | EvidenceResponse.mlflow_tracking_available field |
| API route | api/main.py | GET /evidence returns mlflow_tracking_available |
| Local run store | mlruns/ | Excluded from git; local-only file store |
| Tests | tests/test_mlflow_tracking.py | 25 tests; all use tmp_path + monkeypatch for isolation |

Verified first run (2026-05-20):
- Experiment: agentx_risk_validation
- Run ID: 96bb66e40b5242bca667ef38ab39aba0
- Metrics: roc_auc=0.6776, accuracy=0.804, precision=0.35, recall=0.037, f1_score=0.067
- Params: 8 (dataset_rows, feature_count, model_type, target, class_balance, test_size, random_state, validation_run_id)
- Artifacts: 8 evidence files logged

Tracking URI uses `Path.as_uri()` to produce `file:///C:/...` format required on Windows.
Bare Windows path strings are rejected by MLflow's tracking URI parser.

The MLflow tracking layer is local development tooling only. No remote server,
no model registry, no artifact store, no production MLflow deployment.

---

## 16. Local Audit Pack Layer (Phase 5B.9)

| Component | File | Role |
|---|---|---|
| Audit pack utility | utils/audit_pack.py | collect_audit_pack_context, render_audit_markdown, write_audit_html, write_audit_pdf, generate_audit_pack |
| Audit pack paths | utils/config.py | AUDIT_PACK_DIR, AUDIT_PACK_MD_PATH, AUDIT_PACK_HTML_PATH, AUDIT_PACK_PDF_PATH, AUDIT_PACK_JSON_PATH |
| Pipeline integration | main.py | Step 14: wrapped in try/except; failure does not stop pipeline |
| API integration | api/service.py | audit_pack_available() lazy check |
| API schema | api/schemas.py | EvidenceResponse.audit_pack_available field |
| API route | api/main.py | GET /evidence returns audit_pack_available |
| Output directory | reports/audit_pack/ | Excluded from git; local-only outputs |
| Tests | tests/test_audit_pack.py | 31 tests; all use tmp_path + monkeypatch for isolation |

Audit pack includes: verified metrics, dataset summary, drift status, compliance summary,
governance run ID, benchmark summary, MLflow status, limitations, claim-safety note.

HTML uses markdown2. PDF uses fpdf2 (pure Python, no system binary). No pdfkit or
wkhtmltopdf dependency. GAP-014 (PDF system dependency) is resolved.

The audit pack is local development evidence. It is not a regulatory audit record
and does not constitute regulatory approval.
