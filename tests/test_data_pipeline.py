"""
Tests for utils/load_data.py -- CSV loading and preprocessing pipeline.
"""

import pandas as pd
import pytest

from utils.config import RAW_SAMPLE_PATH
from utils.load_data import load_clean_data, preprocess_uploaded_data


def test_load_clean_data_returns_dataframe():
    df = load_clean_data(str(RAW_SAMPLE_PATH))
    assert isinstance(df, pd.DataFrame)


def test_load_clean_data_has_expected_row_count():
    df = load_clean_data(str(RAW_SAMPLE_PATH))
    assert len(df) == 5000


def test_load_clean_data_has_loan_status_column():
    df = load_clean_data(str(RAW_SAMPLE_PATH))
    assert "loan_status" in df.columns


def test_preprocess_returns_dataframe(raw_sample_df):
    result = preprocess_uploaded_data(raw_sample_df)
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0


def test_target_is_binary_after_preprocess(preprocessed_df):
    assert "loan_status" in preprocessed_df.columns
    unique_vals = set(preprocessed_df["loan_status"].unique())
    assert unique_vals <= {0, 1}, f"loan_status has non-binary values: {unique_vals}"


def test_no_missing_values_after_preprocess(preprocessed_df):
    missing = preprocessed_df.isnull().sum().sum()
    assert missing == 0, f"{missing} missing values remain after preprocessing"


def test_feature_count_is_at_least_five(preprocessed_df):
    feature_cols = [c for c in preprocessed_df.columns if c != "loan_status"]
    assert len(feature_cols) >= 5, f"Too few feature columns: {feature_cols}"


def test_all_columns_numeric_after_preprocess(preprocessed_df):
    non_numeric = preprocessed_df.select_dtypes(exclude=["number"]).columns.tolist()
    assert non_numeric == [], f"Non-numeric columns after preprocessing: {non_numeric}"


def test_class_distribution_has_majority_non_default(preprocessed_df):
    dist = preprocessed_df["loan_status"].value_counts(normalize=True)
    non_default_share = dist.get(0, 0.0)
    assert non_default_share > 0.5, "Majority class (0 = non-default) should be > 50%"


def test_preprocess_is_deterministic(raw_sample_df):
    df1 = preprocess_uploaded_data(raw_sample_df)
    df2 = preprocess_uploaded_data(raw_sample_df)
    pd.testing.assert_frame_equal(df1, df2)


def test_preprocess_does_not_modify_input(raw_sample_df):
    original_shape = raw_sample_df.shape
    original_cols = list(raw_sample_df.columns)
    preprocess_uploaded_data(raw_sample_df)
    assert raw_sample_df.shape == original_shape
    assert list(raw_sample_df.columns) == original_cols
