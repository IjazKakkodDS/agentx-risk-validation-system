# AgentX: Autonomous Risk Model Validation Assistant -- Portfolio Summary

**Status:** DRAFT -- for future portfolio website use.
**Date:** 2026-05-20
**Version:** Phase 5B.6D
**Note:** This document is written for eventual public portfolio use. All claims are
grounded in verified local evidence. Do not publish until git is initialized and
reviewed by the owner.

---

## System Title

AgentX: Autonomous Risk Model Validation Assistant

---

## One-Paragraph Summary

AgentX is a local autonomous multi-agent system for validating machine learning credit
risk models against data quality, performance, explainability, regulatory awareness,
and feature drift criteria. It was built to demonstrate practical agentic AI
architecture in a risk-sensitive domain, integrating seven specialized agents,
a FastAPI local service boundary, SHAP explainability with FAISS vector memory,
a Groq-grounded compliance advisory, KS-test drift detection, and a local governance
evidence layer. The system accepts a credit portfolio dataset, runs it through the
full validation pipeline, and produces structured outputs covering all five validation
dimensions. It is a local engineering portfolio project; it is not production deployed,
not regulatory approved, and not enterprise deployed.

---

## Core Capabilities

| Capability | Technology | Output |
|---|---|---|
| Data quality validation | pandas | Missing values, duplicates, class distribution, summary stats |
| Model performance evaluation | scikit-learn | ROC-AUC, accuracy, precision, recall, F1, confusion matrix |
| SHAP explainability | SHAP | Global feature importance, summary plot, mean SHAP vector |
| FAISS vector memory | FAISS (IndexFlatIP) | Model similarity retrieval by normalized SHAP cosine similarity |
| Compliance advisory review | Groq LLM (llama-3.3-70b-versatile) + local evidence context | Advisory checklist referencing SR 11-7 and Basel principles |
| Feature drift detection | scipy KS test | Per-feature p-values, drift flag, drifted feature list |
| Governance evidence layer | JSON file store + FastAPI | Structured validation-run records with metrics, risk flags, artifact inventory |
| Interactive dashboard | Streamlit | 8-page validation UI with upload, charts, SHAP, compliance, PDF export |
| FastAPI local boundary | FastAPI + uvicorn | 6 REST endpoints for programmatic validation access |
| Docker packaging | python:3.11-slim | Reproducible local container deployment |

---

## Engineering Evidence

| Evidence | Status |
|---|---|
| 212 pytest tests passing (fast suite, 0 failures) | Verified 2026-05-20 |
| ROC-AUC 0.6776 locked as regression guard | Verified 2026-05-20 |
| Benchmark script with machine-readable JSON output | benchmark_results.json 2026-05-20 |
| Docker build succeeded (sha256: 858fbcfe) | Verified 2026-05-20 |
| Docker container smoke test: /health OK, /metrics ROC-AUC 0.6776 | Verified 2026-05-20 |
| claim_safety.md maintained throughout development | Up to date Phase 5B.6D |
| No em dashes in any source file | Scanned 58 files 2026-05-20 |
| .gitignore covers all sensitive and generated paths | Verified Phase 5B.6D |

---

## Model Evidence (verified 2026-05-19, citable)

| Metric | Value | Notes |
|---|---|---|
| ROC-AUC | 0.6776 | Preferred metric; threshold-independent, class-imbalance robust |
| Accuracy | 0.804 | Reflects 81/19 class imbalance; not the primary citation metric |
| Precision | 0.350 | Baseline unweighted logistic regression |
| Recall | 0.037 | Low recall expected; documented limitation |
| F1 Score | 0.067 | Reflects recall penalty from class imbalance |

Dataset: LendingClub public loan data, 5,000 rows, 12 features, 81/19 class balance.
Model: `Pipeline(StandardScaler + LogisticRegression(max_iter=1000, random_state=42))`.
Split: 80/20 stratified, random_state=42, scaler fit on train only.

---

## API and Docker Evidence

| Item | Detail |
|---|---|
| FastAPI endpoints | 6: GET /health, GET /metrics, GET /evidence, POST /validate, GET /governance/latest, GET /governance/history |
| API test coverage | 41 pytest tests in tests/test_api.py |
| GET /health median | 2.0 ms (in-process TestClient, not network) |
| POST /validate median | 2326 ms (full 12-step pipeline per call) |
| Docker base image | python:3.11-slim |
| Docker build | Succeeded locally |
| Docker smoke test | /health: status ok; /metrics: roc_auc 0.6776 |
| Docker registry | Local image only; not published |

---

## Test Evidence

- **212 fast pytest tests passing** as of Phase 5B.6C
- Test files: test_config, test_data_pipeline, test_model_pipeline, test_agents, test_artifacts, test_api, test_benchmark_script, test_governance, test_compliance_context
- ROC-AUC 0.6776 locked as a numerical regression guard in test_api.py and test_governance.py
- All governance write/load tests isolated to tmp_path via monkeypatch
- Compliance tests include no-secrets assertions (GROQ_API_KEY not in output)

---

## Governance Evidence

- Governance utility: utils/governance.py
- Per-run record: data/governance/validation_runs/{run_id}.json
- Latest record: data/governance/latest_validation_run.json
- Latest run ID: vrun_20260520_144840_27c9fe58
- Record fields: run_id, metrics_snapshot, drift_status, compliance_status, artifact_status, risk_flags, reviewer_status, claim_safety_note, limitations
- API access: GET /governance/latest and GET /governance/history
- ~60 unit tests in test_governance.py
- Governance records are local-only; excluded from git

---

## Compliance Grounding Evidence

- Evidence context builder: utils/compliance_context.py
- Evidence sources used: verified_metrics.json, drift_report.json, governance record, benchmark_results.json
- LLM system prompt includes actual ROC-AUC (0.6776), recall (0.037), class balance, drift status, governance run ID
- Fallback advisory path uses same evidence values when Groq API is unavailable
- Saved record includes: advisory_only, not_regulatory_approval, evidence_grounded, evidence_sources, key_validation_concerns
- ~39 unit tests in test_compliance_context.py

---

## Limitations

These must be stated in any portfolio presentation:

- AgentX operates on a 5,000-row public LendingClub sample; not live portfolio data
- The baseline model is an unweighted LogisticRegression pipeline; it is the validation target, not a production scoring model
- Low recall (0.037) is a known, expected, and documented limitation of the baseline
- Compliance output is advisory and illustrative; it is not a regulatory determination
- The system has not been deployed to any production environment
- No organization has adopted or validated this system for operational use
- The Docker image is local only; not published to any registry
- Git repository is not yet initialized (pending owner API key rotation)
- MLflow model governance tracking is not yet implemented

---

## What Can Be Claimed (safe, evidence-backed)

"Designed and built a seven-agent autonomous model validation system integrating
SHAP explainability, FAISS vector memory, Groq-grounded compliance advisory, and
KS-test drift detection. Verified baseline ROC-AUC: 0.6776 on a held-out test set
of 1,000 rows from the LendingClub public dataset."

"Added a FastAPI local service boundary with six endpoints, packaged as a Docker
container (python:3.11-slim), covered by 41 pytest tests including ROC-AUC regression
guards. GET /health median 2.0 ms; POST /validate median 2.3 seconds."

"Built a local governance evidence layer that writes a structured JSON validation-run
record on each pipeline run. Records include run ID, metrics snapshot, drift status,
compliance status, artifact inventory, risk flags, and reviewer_status placeholder.
Records are accessible via GET /governance/latest and GET /governance/history."

"Grounded the compliance advisory agent in local validation evidence. The LLM system
prompt includes actual ROC-AUC, recall, class balance, drift status, and governance
run ID. The fallback path uses the same evidence values."

"212 pytest tests passing. No em dashes. No banned claims. Claim-safety document
maintained throughout development."

---

## What Must Not Be Claimed

- Deployed in production
- Used by financial institutions
- Validated by regulators
- Regulatory approved
- Enterprise adopted
- High recall or strong F1 (the baseline intentionally does not achieve this)
- Public GitHub repository available (not yet initialized)
- MLflow governance tracking (planned, not yet implemented)

---

## Suggested Proof Chips (future portfolio page)

| Chip | Evidence File |
|---|---|
| 212 Tests Passing | test suite run output |
| FastAPI Validation Boundary | docs/evidence/api_boundary_report.md |
| Dockerized Local Service | Dockerfile + Docker smoke test |
| SHAP Explainability | data/validation_outputs/shap_summary.png |
| FAISS Feedback Memory | agents/feedback_memory_agent.py |
| Governance Run Records | docs/evidence/governance_evidence_report.md |
| Grounded Compliance Review | docs/evidence/compliance_grounding_report.md |
| ROC-AUC 0.6776 | docs/evidence/verified_metrics.md |
| Local API Benchmarked | docs/evidence/benchmark_report.md |
| Claim-Safe Evidence | docs/evidence/claim_safety.md |