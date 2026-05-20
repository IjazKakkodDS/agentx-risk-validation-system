import matplotlib
matplotlib.use("Agg")  # non-interactive backend for file output
import matplotlib.pyplot as plt

import shap
import numpy as np
import pandas as pd
from typing import Dict, Any

from utils.config import SHAP_SUMMARY_PATH
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


def explain_model(model, X_sample: pd.DataFrame) -> Dict[str, Any]:
    try:
        if hasattr(model, "predict_proba"):
            explainer = shap.Explainer(model.predict_proba, X_sample)
        else:
            explainer = shap.Explainer(model, X_sample)

        shap_values = explainer(X_sample)

        if hasattr(shap_values, "values") and shap_values.values.ndim == 3:
            if shap_values.output_names is None:
                class_idx = 1
            else:
                class_idx = (
                    list(shap_values.output_names).index("1")
                    if "1" in shap_values.output_names
                    else 1
                )
            shap_values = shap_values[..., class_idx]

        shap.summary_plot(shap_values.values, X_sample, show=False)
        SHAP_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(str(SHAP_SUMMARY_PATH), bbox_inches="tight")
        plt.close()
        logger.info("SHAP summary plot saved to %s", SHAP_SUMMARY_PATH)

        mean_shap = np.abs(shap_values.values).mean(axis=0).astype("float32")
        norm = float(np.linalg.norm(mean_shap))
        if norm > 0:
            mean_shap /= norm

        return {
            "shap_values": shap_values.values.tolist(),
            "mean_vector": mean_shap.tolist(),
            "feature_names": X_sample.columns.tolist(),
            "vector_dim": len(mean_shap),
            "norm_factor": norm,
        }
    except Exception as e:
        raise RuntimeError(f"SHAP explanation failed: {e}")
