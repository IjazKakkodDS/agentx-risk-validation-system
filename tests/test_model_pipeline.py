"""
Tests for utils/model_utils.py and agents/performance_agent.py.
"""

import joblib
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from agents.performance_agent import evaluate_model
from utils.config import MODEL_PATH
from utils.model_utils import train_model


# --- Structure tests (use session fixture, no extra training) ---

def test_train_model_returns_pipeline(trained_model_and_test):
    model, _, _ = trained_model_and_test
    assert isinstance(model, Pipeline)


def test_pipeline_contains_standard_scaler(trained_model_and_test):
    model, _, _ = trained_model_and_test
    step_types = [type(step) for _, step in model.steps]
    assert StandardScaler in step_types


def test_pipeline_contains_logistic_regression(trained_model_and_test):
    model, _, _ = trained_model_and_test
    step_types = [type(step) for _, step in model.steps]
    assert LogisticRegression in step_types


def test_train_model_returns_nonempty_test_set(trained_model_and_test):
    _, X_test, y_test = trained_model_and_test
    assert len(X_test) > 0
    assert len(y_test) == len(X_test)


def test_test_set_size_is_roughly_twenty_percent(preprocessed_df, trained_model_and_test):
    _, X_test, _ = trained_model_and_test
    expected = int(len(preprocessed_df) * 0.2)
    assert abs(len(X_test) - expected) <= 5, "Test set size deviates from 80/20 split"


# --- Metric tests ---

def test_evaluate_model_returns_required_keys(trained_model_and_test):
    model, X_test, y_test = trained_model_and_test
    metrics = evaluate_model(model, X_test, y_test)
    required = {"accuracy", "precision", "recall", "f1_score", "roc_auc", "confusion_matrix"}
    assert required.issubset(set(metrics.keys())), f"Missing keys: {required - set(metrics.keys())}"


def test_metrics_are_numeric_floats(trained_model_and_test):
    model, X_test, y_test = trained_model_and_test
    metrics = evaluate_model(model, X_test, y_test)
    for key in ("accuracy", "precision", "recall", "f1_score", "roc_auc"):
        assert isinstance(metrics[key], (int, float)), f"{key} is not numeric: {metrics[key]}"


def test_roc_auc_in_valid_range(trained_model_and_test):
    model, X_test, y_test = trained_model_and_test
    metrics = evaluate_model(model, X_test, y_test)
    assert 0.0 <= metrics["roc_auc"] <= 1.0


def test_accuracy_in_valid_range(trained_model_and_test):
    model, X_test, y_test = trained_model_and_test
    metrics = evaluate_model(model, X_test, y_test)
    assert 0.0 <= metrics["accuracy"] <= 1.0


def test_confusion_matrix_is_2x2_list(trained_model_and_test):
    model, X_test, y_test = trained_model_and_test
    metrics = evaluate_model(model, X_test, y_test)
    cm = metrics["confusion_matrix"]
    assert isinstance(cm, list)
    assert len(cm) == 2
    assert all(len(row) == 2 for row in cm)


def test_confusion_matrix_sums_to_test_set_size(trained_model_and_test):
    model, X_test, y_test = trained_model_and_test
    metrics = evaluate_model(model, X_test, y_test)
    cm = metrics["confusion_matrix"]
    total = sum(cm[i][j] for i in range(2) for j in range(2))
    assert total == len(y_test)


# --- Artifact tests ---

def test_production_model_artifact_exists():
    assert MODEL_PATH.exists(), f"Model artifact not found: {MODEL_PATH}"


def test_production_model_artifact_is_a_pipeline():
    model = joblib.load(str(MODEL_PATH))
    assert isinstance(model, Pipeline)


def test_model_save_path_accepts_pathlib(preprocessed_df, tmp_path):
    # Verify train_model accepts a pathlib.Path as save_path
    save_path = tmp_path / "check_model.pkl"
    train_model(preprocessed_df, save_path=save_path)
    assert save_path.exists()
    assert save_path.stat().st_size > 0
