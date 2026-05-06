import streamlit as st
import os
import tempfile
import PyPDF2
from groq import Groq
from db_setup import init_db, save_cv
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=API_KEY)

init_db()

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

for key, default in {
    "chat_history": [],
    "analysis_result": "",
    "user_input": "",
    "resume_text": "",
    "job_title": "",
    "job_description": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown("""
<style>
    .stButton button {
        background-color: #4361ee; color: white; border-radius: 5px;
        padding: 10px 20px; font-weight: bold; transition: all 0.3s ease;
    }
    .stButton button:hover { background-color: #3a56e4; transform: translateY(-2px); }
    .result-container {
        padding: 20px; border-radius: 10px;
        border-left: 5px solid #4361ee; margin: 20px 0;
    }
    h1 {
        background: linear-gradient(90deg, #4361ee, #3a0ca3);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
    }
    .section-header {
        padding: 10px 15px; border-radius: 5px; margin-bottom: 15px;
        border-left: 4px solid #4361ee; font-weight: bold;
    }
    .chat-user {
        padding: 12px 15px; border-radius: 15px 15px 15px 0;
        margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .chat-ai {
        padding: 12px 15px; border-radius: 15px 15px 0 15px;
        margin-bottom: 15px; border-left: 3px solid #4361ee;
    }
</style>
""", unsafe_allow_html=True)



def section_header(title, icon):
    return f"<div class='section-header'>{icon} {title}</div>"


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

# ── Groq streaming call ────────────────────────────────────────────────────────

def stream_groq(prompt: str, api_key: str, model: str, placeholder):
    try:
        # Use env-loaded client if no key passed from sidebar
        groq_client = Groq(api_key=api_key) if api_key else client  # <-- this line
        full_text = ""

        with groq_client.chat.completions.create(   # <-- and change client → groq_client
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


# ── AI functions ──────────────────────────────────────────────────────────────

def analyze_resume(resume_text, job_title, job_description, api_key, model, placeholder):
    prompt = f"""You are a resume analyst. Analyze this resume for a {job_title} role.

JOB DESCRIPTION:
{trim_text(job_description, 3000)}

RESUME:
{trim_text(resume_text, 6000)}

Reply with:
1. Match Score (%)
2. Top 3 Strengths
3. Top 3 Gaps / Missing Skills
4. 3 Actionable Improvements

Be concise and direct."""
    return stream_groq(prompt, api_key, model, placeholder)


def ask_question(resume_text, job_title, job_description, question, api_key, model, placeholder):
    prompt = f"""Resume coach for a {job_title} role.

RESUME: {trim_text(resume_text, 5000)}
JOB: {trim_text(job_description, 2000)}

Question: {question}

Answer concisely."""
    return stream_groq(prompt, api_key, model, placeholder)


def chat_response(message, resume_text, job_title, job_description, analysis_result, api_key, model, placeholder):
    if any(p in message.lower() for p in ["generate resume", "create resume", "sample resume", "optimized resume"]):
        prompt = f"""You are a resume writer. Rewrite this resume for a {job_title} role.

ORIGINAL RESUME: {trim_text(resume_text, 1500)}
GAPS TO FIX: {trim_text(analysis_result, 800)}
JOB KEYWORDS: {trim_text(job_description, 500)}

Output a clean Markdown resume."""
    else:
        prompt = f"""Resume coach for {job_title}.
Analysis summary: {trim_text(analysis_result, 600)}
User: {message}
Answer helpfully and concisely."""
    return stream_groq(prompt, api_key, model, placeholder)


def submit_message(api_key, model):
    user_message = st.session_state.user_input
    if not user_message:
        return
    st.session_state.chat_history.append({"text": user_message, "is_user": True})
    placeholder = st.empty()
    response_text = chat_response(
        user_message,
        st.session_state.resume_text,
        st.session_state.job_title,
        st.session_state.job_description,
        st.session_state.analysis_result,
        api_key, model, placeholder,
    )
    st.session_state.chat_history.append({"text": response_text, "is_user": False})
    st.session_state.user_input = ""


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    st.markdown("<h1 style='text-align: center;'>🚀 AI Resume Analyzer</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-bottom: 30px;'>Powered by Groq — blazing fast AI inference ⚡</p>", unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ Groq Configuration")
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk_...",
            help="Get your free key at https://console.groq.com",
        )

        if api_key:
            st.success("✅ API key set!")
        else:
            st.info("👆 Enter your Groq API key to get started.\nGet one free at console.groq.com")

        model = st.selectbox(
            "Model",
            options=[
                "llama-3.1-8b-instant",   # fastest
                "llama-3.3-70b-versatile", # smartest
                "mixtral-8x7b-32768",      # good balance
                "gemma2-9b-it",            # lightweight
            ],
            help="llama-3.1-8b-instant is the fastest for resume analysis",
        )

        st.markdown("---")
        st.markdown("**Why Groq?**")
        st.info("⚡ Groq runs on custom LPU chips — responses in seconds, not minutes. Free tier is generous.")

    tab1, tab2 = st.tabs(["Resume Analysis", "Ask Questions"])

    # ── Tab 1 ──────────────────────────────────────────────────────────────────
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(section_header("📄 Upload Resume", "📤"), unsafe_allow_html=True)
            uploaded_file = st.file_uploader("PDF only", type="pdf")
            if uploaded_file:
                st.success("✅ Uploaded!")
                try:
                    resume_text = extract_text_from_pdf(uploaded_file)
                    st.session_state.resume_text = resume_text
                    
                    if "cv_saved" not in st.session_state:
                        save_cv(resume_text)
                        st.session_state.cv_saved = True
                    
                    with st.expander("Preview extracted text"):
                        st.text(resume_text[:400] + "..." if len(resume_text) > 400 else resume_text)
                except Exception as e:
                    st.error(f"PDF error: {e}")
                    st.session_state.resume_text = ""
            else:
                st.info("📁 Upload your resume (PDF)")
                if not st.session_state.resume_text:
                    st.session_state.resume_text = ""

        with col2:
            st.markdown(section_header("💼 Job Details", "📋"), unsafe_allow_html=True)
            job_title = st.text_input("Job Title", placeholder="e.g., Data Scientist")
            st.session_state.job_title = job_title
            job_description = st.text_area("Job Description", height=200,
                                           placeholder="Paste the job description here...")
            st.session_state.job_description = job_description

        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            can_analyze = bool(
                API_KEY
                and st.session_state.resume_text
                and st.session_state.job_title
                and st.session_state.job_description
            )
            analyze_button = st.button("🔍 Analyze Resume", key="analyze_btn", disabled=not can_analyze)

        if analyze_button:
            st.markdown(section_header("📊 Analysis", "🎯"), unsafe_allow_html=True)
            result_placeholder = st.empty()
            analysis = analyze_resume(
                st.session_state.resume_text,
                st.session_state.job_title,
                st.session_state.job_description,
                api_key, model, result_placeholder,
            )
            st.session_state.analysis_result = analysis


        elif st.session_state.analysis_result:
            st.markdown(section_header("📊 Analysis Results", "🎯"), unsafe_allow_html=True)
            st.markdown('<div class="result-container">', unsafe_allow_html=True)
            st.markdown(st.session_state.analysis_result)
            st.markdown('</div>', unsafe_allow_html=True)
 
        if st.session_state.analysis_result:
            st.markdown("---")
            st.markdown(section_header("💬 Follow-up Questions", "❓"), unsafe_allow_html=True)

            for msg in st.session_state.chat_history:
                if msg["is_user"]:
                    st.markdown(f'<div class="chat-user"><strong>You:</strong> {msg["text"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-ai"><strong>AI:</strong> {msg["text"]}</div>', unsafe_allow_html=True)

            col_in, col_btn = st.columns([5, 1])
            with col_in:
                st.text_input("Your question:", key="chat_input",
                              placeholder="How can I improve my skills section?",
                              value=st.session_state.user_input)
                st.session_state.user_input = st.session_state.chat_input
            with col_btn:
                st.write("")
                if st.button("Send ✉️", key="send_button"):
                    submit_message(api_key, model)
                    st.rerun()

    # ── Tab 2 ──────────────────────────────────────────────────────────────────
    with tab2:
        if not st.session_state.resume_text:
            st.info("📋 Upload your resume in the first tab.")
        elif not st.session_state.job_title or not st.session_state.job_description:
            st.info("💼 Fill in the job details in the first tab.")
        else:
            st.markdown(section_header("❓ Ask About Your Resume", "🔍"), unsafe_allow_html=True)
            question = st.text_area("Question", placeholder="What skills should I add for this job?")
            col_q1, col_q2, col_q3 = st.columns([1, 2, 1])
            with col_q2:
                ask_button = st.button("Get Answer 🔍", key="question_btn",
                                       disabled=not (api_key and question))

            if ask_button:
                st.markdown(section_header("💬 Answer", "✨"), unsafe_allow_html=True)
                answer_placeholder = st.empty()
                ask_question(
                    st.session_state.resume_text,
                    st.session_state.job_title,
                    st.session_state.job_description,
                    question, api_key, model, answer_placeholder,
                )


if __name__ == "__main__":
    main()