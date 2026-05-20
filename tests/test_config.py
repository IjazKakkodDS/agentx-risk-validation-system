"""
Tests for utils/config.py -- centralized path and constant configuration.
"""

import inspect

import pytest

from utils.config import (
    COMPLIANCE_REPORT_PATH,
    DATA_VALIDATION_PATH,
    DEFAULT_MODEL_MAX_ITER,
    DEFAULT_RANDOM_STATE,
    DEFAULT_TEST_SIZE,
    DRIFT_REPORT_PATH,
    EVIDENCE_DIR,
    GROQ_DEFAULT_MODEL,
    LOG_DIR,
    MEMORY_INDEX_DIR,
    MODEL_PATH,
    PERFORMANCE_METRICS_PATH,
    PROJECT_ROOT,
    RAW_SAMPLE_PATH,
    REPORT_MD_PATH,
    SHAP_SUMMARY_PATH,
    VALIDATION_OUTPUTS_DIR,
)
import utils.config as _cfg


def test_project_root_is_a_directory():
    assert PROJECT_ROOT.is_dir(), f"PROJECT_ROOT is not a directory: {PROJECT_ROOT}"


def test_all_configured_paths_are_under_project_root():
    paths = [
        MODEL_PATH,
        RAW_SAMPLE_PATH,
        SHAP_SUMMARY_PATH,
        DRIFT_REPORT_PATH,
        COMPLIANCE_REPORT_PATH,
        REPORT_MD_PATH,
        MEMORY_INDEX_DIR,
        LOG_DIR,
        EVIDENCE_DIR,
        DATA_VALIDATION_PATH,
        PERFORMANCE_METRICS_PATH,
        VALIDATION_OUTPUTS_DIR,
    ]
    root_str = str(PROJECT_ROOT)
    for p in paths:
        assert str(p).startswith(root_str), f"{p} is not under PROJECT_ROOT"


def test_raw_sample_path_exists():
    assert RAW_SAMPLE_PATH.exists(), f"Raw sample CSV not found: {RAW_SAMPLE_PATH}"


def test_evidence_dir_exists():
    assert EVIDENCE_DIR.exists(), f"Evidence directory missing: {EVIDENCE_DIR}"


def test_model_defaults_are_reasonable():
    assert DEFAULT_RANDOM_STATE == 42
    assert 0.0 < DEFAULT_TEST_SIZE < 1.0
    assert DEFAULT_MODEL_MAX_ITER >= 100


def test_groq_default_model_is_non_empty_string():
    assert isinstance(GROQ_DEFAULT_MODEL, str)
    assert len(GROQ_DEFAULT_MODEL) > 0


def test_config_has_no_hardcoded_windows_user_paths():
    source = inspect.getsource(_cfg)
    # PROJECT_ROOT is computed via Path(__file__), not hardcoded.
    # No literal user-specific Windows path should appear in source.
    assert "C:\\\\Users\\\\" not in source
    assert "C:/Users/" not in source


def test_shap_summary_path_ends_with_png():
    assert str(SHAP_SUMMARY_PATH).endswith(".png")


def test_report_md_path_ends_with_md():
    assert str(REPORT_MD_PATH).endswith(".md")


def test_model_path_ends_with_pkl():
    assert str(MODEL_PATH).endswith(".pkl")
