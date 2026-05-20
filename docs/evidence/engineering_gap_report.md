# AgentX Risk Validator -- Engineering Gap Report
Audit date: 2026-05-19
Priority: P1 = must fix before portfolio claim, P2 = needed for elite maturity, P3 = enhancement

---

## GAP-001 [P1] -- No git repository initialized

**Observed:** The project directory has no .git folder. There is no version control.
**Impact:** No history, no branching, no diff, no rollback. Cannot demonstrate professional engineering discipline.
**Fix:** `git init`, create .gitignore, make initial commit.

---

## GAP-002 [P1] -- Live API key exposed in .env with no .gitignore

**Observed:** `.env` contains a Groq API key in plaintext. No `.gitignore` file exists. If git is initialized without first adding a .gitignore, the key will be committed and potentially exposed.
**Impact:** Credential exposure, potential billing abuse. Security disqualifier for any portfolio review.
**Fix:** Create .gitignore immediately (include `.env`, `*.pkl`, large CSVs, `__pycache__`). Rotate the Groq API key. Add `.env.example` with placeholder values.

---

## GAP-003 [P1] -- README.md is empty

**Observed:** README.md contains 1 blank line. No project description, no architecture diagram, no quickstart, no agent descriptions.
**Impact:** Any reviewer opening the repo sees nothing. Zero portfolio value without a README.
**Fix:** Write a professional README covering: what AgentX does, architecture diagram, agent descriptions, quickstart steps, dataset info, key results.

---

## GAP-004 [P1] -- Model performance inconsistency (ROC-AUC 0.333 vs 0.668)

**Observed:** `reports/validation_report.md` records ROC-AUC=0.668. `data/validation_outputs/performance_metrics.json` records ROC-AUC=0.333 (accuracy=0.486, below random).
**Root cause hypothesis:** The model was trained on raw label-encoded data via `model_utils.train_model()`. The JSON metrics reflect evaluation on StandardScaled data via `preprocess_uploaded_data()`. The model has never seen scaled inputs, so predictions are near-random on scaled test data.
**Impact:** The system currently produces misleading performance metrics. Cannot claim any model validation result without resolving this.
**Fix:** Either (a) retrain model with the same preprocessing applied, saving both the model and scaler together, or (b) evaluate model on the same preprocessing used during training. Build a unified preprocessing pipeline that is consistent between train and evaluation.

---

## GAP-005 [P1] -- No test suite

**Observed:** Zero test files. No pytest, unittest, or any test framework.
**Impact:** Cannot verify agent behavior. No regression protection. Portfolio claim of "production-grade" or "validated" system cannot be made.
**Fix:** Add tests/test_agents.py covering at minimum: DataValidatorAgent output schema, PerformanceAgent metric ranges, DriftAgent on known data, FeedbackMemoryAgent vector storage and retrieval.

---

## GAP-006 [P2] -- No Dockerfile or containerization [CLOSED -- Phase 5B.5]

**Observed:** No Dockerfile, no docker-compose.yml. generate_pdf.py has a hardcoded Windows path to wkhtmltopdf.
**Impact:** System cannot be reproduced on another machine without manual environment setup. Not deployment-ready.
**Resolution (Phase 5B.5):** Dockerfile created at project root. Base: python:3.11-slim. System deps: gcc, g++, libgomp1. .dockerignore excludes .env, large CSV, caches, logs. Exposes port 8000. Serves the FastAPI boundary via uvicorn. Verified: docker build and container test confirming GET /health and GET /metrics return correct values.

---

## GAP-007 [P2] -- No FastAPI serving boundary [CLOSED -- Phase 5B.5]

**Observed:** FastAPI and uvicorn are in requirements.txt but no API implementation exists.
**Impact:** The system is run only as a Streamlit app or CLI script. No programmatic API surface for integration.
**Resolution (Phase 5B.5):** api/ package created with schemas.py (Pydantic v2 models), service.py (adapter functions), and main.py (FastAPI app). Four endpoints: GET /health, GET /metrics, GET /evidence, POST /validate. 26 pytest tests in tests/test_api.py. main.py refactored to callable run_agentx_pipeline() so the API can invoke it without triggering a training run at startup.

---

## GAP-008 [P2] -- Compliance agent generates non-model-specific outputs [CLOSED -- Phase 5B.6C]

**Observed:** compliance_agent.py sends static prompts to Groq and returns a generic banking compliance checklist. It does not read model outputs, dataset statistics, or validation results.
**Impact:** The compliance section of the report is not grounded in the actual model being validated. It cannot be claimed as "model-specific compliance assessment."
**Resolution (Phase 5B.6C):** utils/compliance_context.py created with 7 functions that load local validation artifacts (verified_metrics.json, drift_report.json, governance record, benchmark_results.json) and assemble a structured evidence context dict. compliance_agent.py now injects this context into the Groq system prompt, instructing the LLM to cite actual ROC-AUC, recall, class balance, and drift status. The fallback advisory also uses real evidence values. main.py builds the context from the live performance_report before calling the compliance agent. 39 new tests in tests/test_compliance_context.py. Compliance output remains advisory only and does not constitute regulatory approval.

---

## GAP-009 [P2] -- Duplicate implementations

**Observed:**
- Two FAISS stores: `utils/vector_store.py` (IndexFlatL2) and `agents/feedback_memory_agent.py` (IndexFlatIP). Different index types, different paths, no cross-reference.
- Two report writers: `reports/generate_report.py` (minimal) and `agents/report_writer_agent.py` (richer). `main.py` imports from `reports/generate_report.py` but the Streamlit app does not use either.
**Impact:** Maintenance confusion, divergent behavior, wasted code.
**Fix:** Consolidate to one FAISS store module and one report writer. Delete the stubs.

---

## GAP-010 [P2] -- Empty stub files

**Observed:** Three files are empty:
- `utils/shap_explainer.py` (1 blank line)
- `utils/model_metrics.py` (1 blank line)
- `frontend/app_ui.py` (1 blank line)
**Impact:** Suggests abandoned or planned-but-not-built code. Creates confusion about the true architecture.
**Fix:** Either implement them or delete them. If `streamlit_app.py` is the UI, delete `frontend/app_ui.py`.

---

## GAP-011 [P2] -- No config management

**Observed:** File paths are hardcoded across all files: `data/raw_data/...`, `data/incoming_models/...`, `data/validation_outputs/...`, `reports/`. No central config file or environment variable for paths.
**Impact:** Brittle. Any path change requires editing multiple files. Not reproducible across environments.
**Fix:** Create `config.py` or use `python-dotenv` for all configurable paths. Reference `config.py` from all agents and utils.

---

## GAP-012 [P2] -- No logging framework

**Observed:** Agents use `print()` statements. No structured logging (Python `logging` module or similar). No log levels, no timestamps in logs, no log file output.
**Impact:** Cannot diagnose issues in production. Not engineering-grade.
**Fix:** Replace print() with `logging.getLogger(__name__)` across all agents. Add a root logger configuration in main.py / app startup.

---

## GAP-013 [P3] -- No benchmark script

**Observed:** No script to run the full pipeline end-to-end and report time, memory, and metric results.
**Impact:** Cannot demonstrate system performance characteristics.
**Fix:** Add `scripts/benchmark.py` that runs the full pipeline, records timing per agent, and prints a summary table.

---

## GAP-014 [P3] -- PDF generation requires system dependency

**Observed:** `generate_pdf.py` uses pdfkit and wkhtmltopdf with a hardcoded Windows path. The Streamlit PDF (FPDF) does not have this problem.
**Impact:** generate_pdf.py fails on any system without wkhtmltopdf installed at that exact path.
**Fix:** Standardize on FPDF2 for PDF generation (already used in Streamlit). Remove pdfkit and the wkhtmltopdf dependency from the standalone script.

---

## GAP-015 [P3] -- No model versioning or governance tracking

**Observed:** The model is saved as `credit_model.pkl` with no version stamp, metadata, or MLflow tracking. MLflow is in requirements.txt but not used.
**Impact:** Cannot demonstrate model governance lifecycle.
**Fix:** Use MLflow to log each training run: parameters, metrics, model artifact. Add model_version to the validation report.

---

## Summary Table

| Gap | Priority | Category | Status |
|---|---|---|---|
| GAP-001 No git repo | P1 | Infrastructure | Open (pending owner key rotation) |
| GAP-002 Exposed API key | P1 | Security | CLOSED (Phase 5B.1 -- .gitignore created) |
| GAP-003 Empty README | P1 | Documentation | CLOSED (Phase 5B.2 -- README rewritten) |
| GAP-004 ROC-AUC inconsistency | P1 | Model correctness | CLOSED (Phase 5B.1 -- Pipeline fixed) |
| GAP-005 No tests | P1 | Quality | CLOSED (Phase 5B.4 through 5B.6C -- 212 tests passing) |
| GAP-006 No Dockerfile | P2 | Deployment | CLOSED (Phase 5B.5) |
| GAP-007 No FastAPI | P2 | Architecture | CLOSED (Phase 5B.5) |
| GAP-008 Non-grounded compliance | P2 | Agent quality | CLOSED (Phase 5B.6C) |
| GAP-009 Duplicate implementations | P2 | Code quality | CLOSED (Phase 5B.3 -- stubs deleted) |
| GAP-010 Empty stub files | P2 | Code quality | CLOSED (Phase 5B.3 -- stubs deleted) |
| GAP-011 No config management | P2 | Maintainability | CLOSED (Phase 5B.3 -- utils/config.py) |
| GAP-012 No logging framework | P2 | Observability | CLOSED (Phase 5B.3 -- utils/logging_utils.py) |
| GAP-013 No benchmark script | P3 | Evidence | CLOSED (Phase 5B.6A) |
| GAP-014 PDF system dependency | P3 | Portability | Open |
| GAP-015 No model versioning | P3 | Governance | Open (planned Wave 6) |
