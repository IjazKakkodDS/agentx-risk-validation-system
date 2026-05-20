import json
import pandas as pd
from scipy.stats import ks_2samp

from utils.config import DRIFT_INCOMING_PATH, DRIFT_REPORT_PATH, RAW_SAMPLE_PATH
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


def detect_drift(
    reference_path=RAW_SAMPLE_PATH,
    incoming_path=DRIFT_INCOMING_PATH,
    save_path=DRIFT_REPORT_PATH,
    threshold=0.05,
):
    reference_df = pd.read_csv(str(reference_path))
    incoming_df = pd.read_csv(str(incoming_path))

    drift_report = {"drift_detected": False, "details": []}
    common_cols = set(reference_df.columns).intersection(incoming_df.columns)

    for col in common_cols:
        if (
            reference_df[col].dtype in ["float64", "int64"]
            and incoming_df[col].dtype in ["float64", "int64"]
        ):
            stat, p_value = ks_2samp(
                reference_df[col].dropna(), incoming_df[col].dropna()
            )
            drifted = p_value < threshold
            drift_report["details"].append(
                {
                    "feature": col,
                    "p_value": float(round(p_value, 4)),
                    "drifted": bool(drifted),
                }
            )
            if drifted:
                drift_report["drift_detected"] = True

    save_path_obj = save_path if hasattr(save_path, "mkdir") else __import__("pathlib").Path(save_path)
    save_path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(str(save_path_obj), "w") as f:
        json.dump(drift_report, f, indent=2)

    drifted_count = sum(1 for d in drift_report["details"] if d["drifted"])
    logger.info(
        "Drift report saved to %s -- %d/%d features drifted",
        save_path,
        drifted_count,
        len(drift_report["details"]),
    )
    return drift_report
