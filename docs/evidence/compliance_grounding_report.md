# AgentX Compliance Grounding Report

**System:** AgentX Risk Validator v1.0.0
**Report type:** Compliance agent grounding upgrade documentation
**Phase:** 5B.6C
**Date:** 2026-05-20
**Status:** Active -- compliance agent now generates advisory reviews grounded in local validation evidence

---

## Purpose

This document describes the compliance agent grounding upgrade implemented in Phase 5B.6C.
Prior to this phase, the compliance agent generated a generic regulatory checklist using
static LLM prompts disconnected from the actual model being validated. After this upgrade,
the compliance review is grounded in local validation evidence from the current pipeline run.

The compliance output remains advisory only. It does not constitute regulatory approval,
regulatory certification, or a production compliance determination.

---

## What Changed

### Before (Phase 5B.5 and earlier)

- ComplianceAgent sent static text prompts to the Groq LLM
- Prompts contained no reference to actual model metrics
- Fallback response was a hardcoded generic checklist
- No connection between validated ROC-AUC, recall, drift status, or governance record
- Output was identical regardless of which model was being validated

### After (Phase 5B.6C)

- `utils/compliance_context.py` builds a structured evidence context from local artifacts
- ComplianceAgent includes actual metrics in the LLM system prompt
- Grounded prompts instruct the LLM to cite specific values (ROC-AUC, recall, class balance)
- Fallback advisory uses real evidence values, not generic placeholders
- Saved JSON record includes advisory_only, evidence_grounded, evidence_sources, key_validation_concerns
- `main.py` builds compliance context from the current pipeline run before Step 9

---

## Evidence Context Fields

The compliance evidence context assembled by `build_compliance_context()` includes:

| Category | Fields |
|---|---|
| Metrics | roc_auc, accuracy, precision, recall, f1_score, model_type, dataset_rows, feature_count, class_balance, low_recall_flag, class_imbalance_present, roc_auc_preferred_metric |
| Drift | drift_detected, drifted_features, total_features_tested |
| Artifacts | shap_explainability_present, performance_evidence_present, verified_metrics_present, drift_evidence_present |
| Governance | validation_run_id, created_at_utc, reviewer_status, risk_flags |
| Benchmark | health_median_ms, validate_median_ms, pipeline_median_ms, artifacts_all_present |
| Meta | risk_flags (assembled), limitations, claim_safety_note, advisory_only, not_regulatory_approval |

---

## How Verified Metrics Are Passed to the Compliance Review

The pipeline passes the current run's `performance_report` dict to `build_compliance_context(perf_report=...)`:

```python
# In main.py Step 9:
compliance_context = build_compliance_context(perf_report=performance_report)
run_compliance_agent(evidence_context=compliance_context)
```

The `_metrics_from_perf_report()` function in `compliance_context.py` uses the live
`performance_report` (roc_auc=0.6776, accuracy=0.804, etc.) and enriches it with
dataset metadata from `verified_metrics.json` (dataset_rows, feature_count, class_balance,
model_type). This ensures the compliance review is grounded in the actual current run.

---

## Grounded LLM Prompt Structure

When the Groq API key is available, the system prompt includes:

1. Role: "advisory compliance analyst reviewing a machine learning credit risk model"
2. Full evidence context string (model evidence, drift status, governance context, risk flags, limitations)
3. Instructions to cite specific evidence values (not generic commentary)
4. Advisory disclaimer

The checklist prompt instructs the LLM to cite: actual ROC-AUC value, actual class balance
percentages, actual recall value, actual drifted features (if any), actual validation run ID.

---

## Fallback Behavior

When the Groq API key is absent or the API call fails:

- `_fallback_advisory(evidence_context)` generates a structured advisory review using local evidence values
- If evidence_context is provided: ROC-AUC, accuracy, recall, drift status, governance run ID are all included
- If evidence_context is None: "N/A" placeholders are used (backward-compatible behavior)
- Source is set to "LocalFallback" (previously "Cache")
- Output is still a claim-safe advisory review with SR 11-7 and Basel-style checklist items

The `_cached_response()` function is kept for backward compatibility but now delegates to `_fallback_advisory(None)`.

---

## Saved Compliance Record

After this upgrade, `data/validation_outputs/last_compliance.json` includes:

| Field | Description |
|---|---|
| `content` | Full advisory review text (backward compatible) |
| `source` | "API" or "LocalFallback" (was "Cache") |
| `timestamp` | ISO 8601 timestamp |
| `advisory_only` | Always true |
| `not_regulatory_approval` | Always true |
| `evidence_grounded` | True when verified metrics were available |
| `validation_run_id` | Governance run ID if governance record available |
| `evidence_sources` | List of artifact sources used (verified_metrics_json, drift_report, governance_record, benchmark_results) |
| `key_validation_concerns` | Risk flags assembled from metrics, drift, governance |
| `limitations` | Documented system limitations |

---

## Verified Sample (2026-05-20 after pipeline run)

```
source: API
advisory_only: True
not_regulatory_approval: True
evidence_grounded: True
evidence_sources: [verified_metrics_json, drift_report, governance_record, benchmark_results]
key_validation_concerns count: 3
ROC-AUC 0.6776 cited in content: True
No secrets in content: True
```

---

## Files Created and Modified

| File | Change |
|---|---|
| `utils/compliance_context.py` | NEW -- evidence context builder with 6 load functions, build_compliance_context(), format_compliance_context_for_prompt() |
| `agents/compliance_agent.py` | MODIFIED -- grounded Groq prompt, _fallback_advisory(), run_compliance_agent(evidence_context) |
| `main.py` | MODIFIED -- imports build_compliance_context, builds context before Step 9, passes to run_compliance_agent |
| `tests/test_compliance_context.py` | NEW -- ~39 tests for context builder functions and constants |
| `tests/test_agents.py` | MODIFIED -- updated source assertion ("LocalFallback"), added 4 grounded compliance tests |

---

## Tests Added

Total test suite: 212 fast tests passing after Phase 5B.6C.

New tests in `tests/test_compliance_context.py` (~39 tests):
- Context loader functions return dicts with expected keys
- ROC-AUC 0.6776 appears in metrics context when file is present
- low_recall_flag is True (recall 0.037 < 0.1 threshold)
- class_imbalance_present and roc_auc_preferred_metric flags are set
- build_compliance_context returns all required top-level keys
- advisory_only and not_regulatory_approval are True
- build_compliance_context with perf_report override uses provided metrics
- No secrets in context or formatted output
- format_compliance_context_for_prompt contains evidence header, advisory phrase, ROC-AUC value

Updated tests in `tests/test_agents.py` (4 new + 1 updated):
- source == "LocalFallback" (was "Cache")
- _fallback_advisory contains advisory note
- grounded fallback with context includes actual ROC-AUC and accuracy values
- grounded fallback does not expose secrets

---

## Claim Safety

The compliance review output is claim-safe throughout:

- `ADVISORY_NOTE` appears in all reports (API and fallback paths)
- `claim_safety_note` field uses `ADVISORY_CLAIM_SAFETY` constant
- `advisory_only: True` and `not_regulatory_approval: True` in saved JSON
- No report claims regulatory approval, production certification, or enterprise compliance
- All LLM prompts include instruction that the review is "advisory only"

---

## Remaining Limitations

- Compliance review is advisory and illustrative; it is not a regulatory determination
- The LLM does not have access to live production data or regulatory databases
- Compliance agent does not inspect full confusion matrix or threshold analysis (only summary metrics)
- Class weighting and tree-based models are not yet implemented (planned engineering module)
- MLflow validation tracking is not yet implemented (planned engineering module)
- Docker container uses ephemeral filesystem; governance records are not persisted across restarts
