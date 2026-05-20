"""
Smoke test for the full main.py pipeline.

Marked @pytest.mark.slow because it runs the complete 7-agent pipeline
end-to-end (approximately 10-15 seconds including SHAP and Groq API call).

Run with:   python -m pytest -m slow
Skip with:  python -m pytest -m "not slow"
"""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

EXPECTED_ARTIFACTS = [
    "data/validation_outputs/data_validation.json",
    "data/validation_outputs/performance_metrics.json",
    "data/validation_outputs/shap_summary.png",
    "data/validation_outputs/drift_report.json",
    "data/validation_outputs/last_compliance.json",
    "reports/validation_report.md",
    "docs/evidence/verified_metrics.json",
    "docs/evidence/verified_metrics.md",
    "logs/agentx.log",
]


@pytest.mark.slow
def test_main_pipeline_exits_zero():
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py")],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        f"main.py exited with code {result.returncode}\n"
        f"STDOUT:\n{result.stdout[-2000:]}\n"
        f"STDERR:\n{result.stderr[-2000:]}"
    )


@pytest.mark.slow
def test_main_pipeline_produces_all_artifacts():
    # Run the pipeline first
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py")],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        timeout=300,
        check=True,
    )
    for rel_path in EXPECTED_ARTIFACTS:
        artifact = PROJECT_ROOT / rel_path
        assert artifact.exists(), f"Artifact missing after pipeline run: {rel_path}"
        assert artifact.stat().st_size > 0, f"Artifact is empty: {rel_path}"


@pytest.mark.slow
def test_main_pipeline_log_contains_completion_message():
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py")],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        timeout=300,
        check=True,
    )
    log_file = PROJECT_ROOT / "logs" / "agentx.log"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "pipeline complete" in content.lower(), "Pipeline completion message not found in log"
