import json
from .store import get_db_connection, save_chat_message
from .chat import get_ai_support

class AiChatApi:
    def __init__(self, db_path):
        self.db_path = db_path
        self.headers = None

    def handle(self, path, method, headers, rfile, client_address):
        self.headers = headers

        if path == "/api/chat" and method == "POST":
            return self.handle_chat_message(rfile)
        return None

    def handle_chat_message(self, rfile):
        content_length = int(self.headers.get("Content-Length", 0))
        body = rfile.read(content_length).decode("utf-8")
        data = json.loads(body)

        user_id = data.get("user_id")
        session_id = data.get("session_id")
        user_msg = data.get("content", "")

        conn = get_db_connection(self.db_path)
        cur = conn.execute(
            "SELECT * FROM assessments WHERE session_id=? ORDER BY id DESC LIMIT 1",
            (session_id,)
        )
        row = cur.fetchone()
        assessment = dict(row) if row else None

        ai_reply = get_ai_support(user_msg, assessment)

        save_chat_message(conn, user_id, session_id, "user", user_msg)
        save_chat_message(conn, user_id, session_id, "assistant", ai_reply)

        conn.commit()
        conn.close()

        return 200, {"reply": ai_reply}