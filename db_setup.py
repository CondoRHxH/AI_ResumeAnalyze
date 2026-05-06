import sqlite3

def init_db():
    conn = sqlite3.connect("resume.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS CV (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text_content TEXT,
        upload_date TEXT DEFAULT (datetime('now','localtime'))
    )
    """)

    conn.commit()
    conn.close()



from datetime import datetime

def save_cv(text_content):
    conn = sqlite3.connect("resume.db")
    c = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
        INSERT INTO CV (text_content, upload_date)
        VALUES (?, ?)
    """, (text_content, now))

    conn.commit()
    conn.close()