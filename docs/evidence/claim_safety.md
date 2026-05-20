# AgentX Risk Validator -- Claim Safety Assessment
Last updated: 2026-05-20 (Phase 5B.8)

This document defines what can be stated truthfully about AgentX, and what must not be claimed until specific evidence exists.

---

## Phase 5B.1 Update

The model pipeline inconsistency (GAP-004) has been resolved. Verified metrics are now available in:
- `docs/evidence/verified_metrics.json`
- `docs/evidence/verified_metrics.md`

**Prior metrics are invalidated:**
- ROC-AUC 0.668 from `reports/validation_report.md` (old run, inconsistent pipeline)
- ROC-AUC 0.333 from old `data/validation_outputs/performance_metrics.json` (pipeline mismatch)

**Only cite numbers from `docs/evidence/verified_metrics.md` (generated 2026-05-19).**

---

## Section 1: Claims That Are Safe Today

**About the system:**
- "AgentX is a multi-agent autonomous risk model validation system built in Python."
- "AgentX includes six specialized agents: Data Validation, Model Performance, Explainability, Compliance, Drift Detection, and Feedback Memory."
- "The system validates credit risk models against the LendingClub public dataset (5,000 rows, 2007-2018)."
- "AgentX integrates SHAP for model explainability, producing feature importance vectors and summary plots."
- "AgentX uses FAISS vector memory to store SHAP fingerprints and retrieve historically similar models by cosine similarity."
- "AgentX includes a compliance agent that generates regulatory checklist reports referencing SR 11-7 and Basel IV principles."
- "AgentX detects feature distribution shift using Kolmogorov-Smirnov tests, with results showing drift in annual_inc and loan_amnt under simulated conditions."
- "AgentX includes a Streamlit frontend with 8 pages: upload, portfolio overview, performance, explainability, compliance, drift detection, report export, and model comparison."
- "The system generates Markdown and PDF validation reports."
- "The compliance agent uses a Groq-hosted large language model with a structured fallback mechanism."
- "The .env file is protected by .gitignore; credentials will not be accidentally committed."
- "AgentX exposes a local FastAPI service boundary with six endpoints: GET /health, GET /metrics, GET /evidence, POST /validate, GET /governance/latest, and GET /governance/history."
- "The FastAPI boundary is covered by 41 pytest tests including ROC-AUC regression guards."
- "AgentX is packaged as a Docker image (python:3.11-slim, port 8000) for reproducible local execution."
- "The Docker image was built and tested locally; GET /health and GET /metrics return correct verified values."
- "AgentX has a benchmark script (scripts/benchmark_agentx.py) that measures in-process TestClient latency for all four FastAPI endpoints and full pipeline runtime."
- "GET /health and GET /metrics return in under 3ms median on a local development machine (in-process TestClient, not network)."
- "POST /validate (full pipeline) completes in approximately 2.4 seconds median on a local development machine."
- "All 8 expected artifacts are generated and non-empty after a pipeline run, confirmed by benchmark artifact check."
- "AgentX writes a structured governance validation-run record on each pipeline run, including run ID, metrics snapshot, drift status, compliance status, artifact status, risk flags, and claim-safety note."
- "Governance records are accessible via GET /governance/latest and GET /governance/history API endpoints."
- "The governance layer is a local development evidence tool. It is not a regulatory audit system or enterprise governance platform."
- "237 pytest tests passing as of Phase 5B.8 (212 prior + 25 new MLflow tracking tests)."
- "The compliance agent is now grounded in local validation evidence. The LLM prompt and fallback advisory cite actual ROC-AUC (0.6776), recall (0.037), class balance, drift status, and governance run ID."
- "Compliance advisory output includes advisory_only: True and not_regulatory_approval: True fields in the saved JSON record."
- "Each AgentX pipeline run logs verified metrics, validation parameters, and evidence artifacts to a local MLflow file store (mlruns/). Experiment: agentx_risk_validation."
- "MLflow tracking is local development only. No remote server, no model registry, no production MLflow deployment."
- "MLflow tracking failure does not affect pipeline execution. It is wrapped in a try/except block and appended to warnings if it fails."
- "The git repository was initialized in Phase 5B.7. First commit: 37bbb68."

**About the dataset:**
- "The system was developed using the LendingClub public loan dataset, filtered to binary classification: Fully Paid vs Charged Off."
- "The sample contains 5,000 rows, 12 features used for modeling, 81% non-default / 19% default class balance."
- "The dataset has zero missing values and zero duplicates after preprocessing."

**About the model (verified 2026-05-19):**
- "The baseline model is a scikit-learn Pipeline (StandardScaler + LogisticRegression) trained on credit features."
- "The model artifact includes the scaler and classifier in a single .pkl file, ensuring consistent preprocessing between training and inference."
- "Verified ROC-AUC: 0.6776 on a held-out 20% test set (1,000 rows), stratified split, random_state=42."
- "Verified accuracy: 0.804 (note: reflects class imbalance -- 81% non-default)."
- "Precision: 0.35, Recall: 0.037, F1: 0.067 (low recall reflects default class imbalance; no class weighting applied to the baseline model)."

**Metric interpretation note:**
The low recall and F1 are expected for a non-weighted logistic regression on an 81/19 imbalanced dataset. The ROC-AUC (0.6776) is the appropriate metric to cite as it is threshold-independent and class-imbalance robust. The system is designed to validate models, not to optimize model performance.

---

## Section 2: Claims That Must NOT Be Made

**Do not claim:**
- Any metric number other than those in `docs/evidence/verified_metrics.md`.
- "High recall" or "strong F1" -- the baseline model does not achieve this due to class imbalance.
- "Production deployment" -- the system has not been deployed to any server.
- "Enterprise adoption" -- no organization has adopted or licensed this system.
- "Customer usage" -- no external users have used this system.
- "Regulatory approval" -- no regulator has reviewed or approved this system.
- "Live banking use" -- this system has not been used in any banking operation.
- "Real-time monitoring" -- drift detection operates on static file comparison, not live data streams.
- "RAG-based compliance" -- the compliance agent uses static prompts, not retrieval-augmented generation.
- "Tested and validated pipeline" -- NOW SAFE. See test_suite_report.md.
- "Dockerized and deployable for local development" -- NOW SAFE. See api_boundary_report.md.
- "FastAPI-served (local development boundary)" -- NOW SAFE. See api_boundary_report.md.
- "Production deployed" -- the Docker image is local only; not published to any registry.
- "Enterprise deployed" -- not claimed.
- "Regulatory approved" -- not claimed.

---

## Section 3: Claims That Become Safe After Specific Upgrades

| Claim | Prerequisite |
|---|---|
| "Fully tested agent pipeline" | UNLOCKED (Phase 5B.4): 111 passing pytest tests (85 prior + 26 API) |
| "Containerized and reproducible" | UNLOCKED (Phase 5B.5): Dockerfile built and verified locally |
| "FastAPI serving boundary" | UNLOCKED (Phase 5B.5): GET /health, /metrics, /evidence, POST /validate |
| "Measured local performance" | UNLOCKED (Phase 5B.6A): benchmark_results.json with endpoint and pipeline latencies |
| "Local governance evidence layer" | UNLOCKED (Phase 5B.6B): validation-run record per pipeline run; GET /governance/latest and GET /governance/history API endpoints |
| "173 passing pytest tests" | UNLOCKED (Phase 5B.6B): governance utility and API endpoint tests added |
| "Model-specific compliance assessment" | UNLOCKED (Phase 5B.6C): compliance prompt grounded in actual model metrics |
| "Local MLflow validation tracking" | UNLOCKED (Phase 5B.8): local file-based MLflow tracking wired into pipeline |

---

## Section 4: Data Privacy Assessment

**Dataset used:** LendingClub public dataset (accepted_2007_to_2018Q4.csv)
- Publicly available, anonymized dataset widely used in ML research.
- No PII in the 12 features used for modeling.
- Features: loan_amnt, term, int_rate, grade, emp_length, home_ownership, annual_inc, purpose, dti, delinq_2yrs, revol_util, total_acc.

**Residual risks (managed):**
- Full dataset file (accepted_2007_to_2018Q4.csv) is excluded from git by .gitignore.
- Groq API key in .env is excluded from git by .gitignore. Owner must rotate before git init or public share.
