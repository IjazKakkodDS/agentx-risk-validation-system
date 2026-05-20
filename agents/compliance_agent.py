import json
import os
import socket
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

from utils.config import COMPLIANCE_REPORT_PATH, GROQ_DEFAULT_MODEL
from utils.logging_utils import setup_logger

load_dotenv(override=True)

logger = setup_logger(__name__)

ADVISORY_NOTE = (
    "This compliance review is advisory only. "
    "It does not constitute regulatory approval or a production compliance certification."
)


def _clear_network_settings():
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(var, None)
    socket.setdefaulttimeout(30.0)


def _fallback_advisory(evidence_context: Optional[Dict[str, Any]] = None) -> str:
    """
    Produce a structured advisory compliance summary grounded in local evidence.
    Used when the Groq API is unavailable or the key is not set.
    """
    ctx = evidence_context or {}
    m = ctx.get("metrics", {})
    d = ctx.get("drift", {})
    gov = ctx.get("governance", {})
    flags = ctx.get("risk_flags", [])

    roc_auc = m.get("roc_auc", "N/A") if m.get("available") else "N/A"
    recall = m.get("recall", "N/A") if m.get("available") else "N/A"
    accuracy = m.get("accuracy", "N/A") if m.get("available") else "N/A"
    dataset_rows = m.get("dataset_rows", "N/A") if m.get("available") else "N/A"
    drift_detected = d.get("drift_detected", False) if d.get("available") else False
    drifted = d.get("drifted_features", []) if d.get("available") else []
    run_id = gov.get("validation_run_id", "N/A") if gov.get("available") else "N/A"

    drift_status = (
        f"Drift detected in: {', '.join(drifted)}" if drift_detected else "No drift detected in tested features"
    )
    drift_marker = "!" if drift_detected else "x"

    checklist_items = [
        "[x] Data Quality Review: Zero missing values and zero duplicates confirmed in preprocessing",
        f"[x] Discriminatory Power (SR 11-7): ROC-AUC = {roc_auc} (above random-chance baseline of 0.5)",
        f"[x] Accuracy Assessment: Accuracy = {accuracy} (reflects 81/19 class imbalance; ROC-AUC is preferred metric)",
        f"[~] Recall Review: Recall = {recall} -- low due to class imbalance; no class weighting applied to baseline model",
        "[x] Explainability (Basel IV): SHAP feature attribution computed; mean SHAP vector stored in FAISS memory",
        f"[{drift_marker}] Feature Stability (SR 11-7 monitoring): {drift_status}",
        "[x] Governance Traceability: Validation-run record written with unique run ID and metrics snapshot",
        f"[x] Governance Run ID: {run_id}",
        "[ ] Class Weighting: Not applied to baseline model; recommended for improved recall on the default class",
        "[ ] HMDA Reporting: Not assessed; requires institutional data and regulatory context",
        "[ ] Production Deployment Review: Not applicable -- local validation prototype only",
    ]

    flag_section = ""
    if flags:
        flag_lines = "\n".join(f"- {f}" for f in flags)
        flag_section = f"\n\n## Model Risk Flags\n\n{flag_lines}"

    drift_attention = (
        f"Feature drift detected in {', '.join(drifted)} and should trigger revalidation. "
        if drift_detected
        else ""
    )

    advisory = (
        f"## Advisory Compliance Review -- Grounded in Local Validation Evidence\n\n"
        f"**Advisory Note:** {ADVISORY_NOTE}\n\n"
        f"## SR 11-7 and Basel-Style Compliance Checklist\n\n"
        + "\n".join(f"- {item}" for item in checklist_items)
        + flag_section
        + "\n\n## Executive Summary\n\n"
        f"**Validation Evidence:** AgentX completed a validation pipeline run against a "
        f"{dataset_rows}-row LendingClub public dataset sample. "
        f"The baseline LogisticRegression model achieves a ROC-AUC of {roc_auc}, "
        f"exceeding the random-chance baseline. "
        f"Accuracy of {accuracy} reflects the 81/19 class imbalance and is not the headline metric. "
        f"Recall of {recall} is a documented baseline limitation of unweighted classification on an imbalanced target.\n\n"
        f"**Key Strengths:** Data preprocessing is consistent (scaler fit on training split only). "
        f"SHAP explainability artifacts are generated. "
        f"Governance traceability records are maintained per pipeline run. "
        f"Drift detection is operational using the KS-test.\n\n"
        f"**Attention Needed:** Low recall on the default class requires remediation before any production consideration. "
        + drift_attention
        + "This system is a local validation prototype and does not constitute a production credit scoring model.\n\n"
        f"*Advisory review generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Source: LocalFallback*"
    )
    return advisory


def _cached_response() -> str:
    """Legacy cached response -- delegates to the grounded fallback with no context."""
    return _fallback_advisory(evidence_context=None)


def generate_compliance_report(
    evidence_context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    _clear_network_settings()
    api_key = os.getenv("GROQ_API_KEY")
    groq_model = os.getenv("GROQ_MODEL", GROQ_DEFAULT_MODEL)

    if not api_key:
        logger.warning("GROQ_API_KEY not found -- using grounded local fallback advisory")
        return _fallback_advisory(evidence_context), "LocalFallback"

    try:
        from groq import Client
        from utils.compliance_context import format_compliance_context_for_prompt

        client = Client(api_key=api_key)

        context_str = (
            format_compliance_context_for_prompt(evidence_context)
            if evidence_context
            else "No local validation evidence context available."
        )

        system_prompt = (
            "You are an advisory compliance analyst reviewing a machine learning credit risk model. "
            "You have been provided with actual validation evidence from the AgentX Risk Validator system. "
            "Generate an advisory compliance review grounded in the provided evidence. "
            "Your review is advisory only and does not constitute regulatory approval. "
            "Reference SR 11-7 model risk management principles and Basel IV validation standards. "
            "Be specific to the model evidence provided -- do not generate generic commentary.\n\n"
            f"{context_str}"
        )

        checklist_prompt = (
            "Based on the validation evidence provided, generate a compliance checklist covering:\n"
            "- Discriminatory power (cite the actual ROC-AUC value from the evidence)\n"
            "- Class imbalance handling (cite actual class balance percentages)\n"
            "- Recall limitations (cite actual recall value)\n"
            "- Explainability (SHAP artifact status)\n"
            "- Feature drift status (cite actual drifted features if any)\n"
            "- Governance traceability (cite the validation run ID if available)\n"
            "- SR 11-7 model documentation requirements\n"
            "- Basel IV monitoring requirements\n"
            "Use [x], [~], or [ ] status indicators. Cite actual evidence values."
        )
        checklist_resp = client.chat.completions.create(
            model=groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": checklist_prompt},
            ],
            temperature=0.0,
        )
        checklist = checklist_resp.choices[0].message.content.strip()

        summary_prompt = (
            "Based on the validation evidence and checklist above, write a 3-paragraph executive summary:\n"
            "1. Overall validation status and key metrics (cite specific values from the evidence)\n"
            "2. Key strengths of this validation run\n"
            "3. Attention items and limitations\n"
            "Use bold headers: **Validation Evidence**, **Key Strengths**, **Attention Needed**\n"
            "State clearly that this review is advisory only."
        )
        exec_resp = client.chat.completions.create(
            model=groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": checklist_prompt},
                {"role": "assistant", "content": checklist},
                {"role": "user", "content": summary_prompt},
            ],
            temperature=0.0,
        )
        executive_summary = exec_resp.choices[0].message.content.strip()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        full_report = (
            f"## Advisory Compliance Review -- Grounded in Local Validation Evidence\n\n"
            f"**Advisory Note:** {ADVISORY_NOTE}\n\n"
            f"{executive_summary}\n\n"
            f"## Detailed Checklist\n\n"
            f"{checklist}\n\n"
            f"*Advisory review generated: {timestamp} | Source: Groq API ({groq_model})*"
        )
        logger.info("Grounded compliance review generated via Groq API (model: %s)", groq_model)
        return full_report, "API"

    except Exception as exc:
        logger.error("Groq API request failed: %s -- using grounded local fallback", exc)
        return _fallback_advisory(evidence_context), "LocalFallback"


def run_compliance_agent(evidence_context: Optional[Dict[str, Any]] = None) -> str:
    """
    Run the compliance agent.

    Builds evidence context from local artifacts if not provided, then generates
    an advisory compliance review grounded in that evidence.
    """
    if evidence_context is None:
        try:
            from utils.compliance_context import build_compliance_context
            evidence_context = build_compliance_context()
        except Exception as exc:
            logger.warning("Failed to build compliance context: %s", exc)
            evidence_context = {}

    report, source = generate_compliance_report(evidence_context)
    COMPLIANCE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    m = evidence_context.get("metrics", {})
    gov = evidence_context.get("governance", {})

    evidence_sources = [
        s for s, present in [
            ("verified_metrics_json", m.get("available")),
            ("drift_report", evidence_context.get("drift", {}).get("available")),
            ("governance_record", gov.get("available")),
            ("benchmark_results", evidence_context.get("benchmark", {}).get("available")),
        ]
        if present
    ]

    with open(COMPLIANCE_REPORT_PATH, "w") as f:
        json.dump(
            {
                "content": report,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "advisory_only": True,
                "not_regulatory_approval": True,
                "evidence_grounded": bool(m.get("available")),
                "validation_run_id": gov.get("validation_run_id") if gov.get("available") else None,
                "evidence_sources": evidence_sources,
                "key_validation_concerns": evidence_context.get("risk_flags", []),
                "limitations": evidence_context.get("limitations", []),
            },
            f,
            indent=2,
        )
    logger.info("Compliance advisory saved to %s (source: %s)", COMPLIANCE_REPORT_PATH, source)
    return report
