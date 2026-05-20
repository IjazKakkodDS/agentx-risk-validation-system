"""
AgentX Risk Validator -- main pipeline entry point.

Execution order:
  1. Load raw CSV
  2. Preprocess (encode + impute; StandardScaler lives inside the model Pipeline)
  3. Train model Pipeline (StandardScaler + LogisticRegression)
  4. Data Validation Agent
  5. Performance Agent
  6. Explainability Agent (SHAP)
  7. Feedback Memory Agent (FAISS)
  8. Report Writer (optional)
  9. Compliance Agent (Groq LLM, optional)
 10. Drift Monitor Agent (optional)
 11. Write verified metrics to docs/evidence/

run_agentx_pipeline() is importable by the API service layer.
Running this file directly as a script triggers the full pipeline.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List

from agents.compliance_agent import run_compliance_agent
from agents.data_validator_agent import validate_data
from agents.drift_monitor_agent import detect_drift
from agents.explainability_agent import explain_model
from agents.feedback_memory_agent import run_feedback_memory_agent
from agents.performance_agent import evaluate_model
from agents.report_writer_agent import write_report
from utils.config import (
    COMPLIANCE_REPORT_PATH,
    DATA_VALIDATION_PATH,
    DRIFT_REPORT_PATH,
    EVIDENCE_DIR,
    PERFORMANCE_METRICS_PATH,
    RAW_SAMPLE_PATH,
    REPORT_MD_PATH,
    VALIDATION_OUTPUTS_DIR,
    VERIFIED_METRICS_JSON_PATH,
    VERIFIED_METRICS_MD_PATH,
)
from utils.compliance_context import build_compliance_context
from utils.governance import create_validation_run_record, write_validation_run_record
from utils.load_data import load_clean_data, preprocess_uploaded_data
from utils.logging_utils import setup_logger
from utils.model_utils import train_model

logger = setup_logger("agentx.main")


def run_agentx_pipeline(
    run_compliance: bool = True,
    run_drift: bool = True,
    regenerate_reports: bool = True,
) -> Dict[str, Any]:
    """
    Execute the AgentX validation pipeline.

    Args:
        run_compliance: Call the Groq compliance agent. Falls back to cached
                        response when GROQ_API_KEY is absent.
        run_drift:      Run the KS-test drift monitor agent.
        regenerate_reports: Write the Markdown validation report.

    Returns:
        dict with keys: status, metrics, artifacts, warnings.
    """
    VALIDATION_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    warnings: List[str] = []
    artifacts: List[str] = []

    # Step 1
    logger.info("Loading sample dataset from %s", RAW_SAMPLE_PATH)
    df_raw = load_clean_data(str(RAW_SAMPLE_PATH))
    logger.info("Loaded %d rows, %d columns", len(df_raw), len(df_raw.columns))

    # Step 2
    logger.info("Preprocessing data...")
    df = preprocess_uploaded_data(df_raw)
    logger.info("After preprocessing: %d rows, %d columns", len(df), len(df.columns))

    # Step 3
    logger.info("Training model pipeline (StandardScaler + LogisticRegression)...")
    model, X_test, y_test = train_model(df)

    # Step 4
    logger.info("Running Data Validator Agent...")
    validation_report = validate_data(df)
    with open(DATA_VALIDATION_PATH, "w") as f:
        json.dump(validation_report, f, indent=2)
    artifacts.append(str(DATA_VALIDATION_PATH))

    # Step 5
    logger.info("Running Performance Agent...")
    performance_report = evaluate_model(model, X_test, y_test)
    with open(PERFORMANCE_METRICS_PATH, "w") as f:
        json.dump(performance_report, f, indent=2)
    artifacts.append(str(PERFORMANCE_METRICS_PATH))
    for k, v in performance_report.items():
        if k != "confusion_matrix":
            logger.info("  %s: %s", k, v)

    # Step 6
    logger.info("Running Explainability Agent (SHAP)...")
    shap_result = explain_model(model, X_test.iloc[:100])

    # Step 7
    logger.info("Running Feedback Memory Agent...")
    run_feedback_memory_agent(shap_result, model_name="credit_model")

    # Step 8
    if regenerate_reports:
        logger.info("Generating Markdown report...")
        write_report(validation_report, performance_report)
        artifacts.append(str(REPORT_MD_PATH))

    # Step 9
    if run_compliance:
        if not os.getenv("GROQ_API_KEY"):
            warnings.append(
                "GROQ_API_KEY not set -- compliance agent used grounded local fallback advisory"
            )
        logger.info("Building compliance evidence context from current run...")
        compliance_context = build_compliance_context(perf_report=performance_report)
        logger.info("Running Compliance Agent (grounded in local validation evidence)...")
        run_compliance_agent(evidence_context=compliance_context)
        artifacts.append(str(COMPLIANCE_REPORT_PATH))

    # Step 10
    if run_drift:
        logger.info("Running Drift Monitor Agent...")
        drift_report = detect_drift()
        with open(DRIFT_REPORT_PATH, "w") as f:
            json.dump(drift_report, f, indent=2)
        artifacts.append(str(DRIFT_REPORT_PATH))

    # Step 11 -- always write verified metrics
    logger.info("Writing verified metrics to docs/evidence/...")
    dataset_info = {
        "dataset": "LendingClub public loan data (2007-2018Q4 sample)",
        "source_file": str(RAW_SAMPLE_PATH),
        "total_rows": len(df_raw),
        "rows_after_preprocessing": len(df),
        "feature_count": len(df.columns) - 1,
        "target": "loan_status (0 = Fully Paid, 1 = Charged Off)",
        "class_balance": {
            str(k): round(float(v), 4)
            for k, v in df["loan_status"].value_counts(normalize=True).items()
        },
        "train_rows": int(len(df) * 0.8),
        "test_rows": len(X_test),
        "model_type": "sklearn Pipeline: StandardScaler + LogisticRegression(max_iter=1000, random_state=42)",
        "preprocessing": [
            "Drop ID-like columns",
            "Drop rows with missing loan_status",
            "Encode loan_status to 0/1",
            "Impute numeric columns with median",
            "LabelEncode categorical columns",
            "StandardScaler applied inside Pipeline (fit on train split only)",
        ],
        "train_test_split": "80/20, random_state=42, stratified on loan_status",
        "metrics": performance_report,
        "run_timestamp": datetime.now().isoformat(),
    }
    with open(VERIFIED_METRICS_JSON_PATH, "w") as f:
        json.dump(dataset_info, f, indent=2)
    artifacts.append(str(VERIFIED_METRICS_JSON_PATH))

    cm = performance_report["confusion_matrix"]
    md_lines = [
        "# AgentX Risk Validator -- Verified Model Metrics",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "Phase: 5B.5 -- FastAPI boundary added (metrics unchanged from 5B.1)",
        "",
        "## Dataset",
        "- Source: LendingClub public loan data, 2007-2018Q4 sample",
        f"- Total rows loaded: {len(df_raw):,}",
        f"- Rows after preprocessing: {len(df):,}",
        f"- Features: {len(df.columns) - 1}",
        "- Target: loan_status (0 = Fully Paid, 1 = Charged Off)",
        f"- Class balance: {dataset_info['class_balance']}",
        "",
        "## Preprocessing",
        "- Drop ID-like columns",
        "- Impute numeric columns with column median",
        "- LabelEncode all categorical columns",
        "- StandardScaler: fit on training split only, applied inside Pipeline",
        "",
        "## Train / Test Split",
        "- 80% train / 20% test",
        "- random_state=42, stratified on loan_status",
        f"- Train rows: {int(len(df) * 0.8):,}",
        f"- Test rows: {len(X_test):,}",
        "",
        "## Model",
        "- sklearn Pipeline: StandardScaler + LogisticRegression(max_iter=1000, random_state=42)",
        "- Artifact: data/incoming_models/credit_model.pkl (includes scaler)",
        "",
        "## Metrics",
        "| Metric | Value |",
        "|---|---|",
        f"| Accuracy | {performance_report['accuracy']} |",
        f"| Precision | {performance_report['precision']} |",
        f"| Recall | {performance_report['recall']} |",
        f"| F1 Score | {performance_report['f1_score']} |",
        f"| ROC-AUC | {performance_report['roc_auc']} |",
        "",
        "## Confusion Matrix",
        "```",
        "                Predicted 0   Predicted 1",
        f"  Actual 0        {cm[0][0]:>6}        {cm[0][1]:>6}",
        f"  Actual 1        {cm[1][0]:>6}        {cm[1][1]:>6}",
        "```",
        "",
        "## Limitations",
        "- Logistic Regression is the baseline model. It is not the best-performing model",
        "  for this dataset; it serves as the validation target for the AgentX pipeline.",
        "- The dataset is a 5,000-row public sample, not a full production portfolio.",
        "- Compliance outputs are LLM-generated illustrative examples, not regulatory assessments.",
        "",
        "## Claim Safety",
        "- These metrics may be cited after this phase.",
        "- Prior metrics (ROC-AUC 0.668 from markdown report, 0.333 from JSON) are invalidated.",
        "- See docs/evidence/metric_inconsistency_diagnosis.md for root cause.",
    ]
    with open(VERIFIED_METRICS_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    artifacts.append(str(VERIFIED_METRICS_MD_PATH))

    logger.info("Verified metrics written to %s", VERIFIED_METRICS_JSON_PATH)
    logger.info("Verified metrics written to %s", VERIFIED_METRICS_MD_PATH)

    # Step 12 -- write governance validation-run record
    logger.info("Writing governance validation-run record...")
    gov_record = create_validation_run_record()
    gov_paths = write_validation_run_record(gov_record)
    artifacts.append(gov_paths["run_path"])
    artifacts.append(gov_paths["latest_path"])

    # Step 13 -- local MLflow validation tracking (optional; failure does not stop pipeline)
    try:
        from utils.mlflow_tracking import run_mlflow_tracking_summary
        logger.info("Logging validation run to local MLflow tracking...")
        mlflow_result = run_mlflow_tracking_summary(
            performance_report=performance_report,
            governance_run_id=gov_record["validation_run_id"],
        )
        logger.info(
            "MLflow run logged: run_id=%s status=%s",
            mlflow_result.get("run_id", "n/a"),
            mlflow_result.get("status", "n/a"),
        )
    except Exception as exc:
        logger.warning("MLflow tracking did not complete (pipeline not affected): %s", exc)
        warnings.append(f"MLflow tracking skipped: {exc}")

    # Step 14 -- local audit pack generation (optional; failure does not stop pipeline)
    try:
        from utils.audit_pack import generate_audit_pack
        logger.info("Generating local audit pack...")
        audit_result = generate_audit_pack()
        logger.info(
            "Audit pack generated: md=%s html=%s pdf=%s",
            audit_result.get("markdown_path", "n/a"),
            audit_result.get("html_path", "n/a"),
            audit_result.get("pdf_status", "n/a"),
        )
        if audit_result.get("markdown_path"):
            artifacts.append(audit_result["markdown_path"])
        for w in audit_result.get("warnings", []):
            warnings.append(f"Audit pack: {w}")
    except Exception as exc:
        logger.warning("Audit pack generation did not complete (pipeline not affected): %s", exc)
        warnings.append(f"Audit pack skipped: {exc}")

    logger.info("AgentX pipeline complete.")

    return {
        "status": "complete",
        "metrics": performance_report,
        "artifacts": artifacts,
        "warnings": warnings,
        "governance_run_id": gov_record["validation_run_id"],
    }


if __name__ == "__main__":
    run_agentx_pipeline()
