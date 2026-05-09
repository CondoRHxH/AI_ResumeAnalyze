import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "resume.db")


def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# ── Schema ─────────────────────────────────────────────────────────────────────

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Users — info extracted from the resume by AI
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        name    TEXT,
        email   TEXT UNIQUE,
        phone   TEXT
    )''')

    # CVs — the uploaded resume
    c.execute('''CREATE TABLE IF NOT EXISTS cvs (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER,
        file_name    TEXT,
        text_content TEXT,
        upload_date  DATETIME,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Analysis — fully parsed from AI markdown response
    c.execute('''CREATE TABLE IF NOT EXISTS analysis (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        cv_id          INTEGER,
        score          INTEGER,
        feedback       TEXT,
        points_forts   TEXT,
        points_faibles TEXT,
        timestamp      DATETIME,
        FOREIGN KEY(cv_id) REFERENCES cvs(id)
    )''')

    # Chat Q&A
    c.execute('''CREATE TABLE IF NOT EXISTS chat_qa (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_id INTEGER,
        question    TEXT,
        answer      TEXT,
        timestamp   DATETIME,
        FOREIGN KEY(analysis_id) REFERENCES analysis(id)
    )''')

    conn.commit()
    conn.close()
    print("✅ Database ready.")


# ── Users ──────────────────────────────────────────────────────────────────────

def save_user(name: str, email: str, phone: str) -> int:
    """
    Get-or-create pattern: if a user with this email already exists, return
    their id (and optionally update name/phone). Otherwise insert a new row.
    Falls back to insert-always when email is Unknown (no login, no identity).
    """
    conn = get_conn()
    c = conn.cursor()

    # If email is real, try to find existing user first
    if email and email != "Unknown":
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        row = c.fetchone()
        if row:
            # Update name/phone in case they changed
            c.execute(
                "UPDATE users SET name = ?, phone = ? WHERE email = ?",
                (name or "Unknown", phone or "Unknown", email)
            )
            conn.commit()
            user_id = row["id"]
            conn.close()
            return user_id

    # No match or unknown email → insert new row
    c.execute(
        "INSERT INTO users (name, email, phone) VALUES (?, ?, ?)",
        (name or "Unknown", email or "Unknown", phone or "Unknown")
    )
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return user_id


# ── CVs ────────────────────────────────────────────────────────────────────────

def save_cv(user_id: int, file_name: str, text: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO cvs (user_id, file_name, text_content, upload_date) VALUES (?, ?, ?, ?)",
        (user_id, file_name, text, datetime.now())
    )
    conn.commit()
    cv_id = c.lastrowid
    conn.close()
    return cv_id


# ── Analysis ───────────────────────────────────────────────────────────────────

def save_analysis(cv_id: int, score: int, feedback: str,
                  points_forts: str, points_faibles: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO analysis
               (cv_id, score, feedback, points_forts, points_faibles, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (cv_id, score, feedback, points_forts, points_faibles, datetime.now())
    )
    conn.commit()
    analysis_id = c.lastrowid
    conn.close()
    return analysis_id


# ── Chat ───────────────────────────────────────────────────────────────────────

def save_chat_message(analysis_id: int, question: str, answer: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO chat_qa (analysis_id, question, answer, timestamp) VALUES (?, ?, ?, ?)",
        (analysis_id, question, answer, datetime.now())
    )
    conn.commit()
    conn.close()


# ── Read helpers ───────────────────────────────────────────────────────────────

def get_all_analyses():
    conn = get_conn()
    rows = conn.execute('''
        SELECT a.id, a.score, a.feedback, a.points_forts, a.points_faibles, a.timestamp,
               c.file_name,
               u.name, u.email, u.phone
        FROM analysis a
        JOIN cvs   c ON c.id = a.cv_id
        JOIN users u ON u.id = c.user_id
        ORDER BY a.timestamp DESC
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_chat_history(analysis_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT question, answer, timestamp FROM chat_qa WHERE analysis_id = ? ORDER BY id",
        (analysis_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()