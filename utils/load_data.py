import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder


def load_clean_data(path: str) -> pd.DataFrame:
    """Read raw CSV from disk. No preprocessing applied."""
    return pd.read_csv(path)


def preprocess_uploaded_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and encode uploaded CSV data for AgentX risk validation.

    Steps applied here (StandardScaling is intentionally excluded --
    it lives inside the sklearn Pipeline saved with the model, so that
    training and inference use an identical, leakage-free transform):
    - Drop ID-like columns
    - Drop rows where loan_status is missing
    - Encode loan_status to 0 / 1
    - Impute missing numeric values with column median
    - Impute and LabelEncode categorical columns
    """
    df = df.copy()

    # === Drop high-cardinality ID columns ===
    drop_cols = [col for col in df.columns if "id" in col.lower() or "member" in col.lower()]
    df.drop(columns=drop_cols, errors="ignore", inplace=True)

    # === Drop rows where loan_status is missing ===
    if "loan_status" in df.columns:
        df = df.dropna(subset=["loan_status"])

    # === Encode target column (loan_status) to 0 / 1 ===
    if "loan_status" in df.columns:
        if df["loan_status"].nunique() == 2:
            df["loan_status"] = df["loan_status"].map(
                lambda x: 1 if str(x).lower() in ["charged off", "default", "1"] else 0
            )
        target_col = df["loan_status"].astype(int)
        df = df.drop(columns=["loan_status"])
    else:
        target_col = None

    # === Impute numeric columns ===
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    for col in numeric_cols:
        df[col] = df[col].fillna(df[col].median())

    # === Impute and encode categorical columns ===
    cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
    for col in cat_cols:
        df[col] = df[col].fillna("Unknown")
        try:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col])
        except Exception:
            df[col] = pd.factorize(df[col])[0]

    # === Add target column back (unscaled, unmodified) ===
    if target_col is not None:
        df["loan_status"] = target_col.reset_index(drop=True)

    return df
