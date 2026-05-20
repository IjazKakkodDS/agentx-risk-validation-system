"""
utils/audit_pack.py -- Local audit pack generation for AgentX.

Generates a multi-format audit pack (Markdown, HTML, PDF) from available
local evidence artifacts. Uses markdown2 for HTML and fpdf2 for PDF.
No system binaries required.

This is a local development and portfolio evidence tool.
It is not a regulatory audit record and does not constitute regulatory approval.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from utils.config import (
    AUDIT_PACK_DIR,
    AUDIT_PACK_HTML_PATH,
    AUDIT_PACK_JSON_PATH,
    AUDIT_PACK_MD_PATH,
    AUDIT_PACK_PDF_PATH,
    COMPLIANCE_REPORT_PATH,
    DRIFT_REPORT_PATH,
    EVIDENCE_DIR,
    GOVERNANCE_LATEST_PATH,
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_TRACKING_DIR,
    VERIFIED_METRICS_JSON_PATH,
)
from utils.logging_utils import setup_logger

logger = setup_logger("agentx.audit_pack")

CLAIM_SAFETY_NOTE = (
    "This audit pack is a local development and portfolio evidence document. "
    "It is not a regulatory audit record and does not constitute regulatory approval, "
    "regulatory certification, or a production compliance determination."
)

LIMITATIONS: List[str] = [
    "The model is a baseline LogisticRegression pipeline on a 5,000-row public sample.",
    "Low recall (0.037) is a documented limitation of the unweighted baseline on an 81/19 imbalanced target.",
    "Compliance output is advisory only; it is not a regulatory determination.",
    "Drift detection uses a simulated incoming dataset; not live production data.",
    "This system has not been deployed to any production environment.",
    "No regulatory body has reviewed or approved this system.",
]


def _safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read %s: %s", path, exc)
    return {}


def collect_audit_pack_context() -> Dict[str, Any]:
    """Collect all available local evidence into a clean, secret-free context dict."""
    metrics_data = _safe_read_json(VERIFIED_METRICS_JSON_PATH)
    drift_data = _safe_read_json(DRIFT_REPORT_PATH)
    governance_data = _safe_read_json(GOVERNANCE_LATEST_PATH)
    compliance_data = _safe_read_json(COMPLIANCE_REPORT_PATH)
    benchmark_data = _safe_read_json(EVIDENCE_DIR / "benchmark_results.json")

    metrics = metrics_data.get("metrics", {})

    validation_run_id = governance_data.get("validation_run_id", "not_available")
    reviewer_status = governance_data.get("reviewer_status", "not_available")
    risk_flags = governance_data.get("risk_flags", [])

    drift_detected = drift_data.get("drift_detected", False)
    drifted_features = [
        d["feature"]
        for d in drift_data.get("details", [])
        if d.get("drifted")
    ]

    compliance_answer = (
        compliance_data.get("answer") or compliance_data.get("content") or ""
    )
    compliance_source = compliance_data.get("source", "not_available")
    evidence_grounded = compliance_data.get("evidence_grounded", False)

    endpoint_benchmarks = benchmark_data.get("endpoints", {})
    pipeline_benchmark = benchmark_data.get("pipeline", {})

    mlflow_available = (
        MLFLOW_TRACKING_DIR.exists() and any(MLFLOW_TRACKING_DIR.iterdir())
    )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "validation_run_id": validation_run_id,
        "system_name": "AgentX Risk Validator",
        "system_version": "1.0.0",
        "roc_auc": metrics.get("roc_auc"),
        "accuracy": metrics.get("accuracy"),
        "precision": metrics.get("precision"),
        "recall": metrics.get("recall"),
        "f1_score": metrics.get("f1_score"),
        "dataset_rows": metrics_data.get("total_rows"),
        "feature_count": metrics_data.get("feature_count"),
        "model_type": metrics_data.get("model_type"),
        "class_balance": metrics_data.get("class_balance"),
        "drift_detected": drift_detected,
        "drifted_features": drifted_features,
        "reviewer_status": reviewer_status,
        "risk_flags": risk_flags,
        "compliance_source": compliance_source,
        "evidence_grounded": evidence_grounded,
        "compliance_summary": compliance_answer[:500] if compliance_answer else "",
        "benchmark_health_median_ms": endpoint_benchmarks.get(
            "GET /health", {}
        ).get("median_ms"),
        "benchmark_validate_median_ms": pipeline_benchmark.get("median_ms"),
        "mlflow_available": mlflow_available,
        "mlflow_experiment": MLFLOW_EXPERIMENT_NAME if mlflow_available else None,
        "claim_safety_note": CLAIM_SAFETY_NOTE,
        "limitations": LIMITATIONS,
    }


def render_audit_markdown(context: Dict[str, Any]) -> str:
    """Build a complete Markdown string from the audit pack context."""
    drifted = context.get("drifted_features", [])
    risk = context.get("risk_flags", [])
    compliance_summary = context.get("compliance_summary", "")

    lines = [
        "# AgentX Risk Validator -- Local Audit Pack",
        "",
        f"**Generated:** {context.get('generated_at_utc', 'unknown')}",
        f"**System:** {context.get('system_name', '')} v{context.get('system_version', '')}",
        f"**Validation Run ID:** {context.get('validation_run_id', 'not available')}",
        "",
        "> " + CLAIM_SAFETY_NOTE,
        "",
        "---",
        "",
        "## Verified Model Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| ROC-AUC | {context.get('roc_auc', 'N/A')} |",
        f"| Accuracy | {context.get('accuracy', 'N/A')} |",
        f"| Precision | {context.get('precision', 'N/A')} |",
        f"| Recall | {context.get('recall', 'N/A')} |",
        f"| F1 Score | {context.get('f1_score', 'N/A')} |",
        "",
        "ROC-AUC is the preferred metric (threshold-independent, class-imbalance robust). "
        "Accuracy of 0.804 mostly reflects the 81/19 class balance. "
        "Low recall is a known baseline limitation.",
        "",
        "---",
        "",
        "## Dataset and Model Summary",
        "",
        f"- **Dataset rows:** {context.get('dataset_rows', 'N/A')}",
        f"- **Features:** {context.get('feature_count', 'N/A')}",
        f"- **Model:** {context.get('model_type', 'N/A')}",
        f"- **Class balance:** {context.get('class_balance', 'N/A')}",
        "",
        "---",
        "",
        "## Drift Detection",
        "",
        f"- **Drift detected:** {context.get('drift_detected', False)}",
        f"- **Drifted features:** {', '.join(drifted) if drifted else 'None detected'}",
        "",
        "---",
        "",
        "## Compliance Advisory Summary",
        "",
        f"- **Source:** {context.get('compliance_source', 'not available')}",
        f"- **Evidence grounded:** {context.get('evidence_grounded', False)}",
        "",
        "**Advisory (first 500 characters):**",
        "",
        compliance_summary if compliance_summary else "No compliance advisory available.",
        "",
        "> Compliance output is advisory only. It does not constitute regulatory approval.",
        "",
        "---",
        "",
        "## Governance Record",
        "",
        f"- **Validation run ID:** {context.get('validation_run_id', 'not available')}",
        f"- **Reviewer status:** {context.get('reviewer_status', 'not available')}",
        f"- **Risk flags:** {', '.join(risk) if risk else 'None'}",
        "",
        "---",
        "",
        "## Benchmark Summary",
        "",
        f"- **GET /health median:** {context.get('benchmark_health_median_ms', 'N/A')} ms (in-process TestClient, not network)",
        f"- **POST /validate median:** {context.get('benchmark_validate_median_ms', 'N/A')} ms (full pipeline)",
        "",
        "> Benchmark measurements are from a local development machine. "
        "They do not represent production or network performance.",
        "",
        "---",
        "",
        "## MLflow Tracking",
        "",
        f"- **Available:** {context.get('mlflow_available', False)}",
        f"- **Experiment:** {context.get('mlflow_experiment', 'N/A')}",
        "- **Tracking:** Local file store only. No remote server. No model registry.",
        "",
        "---",
        "",
        "## Limitations",
        "",
    ]
    for lim in context.get("limitations", []):
        lines.append(f"- {lim}")

    lines += [
        "",
        "---",
        "",
        "## Claim Safety",
        "",
        CLAIM_SAFETY_NOTE,
    ]

    return "\n".join(lines)


def write_audit_markdown(context: Dict[str, Any]) -> Path:
    """Write audit pack Markdown to AUDIT_PACK_MD_PATH."""
    AUDIT_PACK_DIR.mkdir(parents=True, exist_ok=True)
    md_text = render_audit_markdown(context)
    AUDIT_PACK_MD_PATH.write_text(md_text, encoding="utf-8")
    logger.info("Audit pack Markdown written to %s", AUDIT_PACK_MD_PATH)
    return AUDIT_PACK_MD_PATH


def write_audit_html(markdown_text: str) -> Path:
    """Convert Markdown to HTML using markdown2 and write to AUDIT_PACK_HTML_PATH."""
    try:
        import markdown2  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "markdown2 is required for HTML generation. "
            "Install it with: pip install markdown2"
        ) from exc

    AUDIT_PACK_DIR.mkdir(parents=True, exist_ok=True)
    html_body = markdown2.markdown(markdown_text, extras=["tables"])
    html_doc = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        "  <title>AgentX Local Audit Pack</title>\n"
        "  <style>\n"
        "    body{font-family:Arial,sans-serif;max-width:960px;margin:40px auto;padding:0 20px;line-height:1.6}\n"
        "    table{border-collapse:collapse;width:100%;margin:16px 0}\n"
        "    th,td{border:1px solid #ccc;padding:8px 12px;text-align:left}\n"
        "    th{background:#f2f2f2}\n"
        "    blockquote{border-left:4px solid #ccc;margin:0;padding-left:16px;color:#555}\n"
        "    code,pre{background:#f4f4f4;padding:2px 6px;border-radius:3px}\n"
        "    h1,h2,h3{color:#222}\n"
        "    hr{border:none;border-top:1px solid #ddd}\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        f"{html_body}\n"
        "</body>\n"
        "</html>\n"
    )
    AUDIT_PACK_HTML_PATH.write_text(html_doc, encoding="utf-8")
    logger.info("Audit pack HTML written to %s", AUDIT_PACK_HTML_PATH)
    return AUDIT_PACK_HTML_PATH


def write_audit_pdf(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a PDF audit pack using fpdf2 (pure Python, no system binary required).
    Returns a dict with status, path (if succeeded), and optional reason.
    """
    try:
        from fpdf import FPDF  # type: ignore
    except ImportError:
        return {"status": "skipped", "reason": "fpdf2 not installed", "path": None}

    try:
        AUDIT_PACK_DIR.mkdir(parents=True, exist_ok=True)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        pdf.set_margins(20, 20, 20)

        def _safe(text: str) -> str:
            return str(text).encode("latin-1", errors="replace").decode("latin-1")

        def heading(text: str, size: int = 13) -> None:
            pdf.set_font("Helvetica", "B", size)
            pdf.multi_cell(0, 8, _safe(text))
            pdf.ln(1)

        def body(text: str, size: int = 10) -> None:
            pdf.set_font("Helvetica", "", size)
            pdf.multi_cell(0, 6, _safe(text))

        def rule() -> None:
            pdf.ln(3)
            pdf.set_draw_color(180, 180, 180)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(4)

        heading("AgentX Risk Validator - Local Audit Pack", 15)
        body(f"Generated: {context.get('generated_at_utc', 'unknown')}")
        body(f"Validation Run ID: {context.get('validation_run_id', 'N/A')}")
        body(f"System: {context.get('system_name', '')} v{context.get('system_version', '')}")
        pdf.ln(2)
        body(CLAIM_SAFETY_NOTE)
        rule()

        heading("Verified Model Metrics")
        for label, key in [
            ("ROC-AUC", "roc_auc"),
            ("Accuracy", "accuracy"),
            ("Precision", "precision"),
            ("Recall", "recall"),
            ("F1 Score", "f1_score"),
        ]:
            body(f"  {label}: {context.get(key, 'N/A')}")
        rule()

        heading("Dataset and Model")
        body(f"  Rows: {context.get('dataset_rows', 'N/A')}")
        body(f"  Features: {context.get('feature_count', 'N/A')}")
        body(f"  Model: {context.get('model_type', 'N/A')}")
        body(f"  Class balance: {context.get('class_balance', 'N/A')}")
        rule()

        heading("Drift Detection")
        drifted = context.get("drifted_features", [])
        body(f"  Drift detected: {context.get('drift_detected', False)}")
        body(f"  Drifted features: {', '.join(drifted) if drifted else 'None'}")
        rule()

        heading("Governance Record")
        body(f"  Validation run ID: {context.get('validation_run_id', 'N/A')}")
        body(f"  Reviewer status: {context.get('reviewer_status', 'N/A')}")
        risk = context.get("risk_flags", [])
        body(f"  Risk flags: {', '.join(risk) if risk else 'None'}")
        rule()

        heading("Compliance Advisory")
        body(f"  Source: {context.get('compliance_source', 'N/A')}")
        body(f"  Evidence grounded: {context.get('evidence_grounded', False)}")
        summary = context.get("compliance_summary", "")
        if summary:
            body(f"  Summary: {summary[:300]}")
        body("  Advisory only. Not a regulatory determination.")
        rule()

        heading("Benchmark Summary")
        body(f"  GET /health median: {context.get('benchmark_health_median_ms', 'N/A')} ms")
        body(f"  POST /validate median: {context.get('benchmark_validate_median_ms', 'N/A')} ms")
        body("  Local development machine measurements (in-process TestClient).")
        rule()

        heading("MLflow Tracking")
        body(f"  Available: {context.get('mlflow_available', False)}")
        body(f"  Experiment: {context.get('mlflow_experiment', 'N/A')}")
        body("  Local file store only. No remote server.")
        rule()

        heading("Limitations")
        for lim in context.get("limitations", []):
            body(f"  - {lim}")
        rule()

        heading("Claim Safety Note")
        body(CLAIM_SAFETY_NOTE)

        pdf.output(str(AUDIT_PACK_PDF_PATH))
        logger.info("Audit pack PDF written to %s", AUDIT_PACK_PDF_PATH)
        return {"status": "ok", "path": str(AUDIT_PACK_PDF_PATH), "reason": None}

    except Exception as exc:
        logger.warning("PDF generation did not complete: %s", exc)
        return {"status": "error", "reason": str(exc), "path": None}


def generate_audit_pack() -> Dict[str, Any]:
    """
    Generate the full local audit pack (Markdown, HTML, PDF).
    Never raises. Returns a summary dict with status, paths, and warnings.
    """
    warnings_list = []
    result: Dict[str, Any] = {
        "status": "ok",
        "markdown_path": None,
        "html_path": None,
        "pdf_status": None,
        "pdf_path": None,
        "warnings": warnings_list,
    }

    try:
        context = collect_audit_pack_context()

        AUDIT_PACK_DIR.mkdir(parents=True, exist_ok=True)
        AUDIT_PACK_JSON_PATH.write_text(
            json.dumps(context, indent=2, default=str), encoding="utf-8"
        )

        md_path = write_audit_markdown(context)
        result["markdown_path"] = str(md_path)
        md_text = md_path.read_text(encoding="utf-8")

        try:
            html_path = write_audit_html(md_text)
            result["html_path"] = str(html_path)
        except Exception as exc:
            warnings_list.append(f"HTML generation skipped: {exc}")
            logger.warning("Audit pack HTML generation did not complete: %s", exc)

        pdf_result = write_audit_pdf(context)
        result["pdf_status"] = pdf_result["status"]
        result["pdf_path"] = pdf_result.get("path")
        if pdf_result["status"] != "ok":
            warnings_list.append(f"PDF: {pdf_result.get('reason', 'unknown')}")

        logger.info(
            "Audit pack generated: md=%s html=%s pdf=%s",
            result["markdown_path"],
            result["html_path"],
            result["pdf_status"],
        )

    except Exception as exc:
        logger.error("Audit pack generation error: %s", exc)
        result["status"] = "error"
        result["error"] = str(exc)

    return result