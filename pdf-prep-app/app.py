"""
app.py — Streamlit front-end for filter_course_evals.py

This file is ONLY the interface: upload, settings, run, results table,
downloads. All PDF logic (finding the header, finding the question,
cropping, rasterizing) lives in filter_course_evals.py, which is imported
here as-is and never modified.
"""

import io
import re
import zipfile
import tempfile
from pathlib import Path
from contextlib import redirect_stdout

import pandas as pd
import streamlit as st

import filter_course_evals as fce  # unmodified module — imported, not edited

st.set_page_config(
    page_title="PDF Prep · Stanford Law School",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Branding (matches the EvalReader look) ──────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,300;0,400;0,600;1,400&family=Source+Sans+3:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Source Sans 3', sans-serif;
    font-size: 16px;
}
.stApp { background: #f9f7f4; }
.block-container { padding: 0 2.5rem 3rem 2.5rem; max-width: 1200px; }
#MainMenu, footer { visibility: hidden; }

/* ── Header ── */
.stanford-header {
    background: #8C1515;
    margin: -1rem -2.5rem 0 -2.5rem;
    padding: 0.75rem 2.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.stanford-wordmark {
    font-family: 'Source Serif 4', serif;
    font-size: 1.5rem;
    font-weight: 600;
    color: white;
    letter-spacing: 0.02em;
}
.stanford-subtitle {
    font-size: 0.85rem;
    color: rgba(255,255,255,0.75);
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.stanford-divider {
    height: 4px;
    background: linear-gradient(90deg, #8C1515 0%, #B83A4B 50%, #8C1515 100%);
    margin: 0 -2.5rem 2rem -2.5rem;
}

/* ── Page title ── */
.page-title {
    font-family: 'Source Serif 4', serif;
    font-size: 2.25rem;
    font-weight: 400;
    color: #1a1a1a;
    margin: 1.5rem 0 0.25rem 0;
    line-height: 1.2;
}
.page-subtitle {
    font-size: 1rem;
    color: #666;
    margin-bottom: 2rem;
    font-weight: 300;
}

/* ── Stat cards ── */
.stat-row { display: flex; gap: 1rem; margin: 1.5rem 0 2rem 0; }
.stat-card {
    flex: 1;
    background: white;
    border: 1px solid #e8e0d8;
    border-top: 3px solid #8C1515;
    border-radius: 4px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.stat-val {
    font-family: 'Source Serif 4', serif;
    font-size: 2.5rem;
    font-weight: 600;
    color: #8C1515;
    line-height: 1;
}
.stat-lbl {
    font-size: 0.8rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 6px;
    font-weight: 500;
}

/* ── Section headers ── */
.section-header {
    font-family: 'Source Serif 4', serif;
    font-size: 1.4rem;
    font-weight: 400;
    color: #1a1a1a;
    margin: 0 0 0.25rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #e8e0d8;
}

/* ── Buttons ── */
.stButton > button {
    background: #8C1515;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 0.6rem 2rem;
    font-size: 1rem;
    font-family: 'Source Sans 3', sans-serif;
    font-weight: 500;
    letter-spacing: 0.02em;
    transition: background 0.15s;
}
.stButton > button:hover { background: #6d1010; }
.stButton > button[kind="secondary"] {
    background: white;
    color: #8C1515;
    border: 1px solid #8C1515;
}
.stButton > button[kind="secondary"]:hover { background: #fdf5f5; }

/* ── Download button ── */
.stDownloadButton > button {
    background: white;
    color: #8C1515;
    border: 1px solid #8C1515;
    border-radius: 4px;
    padding: 0.5rem 1.5rem;
    font-size: 1rem;
    font-weight: 500;
}
.stDownloadButton > button:hover { background: #fdf5f5; }

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border: 1px solid #ddd;
    border-radius: 4px;
    font-family: 'Source Sans 3', sans-serif;
    font-size: 1rem;
    background: white;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #8C1515;
    box-shadow: 0 0 0 2px rgba(140,21,21,0.1);
}

/* ── File uploader ── */
.stFileUploader {
    background: white;
    border: 2px dashed #c8a8a8;
    border-radius: 8px;
    padding: 1rem;
}
.stFileUploader:hover { border-color: #8C1515; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #2d1515;
    border-right: none;
}
section[data-testid="stSidebar"] * { color: white !important; }
section[data-testid="stSidebar"] .stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    color: white !important;
}
section[data-testid="stSidebar"] label { color: rgba(255,255,255,0.7) !important; }

/* ── Dataframe ── */
.stDataFrame {
    border: 1px solid #e8e0d8;
    border-radius: 4px;
    overflow: hidden;
}

/* ── Progress ── */
.stProgress > div > div > div { background: #8C1515; }

/* ── Alerts ── */
.stSuccess { background: #f0f9f0; border-left: 4px solid #2d6a2d; border-radius: 4px; }
.stWarning { background: #fffbf0; border-left: 4px solid #b8860b; border-radius: 4px; }

hr { border: none; border-top: 1px solid #e8e0d8; margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Shared-password gate ─────────────────────────────────────────────────────
# One password, stored in Streamlit secrets as APP_PASSWORD, shared by everyone
# who's meant to use this app. Not per-user accounts — just keeps the app from
# being open to anyone who stumbles on the URL.
def _check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True

    try:
        correct_password = st.secrets["APP_PASSWORD"]
    except Exception:
        st.error(
            "No APP_PASSWORD is configured for this app yet. Add one in "
            "Settings → Secrets (Streamlit Cloud) or in .streamlit/secrets.toml "
            "(local) to enable the password gate."
        )
        st.stop()

    def _on_submit():
        if st.session_state.get("_pw_input") == correct_password:
            st.session_state["authenticated"] = True
        else:
            st.session_state["authenticated"] = False
        st.session_state["_pw_input"] = ""

    st.markdown("""
    <div class="stanford-header">
      <div class="stanford-wordmark">Stanford Law School</div>
      <div class="stanford-subtitle">PDF Prep · Course Eval Filter</div>
    </div>
    <div class="stanford-divider"></div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown('<div class="page-title" style="text-align:center;">Sign in</div>', unsafe_allow_html=True)
        st.text_input("Password", type="password", key="_pw_input", on_change=_on_submit)
        if st.session_state.get("authenticated") is False:
            st.error("Incorrect password.")

    return False


if not _check_password():
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="stanford-header">
  <div class="stanford-wordmark">Stanford Law School</div>
  <div class="stanford-subtitle">PDF Prep · Course Eval Filter</div>
</div>
<div class="stanford-divider"></div>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">Prepare Evaluation PDFs</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Upload scanned course-evaluation reports — this keeps only the '
    'printed header block and the target question\'s handwritten answers, dropping everything '
    'else, so files are ready for EvalReader.</div>',
    unsafe_allow_html=True,
)

# ── Sidebar: kept minimal for non-technical users ──────────────────────────
with st.sidebar:
    st.markdown("## Settings")
    target_question = st.text_area(
        "Target question", value=fce.DEFAULT_QUESTION, height=110
    )
    dpi = st.slider("Output quality (DPI)", min_value=100, max_value=400, value=250, step=10)
    st.caption("Higher quality makes sharper, larger files. 250 works well for most reports.")

# Fixed, non-exposed defaults (match the original script's own CLI defaults)
VECTOR = False
USE_OCR = False

# ── Session state ────────────────────────────────────────────────────────────
if "outputs" not in st.session_state:
    st.session_state.outputs = {}  # out_filename -> bytes
if "logs" not in st.session_state:
    st.session_state.logs = {}  # source_filename -> captured stdout
if "rows" not in st.session_state:
    st.session_state.rows = []  # results table rows


def gather_pdfs(files):
    """Expand any uploaded ZIPs into individual PDF byte blobs."""
    pdfs = {}
    for uf in files:
        if uf.name.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(uf.read())) as z:
                for name in z.namelist():
                    if name.lower().endswith(".pdf") and not name.startswith("__"):
                        pdfs[Path(name).name] = z.read(name)
        else:
            pdfs[uf.name] = uf.read()
    return pdfs


def count_notices(log_text: str) -> int:
    return len(re.findall(r"^\s*-\s", log_text, re.MULTILINE))


# ── Upload ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Upload</div>', unsafe_allow_html=True)
st.markdown("")

uploaded = st.file_uploader(
    "Upload PDFs or a ZIP archive of PDFs", type=["pdf", "zip"], accept_multiple_files=True
)

if uploaded:
    pdf_bytes_map = gather_pdfs(uploaded)
    st.info(f"**{len(pdf_bytes_map)} PDF file(s)** ready to process.")

    run = st.button("▶  Run Filter", type="primary", disabled=not pdf_bytes_map)

    if run:
        st.session_state.outputs = {}
        st.session_state.logs = {}
        st.session_state.rows = []
        progress = st.progress(0)
        status = st.empty()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_dir = tmp_path / "FilteredData"
            out_dir.mkdir(parents=True, exist_ok=True)

            for idx, (name, data) in enumerate(pdf_bytes_map.items()):
                status.markdown(f"**Processing {idx + 1} of {len(pdf_bytes_map)}:** `{name}`")

                src_path = tmp_path / name
                src_path.write_bytes(data)

                buf = io.StringIO()
                try:
                    with redirect_stdout(buf):
                        fce.process_pdf(src_path, out_dir, target_question, dpi, USE_OCR, VECTOR)
                except Exception as e:
                    buf.write(f"\nERROR: {e}\n")

                out_name = f"{src_path.stem}_filtered.pdf"
                out_path = out_dir / out_name
                log_text = buf.getvalue()
                st.session_state.logs[name] = log_text

                if out_path.exists():
                    content = out_path.read_bytes()
                    st.session_state.outputs[out_name] = content
                    st.session_state.rows.append({
                        "Source file": name,
                        "Output file": out_name,
                        "Status": "✅ Processed",
                        "Size (KB)": round(len(content) / 1024),
                        "Notices": count_notices(log_text) or "—",
                    })
                else:
                    st.session_state.rows.append({
                        "Source file": name,
                        "Output file": "—",
                        "Status": "⚠️ No output",
                        "Size (KB)": "—",
                        "Notices": count_notices(log_text) or "—",
                    })

                progress.progress((idx + 1) / len(pdf_bytes_map))

        status.empty()
        if st.session_state.outputs:
            st.success(f"Done — {len(st.session_state.outputs)} filtered PDF(s) produced.")
        else:
            st.warning("No output PDFs were produced. Check the log details below.")

# ── Results ──────────────────────────────────────────────────────────────────
if st.session_state.rows:
    df = pd.DataFrame(st.session_state.rows)
    n_ok = int((df["Status"] == "✅ Processed").sum())
    n_warn = int((df["Status"] == "⚠️ No output").sum())

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-card">
            <div class="stat-val">{len(df)}</div>
            <div class="stat-lbl">Files Uploaded</div>
        </div>
        <div class="stat-card">
            <div class="stat-val">{n_ok}</div>
            <div class="stat-lbl">Processed</div>
        </div>
        <div class="stat-card">
            <div class="stat-val">{n_warn}</div>
            <div class="stat-lbl">No Output</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Results</div>', unsafe_allow_html=True)
    st.markdown("")

    st.dataframe(
        df,
        width="stretch",
        height=min(480, 46 * (len(df) + 1)),
        hide_index=True,
        column_config={
            "Source file": st.column_config.TextColumn("Source file", width="large"),
            "Output file": st.column_config.TextColumn("Output file", width="large"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Size (KB)": st.column_config.TextColumn("Size (KB)", width="small"),
            "Notices": st.column_config.TextColumn("Notices", width="small",
                                                     help="Count of diagnostic notices — see 'Details' below for what they mean."),
        },
    )

    st.markdown("")
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.session_state.outputs:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for name, content in st.session_state.outputs.items():
                    zf.writestr(name, content)
            st.download_button(
                "⬇  Download All as ZIP",
                data=zip_buf.getvalue(),
                file_name="filtered_pdfs.zip",
                mime="application/zip",
            )
    with c2:
        if st.button("🗑  Clear results", type="secondary"):
            st.session_state.outputs = {}
            st.session_state.logs = {}
            st.session_state.rows = []
            st.rerun()

    with st.expander("Download individual files"):
        for name, content in st.session_state.outputs.items():
            c1, c2 = st.columns([5, 1])
            c1.write(f"📄 {name}  ·  {len(content) / 1024:.0f} KB")
            c2.download_button(
                "Download", data=content, file_name=name, mime="application/pdf", key=f"dl_{name}"
            )

    with st.expander("Details (per-file processing notes)"):
        for name, log in st.session_state.logs.items():
            st.markdown(f"**{name}**")
            st.code(log or "(no output)")
