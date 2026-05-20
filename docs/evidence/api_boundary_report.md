# AgentX Risk Validator -- API Boundary Report
Phase: 5B.5
Generated: 2026-05-20

---

## Overview

Phase 5B.5 adds a FastAPI local service boundary to AgentX, providing programmatic access
to validation workflows and evidence artifacts. This boundary serves development and
portfolio integration testing purposes. It is not a production deployment and does not
constitute regulatory approval.

---

## Files Added

| File | Role |
|---|---|
| `api/__init__.py` | Package marker |
| `api/schemas.py` | Pydantic v2 request/response models and CLAIM_SAFETY_NOTE constant |
| `api/service.py` | Thin adapters between route handlers and the agent/utility layer |
| `api/main.py` | FastAPI application with middleware, lifespan, and route handlers |
| `Dockerfile` | Docker image build spec (python:3.11-slim, port 8000) |
| `.dockerignore` | Excludes .env, large CSVs, caches, logs from image |
| `tests/test_api.py` | 41 pytest tests covering all six endpoints (updated Phase 5B.6B) |

---

## Endpoints

| Method | Path | Response Model | Description |
|---|---|---|---|
| GET | /health | HealthResponse | Fast liveness check; returns system name, version, file availability |
| GET | /metrics | MetricsResponse | Reads verified_metrics.json; returns 503 if file not yet generated |
| GET | /evidence | EvidenceResponse | Lists evidence files and artifact existence status; includes governance_available flag |
| POST | /validate | ValidationRunResponse | Runs the full validation pipeline; 10-30 seconds |
| GET | /governance/latest | GovernanceLatestResponse | Latest validation-run record; 503 if none exists (added Phase 5B.6B) |
| GET | /governance/history | GovernanceHistoryResponse | List of recent run summaries; always 200 (added Phase 5B.6B) |

---

## Request Schema (POST /validate)

```json
{
  "run_compliance_agent": false,
  "run_drift_monitor": true,
  "regenerate_reports": true
}
```

All fields have safe defaults. `run_compliance_agent` defaults to `false` to avoid
requiring a live Groq API key. Set to `true` when `GROQ_API_KEY` is configured; the
pipeline falls back automatically when the key is absent.

---

## Response Schemas

**GET /health:**
```json
{
  "status": "ok",
  "system": "AgentX Risk Validator",
  "version": "1.0.0",
  "metrics_available": true,
  "evidence_available": true
}
```

**GET /metrics (verified values):**
```json
{
  "roc_auc": 0.6776,
  "accuracy": 0.804,
  "precision": 0.35,
  "recall": 0.037,
  "f1_score": 0.067,
  "dataset_rows": 5000,
  "feature_count": 12,
  "model_type": "Pipeline(StandardScaler + LogisticRegression)",
  "evidence_source": "docs/evidence/verified_metrics.json"
}
```

**POST /validate (abbreviated):**
```json
{
  "status": "complete",
  "message": "AgentX validation pipeline completed successfully.",
  "metrics": { "roc_auc": 0.6776, "accuracy": 0.804 },
  "artifacts": ["data/validation_outputs/data_validation.json", "..."],
  "warnings": [],
  "evidence_note": "This local API boundary runs AgentX validation workflows for development and portfolio evidence. It is not a production regulatory approval system."
}
```

---

## Service Functions (api/service.py)

| Function | Description |
|---|---|
| `load_verified_metrics()` | Reads verified_metrics.json; raises FileNotFoundError if absent |
| `list_evidence_files()` | Lists files in docs/evidence/ with name and size_bytes |
| `list_generated_artifacts()` | Checks all configured artifact paths for existence and size |
| `run_validation_pipeline(request)` | Lazy-imports and calls run_agentx_pipeline() from main.py |

The lazy import pattern (`from main import run_agentx_pipeline` inside the function body)
prevents pipeline execution at FastAPI startup. The app starts and is ready for health
checks without triggering a training run.

---

## main.py Refactoring

To support importable pipeline invocation, main.py was refactored from a pure script
to a callable module:

- All pipeline logic wrapped in `run_agentx_pipeline(run_compliance, run_drift, regenerate_reports)`
- Returns `{"status": "complete", "metrics": {...}, "artifacts": [...], "warnings": [...]}`
- `if __name__ == "__main__":` guard preserves `python main.py` behavior unchanged
- `python main.py` runs the full pipeline with all flags enabled by default

---

## Middleware and Lifecycle

- **Lifespan context manager**: logs service start and stop at INFO level
- **HTTP middleware**: logs method, path, status code, and elapsed time in milliseconds for every request

---

## Claim Safety in API Design

All user-visible text in the API was written with explicit claim safety:

- `CLAIM_SAFETY_NOTE` constant in `api/schemas.py` embedded in EvidenceResponse and ValidationRunResponse payloads
- FastAPI app description: "Not a production regulatory platform."
- POST /validate docstring: "This is a local development endpoint."
- No endpoint claims production deployment, enterprise adoption, regulatory approval, or live banking use.

---

## Test Coverage (tests/test_api.py)

41 tests covering all six endpoints (updated Phase 5B.6B):

| Endpoint | Tests | Speed |
|---|---|---|
| GET /health | 7 | Fast |
| GET /metrics | 6 | Fast (pytest.skip if 503) |
| GET /evidence | 9 | Fast |
| POST /validate | 6 | Slow (marked @pytest.mark.slow) |
| GET /governance/latest | 7 | Fast (pytest.skip if 503) |
| GET /governance/history | 6 | Fast |

All endpoints verified to not expose `GROQ_API_KEY` in responses.

ROC-AUC 0.6776 asserted as a regression guard in `test_metrics_returns_verified_roc_auc`
and `test_validate_returns_metrics`.

Run fast API tests only:
```bash
python -m pytest tests/test_api.py -m "not slow"
```

Run all API tests including POST /validate:
```bash
python -m pytest tests/test_api.py
```

Total test suite after Phase 5B.5: 111 tests (85 prior + 26 API tests), all passing.
Total test suite after Phase 5B.6B: 173 fast tests, all passing (includes governance and API governance tests).

---

## Docker

### Dockerfile

- Base: `python:3.11-slim`
- System dependencies: `gcc`, `g++`, `libgomp1` (required for SHAP and faiss-cpu)
- Copies `requirements.txt` before application code for Docker layer caching
- Copies full project (excluding .dockerignore items)
- Exposes port 8000
- Default command: `uvicorn api.main:app --host 0.0.0.0 --port 8000`

### .dockerignore Exclusions

| Excluded | Reason |
|---|---|
| `.env` | Credentials must not be baked into image |
| `.git/` | Version control not needed at runtime |
| `__pycache__/`, `*.pyc` | Generated files; excluded for cleanliness |
| `data/raw_data/accepted_2007_to_2018Q4.csv` | Large file; sample CSV is included |
| `reports/*.pdf`, `reports/*.html` | Generated at runtime |
| `logs/` | Generated at runtime |
| `.venv/`, `venv/` | Runtime installs from requirements.txt |
| `*.ipynb` | Notebooks not needed at runtime |

The data sample (`lending_club_clean_sample.csv`) and drift dataset are included so
the pipeline can run inside the container without requiring volume mounts.

### Build and Run

```bash
docker build -t agentx-risk-validator .
docker run --rm -p 8000:8000 agentx-risk-validator
```

With Groq API key for compliance agent:
```bash
docker run --rm -p 8000:8000 --env-file .env agentx-risk-validator
```

### Verified Container Test (2026-05-20)

After build, the container was confirmed functional:

| Check | Result |
|---|---|
| GET /health | `{"status": "ok", "system": "AgentX Risk Validator", "version": "1.0.0", "metrics_available": true}` |
| GET /metrics | `{"roc_auc": 0.6776, "accuracy": 0.804, "dataset_rows": 5000}` |
| Container stop | Clean exit |

---

## Limitations

- Not published to any container registry
- Not deployed to any cloud or production environment
- Not suitable for concurrent POST /validate requests (no thread-safety guarantees on FAISS writes)
- State is not persisted across container restarts
- Compliance agent LLM call requires GROQ_API_KEY; falls back to cached response when absent
- POST /validate takes 10-30 seconds depending on SHAP computation and network

No claim of production deployment, enterprise adoption, regulatory approval, or live
banking use is made.
