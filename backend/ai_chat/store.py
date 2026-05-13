import sqlite3

def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# 启动时自动建表（写入 auth.sqlite3）
def init_ai_chat_database(db_path):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 聊天记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        session_id TEXT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # 评估结果表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        session_id TEXT,
        stress_level INTEGER,
        avoidance INTEGER,
        self_efficacy INTEGER,
        coping INTEGER,
        scene TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()
    print("✅ AI 对话模块表已创建完成（写入 auth.sqlite3）")

# ======================
# 缺少的函数，现在加上！
# ======================
def save_chat_message(conn, user_id, session_id, role, content):
    conn.execute(
        "INSERT INTO chat_messages (user_id, session_id, role, content) VALUES (?, ?, ?, ?)",
        (user_id, session_id, role, content)
    )