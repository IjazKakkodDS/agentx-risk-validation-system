# AgentX Risk Validator -- Benchmark Report
Date: 2026-05-20
Phase: 5B.6A

---

## Disclaimer

These measurements were captured on a local development machine and should not be interpreted as production latency or cloud deployment performance.

These benchmarks reflect in-process TestClient calls on a local Windows
development machine. They are not network latency measurements and are not
representative of Docker container, cloud deployment, or concurrent-user performance.

---

## Environment

| Item | Value |
|---|---|
| Platform | Windows |
| Python | 3.13.1 |
| Processor | Intel64 Family 6 Model 170 Stepping 4, GenuineIntel |
| Machine | AMD64 |
| Benchmark date | 2026-05-20 |

---

## Benchmark Configuration

| Setting | Value |
|---|---|
| Fast endpoint iterations | 30 |
| POST /validate iterations | 3 |
| Timing method | time.perf_counter() |
| Units | milliseconds |
| Benchmark client | FastAPI TestClient (in-process, no network) |

---

## Endpoint Latency (in-process TestClient)

| Endpoint | N | Median (ms) | Mean (ms) | Min (ms) | Max (ms) | P95 (ms) | Status |
|---|---|---|---|---|---|---|---|
| GET /health | 30 | 1.946 | 2.311 | 1.817 | 7.729 | 2.832 | 200 (ok) |
| GET /metrics | 30 | 2.62 | 2.56 | 1.939 | 3.64 | 3.199 | 200 (ok) |
| GET /evidence | 30 | 4.318 | 4.205 | 2.711 | 6.129 | 5.6 | 200 (ok) |
| POST /validate | 3 | 2429.944 | 4379.954 | 2353.678 | 8356.241 | 2429.944 | 200 (ok) |

Note: GET /metrics returns 503 if verified_metrics.json has not been generated.
A 503 from /metrics is not a failure -- the pipeline must run first to create the file.
POST /validate runs the full pipeline (train + 6 agents) on each iteration.

---

## Pipeline Direct Call

| Setting | Value |
|---|---|
| Iterations | 3 |
| Compliance agent | False |
| Drift monitor | True |
| Regenerate reports | True |
| Median (ms) | 2467.189 |
| Mean (ms) | 2457.894 |
| Min (ms) | 2414.121 |
| Max (ms) | 2492.373 |
| P95 (ms) | 2467.189 |
| Success | True |

The pipeline call includes: data load, preprocessing, model training,
data validation, performance evaluation, SHAP (100-row sample), FAISS memory,
report generation, and drift monitoring. Compliance agent is skipped to avoid
requiring a live Groq API key.

---

## Artifact Generation

| Metric | Value |
|---|---|
| Total artifacts checked | 8 |
| Present | 8 |
| Non-empty | 8 |
| All present | True |
| All non-empty | True |

| Artifact | Present | Size (bytes) |
|---|---|---|
| data\validation_outputs\data_validation.json | Yes | 2660 |
| data\validation_outputs\performance_metrics.json | Yes | 216 |
| data\validation_outputs\shap_summary.png | Yes | 52730 |
| data\validation_outputs\drift_report.json | Yes | 605 |
| data\validation_outputs\last_compliance.json | Yes | 5753 |
| reports\validation_report.md | Yes | 6625 |
| docs\evidence\verified_metrics.json | Yes | 1305 |
| docs\evidence\verified_metrics.md | Yes | 1794 |

---

## What Can Be Claimed

- The AgentX FastAPI boundary responds to all four endpoints on a local machine.
- GET /health, GET /metrics, and GET /evidence are fast in-process operations.
- POST /validate completes a full seven-agent pipeline run in a measured local runtime.
- All expected artifacts are generated and non-empty after a pipeline run.
- These are local development latencies only.

## What Cannot Be Claimed

- These figures are not production latencies.
- These figures are not representative of Docker container or cloud performance.
- These figures are not network round-trip measurements.
- No concurrency or load testing was performed.
- These results do not imply production readiness, enterprise suitability,
  regulatory approval, or live banking use.

---

## Limitations

- Compliance agent skipped in pipeline benchmark (no Groq API key required).
- SHAP runs on a 100-row sample (same as production pipeline).
- POST /validate benchmark uses 3 iterations only due to full pipeline cost.
- No Docker API benchmark performed in this script; see Docker section of README.
- No concurrent request benchmarking.
- First-iteration JIT warmup effects may inflate the min timing for fast endpoints.
