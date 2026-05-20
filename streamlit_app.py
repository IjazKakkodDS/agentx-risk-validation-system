# ------------------------------------------------------------
# AgentX Risk Validator – Streamlit front-end  v1.2.5
# ------------------------------------------------------------
# Compatible with Streamlit 1.10 → 1.33+
# ------------------------------------------------------------

import os, json, hashlib
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import joblib
from PIL import Image
import faiss

# Plotly
import plotly.express as px
import plotly.graph_objects as go

# PDF + metrics
from fpdf import FPDF
from sklearn.metrics import confusion_matrix, roc_curve, auc

# Agents / utils
from utils.config import MODEL_PATH
from utils.load_data import preprocess_uploaded_data
from agents.data_validator_agent import validate_data
from agents.performance_agent import evaluate_model
from agents.explainability_agent import explain_model
from agents.compliance_agent import run_compliance_agent
from agents.drift_monitor_agent import detect_drift

# Optional MIME sniff
try:
    import magic  # type: ignore
except ImportError:
    magic = None

# ============================================================
# CONSTANTS
# ============================================================
MAX_UPLOAD_SIZE_MB = 50
ALLOWED_DATA_MIME = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
ALLOWED_MODEL_EXT = {".pkl", ".joblib"}

PRIMARY_COLOR   = "#2A3F5F"
SECONDARY_COLOR = "#6C8EBF"
SUCCESS_COLOR   = "#4CAF50"
WARNING_COLOR   = "#FFC107"
DANGER_COLOR    = "#D32F2F"

# ============================================================
# SAFE HELPERS (old Streamlit support)
# ============================================================
DEFAULT_PAGE_CONFIG = dict(
    page_title="AgentX Risk Validator",
    layout="wide",
    page_icon="💰",
    initial_sidebar_state="expanded",
)

def _safe_set_page_config(base_theme: str | None = None):
    """Call set_page_config; ignore unsupported theme kw on very old Streamlit."""
    try:
        if base_theme:
            st.set_page_config(**DEFAULT_PAGE_CONFIG, theme={"base": base_theme})
        else:
            st.set_page_config(**DEFAULT_PAGE_CONFIG)
    except TypeError:
        st.set_page_config(**DEFAULT_PAGE_CONFIG)

def _safe_rerun():
    """Trigger a script rerun, API-agnostic."""
    if hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    elif hasattr(st, "rerun"):
        st.rerun()

# ============================================================
# THEME PREFERENCE  (must run before any UI)
# ============================================================
if "theme_choice" not in st.session_state:
    st.session_state.theme_choice = "Auto"

choice = st.session_state.theme_choice
_safe_set_page_config(None if choice == "Auto" else choice.lower())

effective_base = (choice.lower()
                  if choice != "Auto"
                  else st.get_option("theme.base") or "light")

if effective_base == "dark":
    BG, FG, CARD = "#1E1E1E", "#E8EAF6", "#21262D"
else:
    BG, FG, CARD = "#F5F7FA", PRIMARY_COLOR, "#FFFFFF"

# ============================================================
# UTILITY FUNCTIONS
# ============================================================
def _bytes_to_mb(n: int) -> float:
    return n / (1024 * 1024)

def _sniff_mime(blob: bytes) -> str:
    if magic is None:
        return ""
    try:
        return magic.from_buffer(blob[:2048], mime=True)  # type: ignore
    except Exception:
        return ""

def _hash_vec(vec: np.ndarray) -> str:
    return hashlib.sha1(vec.astype("float32").tobytes()).hexdigest()

# ============================================================
# CACHING
# ============================================================
@st.cache_resource(show_spinner=False)
def load_model(path: str):
    if not os.path.exists(path):
        st.error(f"Model file not found: {path}")
        st.stop()
    try:
        mdl = joblib.load(path)
        if not hasattr(mdl, "predict_proba"):
            raise AttributeError("Loaded object lacks predict_proba")
        return mdl
    except Exception as e:
        st.error(f"Model loading failed: {e}")
        st.stop()

@st.cache_data(show_spinner="Pre-processing & validation…")
def validate_full(df: pd.DataFrame):
    clean = preprocess_uploaded_data(df)
    report = validate_data(clean)
    return clean, report

@st.cache_data(show_spinner="Evaluating performance…")
def perf(_mdl, X, y):                    # _mdl ⇒ unhashable safe
    return evaluate_model(_mdl, X, y)

@st.cache_data(show_spinner="Computing SHAP…")
def shap_data(_mdl, X_sample: pd.DataFrame):
    d = explain_model(_mdl, X_sample)
    if "mean_vector" not in d:
        raise ValueError("explain_model returned invalid payload")
    v = np.asarray(d["mean_vector"], dtype="float32")
    nrm = np.linalg.norm(v)
    if nrm:
        v /= nrm
    return {**d, "normalized_vector": v.tolist(), "norm_factor": float(nrm)}

@st.cache_resource
def memory(dim: int):
    """FAISS memory with duplicate detection & legacy back-fill."""
    class M:
        def __init__(self, d: int):
            self.d = d
            self.idx = faiss.IndexFlatIP(d)
            self.meta: list[dict] = []
            self.p = Path("data/model_memory")
            self.p.mkdir(parents=True, exist_ok=True)

        # ---------- duplicate helpers ----------
        def _dup(self, h: str) -> bool:
            return any(m.get("vec_hash") == h for m in self.meta)

        def add(self, vec: np.ndarray, name: str, extra: dict):
            h = _hash_vec(vec)
            if self._dup(h):
                return
            self.idx.add(vec.reshape(1, -1).astype("float32"))
            self.meta.append({
                "model_name": name,
                "vec_hash":   h,
                "timestamp":  datetime.now().isoformat(),
                **extra
            })

        def find(self, query: np.ndarray, k: int = 5):
            dists, idxs = self.idx.search(query.reshape(1, -1).astype("float32"), k)
            out = []
            for i, dist in zip(idxs[0], dists[0]):
                if i < 0:
                    continue
                m = self.meta[i].copy()
                sim = max(0., min(1., float(dist)))
                m.update(similarity=sim, distance=1 - sim)
                out.append(m)
            return out

        def save(self):
            faiss.write_index(self.idx, str(self.p / "index.faiss"))
            with open(self.p / "metadata.json", "w") as f:
                json.dump(self.meta, f)

        @classmethod
        def load(cls, d: int):
            m = cls(d)
            try:
                m.idx = faiss.read_index(str(m.p / "index.faiss"))
                with open(m.p / "metadata.json") as f:
                    m.meta = json.load(f)

                # back-fill vec_hash if missing
                changed = False
                for rec in m.meta:
                    if rec.get("vec_hash") is None and "vector" in rec:
                        rec["vec_hash"] = _hash_vec(
                            np.asarray(rec["vector"], dtype="float32"))
                        changed = True
                if changed:
                    with open(m.p / "metadata.json", "w") as f:
                        json.dump(m.meta, f)
            except Exception:
                pass
            return m
    return M.load(dim)

@st.cache_data(show_spinner="Checking compliance…")
def compliance():
    try:
        return run_compliance_agent()
    except Exception as e:
        return f"⚠️ {e}"

@st.cache_data(show_spinner="Detecting drift…")
def drift():
    try:
        return detect_drift()
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# GLOBAL CSS
# ============================================================
st.markdown(f"""
<style>
.block-container,.main .block-container{{padding:2rem;background:{BG};color:{FG}!important}}
h1,h2,h3{{color:{FG}!important;border-bottom:2px solid {SECONDARY_COLOR};padding-bottom:.3rem}}
[data-testid="stSidebar"]{{background:linear-gradient(145deg,{PRIMARY_COLOR},#1A2A4F);color:white!important}}
.stButton>button{{background:{SECONDARY_COLOR}!important;color:white!important;border-radius:8px;padding:.5rem 1rem}}
[data-testid="stMetric"]{{background:{CARD};padding:1rem;border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,.1);color:{FG}!important}}
section[data-testid="stFileUploadDropzone"]>div{{background:{CARD};border:2px dashed {SECONDARY_COLOR}}}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE INITIALISATION
# ============================================================
if "init" not in st.session_state:
    st.session_state.update(
        df_raw=None, df_clean=None, validation_report=None,
        performance_report=None, probs=None, y_test=None,
        fpr=None, tpr=None, roc_auc=None, shap_data=None,
        similar_models=None, compliance_summary=None, drift_report=None,
        ov_loan=(0, 50000), ov_purp=[], shap_image=None,
        processing_complete=False, init=True,
    )

# ensure folders exist
Path("data/model_memory").mkdir(parents=True, exist_ok=True)
Path("data/validation_outputs").mkdir(parents=True, exist_ok=True)

# ============================================================
# SIDEBAR  (branding • navigation • theme toggle)
# ============================================================
with st.sidebar:
    st.markdown(
        f"""
        <div style="text-align:center;padding:25px 0 35px;
                    background:linear-gradient(145deg,{PRIMARY_COLOR},#1A2A4F)">
            <img src="https://via.placeholder.com/120x60?text=AgentX+Logo" width="120">
            <h1 style="color:white;margin:15px 0 0">AgentX Risk</h1>
            <p style="color:{SECONDARY_COLOR};font-size:.9rem;margin:4px 0 0">
                AI-Powered Model Validation
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pages = [
        "1. Upload & Preview",
        "2. Overview",
        "3. Performance",
        "4. Explainability",
        "5. Compliance",
        "6. Drift",
        "7. Export",
        "8. Compare Models",
    ]
    selection = st.radio("Navigation", pages, label_visibility="collapsed")

    new_choice = st.radio(
        "Theme",
        ["Auto", "Light", "Dark"],
        horizontal=True,
        index=["Auto", "Light", "Dark"].index(choice),
    )
    if new_choice != choice:
        st.session_state.theme_choice = new_choice
        _safe_rerun()

    st.progress((pages.index(selection) + 1) / len(pages))
    st.caption(f"v1.2.5 • {datetime.now():%Y-%m-%d}")

# ============================================================
# LOAD PRIMARY MODEL
# ============================================================
model = load_model(str(MODEL_PATH))

# ============================================================
# HELPER – column check
# ============================================================
def _check_cols(df: pd.DataFrame) -> bool:
    req = {"loan_amnt", "term", "grade", "purpose", "loan_status"}
    miss = req - set(df.columns)
    if miss:
        st.error("Missing columns: " + ", ".join(sorted(miss)))
        return False
    if len(df) < 1000:
        st.warning("Dataset < 1 000 rows – statistics may be unstable.")
    return True

# ============================================================
# PAGE 1 – UPLOAD & PREVIEW
# ============================================================
if selection == pages[0]:
    st.header("📂 Data Acquisition & Preparation")

    with st.expander("💡 Requirements", True):
        st.markdown(
            "* CSV or Excel\n"
            "* Required: `loan_amnt`, `term`, `grade`, `purpose`, `loan_status`\n"
            "* `loan_status` must be binary (0/1)\n"
            f"* ≤ {MAX_UPLOAD_SIZE_MB} MB"
        )

    upl = st.file_uploader("Upload portfolio", type=["csv", "xlsx"])

    if upl:
        # size & mime guard
        if _bytes_to_mb(upl.size) > MAX_UPLOAD_SIZE_MB:
            st.error("File exceeds 50 MB limit.")
            st.stop()
        mime = _sniff_mime(upl.getvalue())
        if mime and mime not in ALLOWED_DATA_MIME:
            st.error(f"Unsupported MIME type ({mime})")
            st.stop()
        # read
        try:
            df = pd.read_csv(upl) if upl.name.lower().endswith(".csv") else pd.read_excel(upl)
        except Exception as e:
            st.error(f"Read error: {e}")
            st.stop()
        if _check_cols(df):
            st.session_state.df_raw = df
            st.success(f"Loaded {len(df):,} rows • {len(df.columns)} columns")

    # Filters appear after upload
    if st.session_state.df_raw is not None:
        raw = st.session_state.df_raw.copy()
        with st.expander("🔍 Filters", True):
            loan_min, loan_max = map(int, (raw.loan_amnt.min(), raw.loan_amnt.max()))
            loan_sel = st.slider("Loan amount ($)", loan_min, loan_max, st.session_state.ov_loan)

            opt_purposes = sorted(raw.purpose.unique())
            def_purposes = [p for p in st.session_state.ov_purp if p in opt_purposes] or opt_purposes
            purp_sel = st.multiselect("Purposes", opt_purposes, def_purposes)

        view = raw[raw.loan_amnt.between(*loan_sel) & raw.purpose.isin(purp_sel)]
        st.info(f"{len(view):,} rows after filters")

        if st.button("🚀 Process data"):
            with st.spinner("Running validation pipeline…"):
                clean, report = validate_full(view)
                if clean.empty:
                    st.error("Validation produced empty dataframe")
                    st.stop()

                X = clean.drop("loan_status", axis=1)
                y = clean.loan_status.astype(int)
                perf_report = perf(model, X, y)
                probs = model.predict_proba(X)[:, 1]
                fpr, tpr, _ = roc_curve(y, probs)
                roc_val = auc(fpr, tpr)

                shap = shap_data(model, X.iloc[: min(100, len(X))])
                mem = memory(len(shap["normalized_vector"]))
                vec = np.asarray(shap["normalized_vector"], dtype="float32")
                mem.add(vec, "current_model", {})
                similars = mem.find(vec)
                mem.save()

                st.session_state.update(
                    df_clean=clean,
                    validation_report=report,
                    performance_report=perf_report,
                    probs=probs,
                    y_test=y,
                    fpr=fpr,
                    tpr=tpr,
                    roc_auc=roc_val,
                    shap_data=shap,
                    similar_models=similars,
                    compliance_summary=compliance(),
                    drift_report=drift(),
                    ov_loan=loan_sel,
                    ov_purp=purp_sel,
                    processing_complete=True,
                )

                img_path = "data/validation_outputs/shap_summary.png"
                if os.path.exists(img_path):
                    st.session_state.shap_image = Image.open(img_path)

                st.success("✅ Processing complete!")

# ============================================================
# PAGE 2 – OVERVIEW
# ============================================================
elif selection == pages[1]:
    st.header("📊 Portfolio Overview")
    if not st.session_state.processing_complete:
        st.info("Upload & process data first.")
        st.stop()

    dfc = st.session_state.df_clean
    with st.expander("🔧 Dashboard Controls", True):
        loan_min, loan_max = map(int, (dfc.loan_amnt.min(), dfc.loan_amnt.max()))
        loan_sel = st.slider("Loan amount ($)", loan_min, loan_max, st.session_state.ov_loan)

        opt_purposes = sorted(dfc.purpose.unique())
        def_purposes = [p for p in st.session_state.ov_purp if p in opt_purposes]
        purp_sel = st.multiselect("Purposes", opt_purposes, def_purposes)

    filt = dfc[dfc.loan_amnt.between(*loan_sel) & dfc.purpose.isin(purp_sel)]
    if filt.empty:
        st.warning("No data matches current filters.")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total loans", f"{len(filt):,}")
    c2.metric("Default rate", f"{filt.loan_status.mean():.2%}")
    c3.metric("Avg loan size", f"${filt.loan_amnt.mean():,.0f}")
    c4.metric("ROC-AUC", f"{st.session_state.roc_auc:.2f}")

    t1, t2 = st.tabs(["Distribution", "Composition"])
    with t1:
        st.plotly_chart(
            px.histogram(
                filt,
                x="loan_amnt",
                nbins=50,
                color_discrete_sequence=[SECONDARY_COLOR],
                labels={"loan_amnt": "Loan amount ($)"},
            ),
            use_container_width=True,
        )
    with t2:
        l, r = st.columns(2)
        l.plotly_chart(
            px.pie(
                filt.purpose.value_counts().reset_index(),
                names="purpose",
                values="count",
                title="Purpose breakdown",
                hole=0.3,
            ),
            use_container_width=True,
        )
        r.plotly_chart(
            px.bar(
                filt.grade.value_counts().reset_index(),
                x="grade",
                y="count",
                title="Credit-grade distribution",
                color="grade",
            ),
            use_container_width=True,
        )

# ============================================================
# PAGE 3 – PERFORMANCE
# ============================================================
elif selection == pages[2]:
    st.header("📈 Model Performance")
    if not st.session_state.processing_complete:
        st.info("Process data first.")
        st.stop()

    with st.expander("ROC curve", True):
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=st.session_state.fpr,
                y=st.session_state.tpr,
                mode="lines",
                line=dict(color=PRIMARY_COLOR, width=3),
                name=f"AUC = {st.session_state.roc_auc:.2f}",
            )
        )
        fig.add_shape(type="line", x0=0, y0=0, x1=1, y1=1, line=dict(dash="dash"))
        fig.update_layout(
            xaxis_title="False positive rate",
            yaxis_title="True positive rate",
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Threshold optimisation", True):
        thr = st.slider("Decision threshold", 0.0, 1.0, 0.5, 0.01)
        y_pred = (st.session_state.probs >= thr).astype(int)
        cm = confusion_matrix(st.session_state.y_test, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()

        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0
        acc = (tp + tn) / cm.sum()

        l, r = st.columns(2)
        with l:
            st.plotly_chart(
                px.imshow(
                    cm,
                    x=["Non-default", "Default"],
                    y=["Non-default", "Default"],
                    text_auto=True,
                    color_continuous_scale="Blues",
                ),
                use_container_width=True,
            )
        with r:
            for label, value in {
                "Accuracy": acc,
                "Precision": precision,
                "Recall": recall,
                "F1": f1,
            }.items():
                st.metric(label, f"{value:.2%}")

# ============================================================
# PAGE 4 – EXPLAINABILITY
# ============================================================
elif selection == pages[3]:
    st.header("🧠 Explainability")
    if not st.session_state.processing_complete:
        st.info("Process data first.")
        st.stop()

    l, r = st.columns([2, 1])
    with l:
        if st.session_state.shap_image:
            st.subheader("SHAP global importance")
            st.image(st.session_state.shap_image, use_container_width=True)
        else:
            st.warning("SHAP image unavailable.")
    with r:
        st.subheader("Nearest models")
        for m in st.session_state.similar_models or []:
            sim = m.get("similarity", 0)
            with st.expander(f"{m.get('model_name')} (sim = {sim:.2f})"):
                st.metric("Similarity", f"{sim * 100:.1f}%")
                st.json({k: v for k, v in m.items() if k != "vector"})

# ============================================================
# PAGE 5 – COMPLIANCE
# ============================================================
elif selection == pages[4]:
    st.header("🛡️ Compliance")
    if not st.session_state.processing_complete:
        st.info("Process data first.")
        st.stop()

    report = st.session_state.compliance_summary
    if isinstance(report, str) and report.startswith("⚠️"):
        st.error(report)
        st.stop()

    st.markdown(report, unsafe_allow_html=True)
    st.download_button(
        "📥 Download full report",
        data=report,
        file_name="compliance_report.md",
        mime="text/markdown",
    )

# ============================================================
# PAGE 6 – DRIFT
# ============================================================
elif selection == pages[5]:
    st.header("📉 Drift detection")
    if not st.session_state.processing_complete:
        st.info("Process data first.")
        st.stop()

    dr = st.session_state.drift_report
    if dr.get("error"):
        st.error(dr["error"])
        st.stop()

    df = pd.DataFrame(dr.get("details", []))
    if df.empty:
        st.info("No drift output.")
        st.stop()

    df["status"] = np.where(df["drifted"], "Drifted", "Stable")
    p, t = st.columns(2)
    p.plotly_chart(
        px.pie(
            df,
            names="status",
            color="status",
            color_discrete_map={"Drifted": DANGER_COLOR, "Stable": SUCCESS_COLOR},
        ),
        use_container_width=True,
    )
    t.dataframe(df[["feature", "p_value", "status"]], use_container_width=True)

# ============================================================
# PAGE 7 – EXPORT
# ============================================================
elif selection == pages[6]:
    st.header("📤 Report generation")
    if not st.session_state.processing_complete:
        st.info("Process data first.")
        st.stop()

    with st.form("rpt"):
        picks = st.multiselect(
            "Sections",
            ["Executive summary", "Performance", "Compliance", "Drift"],
            default=["Executive summary", "Performance", "Drift"],
        )
        email = st.text_input("Email (optional)")
        go = st.form_submit_button("Generate PDF")

    if go:
        with st.spinner("Building PDF…"):
            try:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, "AgentX Risk Validation Report", 0, 1, "C")
                pdf.cell(200, 10, datetime.now().strftime("%Y-%m-%d"), 0, 1, "C")
                pdf.ln(4)

                if "Executive summary" in picks:
                    pdf.set_font(style="B")
                    pdf.cell(0, 8, "Executive summary", 0, 1)
                    pdf.set_font(style="")
                    pdf.multi_cell(
                        0, 6, st.session_state.compliance_summary.split("##")[0]
                    )
                    pdf.ln(2)

                if "Performance" in picks:
                    pdf.set_font(style="B")
                    pdf.cell(0, 8, "Performance", 0, 1)
                    pdf.set_font(style="")
                    for k, v in st.session_state.performance_report.items():
                        pdf.cell(0, 6, f"{k}: {v}", 0, 1)
                    pdf.ln(2)

                if "Compliance" in picks:
                    pdf.set_font(style="B")
                    pdf.cell(0, 8, "Compliance", 0, 1)
                    pdf.set_font(style="")
                    pdf.multi_cell(0, 6, st.session_state.compliance_summary)
                    pdf.ln(2)

                if "Drift" in picks:
                    pdf.set_font(style="B")
                    pdf.cell(0, 8, "Drift", 0, 1)
                    pdf.set_font(style="")
                    for d in st.session_state.drift_report.get("details", []):
                        status = "Drifted" if d["drifted"] else "Stable"
                        pdf.cell(
                            0,
                            6,
                            f"{d['feature']}: p={d['p_value']:.4f} – {status}",
                            0,
                            1,
                        )

                fname = f"Risk_Report_{datetime.now():%Y%m%d}.pdf"
                pdf.output(fname)

                with open(fname, "rb") as f:
                    st.download_button("Download PDF", f, fname, "application/pdf")
                if email:
                    st.success(f"Report emailed to {email} (simulated)")
            except Exception as e:
                st.error(f"PDF generation failed: {e}")

# ============================================================
# PAGE 8 – COMPARE MODELS
# ============================================================
elif selection == pages[7]:
    st.header("🔬 Compare models")
    if not st.session_state.processing_complete:
        st.info("Process data first.")
        st.stop()

    l, r = st.columns(2)
    cur = st.session_state.performance_report
    l.metric("Current ROC-AUC", f"{cur.get('roc_auc', 0):.2f}")
    l.metric("Current accuracy", f"{cur.get('accuracy', 0):.2%}")

    with r:
        upl = st.file_uploader("Upload model (.pkl / .joblib)", type=["pkl", "joblib"])
        if upl:
            if _bytes_to_mb(upl.size) > 20:
                st.error("Model file too large (> 20 MB)")
                st.stop()
            if Path(upl.name).suffix not in ALLOWED_MODEL_EXT:
                st.error("Unsupported extension")
                st.stop()
            try:
                cmp = joblib.load(upl)
                if not hasattr(cmp, "predict_proba"):
                    st.error("Model must implement predict_proba")
                    st.stop()
                X = st.session_state.df_clean.drop("loan_status", axis=1)
                y = st.session_state.df_clean.loan_status.astype(int)
                new_perf = evaluate_model(cmp, X, y)
                l.metric(
                    "New ROC-AUC",
                    f"{new_perf['roc_auc']:.2f}",
                    delta=f"{new_perf['roc_auc'] - cur['roc_auc']:+.2f}",
                )
                l.metric(
                    "New accuracy",
                    f"{new_perf['accuracy']:.2%}",
                    delta=f"{new_perf['accuracy'] - cur['accuracy']:+.2%}",
                )
            except Exception as e:
                st.error(f"Failed to load model: {e}")

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption("© 2025 AgentX Technologies – All rights reserved.")
