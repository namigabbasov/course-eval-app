import os
import re
import io
import json
import base64
import zipfile
from collections import Counter

import fitz
import pandas as pd
import streamlit as st
from openai import OpenAI
from supabase import create_client, ClientOptions

st.set_page_config(
    page_title="EvalReader · Stanford Law",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: white;
    border: 1px solid #e8e0d8;
    border-radius: 4px;
    padding: 4px;
    margin-bottom: 1.5rem;
}
.stTabs [data-baseweb="tab"] {
    font-size: 1.1rem;
    font-weight: 500;
    padding: 12px 32px;
    color: #666;
    border-radius: 3px;
    background: transparent;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: #8C1515 !important;
    color: white !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 0; }

/* ── Buttons ── */
.stButton > button,
.stFormSubmitButton > button {
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
.stButton > button:hover,
.stFormSubmitButton > button:hover { background: #6d1010; }
.stButton > button[kind="secondary"],
.stFormSubmitButton > button[kind="secondaryFormSubmit"] {
    background: white;
    color: #8C1515;
    border: 1px solid #8C1515;
}
.stButton > button[kind="secondary"]:hover,
.stFormSubmitButton > button[kind="secondaryFormSubmit"]:hover { background: #fdf5f5; }
.st-key-btn_forgot_password {
    text-align: center;
    margin-top: 0.5rem;
}
.st-key-btn_forgot_password button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #8C1515 !important;
    font-size: 0.85rem !important;
    font-weight: 400 !important;
    padding: 0.25rem 0.5rem !important;
    text-decoration: underline;
}
.st-key-btn_forgot_password button:hover {
    background: transparent !important;
    color: #6d1010 !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: white;
    color: #8C1515;
    border: 1px solid #8C1515;
    border-radius: 4px;
    padding: 0.5rem 1.5rem;
    font-size: 1.1rem;
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
.stSelectbox > div > div {
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
    background: white;
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
section[data-testid="stSidebar"] .stTextInput > div > div > input,
section[data-testid="stSidebar"] .stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    color: white !important;
}
section[data-testid="stSidebar"] [data-testid="stTextInputRootElement"],
section[data-testid="stSidebar"] [data-testid="stTextInputRootElement"] div,
section[data-testid="stSidebar"] [data-testid="stTextAreaRootElement"],
section[data-testid="stSidebar"] [data-testid="stTextAreaRootElement"] div {
    background: transparent !important;
}
section[data-testid="stSidebar"] label { color: rgba(255,255,255,0.7) !important; }
section[data-testid="stSidebar"] .stButton > button[kind="secondary"],
section[data-testid="stSidebar"] .stButton > button[kind="secondary"] *,
section[data-testid="stSidebar"] .stFormSubmitButton > button[kind="secondaryFormSubmit"],
section[data-testid="stSidebar"] .stFormSubmitButton > button[kind="secondaryFormSubmit"] * {
    color: #8C1515 !important;
}

/* ── Dataframe ── */
.stDataFrame {
    border: 1px solid #e8e0d8;
    border-radius: 4px;
    overflow: hidden;
}

/* ── Progress ── */
.stProgress > div > div > div {
    background: #8C1515;
}

/* ── Alerts ── */
.stSuccess {
    background: #f0f9f0;
    border-left: 4px solid #2d6a2d;
    border-radius: 4px;
}
.stWarning {
    background: #fffbf0;
    border-left: 4px solid #b8860b;
    border-radius: 4px;
}

/* ── Log items ── */
.log-item {
    background: white;
    border: 1px solid #e8e0d8;
    border-left: 3px solid #8C1515;
    border-radius: 4px;
    padding: 8px 14px;
    margin: 4px 0;
    font-size: 1.1rem;
    color: #333;
}
.log-item.success { border-left-color: #2d6a2d; }
.log-item.error { border-left-color: #cc0000; }

hr { border: none; border-top: 1px solid #e8e0d8; margin: 1.5rem 0; }

/* ── Login page ── */
.login-brand {
    background: white;
    border: 1px solid #ddd5cc;
    border-top: 5px solid #8C1515;
    border-radius: 8px 8px 0 0;
    padding: 2.75rem 2.5rem 2rem 2.5rem;
    text-align: center;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
}
.login-brand-eyebrow {
    font-family: 'Source Serif 4', serif;
    font-size: 0.82rem;
    color: #8C1515;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    font-weight: 600;
    margin-bottom: 0.4rem;
}
.login-brand-school {
    font-family: 'Source Serif 4', serif;
    font-size: 1.9rem;
    color: #1a1a1a;
    font-weight: 400;
    line-height: 1.2;
}
.login-brand-rule {
    width: 40px;
    height: 2px;
    background: #8C1515;
    margin: 1rem auto 1rem auto;
    border-radius: 1px;
}
.login-brand-title {
    font-family: 'Source Serif 4', serif;
    font-size: 2rem;
    font-weight: 400;
    color: #1a1a1a;
}
.login-footer {
    text-align: center;
    font-size: 0.85rem;
    color: #aaa;
    margin-top: 1.25rem;
    letter-spacing: 0.01em;
}
</style>
""", unsafe_allow_html=True)

# ── Supabase client ────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    """Admin client — for DB queries and user management."""
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_KEY"],
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )

@st.cache_resource
def get_supabase_auth():
    """Auth client — for sign_in_with_password."""
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_PUBLISHABLE_KEY"],
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )

# ── Auth helpers ──────────────────────────────────────────────────────────────
def _do_login(email: str, password: str):
    if not email or not password:
        st.error("Enter your email and password.")
        return
    try:
        auth_client = get_supabase_auth()
        resp = auth_client.auth.sign_in_with_password({"email": email, "password": password})
        sb = get_supabase()
        role_row = sb.table("user_roles").select("role").eq("email", resp.user.email).single().execute()
        if not role_row.data:
            st.error("Access denied. Contact your administrator.")
            return
        st.session_state.user = {"email": resp.user.email, "role": role_row.data["role"]}
        st.rerun()
    except Exception:
        st.error("Incorrect email or password.")

def _login_page_style():
    st.markdown("""
    <style>
    .stApp { background: #e8e2d9 !important; }
    section[data-testid="stSidebar"] { display: none; }
    [data-testid="stForm"] {
        background: white !important;
        border: 1px solid #d8d0c8 !important;
        border-top: 4px solid #8C1515 !important;
        border-radius: 8px !important;
        padding: 2rem 2.25rem !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.09) !important;
    }
    </style>
    """, unsafe_allow_html=True)

def _login_brand(title):
    st.markdown(f"""
    <div style="text-align:center; margin: 3rem 0 1.5rem 0;">
        <div style="font-family:'Source Serif 4',serif; font-size:0.78rem; color:#8C1515;
                    letter-spacing:0.22em; text-transform:uppercase; font-weight:600;
                    margin-bottom:0.3rem;">Stanford Law School</div>
        <div style="font-family:'Source Serif 4',serif; font-size:2.2rem; color:#1a1a1a;
                    font-weight:400; line-height:1.1; margin-bottom:0.3rem;">EvalReader</div>
        <div style="font-size:0.95rem; color:#777; font-weight:300; letter-spacing:0.03em;
                    margin-bottom:0.1rem;">Course Evaluation Digital Extraction</div>
        <div style="width:40px; height:2px; background:#8C1515;
                    margin:1rem auto 1rem auto; border-radius:1px;"></div>
        <div style="font-family:'Source Serif 4',serif; font-size:1.6rem;
                    font-weight:400; color:#1a1a1a;">{title}</div>
    </div>
    """, unsafe_allow_html=True)

def _show_login():
    _login_page_style()
    _, col, _ = st.columns([1, 2, 1])
    with col:
        _login_brand("Sign in")
        with st.form("login"):
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign in", use_container_width=True):
                _do_login(email, password)
            if st.form_submit_button("Forgot password?", type="tertiary", use_container_width=False, key="btn_forgot_password"):
                st.session_state["show_forgot_password"] = True
                st.rerun()
        st.markdown('<div class="login-footer">Restricted to authorized users · Stanford Law School</div>', unsafe_allow_html=True)

def _show_forgot_password():
    _login_page_style()
    _, col, _ = st.columns([1, 2, 1])
    with col:
        _login_brand("Reset password")
        with st.form("forgot_password"):
            email = st.text_input("Email address")
            st.caption("Enter your email and we'll send you a reset link.")
            if st.form_submit_button("Send reset link", use_container_width=True):
                if not email:
                    st.error("Enter your email address.")
                else:
                    try:
                        app_url = st.secrets.get("APP_URL", "http://localhost:8502")
                        get_supabase_auth().auth.reset_password_for_email(
                            email, {"redirect_to": app_url}
                        )
                        st.success("If that email is registered, a reset link has been sent. Check your inbox.")
                    except Exception:
                        st.error("Something went wrong. Try again.")
            if st.form_submit_button("Back to sign in", type="secondary", use_container_width=True):
                del st.session_state["show_forgot_password"]
                st.rerun()
        st.markdown('<div class="login-footer">Restricted to authorized users · Stanford Law School</div>', unsafe_allow_html=True)

def _show_reset_password():
    code = st.query_params.get("code")
    _login_page_style()
    _, col, _ = st.columns([1, 2, 1])
    with col:
        _login_brand("Set new password")
        with st.form("reset_password"):
            new_pw = st.text_input("New password", type="password")
            confirm_pw = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Set password", use_container_width=True):
                if not new_pw or not confirm_pw:
                    st.error("Both fields are required.")
                elif new_pw != confirm_pw:
                    st.error("Passwords don't match.")
                elif len(new_pw) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    try:
                        session_resp = get_supabase_auth().auth.exchange_code_for_session({"auth_code": code})
                        user_email = session_resp.user.email
                        auth_users = get_supabase().auth.admin.list_users()
                        user_id = next((u.id for u in auth_users if u.email == user_email), None)
                        if user_id:
                            get_supabase().auth.admin.update_user_by_id(user_id, {"password": new_pw})
                            st.query_params.clear()
                            st.success("Password updated! You can now sign in.")
                        else:
                            st.error("User not found.")
                    except Exception:
                        st.error("Reset link expired or already used. Request a new one.")
        st.markdown('<div class="login-footer">Restricted to authorized users · Stanford Law School</div>', unsafe_allow_html=True)

# ── Auth gate ─────────────────────────────────────────────────────────────────
if "code" in st.query_params:
    _show_reset_password()
    st.stop()

if "user" not in st.session_state:
    if st.session_state.get("show_forgot_password"):
        _show_forgot_password()
    else:
        _show_login()
    st.stop()

_user = st.session_state.user
_is_admin = _user["role"] == "admin"

# ── Session state ─────────────────────────────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

TARGET_QUESTION = "What would you say to a classmate who was planning to take this class?"

DEFAULT_EXTRACTION_RULES = """- One student comment = one JSON object.
- A single comment may span multiple lines or sentences. Only start a new comment object when there's a clear visual break — blank vertical space, or a new line starting back at the same left margin as other separate comments — indicating a different student's response. Do not split one continuous note into separate objects just because it wraps onto a new line.
- Preserve duplicates — do not merge or deduplicate comments.
- Do not summarize or paraphrase.
- Do not combine separate comments into one.
- Ignore printed text (course name, professor, enrollment stats, the question heading) when extracting comments — only transcribe handwritten comments.
- If a word is unclear, write [illegible].
- If the whole comment is hard to read, include the best transcription and set needs_review to "yes".
- If there are no handwritten comments on this page, return an empty comments list.
- If this page shows the report header, extract the course identifier (e.g., W26-LAW-7502-01). It is typically printed in parentheses near the top of the page, following the course title. Return it without parentheses as "course_id". Otherwise, return an empty string."""

# ── PDF helpers ───────────────────────────────────────────────────────────────
# These PDFs are pre-filtered to a single question and have no extractable text
# layer (each page is a flattened image) — course_id must be read visually, so
# it's extracted by the same GPT Vision call that reads comments off the header page.
def get_page_count(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    count = len(doc)
    doc.close()
    return count

def page_to_base64_image(pdf_bytes, page_index, zoom=2.5):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_index]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_bytes = pix.tobytes("png")
    doc.close()
    return base64.b64encode(img_bytes).decode("utf-8")

def extract_comments_from_page(client, pdf_bytes, page_index, file_name, target_question, extraction_rules):
    image_b64 = page_to_base64_image(pdf_bytes, page_index)
    prompt = f"""
You are digitizing handwritten law school course evaluation comments.

This page is from a course evaluation report already filtered down to one question:
"{target_question}"

Extract every handwritten student comment visible on this page.

Rules:
{extraction_rules}
- Return valid JSON only.

Return exactly this JSON structure:
{{
  "course_id": "course id here or empty string",
  "comments": [
    {{
      "comment": "transcribed comment here",
      "needs_review": "yes or no"
    }}
  ]
}}
"""
    response = client.chat.completions.create(
        model="gpt-4.1",
        temperature=0,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
        ]}],
    )
    content = response.choices[0].message.content.strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return "", [{"comment": content, "needs_review": "yes", "file_name": file_name, "page_number": page_index + 1}]
    course_id = str(data.get("course_id", "")).strip()
    rows = []
    for item in data.get("comments", []):
        comment = item.get("comment", "").strip()
        needs_review = item.get("needs_review", "no").strip().lower()
        if comment:
            rows.append({"comment": comment, "needs_review": "yes" if needs_review == "yes" else "no", "file_name": file_name, "page_number": page_index + 1})
    return course_id, rows

def normalize_comment_for_duplicate_check(comment):
    text = str(comment).lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text

def mark_duplicates(df):
    if df.empty:
        df["is_duplicate"] = []
        return df
    df["duplicate_key"] = df["course_id"].astype(str) + "||" + df["file_name"].astype(str) + "||" + df["comment"].apply(normalize_comment_for_duplicate_check)
    counts = df["duplicate_key"].value_counts()
    df["is_duplicate"] = df["duplicate_key"].apply(lambda x: "yes" if counts.get(x, 0) > 1 else "no")
    return df.drop(columns=["duplicate_key"])

def process_pdf(pdf_bytes, file_name, client, target_question, extraction_rules):
    all_rows = []
    course_id = None
    for page_index in range(get_page_count(pdf_bytes)):
        page_course_id, rows = extract_comments_from_page(client, pdf_bytes, page_index, file_name, target_question, extraction_rules)
        if page_course_id and not course_id:
            course_id = page_course_id
        all_rows.extend(rows)
    course_id = course_id or "COURSE_ID_NOT_FOUND"
    for row in all_rows:
        row["course_id"] = course_id
    return all_rows

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙ Settings")
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        api_key = ""
    target_question = st.text_area("Target question", value=TARGET_QUESTION, height=120)
    if _is_admin:
        with st.expander("Advanced: extraction rules (admin)"):
            extraction_rules = st.text_area("Extraction rules", value=DEFAULT_EXTRACTION_RULES, height=280)
    else:
        extraction_rules = DEFAULT_EXTRACTION_RULES
    st.divider()
    st.markdown("**EvalReader**")
    st.caption("Stanford Law School")
    st.caption("GPT-4.1 Vision · PyMuPDF")
    st.divider()
    st.markdown(f"**{_user['email']}**")
    st.caption(f"Role: {_user['role'].capitalize()}")
    with st.expander("Change password"):
        with st.form("change_password"):
            current_pw = st.text_input("Current password", type="password")
            new_pw = st.text_input("New password", type="password")
            confirm_pw = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Update password", use_container_width=True):
                if not current_pw or not new_pw or not confirm_pw:
                    st.error("All fields required.")
                elif new_pw != confirm_pw:
                    st.error("Passwords don't match.")
                elif len(new_pw) < 6:
                    st.error("Minimum 6 characters.")
                else:
                    try:
                        get_supabase_auth().auth.sign_in_with_password(
                            {"email": _user["email"], "password": current_pw}
                        )
                        auth_users = get_supabase().auth.admin.list_users()
                        user_id = next((u.id for u in auth_users if u.email == _user["email"]), None)
                        if user_id:
                            get_supabase().auth.admin.update_user_by_id(user_id, {"password": new_pw})
                            st.success("Password updated.")
                        else:
                            st.error("User not found.")
                    except Exception:
                        st.error("Current password is incorrect.")
    if st.button("Sign out", type="secondary"):
        del st.session_state["user"]
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="stanford-header">
  <div class="stanford-wordmark">Stanford Law School</div>
  <div class="stanford-subtitle">EvalReader · Course Evaluation Extractor</div>
</div>
<div class="stanford-divider"></div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
if _is_admin:
    tab_extract, tab_results, tab_admin = st.tabs(["Upload", "Results", "Manage Users"])
else:
    tab_extract, tab_results = st.tabs(["Upload", "Results"])

# ── Upload tab ────────────────────────────────────────────────────────────────
with tab_extract:
    st.markdown('<div class="page-title">Extract Comments</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Upload course evaluation PDFs — GPT-4.1 Vision transcribes every handwritten student comment.</div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader("Upload PDFs or ZIP archive", type=["pdf", "zip"], accept_multiple_files=True)

    if uploaded_files:
        pdf_files = {}
        for uf in uploaded_files:
            if uf.name.lower().endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(uf.read())) as z:
                    for name in z.namelist():
                        if name.lower().endswith(".pdf") and not name.startswith("__"):
                            pdf_files[os.path.basename(name)] = z.read(name)
            else:
                pdf_files[uf.name] = uf.read()

        st.info(f"**{len(pdf_files)} PDF file(s)** ready to process.")

        col1, col2 = st.columns([1, 5])
        with col1:
            run = st.button("▶  Run Extraction", type="primary", disabled=not api_key)
        if not api_key:
            st.warning("⚠ OPENAI_API_KEY is not configured. Contact your administrator.")

        if run and api_key:
            client = OpenAI(api_key=api_key)
            all_rows = []
            progress_bar = st.progress(0)
            status = st.empty()
            log_container = st.container()

            for idx, (file_name, pdf_bytes) in enumerate(pdf_files.items()):
                progress_bar.progress(idx / len(pdf_files))
                status.markdown(f"**Processing {idx + 1} of {len(pdf_files)}:** `{file_name}`")
                try:
                    rows = process_pdf(pdf_bytes, file_name, client, target_question, extraction_rules)
                    all_rows.extend(rows)
                    with log_container:
                        st.markdown(f'<div class="log-item success">✅ &nbsp;<strong>{file_name}</strong> — {len(rows)} comment(s) extracted</div>', unsafe_allow_html=True)
                except Exception as e:
                    with log_container:
                        st.markdown(f'<div class="log-item error">❌ &nbsp;<strong>{file_name}</strong> — Error: {str(e)}</div>', unsafe_allow_html=True)

            progress_bar.progress(1.0)
            status.empty()

            if all_rows:
                df = pd.DataFrame(all_rows)
                df = mark_duplicates(df)
                df = df[["course_id", "comment", "needs_review", "file_name", "page_number", "is_duplicate"]]
                st.session_state.results = df
                st.success(f"✅ Extraction complete — **{len(df)} comments** from **{len(pdf_files)} files**.")
                st.balloons()
            else:
                st.warning("No comments found in uploaded files.")

# ── Results tab ───────────────────────────────────────────────────────────────
with tab_results:
    df = st.session_state.results

    if df.empty:
        st.markdown('<div class="page-title">Results</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">No results yet. Run an extraction first.</div>', unsafe_allow_html=True)
    else:
        n_review = int((df["needs_review"] == "yes").sum())
        n_dup = int((df["is_duplicate"] == "yes").sum())

        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-card">
                <div class="stat-val">{len(df)}</div>
                <div class="stat-lbl">Total Comments</div>
            </div>
            <div class="stat-card">
                <div class="stat-val">{df["course_id"].nunique()}</div>
                <div class="stat-lbl">Courses</div>
            </div>
            <div class="stat-card">
                <div class="stat-val">{n_review}</div>
                <div class="stat-lbl">Needs Review</div>
            </div>
            <div class="stat-card">
                <div class="stat-val">{n_dup}</div>
                <div class="stat-lbl">Duplicates</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-header">Filter & Search</div>', unsafe_allow_html=True)
        st.markdown("")

        f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
        with f1:
            search = st.text_input("Search", placeholder="Search comments…", label_visibility="collapsed")
        with f2:
            courses = ["All courses"] + sorted(df["course_id"].unique().tolist())
            filter_course = st.selectbox("Course", courses, label_visibility="collapsed")
        with f3:
            filter_review = st.selectbox("Status", ["Any status", "Needs review", "Looks good"], label_visibility="collapsed")
        with f4:
            filter_dup = st.selectbox("Duplicates", ["No duplicates", "Include duplicates"], label_visibility="collapsed")

        filtered = df.copy()
        if search:
            filtered = filtered[filtered["comment"].str.contains(search, case=False, na=False, regex=False)]
        if filter_course != "All courses":
            filtered = filtered[filtered["course_id"] == filter_course]
        if filter_review == "Needs review":
            filtered = filtered[filtered["needs_review"] == "yes"]
        elif filter_review == "Looks good":
            filtered = filtered[filtered["needs_review"] == "no"]
        if filter_dup == "No duplicates":
            filtered = filtered[filtered["is_duplicate"] != "yes"]

        st.caption(f"Showing {len(filtered):,} of {len(df):,} comments")
        st.dataframe(
            filtered[["course_id", "comment", "needs_review", "is_duplicate", "page_number"]],
            width="stretch",
            height=480,
            column_config={
                "course_id": st.column_config.TextColumn("Course ID", width="small"),
                "comment": st.column_config.TextColumn("Comment", width="large"),
                "needs_review": st.column_config.TextColumn("Needs_Review", width="small"),
                "is_duplicate": st.column_config.TextColumn("Duplicate", width="small"),
                "page_number": st.column_config.TextColumn("Page", width="small"),
            },
            hide_index=True,
        )

        st.markdown("")
        c1, c2, _ = st.columns([1, 1, 5])
        with c1:
            csv = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("⬇  Download CSV", data=csv, file_name="eval_comments.csv", mime="text/csv", help="Downloads all extracted comments, regardless of the filters above.")
        with c2:
            if st.button("🗑  Clear All", type="secondary"):
                st.session_state.results = pd.DataFrame()
                st.rerun()

# ── Admin tab ─────────────────────────────────────────────────────────────────
if _is_admin:
    with tab_admin:
        st.markdown('<div class="page-title">Manage Users</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Add or remove people who can access EvalReader.</div>', unsafe_allow_html=True)

        sb = get_supabase()

        # ── Add user ──────────────────────────────────────────────────────────
        st.markdown('<div class="section-header">Add user</div>', unsafe_allow_html=True)
        st.markdown("")
        with st.form("add_user"):
            c1, c2 = st.columns([3, 1])
            new_email = c1.text_input("Email address")
            new_role = c2.selectbox("Role", ["user", "admin"])
            new_password = st.text_input(
                "Temporary password",
                type="password",
                help="Share this with the user. They should change it after first login.",
            )
            if st.form_submit_button("Add user", use_container_width=False):
                if not new_email or not new_password:
                    st.error("Email and temporary password are required.")
                else:
                    try:
                        sb.auth.admin.create_user({
                            "email": new_email,
                            "password": new_password,
                            "email_confirm": True,
                        })
                        sb.table("user_roles").insert({
                            "email": new_email,
                            "role": new_role,
                            "added_by": _user["email"],
                        }).execute()
                        st.success(f"Added {new_email} as {new_role}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not add user: {e}")

        # ── User list ─────────────────────────────────────────────────────────
        st.markdown("")
        st.markdown('<div class="section-header">Current users</div>', unsafe_allow_html=True)
        st.markdown("")

        users = (
            sb.table("user_roles")
            .select("email, role, created_at, added_by")
            .order("created_at")
            .execute()
            .data
        ) or []

        if not users:
            st.caption("No users found.")
        else:
            header = st.columns([3, 1, 2, 1])
            header[0].caption("Email")
            header[1].caption("Role")
            header[2].caption("Added by")
            header[3].caption("")
            st.markdown("<hr style='margin:0.25rem 0 0.75rem 0'>", unsafe_allow_html=True)

            for u in users:
                row = st.columns([3, 1, 2, 1])
                row[0].write(u["email"])
                row[1].write(u["role"].capitalize())
                row[2].caption(u.get("added_by") or "—")
                if u["email"] == _user["email"]:
                    row[3].caption("(you)")
                else:
                    if row[3].button("Remove", key=f"rm_{u['email']}"):
                        try:
                            auth_users = sb.auth.admin.list_users()
                            for au in auth_users:
                                if au.email == u["email"]:
                                    sb.auth.admin.delete_user(au.id)
                                    break
                            sb.table("user_roles").delete().eq("email", u["email"]).execute()
                            st.success(f"Removed {u['email']}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not remove user: {e}")
