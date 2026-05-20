"""
Centralized configuration for AgentX Risk Validator.

All file paths are derived from PROJECT_ROOT using pathlib so the system
is portable across machines and operating systems. No absolute paths are
hardcoded here.
"""

import os
from pathlib import Path

# Project root is two levels up from this file (utils/config.py -> utils/ -> root)
PROJECT_ROOT: Path = Path(__file__).parent.parent.resolve()

# Data directories
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw_data"
MODEL_DIR: Path = DATA_DIR / "incoming_models"
VALIDATION_OUTPUTS_DIR: Path = DATA_DIR / "validation_outputs"
MEMORY_INDEX_DIR: Path = DATA_DIR / "model_memory"
DRIFT_TEST_DIR: Path = DATA_DIR / "drift_test"
GOVERNANCE_DIR: Path = DATA_DIR / "governance"
GOVERNANCE_RUNS_DIR: Path = GOVERNANCE_DIR / "validation_runs"
GOVERNANCE_LATEST_PATH: Path = GOVERNANCE_DIR / "latest_validation_run.json"

# Data files
RAW_SAMPLE_PATH: Path = RAW_DATA_DIR / "lending_club_clean_sample.csv"
FULL_RAW_DATA_PATH: Path = RAW_DATA_DIR / "accepted_2007_to_2018Q4.csv"
DRIFT_INCOMING_PATH: Path = DRIFT_TEST_DIR / "incoming_drifted_data.csv"

# Model artifact
MODEL_PATH: Path = MODEL_DIR / "credit_model.pkl"

# Validation outputs
DATA_VALIDATION_PATH: Path = VALIDATION_OUTPUTS_DIR / "data_validation.json"
PERFORMANCE_METRICS_PATH: Path = VALIDATION_OUTPUTS_DIR / "performance_metrics.json"
SHAP_SUMMARY_PATH: Path = VALIDATION_OUTPUTS_DIR / "shap_summary.png"
DRIFT_REPORT_PATH: Path = VALIDATION_OUTPUTS_DIR / "drift_report.json"
COMPLIANCE_REPORT_PATH: Path = VALIDATION_OUTPUTS_DIR / "last_compliance.json"

# Report outputs
REPORTS_DIR: Path = PROJECT_ROOT / "reports"
REPORT_MD_PATH: Path = REPORTS_DIR / "validation_report.md"
REPORT_HTML_PATH: Path = REPORTS_DIR / "validation_report.html"
REPORT_PDF_PATH: Path = REPORTS_DIR / "validation_report.pdf"

# Docs and evidence
DOCS_DIR: Path = PROJECT_ROOT / "docs"
EVIDENCE_DIR: Path = DOCS_DIR / "evidence"
VERIFIED_METRICS_JSON_PATH: Path = EVIDENCE_DIR / "verified_metrics.json"
VERIFIED_METRICS_MD_PATH: Path = EVIDENCE_DIR / "verified_metrics.md"

# Logs
LOG_DIR: Path = PROJECT_ROOT / "logs"

# Model training defaults
DEFAULT_RANDOM_STATE: int = 42
DEFAULT_TEST_SIZE: float = 0.2
DEFAULT_MODEL_MAX_ITER: int = 1000

# Groq LLM default model (read from env at runtime; fallback defined here)
GROQ_DEFAULT_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
