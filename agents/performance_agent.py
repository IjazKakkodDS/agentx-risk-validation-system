import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


def evaluate_model(model, X_test, y_test) -> dict:
    y_test = np.asarray(y_test, dtype=int)
    preds = model.predict(X_test)
    preds = np.asarray(preds, dtype=int)

    try:
        probs = model.predict_proba(X_test)[:, 1]
    except Exception:
        probs = preds.astype(float)

    metrics = {
        "accuracy":         round(float(accuracy_score(y_test, preds)), 4),
        "precision":        round(float(precision_score(y_test, preds, zero_division=0)), 4),
        "recall":           round(float(recall_score(y_test, preds, zero_division=0)), 4),
        "f1_score":         round(float(f1_score(y_test, preds, zero_division=0)), 4),
        "roc_auc":          round(float(roc_auc_score(y_test, probs)), 4),
        "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
    }
    logger.info(
        "Performance -- accuracy: %.4f, roc_auc: %.4f, recall: %.4f",
        metrics["accuracy"], metrics["roc_auc"], metrics["recall"],
    )
    return metrics
