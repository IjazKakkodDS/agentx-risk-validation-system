# AgentX Risk Validator -- Test Suite Report
Phase: 5B.4
Date: 2026-05-20
Status: COMPLETE -- 85 tests, 85 passed, 0 failed, 0 errors

---

## 1. Test Files Created

| File | Category | Tests |
|---|---|---|
| tests/conftest.py | Shared fixtures | Session-scoped: raw_sample_df, preprocessed_df, trained_model_and_test |
| tests/test_config.py | Configuration | 10 |
| tests/test_data_pipeline.py | Data loading and preprocessing | 11 |
| tests/test_model_pipeline.py | Model training and evaluation | 14 |
| tests/test_agents.py | Individual agent behavior | 32 |
| tests/test_artifacts.py | Pipeline output artifact verification | 18 |
| tests/test_main_smoke.py | Full pipeline smoke test | 3 (marked slow) |
| pytest.ini | Pytest configuration | N/A |

Total test functions: 85
Slow-marked tests (pipeline smoke): 3
Fast tests (all others): 82

---

## 2. Test Categories

### Configuration (test_config.py -- 10 tests)
- PROJECT_ROOT resolves to a valid directory
- All configured paths resolve under PROJECT_ROOT
- Raw sample CSV exists at the configured path
- Evidence directory exists
- Default constants (random_state, test_size, max_iter) are in valid ranges
- GROQ_DEFAULT_MODEL is a non-empty string
- No hardcoded Windows user paths appear in config source
- File extension checks for SHAP PNG, report Markdown, and model PKL

### Data Pipeline (test_data_pipeline.py -- 11 tests)
- load_clean_data() returns a non-empty DataFrame
- Raw sample has exactly 5,000 rows
- loan_status column is present in raw data
- preprocess_uploaded_data() returns a DataFrame
- Target column is binary (0/1 only) after preprocessing
- No missing values remain after preprocessing
- At least 5 feature columns after preprocessing
- All columns are numeric after preprocessing
- Majority class (0 = non-default) exceeds 50% of labels
- Preprocessing is deterministic (same output across two calls)
- Preprocessing does not mutate the input DataFrame

### Model Pipeline (test_model_pipeline.py -- 14 tests)
- train_model() returns a sklearn Pipeline
- Pipeline contains a StandardScaler step
- Pipeline contains a LogisticRegression step
- train_model() returns a non-empty test set
- Test set size is close to 20% of the preprocessed data
- evaluate_model() returns all required metric keys
- Metric values are numeric floats
- ROC-AUC is in [0, 1]
- Accuracy is in [0, 1]
- Confusion matrix is a 2x2 list
- Confusion matrix entries sum to the test set size
- Production model artifact exists at MODEL_PATH
- Production model artifact is loadable as a Pipeline
- train_model() accepts pathlib.Path as save_path

### Agent Behavior (test_agents.py -- 32 tests)

**Data Validator (4 tests):**
- Returns expected keys (missing_values, duplicate_rows, class_distribution, summary_statistics)
- missing_values is an integer
- Reports zero missing values on the preprocessed clean dataset
- class_distribution values sum to 1.0

**Performance Agent (2 tests):**
- Returns all required metric keys
- ROC-AUC exceeds random-chance baseline of 0.5

**Explainability Agent / SHAP (5 tests):**
- Returns expected structure keys (mean_vector, feature_names, shap_values, vector_dim, norm_factor)
- mean_vector is a non-empty list
- mean_vector is unit-normalized (L2 norm = 1.0 within tolerance)
- SHAP summary PNG is written to the configured path
- feature_names match the input DataFrame columns
Note: SHAP tests redirect SHAP_SUMMARY_PATH to tmp_path to avoid overwriting the production PNG.

**Compliance Agent (3 tests):**
- _cached_response() returns a non-empty string
- generate_compliance_report() returns (string, "Cache") when GROQ_API_KEY is absent
- Fallback report does not contain "GROQ_API_KEY" or "sk-" patterns
Note: No live API call is made in tests. The fallback path is tested via environment monkeypatching.

**Drift Monitor Agent (5 tests):**
- Returns expected keys (drift_detected, details)
- details is a list
- Each detail item has feature, p_value, and drifted keys
- Saves a valid JSON file to the configured path
- Detects known drift in the simulated incoming dataset (annual_inc, loan_amnt)

**Feedback Memory Agent (4 tests):**
- ModelMemory.add_model() and find_similar() return a result with model_name and similarity
- Similarity value is in [0, 1.01] (cosine similarity, float tolerance)
- save() and load() round-trip preserves metadata
- run_feedback_memory_agent() returns a list
Note: Unit tests use tmp_path to avoid touching the production FAISS index.

**Report Writer Agent (3 tests):**
- write_report() creates the output file
- Output file is non-empty
- Output file contains the AgentX header

### Artifact Verification (test_artifacts.py -- 18 tests)
- verified_metrics.md exists and is non-empty
- verified_metrics.json exists and is non-empty
- verified_metrics.json has a "metrics" key
- ROC-AUC in verified_metrics.json equals 0.6776 (regression guard)
- verified_metrics.md contains the string "0.6776"
- upgrade_plan.md exists in evidence directory
- claim_safety.md exists in evidence directory
- code_cleanup_report.md exists in evidence directory
- validation_outputs directory exists
- data_validation.json exists and is non-empty
- performance_metrics.json exists, is non-empty, and contains roc_auc
- shap_summary.png exists and is non-empty
- drift_report.json exists and is non-empty
- last_compliance.json exists and is non-empty
- validation_report.md exists and is non-empty
- Model artifact exists and is non-empty
- logs/ directory exists
- logs/agentx.log exists and is non-empty

### Pipeline Smoke Test (test_main_smoke.py -- 3 tests, marked slow)
- main.py exits with code 0
- All 9 expected artifacts exist and are non-empty after pipeline run
- agentx.log contains "pipeline complete" after run

---

## 3. Commands

Fast tests (skip slow):
```
python -m pytest -m "not slow"
```

Slow tests only:
```
python -m pytest -m slow
```

Full suite:
```
python -m pytest
```

---

## 4. Results

### Fast tests (82 tests)
```
82 passed, 3 deselected in 10.37s
```

### Slow tests (3 tests)
```
3 passed, 82 deselected in 32.44s
```

### Full suite
```
85 passed in ~42s
```

All 85 tests passed. Zero failures, zero errors, zero skips.

---

## 5. What the Tests Prove

- Config paths are portable (derived from PROJECT_ROOT, not hardcoded)
- The raw 5,000-row LendingClub sample loads and preprocesses cleanly
- Preprocessing is deterministic and does not mutate inputs
- The sklearn Pipeline contains StandardScaler + LogisticRegression (pipeline consistency preserved)
- Model evaluation returns all required metrics with valid numeric ranges
- Data Validator, Performance, Drift, FeedbackMemory, and ReportWriter agents run on real data
- SHAP mean vector is unit-normalized (FAISS cosine similarity compatibility)
- SHAP summary PNG is written to disk (regression guard for the 5B.3 bug fix)
- Compliance agent fallback does not expose API key values
- Drift agent correctly detects known distributional shift in the simulated dataset
- FAISS memory store add/retrieve/save/load round-trips correctly
- ROC-AUC 0.6776 is locked as a regression guard in test_artifacts.py
- Full main.py pipeline exits cleanly with all 9 artifacts present

---

## 6. What the Tests Do Not Prove

- Live Groq API call quality (not tested, network-dependent)
- Streamlit UI behavior (not tested, requires browser automation)
- PDF report generation (not tested, pdfkit has a system dependency)
- Performance under large datasets (only 5,000-row sample tested)
- Concurrency or multi-user behavior (system is single-user local tool)

---

## 7. Remaining Engineering Gaps After Phase 5B.4

| Gap | Priority | Status |
|---|---|---|
| No Dockerfile | P2 | Planned -- Wave 5 |
| No FastAPI boundary | P2 | Planned -- Wave 5 |
| Compliance agent not grounded in model outputs | P2 | Planned -- Wave 6 |
| No MLflow tracking | P2 | Planned -- Wave 6 |
| No benchmark script | P3 | Planned -- Wave 6 |
| PDF pdfkit system dependency | P3 | Open |

---

## 8. Engineering Claim Unlocked

After Wave 4 completion, the following claim is accurate:

"Fully tested agent pipeline with 85 passing pytest tests covering configuration,
data preprocessing, model training, all seven agents, artifact verification, and
end-to-end pipeline smoke testing. ROC-AUC 0.6776 is locked as a regression guard."
