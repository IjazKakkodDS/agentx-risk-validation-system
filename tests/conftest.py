"""
Shared pytest fixtures for AgentX test suite.

Session-scoped fixtures are used for expensive operations (CSV loading,
preprocessing, model training) so they run once per test session.
The trained model is saved to a temp directory to avoid overwriting the
production artifact during test runs.
"""

import pytest
import pandas as pd

from utils.config import RAW_SAMPLE_PATH


@pytest.fixture(scope="session")
def raw_sample_df():
    """Load the 5,000-row LendingClub sample CSV once per session."""
    return pd.read_csv(str(RAW_SAMPLE_PATH))


@pytest.fixture(scope="session")
def preprocessed_df(raw_sample_df):
    """Preprocessed DataFrame ready for model training."""
    from utils.load_data import preprocess_uploaded_data
    return preprocess_uploaded_data(raw_sample_df)


@pytest.fixture(scope="session")
def trained_model_and_test(preprocessed_df, tmp_path_factory):
    """
    Train model once per session, save to a temp path so the production
    artifact at MODEL_PATH is not overwritten during test runs.
    Returns (pipeline, X_test, y_test).
    """
    tmp = tmp_path_factory.mktemp("model")
    from utils.model_utils import train_model
    return train_model(preprocessed_df, save_path=tmp / "test_credit_model.pkl")
