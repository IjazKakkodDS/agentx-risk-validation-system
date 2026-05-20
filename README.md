# AgentX: Autonomous Risk Model Validation Assistant

> An engineered multi-agent pipeline for model validation, explainability, drift detection,
> compliance review, feedback memory, and governance reporting in financial-risk contexts.

---

## Executive Summary

AgentX is being engineered as a modular, multi-agent model validation assistant for
financial-risk workflows. It automates first-pass model review across six domains:
data quality validation, model performance benchmarking, SHAP-based explainability,
regulatory compliance review, statistical drift detection, and vector-based feedback
memory with historical run comparison.

This is a local research and portfolio system under active engineering development.
It is not a production regulatory platform and does not constitute regulatory approval.
The engineering roadmap is structured to grow AgentX toward a governance-grade
validation tool through a series of planned product modules described later in this README.

---

## Business Problem

Financial institutions are required by regulation and internal governance policies to
validate credit, market, and operational risk models before deployment and on an ongoing
basis. A standard model review process covers:

- input data quality and class balance
- discriminatory power (AUC, accuracy, stability)
- feature attribution and explainability
- alignment with regulatory frameworks such as SR 11-7 and Basel principles
- feature distribution shift over time
- documentation and audit-ready evidence

When done manually, these steps can be slow, inconsistent across reviewers, and
difficult to scale across a growing model inventory. AgentX demonstrates an
automated first-pass validation workflow that produces reproducible, structured outputs
for each run, organized by agent and persisted as JSON and Markdown evidence files.

The long-term product goal is to support faster, more consistent, and more auditable
model review workflows, not to replace independent validation judgment but to accelerate
and standardize the evidence-gathering phase.

---

## Target Users

| Role | Relevance |
|---|---|
| Model validation teams | Primary: run AgentX as automated pre-review layer |
| Model risk management teams | Review governance outputs and evidence files |
| Risk analytics teams | Inspect performance metrics, drift reports, SHAP outputs |
| Data science teams | Use AgentX outputs to prepare models for formal review |
| Compliance and audit stakeholders | Reference compliance checklist and regulatory context |
| Technical reviewers | Assess model governance workflow design and tooling |

---

## System Architecture

```
Input: CSV data file (uploaded or CLI path)
  |
  v
Preprocessing and target encoding
  utils/load_data.py
  - Drop ID columns
  - Impute numeric with median
  - LabelEncode categoricals
  - Encode loan_status to 0/1
  - StandardScaler applied inside model Pipeline (no leakage)
  |
  v
Model Training Pipeline
  utils/model_utils.py
  Pipeline(StandardScaler + LogisticRegression)
  Saved as single artifact with scaler included
  |
  v
+----------------------------------------------------------+
|                       Agent Layer                        |
+----------------------------------------------------------+
|  DataValidatorAgent     -> data_validation.json          |
|  PerformanceAgent       -> performance_metrics.json      |
|  ExplainabilityAgent    -> shap_summary.png + vector     |
|  ComplianceAgent        -> last_compliance.json          |
|  DriftMonitorAgent      -> drift_report.json             |
|  FeedbackMemoryAgent    -> FAISS index (model_memory/)   |
|  ReportWriterAgent      -> validation_report.md          |
+----------------------------------------------------------+
  |
  v
Verified evidence docs
  docs/evidence/verified_metrics.md
  docs/evidence/verified_metrics.json
  |
  v
Governance evidence layer
  utils/governance.py -- validation-run record written on each pipeline run
  data/governance/latest_validation_run.json
  data/governance/validation_runs/{run_id}.json
  |
  v
Streamlit validation dashboard
  streamlit_app.py -- 8-page interactive interface
  |
  v
FastAPI local service boundary
  api/main.py -- GET /health, GET /metrics, GET /evidence, POST /validate
              -- GET /governance/latest, GET /governance/history
  Docker: agentx-risk-validator (python:3.11-slim, port 8000)
```

**Entry points:**

| Path | Command |
|---|---|
| CLI pipeline | `python main.py` |
| Interactive dashboard | `streamlit run streamlit_app.py` |
| Local API service | `uvicorn api.main:app --host 0.0.0.0 --port 8000` |
| Docker container | `docker run --rm -p 8000:8000 agentx-risk-validator` |

---

## Agent Layer

| Agent | Purpose | Status | Evidence output |
|---|---|---|---|
| DataValidatorAgent | Missing values, duplicates, class distribution, summary statistics | Functional | `data/validation_outputs/data_validation.json` |
| PerformanceAgent | Accuracy, precision, recall, F1, ROC-AUC, confusion matrix | Functional | `data/validation_outputs/performance_metrics.json` |
| ExplainabilityAgent | SHAP values, mean feature importance vector, normalized FAISS embedding | Functional | `data/validation_outputs/shap_summary.png` |
| ComplianceAgent | Advisory compliance review grounded in actual model evidence (ROC-AUC, recall, drift, governance run ID); Groq LLM with grounded fallback advisory | Functional (requires configured Groq key; grounded fallback advisory available without key) | `data/validation_outputs/last_compliance.json` |
| DriftMonitorAgent | Kolmogorov-Smirnov test per numeric feature vs reference dataset | Functional | `data/validation_outputs/drift_report.json` |
| FeedbackMemoryAgent | FAISS inner-product vector store; stores normalized SHAP vectors and retrieves historically similar models | Functional | `data/model_memory/` |
| ReportWriterAgent | Generates Markdown validation report combining all agent outputs | Functional | `reports/validation_report.md` |

---

## Verified Model Evidence

Metrics from Phase 5B.1 -- first pipeline-consistent, reproducible run.
Generated 2026-05-19.

| Attribute | Value |
|---|---|
| Dataset | LendingClub public loan data (2007-2018Q4 sample) |
| Total rows | 5,000 |
| Features used | 12 |
| Target | `loan_status` (0 = Fully Paid, 1 = Charged Off) |
| Class balance | 81.0% non-default / 19.0% default |
| Train rows | 4,000 (stratified 80/20 split) |
| Test rows | 1,000 |
| Model | `Pipeline(StandardScaler + LogisticRegression(max_iter=1000))` |

| Metric | Value |
|---|---|
| ROC-AUC | 0.6776 |
| Accuracy | 0.804 |
| Precision | 0.350 |
| Recall | 0.037 |
| F1 Score | 0.067 |

**Interpretation note:**

Accuracy of 0.804 should not be overinterpreted. It mostly reflects the 81% majority
class -- a classifier that always predicts "Fully Paid" would score 0.81 accuracy.
ROC-AUC of 0.6776 is the preferred headline validation metric because it is
threshold-independent and resistant to class imbalance.

Recall of 0.037 is low and is documented as a known limitation of the non-weighted
baseline LogisticRegression on an imbalanced target. Improving recall through
class-weighted or tree-based models is a planned product module described in the
engineering roadmap. AgentX is designed to validate models, not to deliver the
optimal classifier.

Full details: `docs/evidence/verified_metrics.md`

---

## Explainability and Feedback Memory

AgentX uses SHAP (SHapley Additive exPlanations) to compute per-prediction feature
attribution values. The mean SHAP vector across a sample is normalized and stored in a
FAISS inner-product index as a model fingerprint.

On each validation run, the system searches for historically similar models in the
FAISS store by cosine similarity. This feedback memory layer supports:

- tracking how feature importance shifts across model versions
- identifying whether a new submission behaves similarly to previously validated models
- building a model lineage record across validation cycles

The SHAP summary plot is saved locally to `data/validation_outputs/shap_summary.png`
and displayed in the Streamlit dashboard Explainability page.

No claim of production model approval is made. The feedback memory layer is a
local research implementation and is planned to evolve into a full historical
validation-run comparison system.

---

## Compliance Review

The Compliance Agent uses a Groq-hosted large language model to produce an advisory
compliance review grounded in actual AgentX validation evidence. Each review includes
the verified ROC-AUC, recall, class balance, drift status, governance run ID, and
artifact status from the current pipeline run.

Behavior:
- When a valid Groq API key is configured via `.env`, the agent builds a structured
  evidence context and passes it to the LLM as the system prompt.
- When no key is present or the API is unavailable, the agent produces a grounded
  local fallback advisory using the same evidence context.
- Both paths cite actual model evidence values; neither produces generic commentary.

**Important limitations:**

The compliance output is advisory and illustrative. It does not constitute regulatory
approval, regulatory certification, or a production compliance determination.
The LLM prompt is grounded in local validation evidence as of Phase 5B.6C.
The agent does not have access to live production data or regulatory databases.

Reference documents:
- `docs/sr11_7_summary.md` -- Federal Reserve SR 11-7 model risk management principles
- `docs/basel_guidelines_summary.md` -- Basel IV model validation scope and standards

Groq API key setup: copy `.env.example` to `.env` and add your key. Never commit `.env`.

---

## Drift Monitoring

The Drift Monitor Agent applies the Kolmogorov-Smirnov two-sample test to each numeric
feature, comparing the reference dataset against an incoming dataset. Features where
the KS p-value falls below the 0.05 threshold are flagged as drifted.

A simulated drift dataset is included at `data/drift_test/incoming_drifted_data.csv`.
It was generated by inflating `annual_inc` and shifting `loan_amnt` distributions, and
by dropping `int_rate`. The drift report confirms detection of drift in `annual_inc`
and `loan_amnt` under these simulated conditions.

Drift results are written to `data/validation_outputs/drift_report.json` and
visualized in the Streamlit dashboard Drift Detection page.

Planned product module: drift-triggered automatic revalidation, where a detected
drift event initiates a new end-to-end validation pipeline run with a change event
log entry.

---

## How to Run Locally

**1. Set up environment**

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

**2. Configure environment variables**

```bash
cp .env.example .env
# Open .env and add your Groq API key if using the compliance agent.
# The pipeline runs without a key using the fallback compliance response.
```

Never commit `.env`. It is excluded from git by `.gitignore`.

**3. Prepare sample data**

The cleaned sample (5,000 rows) is included at
`data/raw_data/lending_club_clean_sample.csv`.

To regenerate from the full LendingClub dataset:
```bash
python create_sample_data.py
```

To regenerate the simulated drift dataset:
```bash
python simulate_drift.py
```

**4. Run the CLI pipeline**

```bash
python main.py
```

This runs all seven agents, writes validation outputs to `data/validation_outputs/`,
and writes verified metrics to `docs/evidence/`.

**5. Run the interactive dashboard**

```bash
streamlit run streamlit_app.py
```

Opens an 8-page validation dashboard in the browser:

| Page | Content |
|---|---|
| 1. Upload and Preview | CSV upload, column validation, data filtering |
| 2. Overview | Portfolio summary, loan distribution, grade breakdown |
| 3. Performance | ROC curve, threshold slider, confusion matrix |
| 4. Explainability | SHAP global importance, nearest historical models |
| 5. Compliance | LLM compliance checklist and executive summary |
| 6. Drift | KS drift detection by feature, pie chart, table |
| 7. Export | PDF report generation with selectable sections |
| 8. Compare Models | Upload a second model and compare metrics side by side |

---

## FastAPI Local Service Boundary

AgentX exposes a local REST API implemented with FastAPI. This boundary provides
programmatic access to validation workflows and evidence for development and
portfolio integration testing. It is not a production deployment and does not
constitute regulatory approval.

**Start the API server:**

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**Endpoints:**

| Method | Path | Description | Notes |
|---|---|---|---|
| GET | /health | Service liveness check | Fast; no pipeline; returns system name, version, file availability |
| GET | /metrics | Read verified model metrics from docs/evidence/verified_metrics.json | Returns 503 if metrics file not yet generated (run `python main.py` first) |
| GET | /evidence | List evidence files and artifact status | Fast; no pipeline; includes governance_available flag |
| POST | /validate | Run the full validation pipeline | 10-30 seconds; returns metrics, artifact list, warnings |
| GET | /governance/latest | Latest validation-run governance record | Returns 503 if no pipeline run yet |
| GET | /governance/history | List of recent validation-run summaries | Always 200; empty list if no records |

**Example -- health check:**

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok", "system": "AgentX Risk Validator", "version": "1.0.0", "metrics_available": true, "evidence_available": true}
```

**Example -- trigger validation:**

```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{"run_compliance_agent": false, "run_drift_monitor": true, "regenerate_reports": true}'
```

Set `run_compliance_agent` to `true` when `GROQ_API_KEY` is configured. The pipeline
falls back to a cached compliance response when the key is absent.

All six endpoints are tested in `tests/test_api.py` (41 tests). See `api/` for
schemas and service functions, `docs/evidence/api_boundary_report.md` for the
API boundary implementation report, and `docs/evidence/governance_evidence_report.md`
for the governance layer documentation.

---

## Docker

AgentX can be built and run as a Docker container for reproducible local development.
The container serves the FastAPI boundary on port 8000.

**Build:**

```bash
docker build -t agentx-risk-validator .
```

**Run:**

```bash
docker run --rm -p 8000:8000 agentx-risk-validator
```

**Run with Groq API key for compliance agent:**

```bash
docker run --rm -p 8000:8000 --env-file .env agentx-risk-validator
```

The `.env` file is excluded from the container image via `.dockerignore`. Generated
artifacts (reports, logs) are written to the container filesystem and are ephemeral
unless a volume is mounted.

This is a local development container. It is not published to any registry and is
not a production deployment.

---

## Benchmark

AgentX includes a benchmark script that measures in-process local development
performance for all four FastAPI endpoints and the full pipeline.

**Run the benchmark:**

```bash
python scripts/benchmark_agentx.py
```

Outputs are saved to:
- `docs/evidence/benchmark_results.json` -- machine-readable results
- `docs/evidence/benchmark_report.md` -- human-readable report with disclaimer

**Measured results (local Windows machine, Python 3.13.1, Intel Core Ultra):**

| Measurement | Median | P95 | N |
|---|---|---|---|
| GET /health (in-process) | 1.9 ms | 2.4 ms | 30 |
| GET /metrics (in-process) | 2.0 ms | 2.9 ms | 30 |
| GET /evidence (in-process) | 2.5 ms | 2.9 ms | 30 |
| POST /validate (full pipeline) | 2,399 ms | -- | 3 |
| Pipeline direct call | 2,340 ms | -- | 3 |

**Important disclaimer:**

These measurements were captured on a local development machine and should not be
interpreted as production latency or cloud deployment performance. They reflect
in-process TestClient calls (no network) and are not network round-trip measurements.
No concurrency testing was performed.

---

## Evidence Files

| File | Description |
|---|---|
| `docs/evidence/verified_metrics.md` | Verified baseline metrics, Phase 5B.1 |
| `docs/evidence/verified_metrics.json` | Machine-readable version of the above |
| `docs/evidence/api_boundary_report.md` | FastAPI boundary, Docker, and API test summary, Phase 5B.5 |
| `docs/evidence/benchmark_results.json` | Machine-readable benchmark timing results, Phase 5B.6A |
| `docs/evidence/benchmark_report.md` | Human-readable benchmark report with disclaimer and limitations, Phase 5B.6A |
| `docs/evidence/governance_evidence_report.md` | Local governance evidence layer, validation-run record schema, API endpoints, Phase 5B.6B |
| `docs/evidence/compliance_grounding_report.md` | Compliance agent grounding upgrade, evidence context fields, fallback behavior, Phase 5B.6C |
| `docs/evidence/mlflow_tracking_report.md` | Local MLflow tracking configuration, metrics/params/artifacts logged, verified run, limitations, Phase 5B.8 |
| `docs/evidence/system_inventory.md` | Full file-by-file inventory of the codebase |
| `docs/evidence/architecture_audit.md` | Agent layer, data flow, architectural risk analysis |
| `docs/evidence/engineering_gap_report.md` | 15 engineering gaps with priority and status |
| `docs/evidence/metric_inconsistency_diagnosis.md` | Root cause of prior contradictory metrics |
| `docs/evidence/claim_safety.md` | What can be stated now vs what requires future evidence |
| `docs/evidence/security_review.md` | Credential and data risk assessment |
| `docs/evidence/upgrade_plan.md` | L2 upgrade wave plan with completion status |
| `docs/evidence/portfolio_positioning_draft.md` | Claim-safe portfolio framing |
| `docs/sr11_7_summary.md` | SR 11-7 model risk management reference |
| `docs/basel_guidelines_summary.md` | Basel IV model validation reference |
| `reports/validation_report.md` | Generated validation report (excluded from git) |

---

## Security Notes

- `.env` is excluded from git by `.gitignore`. It must never be committed.
- `.env.example` contains only placeholder values and is safe to commit.
- Model artifacts (`*.pkl`, `*.joblib`) are excluded from git.
- The full LendingClub dataset file is excluded from git.
- Generated reports (PDF, HTML, MD) are excluded from git.
- Git initialization is intentionally deferred until the Groq API key in `.env`
  has been rotated by the owner at `console.groq.com`.

---

## Current Limitations

These are engineering boundaries and active upgrade targets, not design defects:

| Limitation | Status |
|---|---|
| Low recall on default class | Known baseline limitation; class-weighted and tree-based models planned |
| Compliance output is advisory only | By design; grounded in local validation evidence but not a regulatory determination |
| Docker image is local only | Not published to any registry; not a production deployment |
| MLflow tracking is local file-based only | No remote server, no model registry, no production MLflow deployment |
| No regulatory approval | Not claimed; regulatory reference docs are informational |

---

## Engineering Roadmap

### Implemented

- Six-agent validation pipeline (data, performance, explainability, compliance, drift, feedback memory)
- Streamlit validation dashboard with 8 pages
- SHAP feature attribution and summary plot generation
- FAISS vector memory for model similarity and lineage tracking
- KS test drift detection with simulated drift dataset
- Compliance agent with Groq LLM and deterministic fallback
- sklearn Pipeline artifact (StandardScaler + LogisticRegression, saved with scaler)
- Stratified train/test split with fixed random state
- Verified baseline metrics documented in `docs/evidence/`
- Security hygiene: `.gitignore`, `.env.example`, `.dockerignore`, credential protection
- Markdown and PDF validation report generation
- Model comparison page in Streamlit dashboard
- `utils/config.py` for centralized path management (Phase 5B.3)
- Structured logging via Python `logging` module (Phase 5B.3)
- 237-passing pytest test suite with ROC-AUC regression guard at 0.6776 (Phases 5B.4-5B.8)
- FastAPI local service boundary: GET /health, GET /metrics, GET /evidence, POST /validate (Phase 5B.5)
- GET /governance/latest and GET /governance/history API endpoints (Phase 5B.6B)
- Docker image: `agentx-risk-validator` (python:3.11-slim, port 8000) (Phase 5B.5)
- Benchmark script with local endpoint and pipeline measurements (Phase 5B.6A)
- Local governance evidence layer: validation-run record with run ID, metrics snapshot, drift status, compliance status, risk flags, and claim-safety note (Phase 5B.6B)
- Compliance agent grounded in local validation evidence: actual ROC-AUC, recall, class balance, drift status, and governance run ID passed to LLM prompt and fallback advisory (Phase 5B.6C)
- Local MLflow file-based tracking on each pipeline run: experiment `agentx_risk_validation`, 5 metrics, 8 parameters, 8 artifacts logged per run; tracking failure does not stop pipeline (Phase 5B.8)

### Planned Product Modules

| Module | Purpose |
|---|---|
| Benchmark per-agent timing | Timing broken down by individual agent step within a single run |
| MCP governance log | Extend local governance layer to a full model-change event log |
| PDF audit pack generation | Structured multi-section report with signature block |
| Drift-triggered revalidation | Automated pipeline re-run when drift threshold is exceeded |
| Class-weighted and XGBoost models | Improved recall on the default class |
| Portfolio case study | After Wave 6 evidence is complete |

---

## Claim Safety

**Safe to state:**

- Local multi-agent model validation workflow, fully runnable
- SHAP-based explainability with FAISS vector memory
- Verified baseline ROC-AUC of 0.6776 (Phase 5B.1, reproducible)
- Streamlit dashboard with performance, explainability, compliance, and drift pages
- Security hygiene: `.gitignore`, `.env.example`, and `.dockerignore` in place
- Active engineering roadmap toward governance-grade validation tooling
- Regulatory framework awareness: SR 11-7 and Basel IV reference docs included
- FastAPI local service boundary with six endpoints, covered by 41 pytest tests
- Docker-packaged for reproducible local execution (python:3.11-slim, port 8000)
- 212 passing pytest tests including agent unit tests, pipeline integration, API boundary, benchmark, governance, and compliance context tests
- Benchmark script with measured local endpoint and pipeline latencies saved as machine-readable JSON evidence
- Local governance evidence layer: structured JSON record per run, GET /governance/latest and GET /governance/history API endpoints, 60+ governance unit tests
- Compliance agent grounded in actual model evidence: verified ROC-AUC, recall, class balance, drift status, and governance run ID used in advisory review
- Local MLflow file tracking: experiment agentx_risk_validation; 5 metrics, 8 params, 8 artifacts per run; mlruns/ excluded from git

**Not safe to state:**

- Production validation platform
- Regulatory-approved system
- Enterprise deployed
- Used by customers or financial institutions
- Live banking system
- High-recall default detection system (recall is 0.037 at baseline)
- Fully automated model approval
- Complete model risk management platform

---

## Original Vision Alignment

AgentX is being built toward a model-risk validation workflow informed by banking
governance needs. The system is designed with awareness of:

- SR 11-7 model risk management principles: independent validation, conceptual soundness,
  performance monitoring, governance and inventory
- Basel-style risk governance: discriminatory power assessment, stability testing,
  explainability, audit-ready documentation
- Validation consistency: reproducible outputs from a fixed pipeline with documented
  preprocessing, split strategy, and random state
- Audit-ready evidence: structured JSON outputs, Markdown reports, and dedicated
  evidence docs under `docs/evidence/`
- Human-in-the-loop model review: AgentX produces structured first-pass evidence;
  final validation judgment remains with the human reviewer

No regulatory compliance or approval is claimed. The system demonstrates how an
AI-assisted validation workflow can be structured to support, not replace, the
model risk management process.

---

## Dataset Citation

LendingClub Loan Data, 2007-2018Q4.
Source: Kaggle / LendingClub public loan dataset.
License: Public domain research use.
Filtered to binary classification: Fully Paid vs Charged Off.
Sample: 5,000 rows drawn with `random_state=42`.

No personally identifiable information is present in the 12 features used.

---

## Key Dependencies

| Package | Purpose |
|---|---|
| scikit-learn | Model pipeline, preprocessing, metrics |
| shap | Feature attribution and explainability |
| faiss-cpu | Vector memory and similarity search |
| scipy | Kolmogorov-Smirnov drift test |
| streamlit | Interactive validation dashboard |
| groq | LLM compliance agent |
| fpdf2 | In-browser PDF report generation |
| plotly | Interactive charts in dashboard |
| python-dotenv | Environment variable management |
| joblib | Model artifact serialization |
| fastapi | REST API boundary for local validation service |
| uvicorn | ASGI server for FastAPI |
| httpx | HTTP client for FastAPI TestClient in tests |
| pydantic | Request/response validation and serialization |

Full list: `requirements.txt`
