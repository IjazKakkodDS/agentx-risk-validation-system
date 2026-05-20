# AgentX Risk Validator -- Portfolio Positioning Draft
Last updated: 2026-05-20 (Phase 5B.9)
Status: DRAFT -- All 15 engineering gaps closed. 268 tests passing. Portable audit pack added.
Waves 1, 2, 3, 4, 5, and 6 are complete. All P1/P2/P3 gaps resolved.

---

## Positioning Statement (Claim-Safe)

AgentX is an autonomous multi-agent system for validating machine learning credit risk
models against regulatory and governance standards. It was built to demonstrate practical
application of agentic AI architecture in a risk-sensitive domain, integrating data
quality validation, model performance benchmarking, SHAP explainability, LLM-based
compliance review, statistical drift detection, FAISS vector memory, and structured
governance reporting.

The system accepts a credit portfolio dataset, runs it through a seven-agent validation
pipeline, and produces structured outputs covering data quality, model performance,
explainability, regulatory compliance, and feature drift detection.

This is a local research and active engineering portfolio project. It is not production
deployed and does not constitute regulatory approval.

---

## What This Project Demonstrates

**Multi-Agent System Design**

Seven agents with clearly separated concerns operate sequentially, each producing
structured JSON output consumed by downstream steps and the report generator. Agent
interfaces are individually invokable and produce consistent outputs across both the
CLI pipeline, the Streamlit dashboard, and the FastAPI local service boundary.

**Applied Explainability**

The Explainability Agent computes SHAP values for each prediction, produces a global
feature importance summary plot, and stores a normalized mean SHAP vector as a FAISS
embedding for model memory and similarity retrieval. This enables comparison of how
feature importance patterns shift across model versions over time.

**LLM Integration with Evidence-Grounded Compliance Review**

The Compliance Agent queries a Groq-hosted language model to generate a structured
regulatory checklist referencing SR 11-7 and Basel governance principles. As of Phase
5B.6C, the LLM system prompt is grounded in actual validation evidence: the current
run's ROC-AUC (0.6776), recall, class balance, drift status, governance run ID, and
artifact inventory. A deterministic fallback advisory using the same evidence values
activates automatically when the API is unavailable, ensuring the pipeline always
completes regardless of connectivity. All compliance output is advisory only.

**Feature Drift Detection**

The Drift Monitor Agent applies Kolmogorov-Smirnov two-sample tests across all numeric
features, comparing a reference dataset to an incoming dataset. Drift in `annual_inc`
and `loan_amnt` was confirmed under simulated conditions (p-value = 0.0 for both).

**Vector Memory for Model Governance**

FAISS is used as a lightweight vector memory store. Each validation run stores a
normalized SHAP fingerprint. The system retrieves historically similar models by
cosine similarity, supporting model lineage tracking across validation cycles.

**Interactive Validation Dashboard**

A Streamlit application provides an 8-page validation interface: data upload and
preview, portfolio overview, performance curves with threshold control, SHAP
explainability visualization, compliance report, drift detection by feature,
PDF report export with selectable sections, and model comparison upload.

**Regulatory Framework Awareness**

Reference documents for SR 11-7 (Federal Reserve model risk management guidance)
and Basel IV model validation principles are included under `docs/`. The compliance
agent references these frameworks in its LLM prompts.

**Verified, Reproducible Metrics**

The model pipeline was corrected in Phase 5B.1. Prior contradictory results were
diagnosed, root-caused, and invalidated. Verified metrics from a single consistent
pipeline are documented in `docs/evidence/verified_metrics.md`.

---

## Verified Metrics (Phase 5B.1, citable)

| Metric | Value |
|---|---|
| ROC-AUC | 0.6776 |
| Accuracy | 0.804 |
| Precision | 0.350 |
| Recall | 0.037 |
| F1 Score | 0.067 |

Model: `Pipeline(StandardScaler + LogisticRegression)`.
Dataset: LendingClub public loan data, 5,000 rows, 12 features, 81/19 class balance.
Split: 80/20 stratified, random_state=42, scaler fit on train only.

Note: ROC-AUC is the preferred citation metric. Accuracy reflects class imbalance.
Recall is a documented baseline limitation; class-weighted and tree-based models
are planned product modules.

---

## Dataset Context

Developed using the LendingClub public loan dataset (2007-2018). Filtered to binary
classification: Fully Paid vs Charged Off. Working sample: 5,000 rows, 12 features.
Widely used public benchmark dataset in credit risk ML research. No PII in the
features used.

---

## Honest Limitations

These must be included in any portfolio presentation of AgentX:

- The system operates on a 5,000-row public sample, not live portfolio data.
- The baseline model is a LogisticRegression pipeline. It is the validation target,
  not a production credit scoring model.
- Compliance outputs are illustrative examples of regulatory checklist automation,
  not actual regulatory assessments.
- The compliance review is advisory only; it is not a regulatory determination.
- The system operates on a 5,000-row public sample, not live portfolio data.
- The system has not been deployed to any production environment.
- No organization has adopted or validated this system for operational use.
- The system has been committed to a local git repository (Phase 5B.7). No remote push yet.
- MLflow tracking is local file-based only. No remote server, model registry, or production MLflow deployment.
- The Docker image is local only; it is not published to any registry.

---

## Appropriate Portfolio Framing

**Appropriate to say:**

"Designed and built a seven-agent autonomous model validation system for credit risk,
integrating SHAP explainability, FAISS vector memory, Groq LLM compliance reporting,
and KS-test drift detection. Verified baseline ROC-AUC: 0.6776 on a held-out test set."

"Implemented a model governance pipeline covering data validation, performance
benchmarking, SHAP explainability, regulatory compliance review, drift monitoring,
and FAISS-based feedback memory."

"Built an 8-page Streamlit dashboard for model risk analysts to upload portfolios,
review validation results across all agent outputs, and export compliance reports as PDF."

"Engineered a reproducible model training and evaluation Pipeline using sklearn,
diagnosing and fixing a prior train/eval preprocessing inconsistency that was producing
misleading results."

"Added a FastAPI local service boundary with six endpoints (GET /health, GET /metrics,
GET /evidence, POST /validate, GET /governance/latest, GET /governance/history), packaged
as a Docker container, and covered with 41 pytest tests including ROC-AUC regression guards."

"Added a benchmark script (scripts/benchmark_agentx.py) measuring in-process TestClient
latency for all four FastAPI endpoints and full pipeline runtime, with results saved as
machine-readable JSON and human-readable Markdown evidence. GET /health median: 1.9ms,
POST /validate median: 2.4 seconds on a local development machine."

"Built a local governance evidence layer that writes a structured JSON validation-run
record on each pipeline run, including run ID, metrics snapshot, drift status, compliance
status, artifact inventory, risk flags, reviewer_status placeholder, and claim-safety note.
Records are accessible via GET /governance/latest and GET /governance/history API endpoints."

"Upgraded the compliance agent so its advisory review is grounded in actual validation
evidence from the current pipeline run. The LLM system prompt includes the verified ROC-AUC
(0.6776), recall, class balance, drift status, governance run ID, and artifact inventory.
The fallback advisory path uses the same evidence values when the API is unavailable."

"Added local MLflow file-based tracking to each pipeline run. Each run logs 5 metrics
(ROC-AUC, accuracy, precision, recall, F1), 8 validation parameters, and up to 8 evidence
artifacts to a local mlruns/ file store. Experiment: agentx_risk_validation. Tracking
failure is caught and does not stop the pipeline. 237 pytest tests passing."

**Not appropriate yet:**

- "Deployed in production"
- "Used by financial institutions"
- "Validated by regulators"
- "High-recall default detection"
- "Complete MRM platform"
- "Remote MLflow server or model registry" (local file tracking only)

---

## Roadmap for Stronger Positioning

AgentX is becoming portfolio-ready after each of the following engineering waves:

| After completing | Positioning unlocks |
|---|---|
| Wave 3 (code quality) -- DONE | "Config-driven codebase, structured logging, no dead code" |
| Wave 4 (test suite) -- DONE | "111 passing pytest tests, ROC-AUC regression guard at 0.6776" |
| Wave 5 (Docker + FastAPI) -- DONE | "Containerized, API-served validation engine (local development)" |
| Wave 6 benchmark (6A) -- DONE | "Measured local performance evidence: benchmark_results.json and benchmark_report.md" |
| Wave 6 governance evidence (6B) -- DONE | "Local governance evidence layer: run record per pipeline run; GET /governance endpoints" |
| Wave 6 compliance grounding (6C) -- DONE | "Evidence-grounded compliance advisory; 212 passing tests" |
| Wave 6 MLflow (5B.8) -- DONE | "Local MLflow-tracked validation runs; 237 passing tests" |
| Wave 6 Audit pack (5B.9) -- DONE | "Portable audit pack (MD/HTML/PDF via fpdf2+markdown2); 268 passing tests; all 15 gaps closed" |
| Portfolio summary doc | Elite-tier portfolio case study ready for public sharing after owner review |
