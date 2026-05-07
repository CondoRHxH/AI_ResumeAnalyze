from services.llm_service import call_llm


def analyze_resume(resume_text, job_title, job_description):
    prompt = f"""
You are an expert resume analyst.

Job Title: {job_title}

Job Description:
{job_description}

Resume:
{resume_text}

Return:
- Match Score
- Strengths
- Weaknesses
- Missing Skills
- Action Plan
"""
    return call_llm(prompt)


def ask_resume_question(resume_text, job_title, job_description, question):
    prompt = f"""
You are a career coach.

Resume: {resume_text}
Job: {job_title}
Job Description: {job_description}

Question: {question}
"""
    return call_llm(prompt)


def generate_resume(resume_text, job_title, job_description, analysis):
    prompt = f"""
Create optimized resume for {job_title}

Original:
{resume_text}

Job:
{job_description}

Analysis:
{analysis}
"""
    return call_llm(prompt)