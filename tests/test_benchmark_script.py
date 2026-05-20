"""
Tests for scripts/benchmark_agentx.py.

Verifies that the benchmark module is importable, the output structure
is correct, and benchmark results do not expose secrets.

These are fast structural tests. No pipeline execution is required.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module importability
# ---------------------------------------------------------------------------

def test_benchmark_module_is_importable():
    spec = importlib.util.spec_from_file_location(
        "benchmark_agentx",
        Path(__file__).parent.parent / "scripts" / "benchmark_agentx.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "run_benchmark")
    assert hasattr(mod, "bench_endpoint")
    assert hasattr(mod, "bench_pipeline")
    assert hasattr(mod, "check_artifacts")


def test_benchmark_module_has_disclaimer():
    spec = importlib.util.spec_from_file_location(
        "benchmark_agentx",
        Path(__file__).parent.parent / "scripts" / "benchmark_agentx.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "local development machine" in mod.DISCLAIMER.lower()
    assert "production" in mod.DISCLAIMER.lower()


# ---------------------------------------------------------------------------
# Output file structure
# ---------------------------------------------------------------------------

BENCHMARK_JSON = Path(__file__).parent.parent / "docs" / "evidence" / "benchmark_results.json"
BENCHMARK_MD = Path(__file__).parent.parent / "docs" / "evidence" / "benchmark_report.md"


def _load_results():
    if not BENCHMARK_JSON.exists():
        pytest.skip("benchmark_results.json not generated -- run scripts/benchmark_agentx.py first")
    with open(BENCHMARK_JSON, encoding="utf-8") as f:
        return json.load(f)


def test_benchmark_json_exists():
    if not BENCHMARK_JSON.exists():
        pytest.skip("benchmark_results.json not generated -- run scripts/benchmark_agentx.py first")
    assert BENCHMARK_JSON.stat().st_size > 0


def test_benchmark_json_has_required_keys():
    data = _load_results()
    for key in ("benchmark_date", "disclaimer", "environment", "benchmark_config",
                "endpoints", "pipeline_direct", "artifacts"):
        assert key in data, f"Missing key in benchmark_results.json: {key}"


def test_benchmark_json_endpoints_has_all_four():
    data = _load_results()
    endpoints = data["endpoints"]
    for ep in ("GET /health", "GET /metrics", "GET /evidence", "POST /validate"):
        assert ep in endpoints, f"Missing endpoint in benchmark results: {ep}"


def test_benchmark_json_endpoints_have_timing_fields():
    data = _load_results()
    for ep_name, ep_data in data["endpoints"].items():
        for field in ("median_ms", "mean_ms", "min_ms", "max_ms", "n_iterations"):
            assert field in ep_data, f"Endpoint {ep_name} missing field: {field}"


def test_benchmark_json_median_ms_is_positive():
    data = _load_results()
    for ep_name, ep_data in data["endpoints"].items():
        assert ep_data["median_ms"] > 0, f"Endpoint {ep_name} median_ms is not positive"


def test_benchmark_json_pipeline_direct_has_timing():
    data = _load_results()
    pipe = data["pipeline_direct"]
    for field in ("median_ms", "mean_ms", "min_ms", "max_ms", "success"):
        assert field in pipe, f"pipeline_direct missing field: {field}"


def test_benchmark_json_pipeline_direct_succeeded():
    data = _load_results()
    assert data["pipeline_direct"]["success"] is True


def test_benchmark_json_artifacts_all_present():
    data = _load_results()
    arts = data["artifacts"]
    assert arts["all_present"] is True, "Not all expected artifacts were present"


def test_benchmark_json_artifacts_all_non_empty():
    data = _load_results()
    arts = data["artifacts"]
    assert arts["all_non_empty"] is True, "Some artifacts were empty"


def test_benchmark_json_disclaimer_is_claim_safe():
    data = _load_results()
    disc = data["disclaimer"].lower()
    assert "local development" in disc
    assert "production" in disc


def test_benchmark_json_does_not_expose_secrets():
    if not BENCHMARK_JSON.exists():
        pytest.skip("benchmark_results.json not generated")
    text = BENCHMARK_JSON.read_text(encoding="utf-8")
    assert "GROQ_API_KEY" not in text


def test_benchmark_markdown_exists():
    if not BENCHMARK_MD.exists():
        pytest.skip("benchmark_report.md not generated -- run scripts/benchmark_agentx.py first")
    assert BENCHMARK_MD.stat().st_size > 0


def test_benchmark_markdown_contains_disclaimer():
    if not BENCHMARK_MD.exists():
        pytest.skip("benchmark_report.md not generated")
    text = BENCHMARK_MD.read_text(encoding="utf-8")
    assert "local development machine" in text.lower()
    assert "not be interpreted as production" in text.lower()


def test_benchmark_markdown_does_not_expose_secrets():
    if not BENCHMARK_MD.exists():
        pytest.skip("benchmark_report.md not generated")
    text = BENCHMARK_MD.read_text(encoding="utf-8")
    assert "GROQ_API_KEY" not in text
