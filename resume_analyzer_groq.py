import streamlit as st
import os
import tempfile
import PyPDF2
from groq import Groq
from db_setup import init_db, save_full_analysis, save_chat_message
from dotenv import load_dotenv

# Config
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=API_KEY)
init_db()

st.set_page_config(page_title="AI Resume Analyzer", page_icon="📝", layout="wide")

# --- STYLE DARK MODE COMPLET ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    
    /* Input text style */
    input { color: white !important; }
    
    /* Result Container */
    .result-container {
        background-color: #1f2937;
        color: white !important;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #374151;
        margin: 20px 0;
    }
    .result-container * { color: white !important; }

    /* Chat Bubbles */
    .chat-user {
        background-color: #4361ee;
        color: white;
        padding: 12px;
        border-radius: 15px 15px 0 15px;
        margin: 10px 0;
        text-align: right;
        margin-left: auto;
        width: fit-content;
        max-width: 80%;
    }
    .chat-ai {
        background-color: #374151;
        color: white;
        padding: 12px;
        border-radius: 15px 15px 15px 0;
        margin: 10px 0;
        width: fit-content;
        max-width: 80%;
        border-left: 4px solid #4361ee;
    }
    
    /* Button Style */
    .stButton button {
        background-color: #4361ee !important;
        color: white !important;
        width: 100%;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Session State
if "chat_history" not in st.session_state:
    st.session_state.update({
        "chat_history": [], "analysis_result": "", "resume_text": "",
        "job_title": "", "job_description": "", "current_analysis_id": None
    })

def extract_text_from_pdf(pdf_file):
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

def stream_groq(prompt, placeholder):
    full_text = ""
    try:
        with client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                stream=True,
        ) as stream:
            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                full_text += token
                placeholder.markdown(f'<div class="result-container">{full_text}▌</div>', unsafe_allow_html=True)
        placeholder.markdown(f'<div class="result-container">{full_text}</div>', unsafe_allow_html=True)
        return full_text
    except Exception as e:
        st.error(f"Error: {e}")
        return ""

def main():
    st.markdown("<h1 style='text-align: center;'>🚀 AI Resume Analyzer</h1>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📄 Resume")
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file:
            st.session_state.resume_text = extract_text_from_pdf(uploaded_file)
    with col2:
        st.subheader("💼 Job")
        st.session_state.job_title = st.text_input("Title", value=st.session_state.job_title)
        st.session_state.job_description = st.text_area("Description", value=st.session_state.job_description)

    if st.button("🔍 Analyze"):
        if st.session_state.resume_text and st.session_state.job_description:
            res_placeholder = st.empty()
            prompt = f"Analyze CV for {st.session_state.job_title}. Score/100, Strengths, Weaknesses. CV: {st.session_state.resume_text}"
            analysis = stream_groq(prompt, res_placeholder)
            st.session_state.analysis_result = analysis

            # Save to DB
            aid = save_full_analysis(1, uploaded_file.name, st.session_state.resume_text, 70, analysis[:500], "Strengths", "Gaps")
            st.session_state.current_analysis_id = aid

    if st.session_state.analysis_result:
        st.markdown("---")
        st.subheader("💬 Chat Coach")

        # Container dial l-chat bach i-bqa m-rrygel
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                div_class = "chat-user" if msg["is_user"] else "chat-ai"
                st.markdown(f'<div class="{div_class}">{msg["text"]}</div>', unsafe_allow_html=True)

        # Hna l-khana dial s-soual (Visible & Fixed)
        with st.form(key="chat_form", clear_on_submit=True):
            user_input = st.text_input("Posez une question sur votre analyse :", placeholder="Ex: Comment améliorer mon score ?")
            submit_button = st.form_submit_button(label="Envoyer ✉️")

            if submit_button and user_input:
                st.session_state.chat_history.append({"text": user_input, "is_user": True})
                ans_placeholder = st.empty()
                prompt_chat = f"Resume: {st.session_state.resume_text}\nAnalysis: {st.session_state.analysis_result}\nUser Question: {user_input}"
                answer = stream_groq(prompt_chat, ans_placeholder)

                if st.session_state.current_analysis_id:
                    save_chat_message(st.session_state.current_analysis_id, user_input, answer)

                st.session_state.chat_history.append({"text": answer, "is_user": False})
                st.rerun()

if __name__ == "__main__":
    main()