"""
app.py — Landing page for the Course Eval pipeline.

Two cards linking out to the two independent apps, plus the hand-off
instructions between them. This page moves no data and stores no state —
it's just a signpost + protocol sheet.
"""

import streamlit as st

st.set_page_config(
    page_title="Course Eval Pipeline · Stanford Law School",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PDF_PREP_URL = "https://pdf-prep.streamlit.app/"
EVAL_READER_URL = "https://course-eval.streamlit.app/"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,300;0,400;0,600;1,400&family=Source+Sans+3:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Source Sans 3', sans-serif;
    font-size: 16px;
}
.stApp { background: #f9f7f4; }
.block-container { padding: 0 2.5rem 3rem 2.5rem; max-width: 1100px; }
#MainMenu, footer { visibility: hidden; }

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

.section-header {
    font-family: 'Source Serif 4', serif;
    font-size: 1.4rem;
    font-weight: 400;
    color: #1a1a1a;
    margin: 2rem 0 0.75rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #e8e0d8;
}

/* ── Step cards ── */
.step-row { display: flex; gap: 1.5rem; align-items: stretch; margin: 1.5rem 0; }
.step-card {
    flex: 1;
    background: white;
    border: 1px solid #e8e0d8;
    border-top: 4px solid #8C1515;
    border-radius: 8px;
    padding: 1.75rem 1.75rem 1.5rem 1.75rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    display: flex;
    flex-direction: column;
}
.step-number {
    font-family: 'Source Serif 4', serif;
    font-size: 0.85rem;
    color: #8C1515;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
.step-title {
    font-family: 'Source Serif 4', serif;
    font-size: 1.5rem;
    font-weight: 400;
    color: #1a1a1a;
    margin-bottom: 0.5rem;
}
.step-desc {
    font-size: 0.95rem;
    color: #555;
    line-height: 1.5;
    flex-grow: 1;
    margin-bottom: 1.25rem;
}
.step-link a {
    display: inline-block;
    background: #8C1515;
    color: white !important;
    text-decoration: none;
    border-radius: 4px;
    padding: 0.6rem 1.75rem;
    font-size: 1rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    transition: background 0.15s;
}
.step-link a:hover { background: #6d1010; }

.step-arrow {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    color: #c8a8a8;
    padding: 0 0.25rem;
}

/* ── Protocol list ── */
.protocol-box {
    background: white;
    border: 1px solid #e8e0d8;
    border-left: 4px solid #8C1515;
    border-radius: 4px;
    padding: 1.5rem 2rem;
    margin: 1rem 0;
}
.protocol-box ol { margin: 0; padding-left: 1.2rem; }
.protocol-box li { margin-bottom: 0.6rem; font-size: 0.98rem; line-height: 1.5; color: #333; }
.protocol-box li:last-child { margin-bottom: 0; }
.protocol-box code {
    background: #f5efe8;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    font-size: 0.9em;
}

.note-box {
    background: #fffbf0;
    border-left: 4px solid #b8860b;
    border-radius: 4px;
    padding: 1rem 1.5rem;
    margin-top: 1rem;
    font-size: 0.92rem;
    color: #555;
}
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="stanford-header">
  <div class="stanford-wordmark">Stanford Law School</div>
  <div class="stanford-subtitle">Course Evaluation Pipeline</div>
</div>
<div class="stanford-divider"></div>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">Course Evaluation Pipeline</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Two independent tools, one workflow: prepare the PDFs, '
    'review them, then extract the handwritten comments.</div>',
    unsafe_allow_html=True,
)

# ── Two-step cards ────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="step-row">
  <div class="step-card">
    <div class="step-number">Step 1</div>
    <div class="step-title">Prepare PDFs</div>
    <div class="step-desc">
      Upload scanned course-evaluation reports. This tool keeps only the
      printed header block and the target question's handwritten answers,
      and produces a ZIP of filtered PDFs.
    </div>
    <div class="step-link"><a href="{PDF_PREP_URL}" target="_blank">Open PDF Prep →</a></div>
  </div>
  <div class="step-arrow">→</div>
  <div class="step-card">
    <div class="step-number">Step 2</div>
    <div class="step-title">Extract Comments</div>
    <div class="step-desc">
      Upload the ZIP of filtered PDFs from Step 1. This tool transcribes
      every handwritten comment and gives you a CSV with course ID,
      comment text, and review flags.
    </div>
    <div class="step-link"><a href="{EVAL_READER_URL}" target="_blank">Open EvalReader →</a></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Protocol ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">How to use these together</div>', unsafe_allow_html=True)

st.markdown("""
<div class="protocol-box">
<ol>
  <li>Open <strong>PDF Prep</strong> and upload the scanned evaluation reports (PDFs or a ZIP).</li>
  <li>Click <strong>Run Filter</strong>, then review the results table — check file sizes and any
      processing notices before trusting the output.</li>
  <li>Click <strong>Download All as ZIP</strong>. This is the file you carry to Step 2 — don't
      unzip or repack it.</li>
  <li>Open <strong>EvalReader</strong> and upload that same ZIP file directly.</li>
  <li>Click <strong>Run Extraction</strong>, then check the Results tab — look at rows flagged
      <code>needs_review</code> before downloading the final CSV.</li>
</ol>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="note-box">
Each step is a human checkpoint, not an automatic pass-through — review the results
before moving to the next step. Nothing is shared between these two apps except the
ZIP file you download and re-upload yourself.
</div>
""", unsafe_allow_html=True)
