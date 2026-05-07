import sqlite3
from datetime import datetime

def init_db():
    # Hada hwa s-miya dial l-milaf li ghadi i-ban lik f IntelliJ
    conn = sqlite3.connect("resume.db")
    c = conn.cursor()

    # 1. Table Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                                                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                      email TEXT UNIQUE,
                                                      name TEXT)''')

    # 2. Table CVs
    c.execute('''CREATE TABLE IF NOT EXISTS cvs (
                                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                    user_id INTEGER,
                                                    file_name TEXT,
                                                    text_content TEXT,
                                                    upload_date DATETIME,
                                                    FOREIGN KEY(user_id) REFERENCES users(id))''')

    # 3. Table Analysis
    c.execute('''CREATE TABLE IF NOT EXISTS analysis (
                                                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                         cv_id INTEGER,
                                                         score INTEGER,
                                                         feedback TEXT,
                                                         points_forts TEXT,
                                                         points_faibles TEXT,
                                                         timestamp DATETIME,
                                                         FOREIGN KEY(cv_id) REFERENCES cvs(id))''')

    # 4. Table Chat Q&A
    c.execute('''CREATE TABLE IF NOT EXISTS chat_qa (
                                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                        analysis_id INTEGER,
                                                        question TEXT,
                                                        answer TEXT,
                                                        timestamp DATETIME,
                                                        FOREIGN KEY(analysis_id) REFERENCES analysis(id))''')

    conn.commit()
    conn.close()
    print("✅ Database 'resume.db' created with all tables!")

def save_full_analysis(user_id, file_name, text, score, feedback, forts, faibles):
    conn = sqlite3.connect("resume.db")
    c = conn.cursor()

    # Sijjel l-CV
    c.execute('INSERT INTO cvs (user_id, file_name, text_content, upload_date) VALUES (?, ?, ?, ?)',
              (user_id, file_name, text, datetime.now()))
    cv_id = c.lastrowid

    # Sijjel l-Analyse
    c.execute('''
              INSERT INTO analysis (cv_id, score, feedback, points_forts, points_faibles, timestamp)
              VALUES (?, ?, ?, ?, ?, ?)
              ''', (cv_id, score, feedback, forts, faibles, datetime.now()))

    analysis_id = c.lastrowid
    conn.commit()
    conn.close()
    return analysis_id

def save_chat_message(analysis_id, question, answer):
    conn = sqlite3.connect("resume.db")
    c = conn.cursor()
    c.execute('''
              INSERT INTO chat_qa (analysis_id, question, answer, timestamp)
              VALUES (?, ?, ?, ?)
              ''', (analysis_id, question, answer, datetime.now()))
    conn.commit()
    conn.close()

# --- HAD L-PARTIE HIYA LI K-T-CREEYI L-FILE ---
if __name__ == "__main__":
    init_db()