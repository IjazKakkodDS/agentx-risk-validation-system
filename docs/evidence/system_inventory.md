# AgentX Risk Validator -- System Inventory
Audit date: 2026-05-19
Last updated: 2026-05-20 (Phase 5B.6C complete)
Auditor: Phase 5A/5B Engineering Readiness Audit

---

## 1. Repository State

| Item | Status |
|---|---|
| Git repository | NOT initialized (.git folder absent) |
| Branch | None |
| Remote | None |
| .gitignore | Absent |
| README.md | Present but empty (1 line, blank) |

---

## 2. Top-Level Files

| File | Role | Status |
|---|---|---|
| main.py | Pipeline orchestrator (callable module + CLI guard) | Present, refactored Phase 5B.5 |
| streamlit_app.py | 8-page Streamlit UI, v1.2.5 | Present, substantive |
| requirements.txt | Full dependency list | Present, updated Phase 5B.5 (httpx, pydantic) |
| Dockerfile | Docker image build spec (python:3.11-slim, port 8000) | Present -- added Phase 5B.5 |
| .dockerignore | Docker build exclusions (.env, large CSV, caches, logs) | Present -- added Phase 5B.5 |
| .gitignore | Git exclusions (.env, *.pkl, large CSVs, reports) | Present -- added Phase 5B.1 |
| .env | Environment secrets | Present -- excluded from git and Docker image |
| .env.example | Safe placeholder values for onboarding | Present -- added Phase 5B.1 |
| create_sample_data.py | Samples 5,000 rows from LendingClub | Present |
| simulate_drift.py | Generates artificial drift dataset | Present |
| generate_pdf.py | Converts Markdown to PDF via pdfkit | Present, system-specific path hardcoded |

---

## 3. Agent Files (agents/)

| Agent | File | Core Function | Status |
|---|---|---|---|
| Data Validator | data_validator_agent.py | Missing values, duplicates, class distribution, summary stats | Present, functional |
| Performance Agent | performance_agent.py | Accuracy, ROC-AUC, confusion matrix | Present, functional |
| Explainability Agent | explainability_agent.py | SHAP values, mean vector, FAISS-compatible output, summary plot | Present, functional |
| Compliance Agent | compliance_agent.py | Groq LLM API call (grounded prompt) + evidence-grounded fallback advisory | Present, functional -- updated Phase 5B.6C |
| Drift Monitor Agent | drift_monitor_agent.py | KS test per numeric feature, JSON output | Present, functional |
| Feedback Memory Agent | feedback_memory_agent.py | FAISS vector store for model similarity | Present, functional |
| Report Writer | report_writer_agent.py (in reports/) | Markdown report generation | Present, functional |

---

## 4. Utility Files (utils/)

| File | Role | Status |
|---|---|---|
| load_data.py | preprocess_uploaded_data: full preprocessing pipeline | Present, functional |
| model_utils.py | train_model: Pipeline(StandardScaler+LR), save model | Present, functional |
| config.py | Centralized path config (PROJECT_ROOT, all artifact paths, governance paths) | Present -- added Phase 5B.3; updated Phase 5B.6B |
| logging_utils.py | setup_logger() wrapper for structured logging | Present -- added Phase 5B.3 |
| governance.py | Validation-run record assembly, write, load, list functions | Present -- added Phase 5B.6B |
| compliance_context.py | Evidence context builder: load local artifacts, assemble structured context dict, format for LLM prompt | Present -- added Phase 5B.6C |
| __init__.py | Package marker | Present |

Deleted in Phase 5B.3 (dead code):
- `vector_store.py` (superseded by feedback_memory_agent)
- `shap_explainer.py` (empty stub)
- `model_metrics.py` (empty stub)

---

## 5. Data Artifacts

| Artifact | Path | Status |
|---|---|---|
| Full LendingClub dataset | data/raw_data/accepted_2007_to_2018Q4.csv | Present (large, not inspected for size) |
| Clean sample (5,000 rows) | data/raw_data/lending_club_clean_sample.csv | Present, verified |
| Drifted dataset | data/drift_test/incoming_drifted_data.csv | Present, simulated |
| Trained model | data/incoming_models/credit_model.pkl | Present (LogisticRegression) |
| FAISS index (memory) | data/memory_index/agentx_faiss.index | Present |
| FAISS metadata | data/memory_index/agentx_meta.pkl | Present |
| FAISS model memory | data/model_memory/index.faiss | Present |
| Model memory metadata | data/model_memory/metadata.json | Present |

---

## 6. Validation Output Artifacts

| File | Status |
|---|---|
| data/validation_outputs/data_validation.json | Present, generated |
| data/validation_outputs/performance_metrics.json | Present, generated |
| data/validation_outputs/drift_report.json | Present, generated |
| data/validation_outputs/shap_summary.png | Present, generated |
| data/validation_outputs/last_compliance.json | Present, generated |
| data/validation_outputs/compliance_error.json | Present (proxy error during one run) |
| data/validation_outputs/feedback_memory.json | Present |

---

## 7. Reports

| File | Status |
|---|---|
| reports/validation_report.md | Present, generated |
| reports/validation_report.html | Present, generated |
| reports/validation_report.pdf | Present, generated |
| reports/test_validation_report.md | Present, test stub |

---

## 8. Docs

| File | Status |
|---|---|
| docs/sr11_7_summary.md | Present, substantive |
| docs/basel_guidelines_summary.md | Present, substantive |

---

## 9. Frontend

| File | Status |
|---|---|
| frontend/app_ui.py | EMPTY FILE |

---

## 10. Tests

| Item | Status |
|---|---|
| Test suite (pytest/unittest) | PRESENT -- 212 fast tests passing (Phase 5B.6C) |
| tests/conftest.py | Present -- session-scoped fixtures |
| tests/test_config.py | Present -- 10 tests |
| tests/test_data_pipeline.py | Present -- 11 tests |
| tests/test_model_pipeline.py | Present -- 14 tests |
| tests/test_agents.py | Present -- 36 tests (all 7 agents + 4 grounded compliance tests added Phase 5B.6C) |
| tests/test_artifacts.py | Present -- 18 tests |
| tests/test_main_smoke.py | Present -- 3 smoke tests (marked slow) |
| tests/test_api.py | Present -- 41 API tests (Phase 5B.5 + 5B.6B) |
| tests/test_benchmark_script.py | Present -- 16 benchmark tests (Phase 5B.6A) |
| tests/test_governance.py | Present -- ~60 governance utility tests (Phase 5B.6B) |
| tests/test_compliance_context.py | Present -- ~39 compliance context tests (Phase 5B.6C) |
| pytest.ini | Present |

---

## 13. Scripts

| File | Role | Status |
|---|---|---|
| scripts/benchmark_agentx.py | Benchmark all 4 endpoints (TestClient) + pipeline + artifacts; writes benchmark_results.json and benchmark_report.md | Present -- Phase 5B.6A |

Benchmark evidence files:
| File | Status |
|---|---|
| docs/evidence/benchmark_results.json | Present -- Phase 5B.6A |
| docs/evidence/benchmark_report.md | Present -- Phase 5B.6A |

---

## 11. Infrastructure

| Item | Status |
|---|---|
| Dockerfile | PRESENT -- python:3.11-slim, port 8000 (Phase 5B.5) |
| docker-compose.yml | ABSENT |
| CI/CD config | ABSENT |
| FastAPI implementation | PRESENT -- api/ package, 6 endpoints (Phase 5B.5 + 5B.6B) |
| Governance evidence layer | PRESENT -- utils/governance.py, data/governance/ (Phase 5B.6B) |
| .gitignore | PRESENT -- added Phase 5B.1 |
| .dockerignore | PRESENT -- added Phase 5B.5 |
| Config management module | PRESENT -- utils/config.py (Phase 5B.3) |
| Logging framework | PRESENT -- utils/logging_utils.py (Phase 5B.3) |

---

## 12. API Layer (Phase 5B.5)

| File | Role | Status |
|---|---|---|
| api/__init__.py | Package marker | Present |
| api/schemas.py | Pydantic v2 request/response models, CLAIM_SAFETY_NOTE | Present |
| api/service.py | Adapter functions: load_verified_metrics, list_evidence_files, run_validation_pipeline | Present |
| api/main.py | FastAPI app: GET /health, GET /metrics, GET /evidence, POST /validate, GET /governance/latest, GET /governance/history | Present -- updated Phase 5B.6B |
