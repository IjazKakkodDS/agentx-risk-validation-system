# AgentX Risk Validator -- Local Audit Pack Report

**Phase:** 5B.9
**Date:** 2026-05-20
**Status:** COMPLETE -- local audit pack (Markdown, HTML, PDF) generated on each pipeline run

---

## Problem: Old PDF Dependency (GAP-014)

`generate_pdf.py` used `pdfkit` with a hardcoded Windows binary path:

```python
config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
```

This required `wkhtmltopdf` to be installed at that exact path. On any other machine
(Linux, macOS, Docker, another Windows installation), `generate_pdf.py` would fail.
This was classified as GAP-014 (P3 -- portability).

---

## Solution: Pure-Python Audit Pack (Phase 5B.9)

`utils/audit_pack.py` was created as a replacement for `generate_pdf.py` in the
pipeline output path. It uses only Python packages already listed in `requirements.txt`:

| Format | Library | System binary required |
|---|---|---|
| Markdown | stdlib (pathlib, json) | None |
| HTML | markdown2 (2.5.3) | None |
| PDF | fpdf2 | None |

`pdfkit` and `wkhtmltopdf` are not used in the new path. `generate_pdf.py` is
retained as a standalone legacy script (unchanged) but is not called by the pipeline.

---

## Audit Pack Contents

Each audit pack includes the following sections:

| Section | Source |
|---|---|
| Generated timestamp and run ID | UTC timestamp + governance record |
| Verified model metrics | docs/evidence/verified_metrics.json |
| Dataset and model summary | docs/evidence/verified_metrics.json |
| Drift detection results | data/validation_outputs/drift_report.json |
| Compliance advisory summary | data/validation_outputs/last_compliance.json |
| Governance record | data/governance/latest_validation_run.json |
| Benchmark summary | docs/evidence/benchmark_results.json |
| MLflow tracking status | mlruns/ directory check |
| Limitations | Hardcoded list (not generated, not model-specific) |
| Claim-safety note | Hardcoded constant |

No raw data rows, API keys, or secrets are included.

---

## Generated Files

| File | Path | Format |
|---|---|---|
| Audit pack Markdown | reports/audit_pack/audit_pack.md | Markdown |
| Audit pack HTML | reports/audit_pack/audit_pack.html | HTML with embedded CSS |
| Audit pack PDF | reports/audit_pack/audit_pack.pdf | PDF via fpdf2 |
| Audit context JSON | reports/audit_pack/audit_pack_context.json | Machine-readable context |

All four files are excluded from git by `.gitignore` (`reports/audit_pack/`).

---

## Verified First Run (2026-05-20)

Pipeline run after Phase 5B.9 wiring:

| Item | Value |
|---|---|
| Markdown generated | Yes (reports/audit_pack/audit_pack.md) |
| HTML generated | Yes (reports/audit_pack/audit_pack.html) |
| PDF generated | Yes (reports/audit_pack/audit_pack.pdf) |
| PDF status | ok |
| ROC-AUC in audit pack | 0.6776 (confirmed from verified_metrics.json) |
| Pipeline completed | Yes (exit status: complete) |
| MLflow run | Logged (agentx_risk_validation) |

---

## Integration Architecture

Audit pack generation is Step 14 of `run_agentx_pipeline()` in `main.py`:

```python
try:
    from utils.audit_pack import generate_audit_pack
    audit_result = generate_audit_pack()
except Exception as exc:
    logger.warning("Audit pack generation did not complete (pipeline not affected): %s", exc)
    warnings.append(f"Audit pack skipped: {exc}")
```

The entire step is wrapped in try/except. Any failure logs a warning and appends
to `result["warnings"]` but does not stop or fail the pipeline.

---

## API Integration

`GET /evidence` now returns `audit_pack_available`:

```json
{
  "evidence_files": [...],
  "generated_artifacts": [...],
  "governance_available": true,
  "mlflow_tracking_available": true,
  "audit_pack_available": true
}
```

`audit_pack_available` is `True` when `reports/audit_pack/audit_pack.md` exists.

---

## New Utility Module

`utils/audit_pack.py` provides:

| Function | Purpose |
|---|---|
| `collect_audit_pack_context()` | Reads local evidence artifacts; returns clean context dict |
| `render_audit_markdown(context)` | Builds complete Markdown string from context |
| `write_audit_markdown(context)` | Writes MD to AUDIT_PACK_MD_PATH; returns Path |
| `write_audit_html(markdown_text)` | Uses markdown2 to convert MD to HTML; writes file |
| `write_audit_pdf(context)` | Uses fpdf2 to write PDF; returns status dict; never raises |
| `generate_audit_pack()` | Orchestrates all steps; returns summary dict; never raises |

---

## Test Coverage

`tests/test_audit_pack.py` contains 31 tests:

| Test Group | Count | Coverage |
|---|---|---|
| Module imports and constants | 4 | All exports present, CLAIM_SAFETY_NOTE, LIMITATIONS |
| `collect_audit_pack_context` | 6 | Expected keys, no secrets, no-files robustness, ROC-AUC from real file, system name, limitations |
| `render_audit_markdown` | 7 | Non-empty, claim safety, ROC-AUC, metrics heading, drift features, limitations, run ID |
| `write_audit_markdown` | 2 | Creates file, returns Path |
| `write_audit_html` | 3 | Non-empty, has HTML tag, contains ROC-AUC |
| `write_audit_pdf` | 3 | Returns status dict, does not raise, graceful when fpdf2 missing |
| `generate_audit_pack` | 6 | Returns ok, creates markdown, status dict keys, no secrets, warnings list, real metrics |

All 31 tests pass. Tests use `tmp_path` and `monkeypatch.setattr` to isolate from
real file paths. No live Groq API calls are made.

After this addition: total passing fast tests = 268.

---

## Limitations

- PDF is generated using fpdf2 text layout, not a full HTML-to-PDF renderer. Tables appear as plain text rows.
- Markdown is the primary evidence artifact; PDF is a supplementary convenience output.
- Compliance advisory is truncated to 500 characters in the audit pack summary.
- All audit pack outputs are local-only and excluded from git.
- The audit pack is not a regulatory audit record and does not constitute regulatory approval.

---

## Claim-Safe Wording

Safe to state:
- "Each AgentX pipeline run generates a local audit pack in Markdown, HTML, and PDF formats."
- "The audit pack includes verified metrics, drift status, compliance advisory summary, governance run ID, benchmark summary, and MLflow tracking status."
- "PDF generation uses fpdf2 (pure Python, no system binary required). No pdfkit or wkhtmltopdf dependency."
- "Audit pack outputs are excluded from git. They are local development evidence only."
- "The audit pack is not a regulatory audit record and does not constitute regulatory approval."

Not safe to state:
- "Audit certified" -- not an official or regulatory certification.
- "Regulatory audit record" -- the audit pack is local development evidence only.
- "Production audit trail" -- not deployed, not production.