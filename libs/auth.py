from passlib.hash import argon2
import secrets
import sqlite3
from libs.db import get_conn
from datetime import datetime
def hash_password(password: str) -> str:
    return argon2.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return argon2.verify(password, password_hash)


def generate_temp_password(length: int = 10) -> str:
    return secrets.token_urlsafe(length)[:length]


def create_user(username: str, password: str, role: str = "giocatore"):
    conn = get_conn()
    try:
        # prevent duplicate usernames
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            return existing["id"]
        now = datetime.utcnow().isoformat()
        pw = hash_password(password)
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at, updated_at) VALUES (?,?,?,?,?)",
            (username, pw, role, now, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def find_user_by_username(username: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_users():
    conn = get_conn()
    rows = conn.execute("SELECT id, username, role, nickname, created_at FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_password(user_id: int, new_password: str):
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    pw = hash_password(new_password)
    conn.execute("UPDATE users SET password_hash = ?, force_password_change = 0, updated_at = ? WHERE id = ?", (pw, now, user_id))
    conn.commit()
    conn.close()


def require_login():
    import streamlit as st
    if "user" not in st.session_state:
        st.warning("Please log in")
        from views import login
        login.show()
        st.stop()


def current_user():
    import streamlit as st
    return st.session_state.get("user")


def is_admin():
    user = current_user()
    return user and user.get("role") == "admin"
