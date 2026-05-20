# AgentX Risk Validator -- README Upgrade Report
Phase: 5B.2
Date: 2026-05-19

---

## 1. README Sections Added

The README was empty (0 bytes of content) before this phase. The following sections
were written from scratch:

| Section | Content |
|---|---|
| Title and tagline | AgentX: Autonomous Risk Model Validation Assistant |
| Executive Summary | What AgentX is, what it is not, what it is becoming |
| Business Problem | Financial model validation context, regulatory background |
| Target Users | Table of six user roles and their relevance |
| System Architecture | ASCII diagram of full pipeline from input to dashboard |
| Agent Layer | Table of all seven agents: purpose, status, output file |
| Verified Model Evidence | Phase 5B.1 metrics table with interpretation note |
| Explainability and Memory | SHAP + FAISS description with honest scope |
| Compliance Review | Compliance agent behavior, fallback, limitations |
| Drift Monitoring | KS test, simulated drift, planned module |
| How to Run Locally | Environment setup, .env configuration, CLI and Streamlit commands |
| Streamlit dashboard page table | 8 pages described with content |
| Evidence Files | Table of all docs/evidence/ and docs/ files |
| Security Notes | .gitignore protection, key rotation requirement |
| Current Limitations | Honest engineering boundary table |
| Engineering Roadmap | Three tiers: Implemented, In Progress, Planned Product Modules |
| Claim Safety | Safe vs unsafe claim list |
| Original Vision Alignment | SR 11-7, Basel IV, audit-ready evidence, human-in-the-loop |
| Dataset Citation | LendingClub public data attribution |
| Key Dependencies | Table of main packages and their roles |

---

## 2. Verified Metrics Used

Only metrics from `docs/evidence/verified_metrics.md` (Phase 5B.1) were cited:

| Metric | Value used in README |
|---|---|
| ROC-AUC | 0.6776 |
| Accuracy | 0.804 |
| Precision | 0.350 |
| Recall | 0.037 |
| F1 Score | 0.067 |

The README includes an interpretation note explaining that accuracy reflects class
imbalance (81% majority), ROC-AUC is the preferred headline metric, and low recall
is a documented baseline limitation.

---

## 3. Confirmation That Old Metrics Were Not Cited

The following invalidated metrics do not appear anywhere in README.md:

- ROC-AUC 0.668 (old markdown report, inconsistent pipeline)
- ROC-AUC 0.333 (pipeline mismatch, model evaluated on differently scaled data)
- Accuracy 0.82 (old markdown report)
- Accuracy 0.486 (pipeline mismatch)

---

## 4. How the Original AgentX Vision Was Reflected Safely

The original product vision (autonomous risk model validation assistant for banking
workflows) is preserved in the README through:

- The title: "Autonomous Risk Model Validation Assistant"
- The business problem section describing real MRM pain points
- The target users table including model validation teams and compliance stakeholders
- The compliance agent description referencing SR 11-7 and Basel IV
- The original vision alignment section naming specific regulatory frameworks

The system is not described as deployed, approved, or adopted. It is described as
"being engineered" and "under active engineering development" -- which is accurate.

---

## 5. How "Future Roadmap" Was Converted to "Planned Product Modules"

The Engineering Roadmap section uses three explicit tiers:

- Implemented: what exists and runs
- In Progress: the current L2 wave
- Planned Product Modules: a named table of specific capabilities

The following items were lifted from vague "future extensions" framing to named
planned product modules with a stated purpose:

- FastAPI validation boundary (POST /validate, GET /health, GET /metrics)
- Docker packaging
- MLflow validation tracking
- MCP governance log for model-change events
- PDF audit pack generation
- Drift-triggered automatic revalidation
- Compliance report grounding in actual model outputs
- Class-weighted and XGBoost model variants
- Benchmark script with per-agent timing

---

## 6. Security Wording Added

The Security Notes section documents:
- .env is excluded from git by .gitignore
- .env.example is safe (placeholder values only)
- Model artifacts and large data files are excluded
- Git initialization is deferred until Groq API key is rotated
- The "How to Run Locally" section instructs users to copy .env.example and never commit .env

---

## 7. Claim-Safety Check Results

The Claim Safety section of the README explicitly separates:

**Safe claims:** ROC-AUC 0.6776, runnable pipeline, SHAP, FAISS, Streamlit dashboard,
security hygiene, active roadmap.

**Unsafe claims:** production platform, regulatory approved, enterprise deployed,
customer used, live banking system, high-recall detector, fully automated approval.

The words below were searched across README.md and portfolio_positioning_draft.md:

| Phrase | Found in positive claim? |
|---|---|
| production deployed | No -- appears only in "not" or "unsafe" context |
| enterprise deployed | No |
| customer | No positive claim |
| regulatory approved | No |
| guaranteed | Not present |
| live banking | No |
| real bank | Not present |
| fully automated approval | Appears only in unsafe section |
| production validation platform | Appears only in unsafe section |
| enterprise-ready | Not present |
| production-ready | Not present |

No unsafe claim appears as a positive statement in either document.

---

## 8. Em Dash Check

No em dashes (--) were used in README.md. Sentence structure was rewritten where
em dashes would typically appear. Standard dashes (-) used for list markers only.

Portfolio_positioning_draft.md was reviewed and updated in this phase to remove any
remaining em dash characters.

---

## 9. Remaining Documentation Gaps

| Gap | Status |
|---|---|
| SHAP top-5 feature names in evidence | Not captured yet (requires re-reading shap output file) |
| Benchmark results in docs/evidence/ | Planned product module (Wave 3) |
| Test coverage report | Pending test suite (Wave 4) |
| Architecture diagram image (PNG/SVG) | ASCII diagram in README; visual diagram pending |
| docs/evidence/verified_metrics.md drift results | Not merged in yet |
