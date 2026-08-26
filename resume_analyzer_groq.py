import streamlit as st
import os
import tempfile
import PyPDF2
from groq import Groq
from db_setup import init_db, save_user, save_cv, save_analysis, save_chat_message
from dotenv import load_dotenv
import base64

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=API_KEY) if API_KEY else None

init_db()

st.set_page_config(
    page_title="JobFit — AI Resume Analyzer",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in {
    "chat_history": [],
    "analysis_result": "",
    "user_input": "",
    "resume_text": "",
    "job_title": "",
    "job_description": "",
    "cv_saved": False,
    "analysis_id": None,
    "user_id": None,
    "cv_id": None,
    "candidate_info": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Global CSS — clean, theme-adaptive ────────────────────────────────────────
st.markdown("""
<style>
/* ── Accent color ── */
:root { --accent: #4361ee; --accent-light: #4361ee18; --radius: 10px; }

/* ── Buttons ── */
.stButton > button {
    background: var(--accent) !important;
    color: #fff !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: opacity 0.2s, transform 0.2s !important;
    width: 100% !important;
}
.stButton > button:hover  { opacity: 0.88 !important; transform: translateY(-1px) !important; }
.stButton > button:disabled { opacity: 0.35 !important; transform: none !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px !important;
    border-bottom: 2px solid var(--accent-light) !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0 !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 8px 20px !important;
}
.stTabs [aria-selected="true"] {
    border-bottom: 2px solid var(--accent) !important;
    color: var(--accent) !important;
}

/* ── Cards ── */
.jf-card {
    border: 1px solid rgba(128,128,128,0.2);
    border-left: 3px solid var(--accent);
    border-radius: var(--radius);
    padding: 20px 24px;
    margin: 12px 0;
    line-height: 1.8;
}

/* ── Chat ── */
.chat-wrap { display: flex; flex-direction: column; gap: 10px; margin: 12px 0; }
.bubble-user {
    align-self: flex-end;
    background: var(--accent-light);
    border: 1px solid rgba(67,97,238,0.25);
    border-radius: 16px 16px 4px 16px;
    padding: 10px 16px;
    max-width: 78%;
    font-size: 0.9rem;
}
.bubble-ai {
    align-self: flex-start;
    border: 1px solid rgba(128,128,128,0.2);
    border-left: 3px solid var(--accent);
    border-radius: 4px 16px 16px 16px;
    padding: 10px 16px;
    max-width: 82%;
    font-size: 0.9rem;
}
.bubble-label {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--accent);
    margin-bottom: 4px;
}

/* ── Section label ── */
.jf-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
    margin-bottom: 8px;
}

/* ── Stat row ── */
.stat-row { display: flex; gap: 12px; margin: 14px 0; }
.stat-box {
    flex: 1;
    border: 1px solid rgba(128,128,128,0.2);
    border-radius: var(--radius);
    padding: 14px;
    text-align: center;
}
.stat-val { font-size: 1.4rem; font-weight: 800; color: var(--accent); }
.stat-lbl { font-size: 0.72rem; opacity: 0.55; text-transform: uppercase; margin-top: 2px; }

/* ── Empty state ── */
.jf-empty {
    border: 1px dashed rgba(128,128,128,0.25);
    border-radius: var(--radius);
    padding: 40px 20px;
    text-align: center;
    opacity: 0.6;
}
.jf-empty-icon { font-size: 2rem; margin-bottom: 8px; }
.jf-empty-text { font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def section_label(icon, title):
    st.markdown(f'<div class="jf-label">{icon} {title}</div>', unsafe_allow_html=True)


def trim_text(text: str, max_chars: int = 3000) -> str:
    text = text.strip()
    return text[:max_chars] + "\n...[truncated]" if len(text) > max_chars else text


def extract_text_from_pdf(pdf_file) -> str:
    text = ""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(pdf_file.read())
        tmp_path = tmp.name
    with open(tmp_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
    os.unlink(tmp_path)
    return text.strip()


def get_base64(img_path):
    try:
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


# ── Groq streaming ─────────────────────────────────────────────────────────────

def stream_groq(prompt: str, api_key: str, model: str, placeholder):
    try:
        groq_client = Groq(api_key=api_key) if api_key else client
        full_text = ""
        with groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            max_tokens=1024,
            temperature=0.5,
        ) as stream:
            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                full_text += token
                placeholder.markdown(full_text + "▌")

        placeholder.markdown(full_text)
        return full_text
    except Exception as e:
        msg = f"❌ Groq error: {e}"
        placeholder.error(msg)
        return msg


# ── AI functions ───────────────────────────────────────────────────────────────

def analyze_resume(resume_text, job_title, job_description, api_key, model, placeholder):
    prompt = f"""You are a senior resume analyst. Analyze this resume for a **{job_title}** role.

JOB DESCRIPTION:
{trim_text(job_description, 3000)}

RESUME:
{trim_text(resume_text, 6000)}

Reply using EXACTLY this structure. Each section must start on its own new line with a blank line before it:

## 🎯 Match Score: XX%

> One-sentence overall verdict.

## ✅ Top 3 Strengths

1. ...
2. ...
3. ...

## ⚠️ Top 3 Gaps / Missing Skills

1. ...
2. ...
3. ...

## 🛠️ 3 Actionable Improvements

1. ...
2. ...
3. ...

Be concise, direct, and insightful."""
    return stream_groq(prompt, api_key, model, placeholder)


def ask_question(resume_text, job_title, job_description, question, api_key, model, placeholder):
    prompt = f"""You are a professional resume coach helping someone apply for a **{job_title}** role.

RESUME: {trim_text(resume_text, 5000)}
JOB DESCRIPTION: {trim_text(job_description, 2000)}

Question: {question}

Answer helpfully, concisely, and with actionable advice. Use bullet points where appropriate."""
    return stream_groq(prompt, api_key, model, placeholder)


def extract_user_info(resume_text: str, api_key: str, model: str) -> dict:
    """Ask the AI to extract name, email, phone from resume text. Returns a dict."""
    import json
    try:
        groq_client = Groq(api_key=api_key) if api_key else client
        prompt = f"""Extract the candidate's personal information from this resume.

RESUME:
{trim_text(resume_text, 4000)}

Reply ONLY with a valid JSON object — no explanation, no markdown, no code fences:
{{"name": "...", "email": "...", "phone": "..."}}

If a field is not found, use null."""
        resp = groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        # Strip accidental markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return {
            "name":  data.get("name")  or "Unknown",
            "email": data.get("email") or "Unknown",
            "phone": data.get("phone") or "Unknown",
        }
    except Exception:
        return {"name": "Unknown", "email": "Unknown", "phone": "Unknown"}


def parse_analysis_result(analysis_text: str) -> dict:
    """
    Parse the AI markdown analysis response into structured fields.
    Returns dict with keys: score (int), feedback, points_forts, points_faibles.
    """
    import re

    # Extract score — looks for patterns like "Match Score: 78%" or "Score: 78"
    score = 0
    score_match = re.search(r'(?:match\s*score|score)[^\d]*(\d{1,3})\s*%', analysis_text, re.IGNORECASE)
    if score_match:
        score = int(score_match.group(1))

    # Extract strengths block (between "Strengths" header and next "##" or end)
    forts = ""
    forts_match = re.search(
        r'##.*?strength[s]?.*?\n(.*?)(?=\n##|\Z)', analysis_text,
        re.IGNORECASE | re.DOTALL
    )
    if forts_match:
        forts = forts_match.group(1).strip()

    # Extract gaps/weaknesses block
    faibles = ""
    faibles_match = re.search(
        r'##.*?(?:gap|missing|weakness|faible)[s]?.*?\n(.*?)(?=\n##|\Z)', analysis_text,
        re.IGNORECASE | re.DOTALL
    )
    if faibles_match:
        faibles = faibles_match.group(1).strip()

    # Feedback = everything that's not strengths or gaps (the full text is a safe fallback)
    feedback = analysis_text.strip()

    return {
        "score":          score,
        "feedback":       feedback,
        "points_forts":   forts,
        "points_faibles": faibles,
    }


def chat_response(message, resume_text, job_title, job_description, analysis_result, api_key, model, placeholder):
    if any(p in message.lower() for p in ["generate resume", "create resume", "sample resume", "optimized resume", "rewrite"]):
        prompt = f"""You are an expert resume writer. Rewrite this resume for a **{job_title}** role.

ORIGINAL RESUME: {trim_text(resume_text, 1500)}
GAPS TO FIX: {trim_text(analysis_result, 800)}
JOB KEYWORDS: {trim_text(job_description, 500)}

Output a clean, ATS-optimized Markdown resume with clear sections."""
    else:
        prompt = f"""You are a friendly but sharp resume coach for a **{job_title}** role.
Previous analysis: {trim_text(analysis_result, 600)}
User message: {message}
Answer helpfully, concisely, with actionable advice."""
    return stream_groq(prompt, api_key, model, placeholder)


def submit_chat(api_key, model):
    # Read from the buffer key (set by widget or suggestion chips)
    user_message = st.session_state.pop("_chat_pending", None)
    if user_message is None:
        user_message = st.session_state.get("chat_input_box", "").strip()
    if not user_message:
        return
    # Clear the widget via its own on_change-safe buffer before next render
    st.session_state["_chat_clear"] = True
    st.session_state.chat_history.append({"text": user_message, "is_user": True})
    placeholder = st.empty()
    response = chat_response(
        user_message,
        st.session_state.resume_text,
        st.session_state.job_title,
        st.session_state.job_description,
        st.session_state.analysis_result,
        api_key, model, placeholder,
    )
    st.session_state.chat_history.append({"text": response, "is_user": False})
    # Persist Q&A to DB if we have an analysis context
    if st.session_state.get("analysis_id"):
        save_chat_message(st.session_state.analysis_id, user_message, response)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():

    # ── Header ─────────────────────────────────────────────────────────────────
    img_b64 = get_base64("JOB_Fit_Logo-BG.png")
    if img_b64:
        c1, c2 = st.columns([1, 11])
        with c1:
            st.image(f"data:image/png;base64,{img_b64}", width=52)
        with c2:
            st.markdown("## JobFit — AI Resume Analyzer")
    else:
        st.markdown("## 📝 JobFit — AI Resume Analyzer")
    st.divider()

    api_key = API_KEY
    model   = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    # ══════════════════════════════════════════════════════════════════════════
    # Resume Analysis
    # ══════════════════════════════════════════════════════════════════════════
    if True:
        col1, col2 = st.columns(2, gap="large")

        # ── Upload ──
        with col1:
            section_label("📤", "Resume")
            uploaded_file = st.file_uploader("Upload your resume (PDF)", type="pdf")

            if uploaded_file:
                try:
                    resume_text = extract_text_from_pdf(uploaded_file)
                    st.session_state.resume_text = resume_text

                    if not st.session_state.cv_saved:
                        with st.spinner("Reading candidate info..."):
                            info = extract_user_info(resume_text, api_key, model)
                        st.session_state.candidate_info = info  # store for later renders
                        user_id = save_user(info["name"], info["email"], info["phone"])
                        cv_id   = save_cv(user_id, uploaded_file.name, resume_text)
                        st.session_state.user_id  = user_id
                        st.session_state.cv_id    = cv_id
                        st.session_state.cv_saved = True

                    st.success(f"✅ {uploaded_file.name}")

                except Exception as e:
                    st.error(f"PDF error: {e}")
                    st.session_state.resume_text = ""
            else:
                st.markdown("""
                <div class="jf-empty">
                    <div class="jf-empty-icon">📄</div>
                    <div class="jf-empty-text">No resume uploaded yet</div>
                </div>
                """, unsafe_allow_html=True)

        # ── Job Details ──
        with col2:
            section_label("💼", "Job Details")
            job_title = st.text_input("Job Title", placeholder="e.g. Data Scientist",
                                      value=st.session_state.job_title)
            st.session_state.job_title = job_title

            job_description = st.text_area("Job Description", height=220,
                                           placeholder="Paste the job description here...",
                                           value=st.session_state.job_description)
            st.session_state.job_description = job_description

            if job_description:
                w = len(job_description.split())
                st.caption(f"{'✅' if w > 50 else '⚠️'} {w} words {'— good detail' if w > 50 else '— more detail = better results'}")

        st.write("")

        # ── Analyze button ──
        ready = bool(
            (api_key)
            and st.session_state.resume_text
            and st.session_state.job_title
            and st.session_state.job_description
        )

        if not ready:
            missing = [x for x, v in [
                ("API key", api_key),
                ("resume", st.session_state.resume_text),
                ("job title", st.session_state.job_title),
                ("job description", st.session_state.job_description),
            ] if not v]
            st.caption(f"Still needed: {', '.join(missing)}")

        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            analyze_btn = st.button("🔍 Analyze Resume", disabled=not ready, use_container_width=True)

        st.write("")

        # ── Results ──
        if analyze_btn:
            section_label("🎯", "Analysis")
            placeholder = st.empty()
            analysis = analyze_resume(
                st.session_state.resume_text,
                st.session_state.job_title,
                st.session_state.job_description,
                api_key, model, placeholder,
            )
            st.session_state.analysis_result = analysis
            if st.session_state.cv_id:
                parsed = parse_analysis_result(analysis)
                aid = save_analysis(
                    st.session_state.cv_id,
                    parsed["score"], parsed["feedback"],
                    parsed["points_forts"], parsed["points_faibles"],
                    st.session_state.job_title,
                    st.session_state.job_description,
                )
                st.session_state.analysis_id = aid

        elif st.session_state.analysis_result:
            section_label("🎯", "Last Analysis")
            st.markdown(st.session_state.analysis_result)

        # ── Chat ──
        if st.session_state.analysis_result:
            st.divider()
            section_label("💬", "Follow-up Chat")

            if st.session_state.chat_history:
                st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
                for msg in st.session_state.chat_history:
                    if msg["is_user"]:
                        st.markdown(f'<div class="bubble-user"><div class="bubble-label">You</div>{msg["text"]}</div>',
                                    unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="bubble-ai"><div class="bubble-label">JobFit AI</div>{msg["text"]}</div>',
                                    unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            if st.session_state.pop("_chat_clear", False):
                st.session_state["chat_input_box"] = ""

            c_in, c_btn = st.columns([5, 1])
            with c_in:
                st.text_input("Message", key="chat_input_box",
                              placeholder="Ask anything about your resume...",
                              label_visibility="collapsed")
            with c_btn:
                if st.button("Send", use_container_width=True):
                    submit_chat(api_key, model)
                    st.rerun()

            st.caption("Quick: ")
            q_cols = st.columns(4)
            for i, sug in enumerate(["Missing skills?", "Rewrite summary", "ATS tips", "Generate resume"]):
                with q_cols[i]:
                    if st.button(sug, key=f"sug_{i}", use_container_width=True):
                        st.session_state["_chat_pending"] = sug
                        submit_chat(api_key, model)
                        st.rerun()



if __name__ == "__main__":
    main()
