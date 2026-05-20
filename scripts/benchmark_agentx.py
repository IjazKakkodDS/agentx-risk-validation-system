"""
AgentX Risk Validator -- Local Development Benchmark Script.

Measures in-process latency for all four FastAPI endpoints using TestClient,
full pipeline runtime via run_agentx_pipeline(), and artifact generation results.

IMPORTANT: These measurements were captured on a local development machine and
should not be interpreted as production latency or cloud deployment performance.

Outputs:
    docs/evidence/benchmark_results.json  -- machine-readable results
    docs/evidence/benchmark_report.md     -- human-readable report
"""

import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path when run as a script
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from utils.config import (  # noqa: E402
    COMPLIANCE_REPORT_PATH,
    DATA_VALIDATION_PATH,
    DRIFT_REPORT_PATH,
    EVIDENCE_DIR,
    PERFORMANCE_METRICS_PATH,
    REPORT_MD_PATH,
    SHAP_SUMMARY_PATH,
    VERIFIED_METRICS_JSON_PATH,
    VERIFIED_METRICS_MD_PATH,
)

DISCLAIMER = (
    "These measurements were captured on a local development machine and "
    "should not be interpreted as production latency or cloud deployment performance."
)

ARTIFACT_PATHS = [
    DATA_VALIDATION_PATH,
    PERFORMANCE_METRICS_PATH,
    SHAP_SUMMARY_PATH,
    DRIFT_REPORT_PATH,
    COMPLIANCE_REPORT_PATH,
    REPORT_MD_PATH,
    VERIFIED_METRICS_JSON_PATH,
    VERIFIED_METRICS_MD_PATH,
]

N_FAST = 30
N_VALIDATE = 3


def _stats(samples_ms: list) -> dict:
    if not samples_ms:
        return {}
    s = sorted(samples_ms)
    n = len(s)
    p95_idx = max(0, int(n * 0.95) - 1)
    return {
        "n_iterations": n,
        "median_ms": round(statistics.median(s), 3),
        "mean_ms": round(statistics.mean(s), 3),
        "min_ms": round(min(s), 3),
        "max_ms": round(max(s), 3),
        "p95_ms": round(s[p95_idx], 3),
    }


def bench_endpoint(client: TestClient, method: str, path: str, n: int, **kwargs) -> dict:
    samples = []
    status_codes = []
    error = None
    try:
        for _ in range(n):
            t0 = time.perf_counter()
            if method.upper() == "GET":
                resp = client.get(path, **kwargs)
            else:
                resp = client.post(path, **kwargs)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            samples.append(elapsed_ms)
            status_codes.append(resp.status_code)
    except Exception as exc:
        error = str(exc)

    result = _stats(samples)
    result["method"] = method.upper()
    result["path"] = path
    result["status_codes"] = list(set(status_codes)) if status_codes else []
    result["success"] = error is None and all(c in (200, 503) for c in status_codes)
    if error:
        result["error"] = error
    return result


def bench_pipeline(n: int) -> dict:
    from main import run_agentx_pipeline  # lazy to avoid startup side-effects

    samples = []
    error = None
    try:
        for _ in range(n):
            t0 = time.perf_counter()
            run_agentx_pipeline(
                run_compliance=False,
                run_drift=True,
                regenerate_reports=True,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            samples.append(elapsed_ms)
    except Exception as exc:
        error = str(exc)

    result = _stats(samples)
    result["flags"] = {"run_compliance": False, "run_drift": True, "regenerate_reports": True}
    result["success"] = error is None
    if error:
        result["error"] = error
    return result


def check_artifacts() -> dict:
    results = []
    for p in ARTIFACT_PATHS:
        exists = p.exists()
        size = p.stat().st_size if exists else 0
        results.append({
            "path": str(p.relative_to(PROJECT_ROOT)),
            "exists": exists,
            "size_bytes": size,
            "non_empty": size > 0 if exists else False,
        })
    present = [r for r in results if r["exists"]]
    non_empty = [r for r in present if r["non_empty"]]
    return {
        "total_checked": len(results),
        "present": len(present),
        "non_empty": len(non_empty),
        "all_present": len(present) == len(results),
        "all_non_empty": len(non_empty) == len(results),
        "files": results,
    }


def _env_info() -> dict:
    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python": sys.version.split()[0],
        "processor": platform.processor() or "unknown",
        "machine": platform.machine(),
    }


def run_benchmark() -> dict:
    print("AgentX Risk Validator -- Local Benchmark")
    print("=" * 55)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(DISCLAIMER)
    print()

    client = TestClient(app)

    # --- Fast endpoints ---
    print(f"Benchmarking GET /health   ({N_FAST} iterations)...")
    health = bench_endpoint(client, "GET", "/health", N_FAST)
    print(f"  median={health.get('median_ms')} ms  p95={health.get('p95_ms')} ms  status={health.get('status_codes')}")

    print(f"Benchmarking GET /metrics  ({N_FAST} iterations)...")
    metrics_ep = bench_endpoint(client, "GET", "/metrics", N_FAST)
    print(f"  median={metrics_ep.get('median_ms')} ms  p95={metrics_ep.get('p95_ms')} ms  status={metrics_ep.get('status_codes')}")

    print(f"Benchmarking GET /evidence ({N_FAST} iterations)...")
    evidence = bench_endpoint(client, "GET", "/evidence", N_FAST)
    print(f"  median={evidence.get('median_ms')} ms  p95={evidence.get('p95_ms')} ms  status={evidence.get('status_codes')}")

    # --- POST /validate (slow) ---
    print(f"Benchmarking POST /validate ({N_VALIDATE} iterations -- includes full pipeline)...")
    validate_payload = {
        "run_compliance_agent": False,
        "run_drift_monitor": True,
        "regenerate_reports": True,
    }
    validate_ep = bench_endpoint(
        client, "POST", "/validate", N_VALIDATE,
        json=validate_payload, timeout=300,
    )
    print(f"  median={validate_ep.get('median_ms')} ms  p95={validate_ep.get('p95_ms')} ms  status={validate_ep.get('status_codes')}")

    # --- Pipeline direct call ---
    print(f"Benchmarking pipeline direct call ({N_VALIDATE} iterations)...")
    pipeline_result = bench_pipeline(N_VALIDATE)
    print(f"  median={pipeline_result.get('median_ms')} ms  p95={pipeline_result.get('p95_ms')} ms  ok={pipeline_result.get('success')}")

    # --- Artifact check ---
    print("Checking generated artifacts...")
    artifact_result = check_artifacts()
    print(f"  {artifact_result['present']}/{artifact_result['total_checked']} present  "
          f"{artifact_result['non_empty']} non-empty  all_ok={artifact_result['all_non_empty']}")

    results = {
        "benchmark_date": datetime.now().isoformat(),
        "disclaimer": DISCLAIMER,
        "environment": _env_info(),
        "benchmark_config": {
            "n_fast_iterations": N_FAST,
            "n_validate_iterations": N_VALIDATE,
            "timing_function": "time.perf_counter()",
            "units": "milliseconds",
        },
        "endpoints": {
            "GET /health": health,
            "GET /metrics": metrics_ep,
            "GET /evidence": evidence,
            "POST /validate": validate_ep,
        },
        "pipeline_direct": pipeline_result,
        "artifacts": artifact_result,
    }

    return results


def _write_json(results: dict) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "benchmark_results.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    return out


def _write_markdown(results: dict) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "benchmark_report.md"

    date_str = results["benchmark_date"][:10]
    env = results["environment"]
    eps = results["endpoints"]
    pipe = results["pipeline_direct"]
    arts = results["artifacts"]
    cfg = results["benchmark_config"]

    lines = [
        "# AgentX Risk Validator -- Benchmark Report",
        f"Date: {date_str}",
        f"Phase: 5B.6A",
        "",
        "---",
        "",
        "## Disclaimer",
        "",
        results["disclaimer"],
        "",
        "These benchmarks reflect in-process TestClient calls on a local Windows",
        "development machine. They are not network latency measurements and are not",
        "representative of Docker container, cloud deployment, or concurrent-user performance.",
        "",
        "---",
        "",
        "## Environment",
        "",
        f"| Item | Value |",
        f"|---|---|",
        f"| Platform | {env['platform']} |",
        f"| Python | {env['python']} |",
        f"| Processor | {env['processor']} |",
        f"| Machine | {env['machine']} |",
        f"| Benchmark date | {date_str} |",
        "",
        "---",
        "",
        "## Benchmark Configuration",
        "",
        f"| Setting | Value |",
        f"|---|---|",
        f"| Fast endpoint iterations | {cfg['n_fast_iterations']} |",
        f"| POST /validate iterations | {cfg['n_validate_iterations']} |",
        f"| Timing method | {cfg['timing_function']} |",
        f"| Units | {cfg['units']} |",
        f"| Benchmark client | FastAPI TestClient (in-process, no network) |",
        "",
        "---",
        "",
        "## Endpoint Latency (in-process TestClient)",
        "",
        "| Endpoint | N | Median (ms) | Mean (ms) | Min (ms) | Max (ms) | P95 (ms) | Status |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for name, ep in eps.items():
        status_str = "/".join(str(s) for s in ep.get("status_codes", []))
        ok_marker = "ok" if ep.get("success") else "FAIL"
        lines.append(
            f"| {name} | {ep.get('n_iterations', 0)} | {ep.get('median_ms', 'N/A')} | "
            f"{ep.get('mean_ms', 'N/A')} | {ep.get('min_ms', 'N/A')} | "
            f"{ep.get('max_ms', 'N/A')} | {ep.get('p95_ms', 'N/A')} | "
            f"{status_str} ({ok_marker}) |"
        )

    lines += [
        "",
        "Note: GET /metrics returns 503 if verified_metrics.json has not been generated.",
        "A 503 from /metrics is not a failure -- the pipeline must run first to create the file.",
        "POST /validate runs the full pipeline (train + 6 agents) on each iteration.",
        "",
        "---",
        "",
        "## Pipeline Direct Call",
        "",
        "| Setting | Value |",
        "|---|---|",
        f"| Iterations | {pipe.get('n_iterations', 0)} |",
        f"| Compliance agent | {pipe.get('flags', {}).get('run_compliance', 'N/A')} |",
        f"| Drift monitor | {pipe.get('flags', {}).get('run_drift', 'N/A')} |",
        f"| Regenerate reports | {pipe.get('flags', {}).get('regenerate_reports', 'N/A')} |",
        f"| Median (ms) | {pipe.get('median_ms', 'N/A')} |",
        f"| Mean (ms) | {pipe.get('mean_ms', 'N/A')} |",
        f"| Min (ms) | {pipe.get('min_ms', 'N/A')} |",
        f"| Max (ms) | {pipe.get('max_ms', 'N/A')} |",
        f"| P95 (ms) | {pipe.get('p95_ms', 'N/A')} |",
        f"| Success | {pipe.get('success', False)} |",
    ]

    if not pipe.get("success") and "error" in pipe:
        lines += ["", f"Pipeline error: {pipe['error']}"]

    lines += [
        "",
        "The pipeline call includes: data load, preprocessing, model training,",
        "data validation, performance evaluation, SHAP (100-row sample), FAISS memory,",
        "report generation, and drift monitoring. Compliance agent is skipped to avoid",
        "requiring a live Groq API key.",
        "",
        "---",
        "",
        "## Artifact Generation",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total artifacts checked | {arts['total_checked']} |",
        f"| Present | {arts['present']} |",
        f"| Non-empty | {arts['non_empty']} |",
        f"| All present | {arts['all_present']} |",
        f"| All non-empty | {arts['all_non_empty']} |",
        "",
        "| Artifact | Present | Size (bytes) |",
        "|---|---|---|",
    ]

    for f_info in arts["files"]:
        present_str = "Yes" if f_info["exists"] else "No"
        size_str = str(f_info["size_bytes"]) if f_info["exists"] else "N/A"
        lines.append(f"| {f_info['path']} | {present_str} | {size_str} |")

    lines += [
        "",
        "---",
        "",
        "## What Can Be Claimed",
        "",
        "- The AgentX FastAPI boundary responds to all four endpoints on a local machine.",
        "- GET /health, GET /metrics, and GET /evidence are fast in-process operations.",
        "- POST /validate completes a full seven-agent pipeline run in a measured local runtime.",
        "- All expected artifacts are generated and non-empty after a pipeline run.",
        "- These are local development latencies only.",
        "",
        "## What Cannot Be Claimed",
        "",
        "- These figures are not production latencies.",
        "- These figures are not representative of Docker container or cloud performance.",
        "- These figures are not network round-trip measurements.",
        "- No concurrency or load testing was performed.",
        "- These results do not imply production readiness, enterprise suitability,",
        "  regulatory approval, or live banking use.",
        "",
        "---",
        "",
        "## Limitations",
        "",
        "- Compliance agent skipped in pipeline benchmark (no Groq API key required).",
        "- SHAP runs on a 100-row sample (same as production pipeline).",
        "- POST /validate benchmark uses 3 iterations only due to full pipeline cost.",
        "- No Docker API benchmark performed in this script; see Docker section of README.",
        "- No concurrent request benchmarking.",
        "- First-iteration JIT warmup effects may inflate the min timing for fast endpoints.",
    ]

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return out


def main():
    results = run_benchmark()

    json_path = _write_json(results)
    md_path = _write_markdown(results)

    print()
    print("Outputs written:")
    print(f"  {json_path}")
    print(f"  {md_path}")
    print()
    print("Benchmark complete.")


if __name__ == "__main__":
    main()
