import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from utils.config import (
    DEFAULT_MODEL_MAX_ITER,
    DEFAULT_RANDOM_STATE,
    DEFAULT_TEST_SIZE,
    MODEL_PATH,
)
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


def train_model(df: pd.DataFrame, save_path=MODEL_PATH):
    X = df.drop("loan_status", axis=1)
    y = df["loan_status"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=DEFAULT_TEST_SIZE,
        random_state=DEFAULT_RANDOM_STATE,
        stratify=y,
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            max_iter=DEFAULT_MODEL_MAX_ITER,
            random_state=DEFAULT_RANDOM_STATE,
        )),
    ])
    pipeline.fit(X_train, y_train)

    save_path = str(save_path)
    import os
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    joblib.dump(pipeline, save_path)
    logger.info("Model pipeline saved to %s", save_path)

    return pipeline, X_test, y_test
